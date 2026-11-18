#!/usr/bin/env bash
# Implanta a Vitrine a partir da Fábrica (ADR-0025, plano R-V, etapa V1/V2).
#
# Uso (na raiz do repositório, no WSL):
#   infrastructure/vitrine/deploy.sh               # imagens + app + Gold + catálogo
#   infrastructure/vitrine/deploy.sh --sem-dados   # só imagens e app (Gold e catálogo intactos)
#
# Etapas:
#   1. imagens locais (:dev) -> servidor, só as que mudaram, com a tag homolog-<commit>;
#   2. compose.yaml e Caddyfile -> /srv/odb/app; .env gerado no servidor na 1ª vez;
#   3. catálogo: pg_dump da Fábrica -> pg_restore numa transação só;
#   4. Gold: cópia completa para gold.new e troca no fim (a versão em uso nunca fica pela metade);
#   5. sobe tudo e confere o portal e o release ativo.
# Modelo atual: a Gold vai inteira (5,4 GB, com histórico Delta). O pacote enxuto vem na R3.
set -euo pipefail

HOST="${ODB_VITRINE_HOST:?defina o destino SSH em ODB_VITRINE_HOST}"
LAN_IP="${ODB_VITRINE_IP:?defina o IP da Vitrine em ODB_VITRINE_IP}"
REMOTE=/srv/odb
DADOS=1
[ "${1:-}" = "--sem-dados" ] && DADOS=0

cd "$(git rev-parse --show-toplevel)"
TAG="homolog-$(git rev-parse --short HEAD)"
LOG="deploy-$(date -u +%Y%m%dT%H%M%SZ).log"
remoto() { ssh -o BatchMode=yes "$HOST" "$@"; }
compose_remoto() { remoto "cd $REMOTE/app && docker compose --env-file .env $*"; }
passo() { printf '\n==> %s\n' "$*"; }

passo "Vitrine $HOST ($LAN_IP), tag $TAG"
[ -z "$(git status --porcelain -- apps packages configs infrastructure)" ] \
  || echo "aviso: há mudanças não commitadas; as imagens :dev podem não corresponder a $TAG"

passo "1/5 Imagens"
for img in odb portal postgres; do
  local_id=$(docker image inspect -f '{{.Id}}' "opendatabrasil/$img:dev")
  # A última imagem recebida fica como :dev no servidor; só envia se ela mudou.
  remoto_id=$(remoto "docker image inspect -f '{{.Id}}' opendatabrasil/$img:dev 2>/dev/null" || true)
  if [ "$local_id" = "$remoto_id" ]; then
    echo "  $img: já no servidor"
  else
    echo "  $img: enviando $(docker image inspect -f '{{.Size}}' "opendatabrasil/$img:dev" | numfmt --to=iec)"
    docker save "opendatabrasil/$img:dev" | gzip -1 | remoto "gzip -d | docker load -q >/dev/null"
  fi
  remoto "docker tag opendatabrasil/$img:dev opendatabrasil/$img:$TAG"
  echo "$img $local_id" >> "/tmp/$LOG"
done

passo "2/5 Arquivos da aplicação"
scp -q infrastructure/vitrine/compose.yaml infrastructure/vitrine/Caddyfile "$HOST:$REMOTE/app/"
rsync -a --delete infrastructure/vitrine/otel/ "$HOST:$REMOTE/app/otel/"
remoto "bash -s" <<EOF
set -euo pipefail
cd $REMOTE/app
if [ ! -f .env ]; then
  umask 077
  senha() { openssl rand -base64 30 | tr -d '/+=' | cut -c1-32; }
  cat > .env <<ENV
ODB_IMAGE_TAG=$TAG
ODB_LAN_IP=$LAN_IP
ODB_API_CORS_ORIGINS=["http://$LAN_IP"]
POSTGRES_USER=odb_admin
POSTGRES_PASSWORD=\$(senha)
POSTGRES_DB=odb
ODB_OWNER_PASSWORD=\$(senha)
ODB_PIPELINE_PASSWORD=\$(senha)
ODB_READER_PASSWORD=\$(senha)
ODB_API_WORKERS=2
ODB_API_DUCKDB_MEMORY=1GB
ODB_LOG_LEVEL=INFO
ENV
  echo "  .env criado com senhas aleatórias"
fi
sed -i "s/^ODB_IMAGE_TAG=.*/ODB_IMAGE_TAG=$TAG/" .env
grep -q "^GRAFANA_ADMIN_PASSWORD=" .env || echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-24)" >> .env
# ADR-0027: papéis do banco de métricas (senhas geradas uma vez, nunca impressas).
grep -q "^ODB_METRICS_WRITER_PASSWORD=" .env || echo "ODB_METRICS_WRITER_PASSWORD=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-32)" >> .env
grep -q "^ODB_METRICS_READER_PASSWORD=" .env || echo "ODB_METRICS_READER_PASSWORD=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-32)" >> .env
EOF
compose_remoto "up -d --wait postgres" >/dev/null
# Banco de métricas (ADR-0027): idempotente; cria na 1ª vez e reaplica senhas e permissões.
compose_remoto "exec -T postgres bash /docker-entrypoint-initdb.d/02-metrics-database.sh" >/dev/null
# As métricas só existem na Vitrine: backup antes de trocar qualquer coisa.
infrastructure/vitrine/backup-metrics.sh

if [ "$DADOS" = 1 ]; then
  passo "3/5 Catálogo"
  # shellcheck disable=SC2016  # as variáveis expandem dentro do contêiner
  docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    | remoto "cd $REMOTE/app && docker compose --env-file .env exec -T postgres sh -c 'pg_restore -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --clean --if-exists --single-transaction'"
  echo "  catálogo restaurado"

  passo "4/5 Gold"
  remoto "rm -rf $REMOTE/gold.new && mkdir -m 0750 $REMOTE/gold.new"
  docker run --rm -v opendatabrasil_lake_gold:/g:ro alpine:3.20 tar -C /g -cf - . \
    | gzip -1 | remoto "gzip -d | tar -C $REMOTE/gold.new -xf -"
  local_n=$(docker run --rm -v opendatabrasil_lake_gold:/g:ro alpine:3.20 sh -c 'find /g -type f | wc -l')
  remoto_n=$(remoto "find $REMOTE/gold.new -type f | wc -l")
  [ "$local_n" = "$remoto_n" ] || { echo "ERRO: Gold incompleta ($remoto_n de $local_n arquivos)"; exit 1; }
  compose_remoto "stop api" >/dev/null 2>&1 || true
  remoto "cd $REMOTE && rm -rf gold.prev && { [ -d gold ] && mv gold gold.prev || true; } && mv gold.new gold"
  echo "  $remoto_n arquivos; versão anterior em gold.prev"
fi

passo "5/5 Subindo"
compose_remoto "up -d --wait --remove-orphans" >/dev/null
compose_remoto "up -d --wait --force-recreate api portal caddy" >/dev/null
compose_remoto "ps --format '{{.Service}}: {{.Status}}'"
release=$(curl -fsS "http://$LAN_IP/odb-api/release" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("release_id"))')
status=$(curl -fsS -o /dev/null -w '%{http_code}' "http://$LAN_IP/")
echo "  portal: HTTP $status | release ativo: $release"
scp -q "/tmp/$LOG" "$HOST:$REMOTE/logs/$LOG" && rm -f "/tmp/$LOG"
echo "Pronto: http://$LAN_IP/"

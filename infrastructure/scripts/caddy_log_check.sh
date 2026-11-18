#!/usr/bin/env bash
# Prova que o log de acesso da Vitrine não grava IP nem dado fino (ADR-0027).
#
# Sobe o Caddyfile REAL da Vitrine (mesma imagem fixada no compose.yaml) na frente de um
# "portal" de mentira, manda requisições com IP, cookie, credencial, cidade, CEP e
# coordenadas, e confere:
#   1. nenhuma linha do access.log contém o IP do cliente, o IP forjado nos cabeçalhos,
#      cookie, credencial ou localização mais fina que a UF;
#   2. o log tem o que a contagem precisa (país, UF, rota, indicador e formato do download);
#   3. o portal não recebe cidade, CEP, coordenadas nem o CF-Connecting-IP;
#   4. (com Python do projeto) o agregador conta 1 visualização, 1 abertura e 1 download.
#
# Uso: bash infrastructure/scripts/caddy_log_check.sh
#      PYTHON="uv run python" bash infrastructure/scripts/caddy_log_check.sh   (no CI)
# Precisa só do Docker. Sai com código diferente de 0 em qualquer falha.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
CADDYFILE="$ROOT/infrastructure/vitrine/Caddyfile"
IMAGE=$(sed -n 's/^ *image: \(caddy@sha256:[0-9a-f]*\).*/\1/p' "$ROOT/infrastructure/vitrine/compose.yaml")
[ -n "$IMAGE" ] || { echo "imagem do Caddy não encontrada no compose.yaml" >&2; exit 1; }
PYTHON=${PYTHON:-"$ROOT/.venv/bin/python"}

NAME="odb-caddy-check-$$"
WORK=$(mktemp -d)
cleanup() {
  docker rm -f "$NAME-proxy" "$NAME-portal" >/dev/null 2>&1 || true
  docker network rm "$NAME" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

# IP forjado: faixa de documentação (RFC 5737), nunca de alguém.
FAKE_IP=203.0.113.77
cat > "$WORK/portal.Caddyfile" <<'EOF'
{
	admin off
}
:3000 {
	@exp path /odb-api/exports
	header @exp X-Odb-Kpi "populacao_teste"
	header @exp X-Odb-Format "csv"
	respond "cidade=[{http.request.header.Cf-Ipcity}] cep=[{http.request.header.Cf-Postal-Code}] lat=[{http.request.header.Cf-Iplatitude}] cfip=[{http.request.header.Cf-Connecting-Ip}]" 200
}
EOF
mkdir -m 0777 "$WORK/logs"

docker network create "$NAME" >/dev/null
docker run -d --name "$NAME-portal" --network "$NAME" --network-alias portal \
  -v "$WORK/portal.Caddyfile:/etc/caddy/Caddyfile:ro" "$IMAGE" >/dev/null
docker run -d --name "$NAME-proxy" --network "$NAME" -e ODB_ROBOTS_TAG=noindex \
  -v "$CADDYFILE:/etc/caddy/Caddyfile:ro" -v "$WORK/logs:/var/log/caddy" "$IMAGE" >/dev/null

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/140.0"
client() {
  # Cliente na mesma rede (busybox wget da própria imagem), com todos os cabeçalhos sensíveis.
  docker run --rm --network "$NAME" "$IMAGE" wget -q -O - -U "$UA" \
    --header "CF-Connecting-IP: $FAKE_IP" \
    --header "X-Forwarded-For: $FAKE_IP" \
    --header "Cookie: sessao=segredo-do-cookie" \
    --header "Authorization: Bearer credencial-secreta" \
    --header "Cf-Ipcountry: BR" \
    --header "Cf-Region-Code: SP" \
    --header "Cf-Region: Sao Paulo" \
    --header "Cf-Ipcity: Campinas" \
    --header "Cf-Postal-Code: 13083-000" \
    --header "Cf-Iplatitude: -22.81690" \
    --header "Cf-Iplongitude: -47.06980" \
    --header "Cf-Metro-Code: 99999" \
    --header "Referer: https://www.exemplo.org/busca?q=termo-privado" \
    "$@"
}

for _ in $(seq 1 50); do
  docker run --rm --network "$NAME" "$IMAGE" wget -q -O /dev/null "http://$NAME-proxy/_odb/tick" \
    2>/dev/null && break
  sleep 0.2
done
BODY=$(client "http://$NAME-proxy/dashboard?kpi=populacao_teste")
client --post-data '{"kpi_id":"populacao_teste","format":"csv"}' \
  "http://$NAME-proxy/odb-api/exports" >/dev/null
# O IP real do cliente na rede de teste (o que o Caddy veria como remote_ip).
CLIENT_NET=$(docker network inspect "$NAME" -f '{{range .IPAM.Config}}{{.Subnet}}{{end}}')
CLIENT_PREFIX=${CLIENT_NET%.*}
sleep 1
LOG=$(docker exec "$NAME-proxy" cat /var/log/caddy/access.log)

fail=0
check_absent() {
  if grep -qiF -- "$1" <<<"$LOG"; then
    echo "FALHA: o log contém $2 ($1)" >&2
    fail=1
  fi
}
check_absent "$FAKE_IP" "o IP forjado nos cabeçalhos"
check_absent "$CLIENT_PREFIX." "o IP do cliente na rede de teste"
check_absent "remote_ip" "o campo remote_ip"
check_absent "client_ip" "o campo client_ip"
check_absent "segredo-do-cookie" "o cookie"
check_absent "credencial-secreta" "a credencial"
check_absent "Campinas" "a cidade"
check_absent "13083" "o CEP"
check_absent "22.8169" "a latitude"
check_absent "47.0698" "a longitude"
check_absent "99999" "o metro code"
check_absent '"headers"' "cabeçalhos da requisição"
check_absent "resp_headers" "cabeçalhos da resposta"

check_present() {
  if ! grep -qF -- "$1" <<<"$LOG"; then
    echo "FALHA: falta no log $2 ($1)" >&2
    fail=1
  fi
}
check_present '"country":"BR"' "o país"
check_present '"region":"SP"' "a UF"
check_present '"uri":"/dashboard?kpi=populacao_teste"' "a rota com o indicador"
check_present '"export_kpi":"populacao_teste"' "o indicador do download"
check_present '"export_format":"csv"' "o formato do download"

if [ "$BODY" != "cidade=[] cep=[] lat=[] cfip=[]" ]; then
  echo "FALHA: o portal recebeu localização fina ou o CF-Connecting-IP: $BODY" >&2
  fail=1
fi

if [ -x "${PYTHON%% *}" ] || command -v "${PYTHON%% *}" >/dev/null 2>&1; then
  COUNTS=$(printf '%s\n' "$LOG" | $PYTHON -c '
import sys
from collections import Counter
from odb_cli.access_log import aggregate
counts, _, invalid = aggregate(sys.stdin.read().splitlines())
by = Counter()
for k, n in counts.items():
    by[(k.event, k.country, k.uf, k.kpi_id, k.format, k.referrer_domain)] += n
print(sorted(by.items()), invalid)
')
  EXPECTED="[(('download', 'BR', 35, 'populacao_teste', 'csv', ''), 1), (('kpi_open', 'BR', 35, 'populacao_teste', '', ''), 1), (('page_view', 'BR', 35, '', '', 'www.exemplo.org'), 1)] 0"
  if [ "$COUNTS" != "$EXPECTED" ]; then
    echo "FALHA: contagem do agregador: $COUNTS" >&2
    fail=1
  fi
else
  echo "aviso: sem Python do projeto ($PYTHON); conferência do agregador pulada" >&2
fi

if [ "$fail" -ne 0 ]; then
  echo "--- access.log ---" >&2
  echo "$LOG" >&2
  exit 1
fi
echo "ok: $(wc -l <<<"$LOG") linhas no log, nenhuma com IP, cookie, credencial ou local fino"

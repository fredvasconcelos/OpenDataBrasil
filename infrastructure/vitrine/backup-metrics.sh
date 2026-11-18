#!/usr/bin/env bash
# Backup do banco de métricas de acesso da Vitrine (ADR-0027), rodado da Fábrica.
#
# O odb_metrics é o único dado que só existe na Vitrine: o catálogo e a Gold vêm da
# Fábrica a cada deploy. Por isso o dump fica no servidor E é copiado para a Fábrica
# (cópia fora da Vitrine, CLAUDE.md §26.1).
#
# Uso (na raiz do repositório):  infrastructure/vitrine/backup-metrics.sh
#   - servidor: /srv/odb/backups/metrics/odb_metrics-<instante>.dump (mantém 30);
#   - Fábrica:  ${ODB_BACKUP_DIR:-./backups}/vitrine-metrics/ (mantém 90).
# O deploy.sh chama este script antes de subir a nova versão.
# Restauração: docs/runbooks/vitrine.md, seção "Métricas de acesso".
set -euo pipefail

HOST="${ODB_VITRINE_HOST:?defina o destino SSH em ODB_VITRINE_HOST}"
REMOTE=/srv/odb
cd "$(git rev-parse --show-toplevel)"
DEST="${ODB_BACKUP_DIR:-./backups}/vitrine-metrics"
NAME="odb_metrics-$(date -u +%Y%m%dT%H%M%SZ).dump"

ssh -o BatchMode=yes "$HOST" "bash -s" <<REMOTO
set -euo pipefail
mkdir -p -m 0750 $REMOTE/backups/metrics
cd $REMOTE/app
# shellcheck disable=SC2016
# </dev/null: sem ele o exec consome o resto deste script, que chega pela entrada padrão.
docker compose --env-file .env exec -T postgres sh -c 'pg_dump -U "\$POSTGRES_USER" -d odb_metrics -Fc' \
  </dev/null > $REMOTE/backups/metrics/$NAME.tmp
mv $REMOTE/backups/metrics/$NAME.tmp $REMOTE/backups/metrics/$NAME
ls -1t $REMOTE/backups/metrics/odb_metrics-*.dump | tail -n +31 | xargs -r rm -f
REMOTO

mkdir -p "$DEST"
scp -q "$HOST:$REMOTE/backups/metrics/$NAME" "$DEST/$NAME"
# Confere que o dump abre e tem a tabela das somas (lista o conteúdo, sem restaurar).
docker compose exec -T postgres pg_restore --list < "$DEST/$NAME" | grep -q "TABLE public access_daily" \
  || { echo "ERRO: dump sem access_daily: $DEST/$NAME" >&2; exit 1; }
ls -1t "$DEST"/odb_metrics-*.dump | tail -n +91 | xargs -r rm -f
echo "métricas: $DEST/$NAME ($(du -h "$DEST/$NAME" | cut -f1))"

#!/usr/bin/env bash
# Backup da Bronze e do catálogo PostgreSQL (runbook: docs/runbooks/backup.md).
#
# Só a Bronze e o catálogo entram no backup: a Silver e a Gold são reconstruídas a
# partir deles com o código do Git (`odb silver build`, `odb gold build`).
#
# Destino: ODB_BACKUP_DIR (no .env ou no ambiente); padrão: ./backups na raiz do
# projeto, fora do Git. Pode apontar para outro disco ou para uma montagem de
# armazenamento de objetos, sem mudar o script.
#
# Uso:
#   infrastructure/scripts/backup.sh            # Bronze (incremental) + catálogo
#   infrastructure/scripts/backup.sh --verify   # também confere o SHA-256 de cada
#                                               # artefato contra o catálogo
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

env_value() {  # lê uma variável do .env sem executar o arquivo
  [ -f .env ] || return 0
  { grep -E "^$1=" .env || true; } | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//'
}

VERIFY=0
for arg in "$@"; do
  case "$arg" in
    --verify) VERIFY=1 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $arg" >&2; exit 2 ;;
  esac
done

DEST="${ODB_BACKUP_DIR:-$(env_value ODB_BACKUP_DIR)}"
DEST="${DEST:-$ROOT/backups}"
case "$DEST" in /*) ;; *) DEST="$ROOT/$DEST" ;; esac
KEEP="${ODB_BACKUP_KEEP_DUMPS:-$(env_value ODB_BACKUP_KEEP_DUMPS)}"
KEEP="${KEEP:-14}"
PROJECT="${COMPOSE_PROJECT_NAME:-opendatabrasil}"
IMAGE="${ODB_BACKUP_IMAGE:-opendatabrasil/odb:${ODB_IMAGE_TAG:-dev}}"
PG_USER="$(env_value POSTGRES_USER)"; PG_USER="${PG_USER:-postgres}"
PG_DB="$(env_value POSTGRES_DB)"; PG_DB="${PG_DB:-odb}"
STAMP="$(date -u +%Y%m%dt%H%M%Sz)"

mkdir -p "$DEST/bronze" "$DEST/catalog"
echo "destino: $DEST"

# 1. Catálogo: dump no formato custom (pg_restore), com retenção dos últimos $KEEP.
DUMP="$DEST/catalog/odb-$STAMP.dump"
docker compose exec -T postgres pg_dump -U "$PG_USER" -d "$PG_DB" -Fc > "$DUMP.part"
mv "$DUMP.part" "$DUMP"
echo "catálogo: $(basename "$DUMP") ($(du -h "$DUMP" | cut -f1))"
ls -1t "$DEST"/catalog/odb-*.dump | tail -n +"$((KEEP + 1))" | xargs -r rm --

# Lista dos artefatos guardados e seus SHA-256, lida antes da cópia (ver o passo 3).
LIST="$DEST/catalog/checksums-$STAMP.txt"
trap 'rm -f "$LIST"' EXIT
if [ "$VERIFY" = 1 ]; then
  docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -Atc \
    "SELECT checksum_sha256 || '  ' || replace(storage_uri, 'file:///lakehouse/bronze/', '')
       FROM operations.bronze_artifact WHERE ingestion_status = 'stored'" > "$LIST"
fi

# 2. Bronze: cópia incremental. Os artefatos são imutáveis (§6.5), então o que já
#    está no destino não é copiado de novo nem sobrescrito.
docker run --rm --user "$(id -u):$(id -g)" \
  -v "${PROJECT}_lake_bronze:/src:ro" -v "$DEST/bronze:/dst" \
  --entrypoint sh "$IMAGE" -c 'cp -a --no-clobber /src/. /dst/ && \
    echo "bronze: $(find /src -type f | wc -l) arquivos na origem, $(find /dst -type f | wc -l) no backup ($(du -sh /dst | cut -f1))"'

# 3. Conferência opcional: SHA-256 de cada artefato contra o catálogo. A lista foi
#    lida antes da cópia; artefatos gravados depois (carga em andamento) entram na
#    conferência do próximo backup.
if [ "$VERIFY" = 1 ]; then
  docker run --rm --user "$(id -u):$(id -g)" -v "$DEST/bronze:/dst:ro" -v "$LIST:/list:ro" \
    -w /dst --entrypoint sh "$IMAGE" -c 'sha256sum --quiet -c /list && echo "conferência: $(wc -l < /list) artefatos com o SHA-256 do catálogo"'
fi

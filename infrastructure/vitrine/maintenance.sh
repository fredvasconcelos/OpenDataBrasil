#!/usr/bin/env bash
# Alterna apenas o marcador local lido pelo Caddy, sem rede ou reinício.
set -euo pipefail
DIRECTORY="$(cd "$(dirname "$0")" && pwd)/maintenance"
case "${1:-status}" in
  on)
    umask 022
    MARKER=$(mktemp "$DIRECTORY/.enabled.XXXXXX")
    printf 'Manutenção ativada em %s\n' "$(date -u +%FT%TZ)" > "$MARKER"
    mv "$MARKER" "$DIRECTORY/enabled"
    echo 'Manutenção ativada.'
    ;;
  off)
    rm -f -- "$DIRECTORY/enabled"
    echo 'Manutenção desativada.'
    ;;
  status)
    if [ -f "$DIRECTORY/enabled" ]; then echo 'Manutenção ativa.'; else echo 'Operação normal.'; fi
    ;;
  *) echo 'Uso: bash maintenance.sh on|off|status' >&2; exit 2 ;;
esac

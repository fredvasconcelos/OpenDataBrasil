#!/usr/bin/env bash
# Amostra CPU, memória e carga do servidor da Vitrine enquanto um teste roda.
# Uso: tests/performance/k6/amostrar.sh <arquivo-de-saída> <segundos>
set -euo pipefail
saida="$1"; duracao="$2"; host="${ODB_VITRINE_HOST:?defina o destino SSH em ODB_VITRINE_HOST}"
fim=$((SECONDS + duracao))
echo "ts,servico,cpu_pct,mem_mib,load1" > "$saida"
while [ $SECONDS -lt $fim ]; do
  ssh -o BatchMode=yes "$host" 'l=$(cut -d" " -f1 /proc/loadavg); docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" | sed "s/odb-vitrine-//; s/-1,/,/; s/%//; s/ \/.*//" | while IFS=, read -r n c m; do v=${m%%[A-Za-z]*}; case "$m" in *GiB) v=$(awk "BEGIN{print $v*1024}");; *KiB) v=$(awk "BEGIN{print $v/1024}");; esac; echo "$(date -u +%H:%M:%S),$n,$c,$v,$l"; done' >> "$saida" || true
  sleep 5
done

# Runbook: ingestão para a Bronze

Todos os comandos rodam no worker:
`docker compose --profile data run --rm worker <comando>`.

## Operação normal

```bash
odb sources list                        # datasets configurados
odb sources health                      # disponibilidade das fontes (sai com 1 se alguma falhar)
odb ingest plan ibge-sidra-6579         # requisições previstas, sem baixar dados
odb ingest run --all                    # todos os datasets habilitados
odb ingest run ibge-sidra-6579 --full   # ignora o watermark e baixa todas as partições
odb ingest status [dataset] --limit 20  # últimas ingestões e contagens por estado
```

- O código de saída é `1` quando algum dataset falha. Os demais são processados
  normalmente.
- Toda execução fica em `operations.pipeline_run` (`command = 'ingest.run'`).

## Estados de artefato

| Estado | Significado | Bytes gravados |
|---|---|---|
| `stored` | conteúdo novo e válido | sim |
| `reused` | conteúdo idêntico a um `stored` existente (`reused_from`) | não |
| `not_modified` | servidor respondeu 304 | não |
| `quarantined` | conteúdo inválido, preservado em `…/quarantine/…` | sim (na quarentena) |
| `failed` | erro HTTP ou de rede após as tentativas | não |

## Investigar uma falha

```sql
-- últimas ingestões com erro
SELECT ingestion_id, dataset_id, started_at, error
FROM operations.ingestion WHERE status = 'failed' ORDER BY started_at DESC LIMIT 10;

-- artefatos problemáticos de uma ingestão
SELECT partition_key, ingestion_status, http_status, error, storage_uri, validation
FROM operations.bronze_artifact
WHERE ingestion_id = '<id>' AND ingestion_status IN ('failed', 'quarantined');
```

- **`quarantined`:** abra o arquivo em `storage_uri` e leia
  `validation.errors`. Uma resposta SIDRA com apenas o cabeçalho indica
  período inexistente ou consulta vazia. Se a fonte mudou de formato, ajuste o
  conector e os testes. Não edite o arquivo.
- **`failed` com 429/503:** a fonte está limitando o ritmo ou indisponível.
  Aguarde e reexecute. Se for recorrente, aumente `min_interval_s` em
  `configs/sources/*.toml`. Nunca reduza abaixo do padrão para "acelerar".
- **Disco:** a ingestão é bloqueada a partir de `ODB_DISK_BLOCK_PERCENT` (90%).
  Veja `odb doctor`.

Uma ingestão com falha **não avança o watermark**: a próxima execução refaz o
plano completo, e a deduplicação evita bytes repetidos.

## Verificar a integridade da Bronze

```bash
# no host: lista checksum + caminho dos artefatos stored
docker compose exec -T postgres psql -U odb_owner -d odb -At -F ' ' -c \
  "SELECT checksum_sha256, replace(storage_uri,'file://','') FROM operations.bronze_artifact WHERE ingestion_status='stored'" > sums.txt
docker compose --profile data run --rm -T -v "$PWD/sums.txt:/tmp/sums.txt:ro" worker \
  sh -c 'awk "{print \$1\"  \"\$2}" /tmp/sums.txt | sha256sum -c --quiet && echo OK'
```

## Regras

- Não apague nem edite arquivos da Bronze: eles são somente leitura e
  referenciados pelo catálogo.
- Novos datasets entram por configuração (`configs/sources/*.toml`), com
  identificadores verificados na fonte e documentados em `docs/data_catalog/`.
- Não contorne autenticação, CAPTCHA ou limites de taxa (§7.3).

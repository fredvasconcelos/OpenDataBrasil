# Matriz de compatibilidade

**Validada em:** 2026-11-03, por execução (CLAUDE.md §4.3)
**Evidência:** `tests/contracts/delta_interop/` (13 contratos) + suíte completa
(105 testes na Fase 1; 165 na Fase 2) executada no host (Ubuntu 24.04 / WSL2) e no container `tests`.

Regra de seleção: versão estável publicada há pelo menos 14 dias na data da
seleção. Todas as dependências transitivas estão fixadas em `uv.lock`.

## Runtime

| Componente | Versão | Origem | Observação |
|---|---|---|---|
| Python | 3.12.16 (container) / 3.12.3 (host) | `python:3.12-slim-bookworm@sha256:e697c818…` | |
| uv | 0.13.2 | `ghcr.io/astral-sh/uv:0.13.2@sha256:b9fddcde…` | fixado em `tool.uv.required-version` |
| PostgreSQL | 17.11 | `postgres:17-bookworm@sha256:839fbb5a…` | |
| Arquitetura | linux/amd64 | | arm64 não testado |

## Bibliotecas

| Pacote | Versão | Publicada em | Motivo da escolha |
|---|---|---|---|
| polars | 1.44.2 | 2026-09-09 | última 1.x. A 2.0.0 (2026-10-06) é major recente (ADR-0002) |
| deltalake (delta-rs) | 1.6.6 | 2026-09-24 | |
| pyarrow | 26.0.0 | 2026-10-09 | exigido por `polars.write_delta` |
| duckdb | 1.5.6 | 2026-09-28 | a 2.0.0 (2026-10-21) tem menos de 14 dias (ADR-0002) |
| extensão DuckDB `delta` | 6059958 | repositório oficial de extensões | pré-instalada na imagem em `/opt/duckdb/extensions` |
| sqlalchemy | 2.0.55 | 2026-10-16 | |
| alembic | 1.20.0 | 2026-09-11 | |
| psycopg[binary] | 3.3.6 | 2026-09-18 | |
| pydantic / pydantic-settings | 2.14.1 / 2.16.0 | 2026-10 | |
| typer | 0.27.3 | 2026-10-06 | |
| httpx | 0.28.1 | 2024-12-06 | cliente HTTP da ingestão (Fase 2), via `MockTransport` nos testes |
| ruff / mypy / pytest / pytest-cov | 0.17.1 / 2.4.0 / 9.1.1 / 7.1.0 | | desenvolvimento |

## Protocolo Delta (perfil conservador, ADR-0001)

| Item | Valor |
|---|---|
| `minReaderVersion` / `minWriterVersion` | 1 / 2 |
| Table features | nenhuma |
| Timestamps | `timestamp` (UTC). `timestampNtz` é proibido |
| Recursos proibidos | deletion vectors, column mapping, type widening, V2 checkpoints, liquid clustering, row tracking, CDF |

## Resultados dos contratos de interoperabilidade

| Recurso | delta-rs (escrita) | Polars (leitura) | DuckDB (leitura) | Teste |
|---|---|---|---|---|
| Criação de tabela (protocolo 1/2) | ✅ | ✅ | ✅ | `test_polars_write_creates_conservative_protocol` |
| Tipos: Int64, String, Date, Decimal(18,4), Float64, Boolean, Datetime UTC | ✅ | ✅ (schema idêntico) | ✅ (`TIMESTAMP WITH TIME ZONE`) | `test_types_roundtrip_polars_and_duckdb` |
| Append / overwrite com histórico | ✅ | ✅ `scan_delta(version=n)` | ✅ `delta_scan(uri, version => n)` | `test_append_and_version_reads_agree` |
| Versão inexistente gera erro | n/a | ✅ | ✅ `IOException` | `test_nonexistent_version_is_an_error` |
| URIs `file:///` | ✅ | ✅ | ✅ | `test_file_uri_accepted_by_all_engines` |
| Checkpoint + time travel | ✅ `create_checkpoint` | ✅ | ✅ | `test_checkpoint_then_time_travel` |
| Merge (upsert), protocolo inalterado | ✅ `DeltaTable.merge` | ✅ | ✅ | `test_merge_upsert_keeps_protocol` |
| Evolução de schema (só com `schema_mode=merge`) | ✅ | ✅ (v0 mantém schema antigo) | ✅ | `test_schema_evolution_requires_explicit_merge` |
| Particionamento + filtro | ✅ | ✅ | ✅ | `test_partitioned_table_filter_pushdown` |
| CSV (`;`, vírgula decimal, zeros à esquerda) | n/a | ✅ | ✅ | `test_csv_read_polars_and_duckdb` |

## Comportamentos de risco documentados (com teste)

| Comportamento | Consequência na arquitetura |
|---|---|
| Datetime sem fuso gera `timestampNtz` (reader 3 / writer 7) | `validate_schema` rejeita antes da escrita |
| `Categorical` provoca panic no writer do delta-rs | tipo fora da lista permitida |
| `UInt64` gravado silenciosamente como `long` | inteiros sem sinal são rejeitados |
| `Time`, `Null` e `Duration` não são suportados pelo Delta | rejeitados com mensagem explícita |
| **A extensão `delta` do DuckDB escreve via `ATTACH` + `INSERT`** | adaptador sem `ATTACH`, apenas `SELECT`, sandbox e Gold `:ro` (ADR-0005) |
| `enable_external_access=false` não impede escrita dentro de `allowed_directories` | o sandbox sozinho não basta (ADR-0005) |

## Como revalidar

```bash
uv run pytest -m interop -v                          # host
docker compose --profile test run --rm tests         # container (suíte completa)
```

Qualquer atualização de dependência exige rodar os dois comandos e atualizar
esta matriz.

## Pendências de compatibilidade

- Leitura das tabelas por Databricks/Fabric ainda não foi testada, porque não
  há ambiente gratuito disponível. O perfil 1/2 é o mais amplamente suportado,
  mas não está validado nesses motores.
- Polars 2.x e DuckDB 2.x serão avaliados em ADR próprio.

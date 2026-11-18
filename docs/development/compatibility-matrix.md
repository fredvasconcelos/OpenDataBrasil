# Matriz de compatibilidade

**Validada em:** 2026-11-03, por execução (CLAUDE.md §4.3)
**Evidência:** `tests/contracts/delta_interop/` (13 contratos) + suíte completa
(105 testes na Fase 1; 165 na Fase 2; 212 na Fase 3; 251 na Fase 4; 268 na etapa 5.0 da Fase 5; 290 com a API) executada no host (Ubuntu 24.04 / WSL2) e no container `tests`.

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
| fastexcel | 0.21.0 | 2026-08-19 | leitura de ODS/XLS (calamine) via `polars.read_excel` (Fase 3) |
| shapely | 2.2.0 (GEOS 3.14.1) | 2026-10-07 | malhas territoriais: WKB, `coverage_simplify` (preserva divisas), `union_all`, `make_valid` (Fase 5) |
| pyshp | 3.1.6 | 2026-07-25 | leitura de shapefile em Python puro, sem GDAL (Fase 5) |
| numpy | 2.5.4 | 2026-10-10 | dependência do shapely; arredondamento das coordenadas (Fase 5) |
| fastapi | 0.161.1 | 2026-10-22 | API (Fase 5) |
| starlette | 1.9.0 | 2026-10-18 | transitiva do FastAPI, fixada (a 1.10.0 tinha menos de 14 dias) |
| opentelemetry-api | 1.45.1 | 2026-10-06 | transitiva do FastAPI, fixada (a 1.45.2 tinha menos de 14 dias) |
| uvicorn | 0.54.0 | 2026-09-25 | servidor ASGI da API |
| xlsxwriter | 3.3.0 | 2026-10-22 | exportação XLSX (`polars.write_excel`) |
| anyio | 4.15.1 | 2026-09-05 | transitiva do httpx e do Starlette. **Correção:** o lock da Fase 2 tinha a 4.16.0 (2026-11-01), contra a regra dos 14 dias. Agora fixada em `tool.uv.constraint-dependencies` |
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
| Overwrite com predicado (`replace_where`), protocolo inalterado | ✅ | ✅ | ✅ | `test_predicate_overwrite_keeps_protocol_and_history` |
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

## Observações da Fase 5

- O `starlette.testclient` 1.9 avisa que o `httpx` está depreciado em favor do
  `httpx2`. O aviso é filtrado na configuração do pytest, e o `httpx` 0.28.1
  continua fixado. Trocar pelo `httpx2` é uma decisão à parte.

## Portal (Fase 5)

Seleção pela mesma regra dos 14 dias, inclusive nas transitivas
(`npm install --before=2026-10-23T23:59:59Z`, data de seleção 2026-11-06).

| Componente | Versão | Publicada em | Observação |
|---|---|---|---|
| Node.js | 24.22.1 (LTS "Krypton") | 2026-10-20 | `node:24.22.1-bookworm-slim@sha256:be8204d4…`; a linha 26 ainda não era LTS |
| npm | 11.19.1 | (da imagem) | |
| next | 16.4.3 | 2026-10-23 | `output: "standalone"` |
| react / react-dom | 19.3.1 | 2026-10-14 | |
| typescript | 5.9.3 | 2025-09-30 | o 6.x é recusado pelo `openapi-typescript` 7 (peer `^5`); o 7.x (compilador nativo) muda a API JS |
| d3-geo / d3-scale / d3-shape / d3-array / d3-format | 3.1.1 / 4.0.2 / 3.2.0 / 3.2.4 / 3.1.2 | 2021–2026 | os pacotes d3 ganharam versões novas em 2026-11-03, menos de 14 dias antes da seleção. O `d3-scale-chromatic` saiu com o design system, que define as cores por tokens |
| d3-zoom / d3-selection / d3-transition | 3.0.0 / 3.0.0 / 3.0.1 | 2021–2022 | zoom do mapa (revisão da beta). As versões 3.0.1 / 3.0.1 / 3.0.2 saíram em 2026-11-03 e ficaram de fora pela regra dos 14 dias. Seleção em 2026-11-06 com `--before=2026-10-23T23:59:59Z` |
| next-intl | 4.14.9 | 2026-10-02 | só pt-BR no MVP |
| openapi-typescript | 7.13.0 | 2026-02-11 | tipos gerados do contrato |
| vitest / jsdom / @vitejs/plugin-react | 4.1.12 / 30.1.3 / 6.1.2 | 2026-10 | |
| @testing-library/react / dom | 16.3.3 / 10.4.2 | 2026-08/09 | |
| eslint / eslint-config-next | 10.13.0 / 16.4.3 | 2026-10 | |
| @playwright/test | 1.64.1 | 2026-10-14 | imagem `mcr.microsoft.com/playwright@sha256:2f05f8a7…` (v1.64.1-noble) |

- Fonte Nunito (design system) por `next/font/google`, que faz parte do `next`
  e não acrescenta dependência. Os arquivos são baixados no `next build` e
  servidos pelo próprio portal, sem chamada ao Google no navegador. O build
  precisa de rede; sem ela, troque por `next/font/local`.
- O npm 11 não executa scripts de instalação sem aprovação (`@swc/core`,
  `@parcel/watcher`, `unrs-resolver`). O build, o lint e os testes funcionam sem
  eles. Nenhum script foi aprovado.

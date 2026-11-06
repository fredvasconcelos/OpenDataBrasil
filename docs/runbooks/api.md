# Runbook: API de consulta

A API (FastAPI) lê o **release Gold ativo**. Ela usa o papel `odb_reader` do
PostgreSQL e monta a Gold **somente leitura**. Não monta Bronze nem Silver
(ADR-0009, §23.4).

## Subir

```bash
docker compose --profile web up -d api      # porta 127.0.0.1:${ODB_API_PORT:-8000}
curl -s localhost:8000/health               # {"status":"ok","release_id":"..."}
```

- Documentação interativa (OpenAPI): <http://localhost:8000/docs>
- Esquema: <http://localhost:8000/openapi.json>

Depois de `odb gold build --activate`, a API passa a usar o release novo em
até `ODB_API_RELEASE_TTL_S` segundos (padrão 5), sem reiniciar. Se o
PostgreSQL cair, a API continua com o último release lido. Sem release
nenhum, responde 503.

## Rotas

| Rota | Uso |
|---|---|
| `GET /api/v1/release` | release ativo e versões Delta |
| `GET /api/v1/sources`, `/datasets`, `/datasets/{id}` | catálogo e licenças (PostgreSQL) |
| `GET /api/v1/indicators?q=`, `/indicators/{id}`, `/indicators/tree` | indicadores do release |
| `GET /api/v1/geographies?q=&level=&within=` | busca de territórios (ignora acentos) |
| `GET /api/v1/geometries/{level}?within=` | GeoJSON simplificado (`dim_geometry`), com ETag |
| `GET /api/v1/portal/navigation` | temas, subtemas e KPIs (`configs/portal/demografia.toml`) |
| `GET /api/v1/kpis/{kpi}/map?level=&period=&within=` | Total por território (cor do mapa) |
| `GET /api/v1/kpis/{kpi}/detail?geography=&dimensions=c86,c2` | tooltip: sub-KPIs aninhados |
| `GET /api/v1/kpis/{kpi}/series?geography=&dimensions=` | evolução temporal |
| `GET /api/v1/kpis/{kpi}/table?level=&dimensions=&sort=&order=&offset=&limit=` | tabela paginada |
| `POST /api/v1/exports` | CSV (ZIP), XLSX, Parquet ou JSON, com metadados |
| `POST /api/v1/query` | consulta estruturada sobre qualquer indicador |

Exemplos:

```bash
curl -s 'localhost:8000/api/v1/kpis/populacao_residente/detail?geography=uf:29&dimensions=c86,c2'
curl -s -X POST localhost:8000/api/v1/exports -H 'Content-Type: application/json' \
  -d '{"kpi_id":"pessoas_quilombolas","level":"uf","dimensions":["c2"],"format":"csv"}' -o quilombolas.zip
```

## Erros

`{"error": {"code", "message"}}`:

| Código | HTTP | Quando |
|---|---|---|
| `semantic_rule` | 422 | regra semântica: nível não publicado, dimensão não exposta, soma de não aditivos, indicadores incompatíveis |
| `invalid_request` | 422 | parâmetro fora do formato |
| `not_found` | 404 | KPI, território ou nível sem geometria inexistente |
| `too_large` | 413 | exportação acima de `ODB_API_EXPORT_MAX_ROWS` |
| `rate_limited` | 429 | acima de `ODB_API_RATE_LIMIT_PER_MINUTE` por IP |
| `busy` / `release_unavailable` | 503 | motor ocupado ou sem release ativo |
| `timeout` | 504 | consulta acima de `ODB_DUCKDB_QUERY_TIMEOUT_S` |

## Configuração

| Variável | Padrão | |
|---|---|---|
| `ODB_API_CORS_ORIGINS` | `["http://localhost:3000"]` | origens do portal (JSON) |
| `ODB_API_RELEASE_TTL_S` | 5 | releitura do release ativo |
| `ODB_API_PAGE_MAX` | 1000 | linhas por página |
| `ODB_API_EXPORT_MAX_ROWS` | 1.000.000 | limite da exportação síncrona |
| `ODB_API_RATE_LIMIT_PER_MINUTE` | 600 | por IP (0 desliga) |
| `ODB_API_MEMORY`, `ODB_API_CPUS`, `ODB_API_DUCKDB_MEMORY` | 3g, 2, 2GB | recursos do container |

## Expor um KPI ou uma dimensão

Edite `configs/portal/demografia.toml`, reconstrua a imagem e suba a API de
novo. Na primeira requisição, a configuração é conferida contra o release
(indicador publicado, classificação do indicador e partição existente). Uma
divergência gera erro `portal_config` (500) com a explicação.

# Runbook: API de consulta

A API (FastAPI) lê o **release Gold ativo**. Ela usa o papel `odb_reader` do
PostgreSQL e monta a Gold **somente leitura**. Não monta Bronze nem Silver
(ADR-0009, §23.4).

## Subir

```bash
docker compose --profile web up -d api      # porta 127.0.0.1:${ODB_API_PORT:-8000}
curl -s localhost:8000/health               # {"status":"ok","release_id":"...","portal":"ok","unavailable_kpis":{}}
```

- Documentação interativa (OpenAPI): <http://localhost:8000/docs>
- Esquema: <http://localhost:8000/openapi.json>

Depois de `odb gold build --activate`, a API passa a usar o release novo em
até `ODB_API_RELEASE_TTL_S` segundos (padrão 5), sem reiniciar. Se o
PostgreSQL cair, a API continua com o último release lido. Sem release
nenhum, responde 503. As rotas que precisam do catálogo (`/health`,
`/sources`, `/datasets`) também respondem 503 (`catalog_unavailable`, com
`Retry-After`), com uma linha `catalog unavailable` no log, sem traceback.
Quando o banco volta, tudo se normaliza sem reiniciar a API.

### Portal degradado

`/health` com `"portal": "degraded"` indica KPIs da configuração que não casam com
o release ativo, por exemplo uma API com a configuração antiga depois de uma
ativação ([ADR-0015](../adr/0015-conferencia-portal-release-e-ciclo-de-atualizacao.md)).
O que acontece:

- esses KPIs saem da navegação e respondem 404;
- o resto do portal segue no ar;
- `unavailable_kpis` lista os problemas por KPI;
- o log registra o evento `portal.kpis_indisponiveis`.

Para corrigir, reconstrua e reinicie a API com a configuração do release
(`docker compose --profile web build api && docker compose --profile web up -d api`)
e confira de novo com `odb release check`.

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
| `GET /api/v1/kpis/{kpi}/table?level=&within=&dimensions=&sort=&order=&offset=&limit=&locate=` | tabela paginada. Com `locate=<território>`, devolve a página que o contém, na mesma ordenação, e ignora o `offset` (usado pelo portal ao clicar no mapa) |
| `POST /api/v1/exports` | CSV (ZIP), XLSX, Parquet ou JSON, com metadados |
| `POST /api/v1/query` | consulta estruturada sobre qualquer indicador |

**Grão de tempo (ADR-0013):**
- Mapa, detalhe, série, tabela e exportação aceitam `grain=mes|trimestre|semestre|ano`.
- O valor é a soma das partes publicadas e vem marcado como derivado
  (`provenance.derived`, status `derived_sum`).
- O período com parte sem valor fica sem valor, com status `incomplete_period`.
- Só vale para os grãos em `time_grains` do KPI, que são os fluxos com
  `time_aggregation = "sum"`. Outro grão é recusado (400).

Exemplos:

```bash
curl -s 'localhost:8000/api/v1/kpis/populacao_residente/detail?geography=uf:29&dimensions=c86,c2'
curl -s 'localhost:8000/api/v1/kpis/sinesp_homicidio_doloso/map?level=uf&grain=ano&period=2025'
curl -s -X POST localhost:8000/api/v1/exports -H 'Content-Type: application/json' \
  -d '{"kpi_id":"pessoas_quilombolas","level":"uf","dimensions":["c2"],"format":"csv"}' -o quilombolas.zip
```

No tooltip (`/detail`) e na tabela (`/table`), categorias sem nenhuma observação no
período ficam de fora. Exemplo: as faixas de rendimento de outra edição da POF. Uma
categoria publicada sem valor ("..", "-") continua aparecendo com o símbolo
(ADR-0016).

## Erros

`{"error": {"code", "message"}}`:

| Código | HTTP | Quando |
|---|---|---|
| `semantic_rule` | 422 | regra semântica: nível não publicado, dimensão não exposta, soma de não aditivos, indicadores incompatíveis, duas dimensões marginais juntas (`exclusive_dimensions`, ADR-0016) |
| `invalid_request` | 422 | parâmetro fora do formato |
| `not_found` | 404 | KPI, território ou nível sem geometria inexistente; KPI indisponível no release ativo (ADR-0015) |
| `too_large` | 413 | exportação acima de `ODB_API_EXPORT_MAX_ROWS` |
| `rate_limited` | 429 | acima de `ODB_API_RATE_LIMIT_PER_MINUTE` por IP |
| `busy` / `release_unavailable` | 503 | motor ocupado ou sem release ativo |
| `catalog_unavailable` | 503 | PostgreSQL inacessível (erro de conexão). Erros de SQL continuam 500 |
| `timeout` | 504 | consulta acima de `ODB_DUCKDB_QUERY_TIMEOUT_S` |

## Configuração

| Variável | Padrão | |
|---|---|---|
| `ODB_API_CORS_ORIGINS` | `["http://localhost:3000"]` | origens do portal (JSON) |
| `ODB_API_PANORAMA_PATH` | `configs/catalog/panorama.toml` | taxonomia da navegação (ADR-0010); vazio: só os KPIs do portal |
| `ODB_API_RELEASE_TTL_S` | 5 | releitura do release ativo |
| `ODB_API_PAGE_MAX` | 1000 | linhas por página |
| `ODB_API_EXPORT_MAX_ROWS` | 1.000.000 | limite da exportação síncrona |
| `ODB_API_RATE_LIMIT_PER_MINUTE` | 600 | por IP (0 desliga) |
| `ODB_API_MEMORY`, `ODB_API_CPUS`, `ODB_API_DUCKDB_MEMORY` | 3g, 2, 2GB | recursos do container |

## Expor um KPI ou uma dimensão

Edite `configs/portal/demografia.toml` (ou um fragmento curado em
`configs/portal/demografia/`, como `pof.toml`) e ligue o KPI ao item
correspondente de `configs/catalog/panorama.toml`: pelo campo `kpi` ou dando ao
KPI o mesmo id do item. Não edite `configs/portal/demografia/panorama.toml`:
ele é gerado por `odb panorama gerar`. Depois, reconstrua a imagem e suba a
API de novo, **só depois** de ativar um release que contenha os indicadores
novos (senão a primeira requisição falha com `portal_config`). Na carga, cada KPI do portal precisa aparecer em exatamente
um item do panorama. Na primeira requisição, a configuração é conferida contra o release
(indicador publicado, classificação do indicador e partição existente) e
contra o panorama (a tabela de origem na Gold é a declarada). Uma
divergência gera erro `portal_config` (500) com a explicação.

## Panorama (temas e Tier 1)

`configs/catalog/panorama.toml` define os 20 temas, os 64 subtemas e os KPIs
do Tier 1 (ADR-0010). Os itens sem `kpi` saem na navegação como `planned`.

```bash
uv run odb panorama validar            # estrutura, snapshot do acervo e ligação com o portal
uv run odb panorama verificar          # metadados na API SIDRA (cerca de 45 min, retomável)
uv run odb panorama verificar --retomar --tabela 6579 --tabela 417
```

A verificação grava `configs/catalog/panorama_verificacao.json` após cada
tabela. Com `--retomar`, ela mantém as tabelas já verificadas com sucesso.

### Descritores e KPIs de Total

```bash
uv run odb panorama descrever          # descritor oficial de cada tabela (147 req., ~5 min)
uv run odb panorama gerar              # fragmentos de fontes, catálogo e portal (KPIs de Total)
uv run odb panorama documentar         # docs/data_catalog/panorama-tier1.md, com os pendentes
uv run odb panorama propor             # proposta da dimensão principal (onda Total + %)
```

`descrever` grava `/DescritoresTabela/t/<tabela>` em `configs/catalog/descritores/`
(índice com SHA-256). `gerar` reescreve, a partir do panorama, da verificação e dos
descritores:

- `configs/sources/ibge-panorama.toml`;
- `configs/indicators/demografia/panorama.toml`;
- `configs/portal/demografia/panorama.toml`.

O teste `test_repository_fragments_are_up_to_date` falha se esses arquivos
ficarem desatualizados. Para publicar os KPIs gerados:

```bash
docker compose --profile data build worker
docker compose --profile data run --rm worker odb ingest run <datasets novos>
docker compose --profile data run --rm worker odb silver build <datasets novos>
docker compose --profile data run --rm worker odb gold build --activate
docker compose --profile web build api portal && docker compose --profile web up -d
```

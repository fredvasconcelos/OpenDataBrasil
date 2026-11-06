# OpenDataBrasil

Plataforma de dados abertos oficiais do Brasil, com arquitetura lakehouse local:
**Python · Polars · Delta Lake (delta-rs) · DuckDB · PostgreSQL · FastAPI ·
Next.js**. A
especificação completa está em [`CLAUDE.md`](CLAUDE.md).

> **Estado:** Fases 1 (fundação), 2 (ingestão para a Bronze), 3 (Silver em
> Delta Lake, com qualidade e reconciliação) e 4 (Gold em Delta Lake, com
> hierarquias territorial e temática, publicação por release, consulta DuckDB
> e exportação para análise) implementadas. A etapa 4b (sexo e idade dos
> indígenas, territórios quilombolas e terras indígenas como recortes
> territoriais) está concluída. A Fase 5 (API FastAPI e portal Next.js com d3)
está em **beta** (`v0.5.0-beta.1`), em teste pelo mantenedor antes das correções
finais. Uso só interno (licença do IBGE em revisão, KI-003).

## Pacotes (`packages/`)

| Pacote | Responsabilidade |
|---|---|
| `common` | configuração (`ODB_*` + TOML por ambiente), logs JSON, URIs de armazenamento, chave de lock |
| `lakehouse` | escritor/leitor Delta (Polars + delta-rs), perfil de protocolo conservador, checagem de disco |
| `query_engine` | contrato `ReadEngine` e adaptador DuckDB somente leitura sobre versões fixadas |
| `catalog` | PostgreSQL: migrações Alembic, execuções, publicação de releases, advisory locks |
| `ingestion` | contrato de conectores, HTTP robusto, Bronze imutável com deduplicação, conectores `sidra` e `http_file` |
| `processing` | parsers Bronze → Silver (Polars), contratos de schema, classificação de valores especiais e verificações de qualidade |
| `semantics` | catálogo semântico (indicadores, classificações, hierarquias de categorias), níveis territoriais e planejador de consultas com regras semânticas |
| `modeling` | Silver → Gold (Polars): dimensões, fatos temáticos, `indicator_observation`, qualidade e construtor |
| `apps/api` | API FastAPI sobre o release Gold: catálogo, territórios, geometrias, KPIs do portal, `/query` e exportações |
| `apps/portal` | portal Next.js + d3: pesquisa, painel (menu temático, mapa, tooltip aninhado, série, tabela), exportações |
| `cli` | `odb doctor`, `odb db`, `odb smoke lakehouse`, `odb sources`, `odb ingest`, `odb silver`, `odb quality`, `odb gold`, `odb release`, `odb indicators`, `odb query` |

## Início rápido

```bash
cp .env.example .env   # e troque as senhas
docker compose --profile data --profile test build
docker compose --profile data run --rm migrate
docker compose --profile data run --rm worker odb doctor
docker compose --profile data run --rm worker odb smoke lakehouse
docker compose --profile test run --rm tests
docker compose --profile data run --rm worker odb ingest run --all   # IBGE para a Bronze
docker compose --profile data run --rm worker odb silver build --all # Bronze para a Silver
docker compose --profile data run --rm worker odb gold build --activate  # Silver para a Gold e publicação
docker compose --profile data run --rm worker odb query -i censo_pessoas_quilombolas --level uf
mkdir -p data/exports && docker compose --profile data run --rm worker odb gold export  # Parquet + DuckDB para análise
docker compose --profile web up -d   # API em localhost:8000/docs e portal em localhost:3000
```

Guia completo: [`docs/development/setup-windows-wsl2.md`](docs/development/setup-windows-wsl2.md).

## Documentação

- Decisões: [`docs/adr/`](docs/adr/)
  - 0001: fundação técnica
  - 0002: versões
  - 0003: leitura por versão fixada
  - 0004: publicação em duas etapas
  - 0005: somente leitura e escritor único
  - 0006: framework de ingestão e Bronze
  - 0007: Silver, valores especiais e reconciliação
  - 0008: Gold, modelo hierárquico e camada semântica
  - 0009: API e portal do MVP (Fase 5)
- Fontes e datasets: [`docs/data_catalog/ibge.md`](docs/data_catalog/ibge.md)
- Níveis territoriais do SIDRA (inclusive recortes especiais): [`docs/data_catalog/ibge-niveis-territoriais.md`](docs/data_catalog/ibge-niveis-territoriais.md)
- Indicadores da Gold: [`docs/data_catalog/gold-demografia.md`](docs/data_catalog/gold-demografia.md)
- Escopo de detalhamento do MVP e plano de expansão: [`docs/data_catalog/escopo-mvp-e-expansao.md`](docs/data_catalog/escopo-mvp-e-expansao.md)
- Operação: [ingestão](docs/runbooks/ingestao.md), [Silver](docs/runbooks/silver.md), [Gold](docs/runbooks/gold.md), [exportação para análise](docs/runbooks/exportacao.md), [API](docs/runbooks/api.md) e [portal](docs/runbooks/portal.md)
- Problemas conhecidos: [`docs/known-issues.md`](docs/known-issues.md)
- Compatibilidade: [`docs/development/compatibility-matrix.md`](docs/development/compatibility-matrix.md)

## Licença

O código está sob a licença [MIT](LICENSE). Os dados ingeridos seguem a licença
da fonte de cada dataset, registrada no catálogo.

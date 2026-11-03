# OpenDataBrasil

Plataforma de dados abertos oficiais do Brasil, com arquitetura lakehouse local:
**Python · Polars · Delta Lake (delta-rs) · DuckDB · PostgreSQL**. A
especificação completa está em [`CLAUDE.md`](CLAUDE.md).

> **Estado:** Fases 1 (fundação técnica) e 2 (ingestão para a Bronze, com o
> conector IBGE) implementadas. Ainda não há Silver, Gold, API ou portal.

## Pacotes (`packages/`)

| Pacote | Responsabilidade |
|---|---|
| `common` | configuração (`ODB_*` + TOML por ambiente), logs JSON, URIs de armazenamento, chave de lock |
| `lakehouse` | escritor/leitor Delta (Polars + delta-rs), perfil de protocolo conservador, checagem de disco |
| `query_engine` | contrato `ReadEngine` e adaptador DuckDB somente leitura sobre versões fixadas |
| `catalog` | PostgreSQL: migrações Alembic, execuções, publicação de releases, advisory locks |
| `ingestion` | contrato de conectores, HTTP robusto, Bronze imutável com deduplicação, conectores `sidra` e `http_file` |
| `cli` | `odb doctor`, `odb db`, `odb smoke lakehouse`, `odb sources`, `odb ingest` |

## Início rápido

```bash
cp .env.example .env   # e troque as senhas
docker compose --profile data --profile test build
docker compose --profile data run --rm migrate
docker compose --profile data run --rm worker odb doctor
docker compose --profile data run --rm worker odb smoke lakehouse
docker compose --profile test run --rm tests
docker compose --profile data run --rm worker odb ingest run --all   # IBGE para a Bronze
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
- Fontes e datasets: [`docs/data_catalog/ibge.md`](docs/data_catalog/ibge.md)
- Operação: [`docs/runbooks/ingestao.md`](docs/runbooks/ingestao.md)
- Compatibilidade: [`docs/development/compatibility-matrix.md`](docs/development/compatibility-matrix.md)

## Licença

O código está sob a licença [MIT](LICENSE). Os dados ingeridos seguem a licença
da fonte de cada dataset, registrada no catálogo.

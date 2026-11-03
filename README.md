# OpenDataBrasil

Plataforma de dados abertos oficiais do Brasil, com arquitetura lakehouse local:
**Python · Polars · Delta Lake (delta-rs) · DuckDB · PostgreSQL**. A
especificação completa está em [`CLAUDE.md`](CLAUDE.md).

> **Estado:** Fase 1 (fundação técnica) implementada. Ainda não há ingestão de
> dados, API ou portal.

## Pacotes (`packages/`)

| Pacote | Responsabilidade |
|---|---|
| `common` | configuração (`ODB_*` + TOML por ambiente), logs JSON, URIs de armazenamento, chave de lock |
| `lakehouse` | escritor/leitor Delta (Polars + delta-rs), perfil de protocolo conservador, checagem de disco |
| `query_engine` | contrato `ReadEngine` e adaptador DuckDB somente leitura sobre versões fixadas |
| `catalog` | PostgreSQL: migrações Alembic, execuções, publicação de releases, advisory locks |
| `cli` | `odb doctor`, `odb db upgrade\|current`, `odb smoke lakehouse` |

## Início rápido

```bash
cp .env.example .env   # e troque as senhas
docker compose --profile data --profile test build
docker compose --profile data run --rm migrate
docker compose --profile data run --rm worker odb doctor
docker compose --profile data run --rm worker odb smoke lakehouse
docker compose --profile test run --rm tests
```

Guia completo: [`docs/development/setup-windows-wsl2.md`](docs/development/setup-windows-wsl2.md).

## Documentação

- Decisões: [`docs/adr/`](docs/adr/)
  - 0001: fundação técnica
  - 0002: versões
  - 0003: leitura por versão fixada
  - 0004: publicação em duas etapas
  - 0005: somente leitura e escritor único
- Compatibilidade: [`docs/development/compatibility-matrix.md`](docs/development/compatibility-matrix.md)

## Licença

O código está sob a licença [MIT](LICENSE). Os dados ingeridos seguem a licença
da fonte de cada dataset, registrada no catálogo.

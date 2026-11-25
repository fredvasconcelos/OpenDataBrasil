# Open Data Brasil

Plataforma para reunir, preservar e consultar dados oficiais do Brasil. O portal está
em desenvolvimento; a abertura do código não representa aprovação de todos os dados
para publicação. As limitações conhecidas estão em [docs/known-issues.md](docs/known-issues.md).

**Novidades:** acompanhe o [Dev Log](DEVLOG.md), com novos indicadores, funções e
melhorias do portal, em linguagem simples e com a situação de cada entrega.

**Fonte → Bronze → Silver → Gold → consulta → API → portal.** A Gold oficial existe
somente no lakehouse. DuckDB consulta versões Delta fixadas por um release;
PostgreSQL armazena metadados e o estado da publicação.

## O que há neste repositório

| Caminho | Responsabilidade |
|---|---|
| `packages/ingestion` | Conectores, preservação dos originais e checkpoints |
| `packages/processing` | Silver, contratos e qualidade com Polars |
| `packages/modeling` | Gold, dimensões, fatos e linhagem |
| `packages/semantics` | Catálogo semântico e planejamento das consultas |
| `packages/query_engine` | Leitura DuckDB sobre versões publicadas |
| `packages/catalog` | Catálogo operacional e publicação transacional |
| `packages/lakehouse`, `packages/common`, `packages/cli` | Armazenamento, configuração e comando `odb` |
| `apps/api` | FastAPI, catálogo, KPIs e exportação |
| `apps/portal` | Next.js, mapas, séries, tabelas e pesquisa |
| `configs` | Fontes, contratos e indicadores com procedência |
| `tests`, `infrastructure` | Testes e infraestrutura reproduzível |
| `design-system/assets` | Ativos da marca e suas condições de uso |

Relatórios internos, credenciais, dados baixados e backups não fazem parte desta distribuição.
A especificação normativa é o [CLAUDE.md](CLAUDE.md), aplicável a qualquer agente ou pessoa.

## Executar localmente

Requer Docker Compose e ambiente Linux ou WSL2. Python usa `uv` com versões fixadas;
Node é executado nas imagens fixadas do projeto. Consulte a
[matriz de compatibilidade](docs/development/compatibility-matrix.md).

```bash
cp .env.example .env  # substitua as senhas; mantenha o arquivo somente na sua máquina

docker compose --profile data --profile test build
docker compose --profile data run --rm migrate
docker compose --profile data run --rm worker odb doctor
docker compose --profile data run --rm worker odb smoke lakehouse
docker compose --profile test run --rm tests
```

A ingestão e a publicação de dados precisam de configuração da fonte, licença,
qualidade e release validado. Um build da Gold não ativa uma publicação. Siga os
runbooks antes de servir os dados; nenhum download ou release está embutido no código.
Com um release ativo, o perfil `web` atende o portal em `localhost:3000` e a API em
`localhost:8000`.

## Documentação

- [Instalação no Windows/WSL2](docs/development/setup-windows-wsl2.md)
- [Decisões arquiteturais](docs/adr/)
- [Catálogo IBGE](docs/data_catalog/ibge.md)
- [Ingestão](docs/runbooks/ingestao.md), [Silver](docs/runbooks/silver.md),
  [Gold](docs/runbooks/gold.md), [exportação](docs/runbooks/exportacao.md)
- [API](docs/runbooks/api.md), [portal](docs/runbooks/portal.md),
  [atualização](docs/runbooks/atualizacao.md), [Vitrine](docs/runbooks/vitrine.md)
- [Como contribuir e validar alterações](CONTRIBUTING.md)
- [Segurança](SECURITY.md), [roteiro](ROADMAP.md), [licenças dos dados](DADOS.md)

## Licenças

Código sob [Apache 2.0](LICENSE), com os avisos de [NOTICE](NOTICE).
Documentação, ADRs, metodologia e catálogo sob
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt-br).
Os dados seguem a licença de cada fonte, conforme [DADOS.md](DADOS.md).
O nome e a marca Open Data Brasil não são licenciados. A decisão está na
[ADR-0028](docs/adr/0028-licencas-do-codigo-dos-textos-e-dos-dados.md).

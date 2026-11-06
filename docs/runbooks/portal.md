# Runbook: portal

Portal Next.js (`apps/portal`), com mapas e gráficos em d3 (ADR-0009). O portal
fala só com a API, pela rede interna do Docker. O navegador usa o proxy
`/odb-api/*` do próprio portal, que deixa passar apenas os prefixos de uma lista
fechada. O portal não lê Delta, PostgreSQL nem arquivos.

## Subir

```bash
docker compose --profile web up -d          # postgres + api + portal
# Portal:  http://localhost:3000   (ODB_PORTAL_PORT)
# API:     http://localhost:8000/docs
```

A primeira vez exige uma Gold publicada (`odb gold build --activate`, ver o
[runbook da Gold](gold.md)). Depois de mudar o código do portal:

```bash
docker compose --profile web build portal && docker compose --profile web up -d portal
```

## Páginas

| Página | Conteúdo |
|---|---|
| `/` | pesquisa de indicadores (ignora acentos) e temas |
| `/dashboard` | painel: menu lateral (temas > subtemas > KPIs e dimensões), mapa, evolução temporal, tabela, exportação e metadados |
| `/sobre` | release ativo, conjuntos de dados e licenças |

O estado do painel fica na URL e pode ser compartilhado:
`/dashboard?kpi=populacao_residente&nivel=uf&periodo=2022&dim=c86,c2&territorio=uf:29`.

## Desenvolvimento

Não é preciso ter Node no host. Os comandos rodam na imagem Node fixada:

```bash
NODE=node:24.22.1-bookworm-slim@sha256:be8204d4bd327363357f532187b752ff62759c31bedf98e9e18fc08c9cbd605c
cd apps/portal
docker run --rm --user 1000:1000 -e HOME=/tmp -v "$PWD":/app -w /app $NODE npm ci
docker run --rm --user 1000:1000 -e HOME=/tmp -v "$PWD":/app -w /app $NODE \
  sh -c 'npx tsc --noEmit && npx eslint . && npx vitest run'
```

Para instalar ou atualizar dependências, respeite a regra dos 14 dias também
nas transitivas: `npm install --before=<data de 14 dias atrás>T23:59:59Z --save-exact`.

### Contrato com a API

Os tipos de `src/lib/api-schema.ts` são gerados do contrato de referência:

```bash
uv run python -m odb_api.app tests/contracts/openapi.json      # na raiz
docker run --rm --user 1000:1000 -e HOME=/tmp -v "$(git rev-parse --show-toplevel)":/repo \
  -w /repo/apps/portal $NODE npm run gen:api
```

O CI falha se a API mudar sem atualizar o contrato (`tests/contracts/test_openapi.py`)
ou se os tipos do portal ficarem desatualizados.

### Ponta a ponta (navegador real)

Com o perfil `web` no ar:

```bash
cd apps/portal
docker run --rm --network opendatabrasil_default --ipc=host --user 1000:1000 -e HOME=/tmp \
  -e PORTAL_URL=http://portal:3000 -v "$PWD":/app -w /app \
  mcr.microsoft.com/playwright@sha256:2f05f8a734509a7b3f26a912639488ee08f58a7b292d14d62271bcff9038768f \
  npx playwright test
```

Os testes cobrem pesquisa, tooltip aninhado (Bahia: Parda 57,3% > Homens
48,3%), seleção, período, nível, fonte visível, exportação CSV, mapa municipal e
a página "Sobre". As capturas ficam em `apps/portal/test-results/`. Esses testes
dependem dos dados reais e não rodam no CI.

## Detalhes de mapa

- **Orientação dos anéis:** a API entrega GeoJSON pela RFC 7946 (anel externo
  anti-horário). O d3-geo, que trabalha na esfera, espera o contrário. O portal
  inverte os anéis (`src/lib/geo.ts`) e confere a área esférica. Um polígono com
  orientação trocada vira "o globo menos o território" e encolhe o mapa.
- **Escala:** 7 faixas por quantis. Quando o zero é comum (por exemplo,
  municípios sem pessoas quilombolas), ele vira uma classe à parte. Com
  contagens, os limites são inteiros.
- **Tamanho:** o painel do mapa tem altura definida. Um SVG que acompanha a
  altura do contêiner entra em ciclo de redimensionamento.

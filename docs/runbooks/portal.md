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

Os links "Contato" e GitHub do cabeçalho e do rodapé (Design System v2.3) vêm de
`NEXT_PUBLIC_CONTACT_URL` e `NEXT_PUBLIC_REPO_URL`. O Next embute essas variáveis no
build, então mudar o valor exige `build portal` de novo. Sem valor, o link não aparece.

## Páginas

| Página | Conteúdo |
|---|---|
| `/` | Início (Design System v2.3): números do catálogo, busca (nome, tema, subtema ou nº da tabela, sem acentos), etiquetas de tema com ícone e contagem, grade de temas, lista do tema com os itens em preparação e prévia do indicador com "Abrir no painel" |
| `/dashboard` | painel: barra lateral (filtros e temas > subtemas > KPIs; temas recolhidos, KPIs planejados desativados "em preparação"), mapa, evolução temporal, tabela, exportações e metadados (layout do Design System v2: empilhado até 1599 px, tela cheia a partir de 1600 px) |
| `/sobre` | Sobre os dados (v2.3): release ativo, licença e números; busca, filtro de situação (Todos, Publicados, Em preparação) e etiquetas de tema; uma linha por indicador com descrição, limitações e metadados |

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

Os testes cobrem:

- pesquisa no Início, prévia do indicador e "Abrir no painel";
- página sem rolagem, sem `<title>` no mapa e hover no menu e no header;
- recorte por duplo clique:
  - no Nordeste, 9 UFs coloridas e 4 regiões em cinza;
  - na Bahia, 417 municípios e 26 UFs em cinza;
  - trilha do recorte e tabela restrita ao recorte;
- recorte pela roda do mouse (abrir e fechar), descartando o tooltip do nível anterior;
- recorte vindo da URL e tema escuro, com a escolha mantida ao recarregar;
- legenda com título ("Pessoas", pela unidade) e grupos "Até…" / "Mais de…";
- tela cheia (1920 × 1080): sem rolagem, mapa à esquerda e gráfico e tabela à
  direita; filtros na barra lateral e exportações junto do que exportam;
- clique num município do mapa (Ourolândia, no recorte da Bahia): a tabela vai
  à página dele e rola até a linha;
- tooltip aninhado (Bahia: Parda 57,3% > Homens 48,3%), seleção sem contorno de
  foco e período;
- "Limpar filtros", fonte visível e exportação CSV;
- mapa municipal e a página "Sobre";
- panorama: 20 temas recolhidos (só o tema atual aberto), KPIs "em preparação"
  sem ação, com a tabela SIDRA no `title` (Serviços > Turismo e transportes, 8695);
- tooltip da evolução temporal (v2.3): período mais próximo do ponteiro, inteiro
  dentro do quadro, e navegação pelo teclado;
- busca da barra lateral fixa (v2.3.1): ao rolar a árvore até o fim, a 1280 px e em
  tela cheia, título e campo continuam no topo, por cima da árvore, e a busca segue
  funcionando;
- trechos da busca lateral em texto puro, sem entidades nem marcas HTML da fonte
  ("Mortalidade": descrição da tabela 6606);
- KPI de Total gerado do panorama (Nascidos vivos, tabela 2609): mapa por UF,
  fonte e notas oficiais no rodapé;
- POF 6715 completa: classes de rendimento e despesas de consumo, com o tooltip do
  mapa em matriz inteiro na janela;
- cabeçalho e rodapé (v2.3): botão do GitHub quando há endereço, rodapé completo
  no início e faixa de 44 px no Painel, sem rolagem da página;
- série mensal do IPCA desde jan 1998, eixo de tempo e tooltip por teclado;
- Início e Sobre (v2.3): números com "em preparação", etiqueta de tema, item em
  preparação sem ação, busca pelo nº da tabela, filtro de situação e link da
  tabela na fonte; Início no tema escuro;
- mapa em % de uma categoria (Municípios com Plano Diretor, legenda
  "% Com Plano Diretor").

As capturas ficam em `apps/portal/test-results/`. Esses testes dependem dos
dados reais e não rodam no CI.

## API indisponível

Se a API responder com erro, por exemplo 503 enquanto o PostgreSQL volta depois
de um reinício do Docker, as páginas mostram "Dados temporariamente
indisponíveis" (`src/app/error.tsx`). Elas tentam de novo a cada 15 s e têm um
botão para tentar na hora. Não é preciso recriar o contêiner do portal.

## Detalhes de mapa

- **Orientação dos anéis:** a API entrega GeoJSON pela RFC 7946 (anel externo
  anti-horário). O d3-geo, que trabalha na esfera, espera o contrário. O portal
  inverte os anéis (`src/lib/geo.ts`) e confere a área esférica. Um polígono com
  orientação trocada vira "o globo menos o território" e encolhe o mapa.
- **Escala:** 7 faixas por quantis. Quando o zero é comum (por exemplo,
  municípios sem pessoas quilombolas), ele vira uma classe à parte. Com
  contagens, os limites são inteiros.
- **Tamanho:** o painel do mapa ocupa a linha flexível da grade do painel, e o
  SVG fica em posição absoluta. Um SVG que dita a altura do contêiner entra em
  ciclo de redimensionamento.
- **Zoom e recorte:** d3-zoom aplica a transformação direto no `<g>`, sem
  re-render do React, e os traços usam `vector-effect: non-scaling-stroke`.
  - **Recorte:** o duplo clique, a roda ou o `+` abrem o recorte no território
    (ADR-0009, seção 6). O painel carrega então três coisas: a geometria do
    nível exibido com `within=<recorte>`, a do nível do recorte no país inteiro
    (contexto em cinza) e os valores com `within`.
  - **Transições:** as de enquadramento não têm evento de origem e só fixam a
    escala-base. As dos botões `+`/`−` contam como gesto. O enquadramento espera
    o painel ser medido e é refeito quando ele muda de tamanho.
  - **Teclado:** `+` abre o recorte no território focado e `-` sobe um recorte.
- **Cores:** tokens do design system (`src/lib/theme.ts`, `--odbr-seq-1..7`). O
  cinza do contexto é neutro, para não se confundir com a primeira classe da
  escala, que é azulada.

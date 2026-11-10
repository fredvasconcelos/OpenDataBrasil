# ADR-0009 — API e portal do MVP (Fase 5)

- **Estado:** Aceito (decisões de escopo e de interface; a implementação segue em etapas)
- **Data:** 2026-11-05
- **Contexto normativo:** CLAUDE.md §4.2, §11, §13.4, §18, §19, §23 e §27 (Fase 5)

## Contexto

A Fase 5 entrega a API (FastAPI) e o portal (Next.js) sobre o release Gold
publicado. O mantenedor aprovou o plano em 2026-11-05 com os ajustes abaixo.
A base são as tabelas da Fase 4, mais as tabelas que completam o recorte por
sexo (etapa 5.0).

## Decisões

### 1. Detalhe dos dados no MVP

Todas as populações (geral, indígena e quilombola) aparecem com **Total e
sexo**. A população geral também aparece por **cor ou raça**, combinável com o
sexo. Idade fica fora do portal. Os dados de idade já ingeridos continuam na
Gold. A expansão está catalogada em
[`escopo-mvp-e-expansao.md`](../data_catalog/escopo-mvp-e-expansao.md).

Etapa 5.0: ingeridas a 9606 (cor ou raça × sexo, 2010 e 2022), a 8176
(quilombolas por sexo) e a 9765 (territórios quilombolas por sexo). A 9606
substitui a 9514, porque os totais por sexo de 2022 são idênticos e ela
também cobre 2010.

### 2. Uma tabela por KPI, com conferência das sobrepostas

Cada KPI do portal aponta para **uma única tabela**, a que tem todas as
dimensões oferecidas. O portal não troca de fonte conforme a combinação
escolhida. As tabelas sobrepostas ficam na Gold, e o catálogo declara pares
`[[consistency]]`. A construção da Gold compara os valores nas classificações
comuns, com as demais no Total, e gera aviso se divergirem. No release
`35489cf6`, os seis pares conferem: 9606 × 9605, 9606 × 4714, 8176 × 9578,
9765 × 9723 (duas variáveis) e 9971 × 9718.

### 3. Hierarquia de KPIs do portal

Separa-se **o que se mede** (KPI) de **como se desagrega** (dimensões):

```text
Tema › Subtema › KPI
                 └ dimensões: Geografia (sempre) · Cor ou raça · Sexo
```

A navegação temática do portal é uma configuração própria (tema, subtema, KPI
→ indicador da Gold e dimensões expostas). A árvore da Gold continua
organizada pela fonte. Liberar uma dimensão é editar essa configuração. As
dimensões são combináveis (nenhuma, uma ou várias) e aninhadas numa
**ordem fixa**: cor ou raça e depois sexo. Dimensões futuras, como grupos de
idade, entram nessa ordem.

### 4. Layout do dashboard

- Header de navegação.
- **Barra lateral** (260 px; 290 px em tela cheia), com dois blocos:
  - "Filtros": nível territorial, período, "Detalhar por" (dimensões) e
    **Limpar filtros**, que volta ao estado inicial do KPI (dimensões, período e
    território padrão, Grande Região e mapa inteiro);
  - abaixo, "Temas e indicadores" (temas, subtemas e KPIs).

  A área central não tem seletores.
- **Área central** (grade `.dash-grid`, Design System v2). Cada exportação fica
  junto do que exporta: "Imagem do mapa" (SVG, PNG) no cabeçalho do mapa e
  "Baixar dados" (CSV, XLSX, Parquet, JSON) no cabeçalho de "Gráfico e tabela".
  - até 1599 px: empilhado (mapa; gráfico e tabela lado a lado; "Sobre este
    indicador"). Rola só a área central, nunca a página;
  - a partir de 1600 px: tela cheia sem rolagem. O mapa fica à esquerda, na
    altura toda; à direita, gráfico em cima e tabela embaixo, com a altura
    dividida em frações fixas, para que carregar a série não empurre a tabela;
    a fonte vira rodapé;
  - abaixo de 900 px: uma coluna, com a barra lateral no topo.
- Clicar num território atualiza o gráfico e **localiza o território na
  tabela**:
  - a API devolve a página que o contém (`locate`), na mesma ordenação;
  - a tabela rola por dentro até a linha, sem mover a página.

  O nível inicial é a Grande Região.
- **Sobre este indicador:** a linha da fonte fica sempre visível (fonte,
  tabela, link oficial, licença e release). Descrição, unidade, períodos e
  limitações ficam num bloco recolhível, aberto até 1599 px e fechado em tela
  cheia.
- Header e menu lateral mudam de cor com o ponteiro, além de marcar o item
  selecionado.
- **Visual:** Design System ODBr (`design-system/`, gerado no Claude Design;
  v1 e v2 na revisão da beta, 2026-11). Os tokens (`--odbr-*`) ficam em
  `src/styles/tokens.css`, com tema claro, escuro e o do sistema operacional. O
  botão de tema guarda a escolha no navegador. A fonte é a Nunito
  (`next/font`, servida pelo próprio portal). Cores de dados em SVG ficam em
  `style`, porque `var()` não vale em atributo.

### 5. Tooltip do mapa

O tooltip mostra **apenas o território sob o ponteiro**, no nível escolhido,
sem os níveis superiores, para não ficar grande. Ele detalha os sub-KPIs das
dimensões marcadas, aninhados na ordem fixa:

```text
Bahia · Censo 2022
Total                 14.141.626
Parda                  8.103.964   57,3%
   Homens              3.911.184   48,3%
   Mulheres            4.192.780   51,7%
Preta …
```

- Cada percentual é sobre o nó de cima: cor ou raça sobre o Total, sexo sobre
  aquela cor ou raça. São calculados na consulta e marcados como derivados.
- KPI não aditivo (percentual, densidade): só o valor, sem percentuais.
- Valor ausente (`X`, `...`) aparece como ausente, nunca como zero.
- A categoria Indígena de cor ou raça traz a nota de que não equivale a
  "Pessoas indígenas".
- O mapa carrega um valor por território. O detalhe do tooltip vem de uma
  chamada pequena por território, com cache.

### 6. Mapa e gráficos com d3, dentro do Next.js

O portal é uma aplicação Next.js (React, TypeScript), como pede o §4.2. Mapa e
gráficos usam **d3** pelos seus módulos oficiais (<https://d3js.org>), que é como
a própria biblioteca se distribui. O pacote `d3` é só o agregado deles.
Instalamos apenas os módulos usados:

| Módulo | Uso |
|---|---|
| d3-geo | projeção (Mercator) e caminhos dos territórios |
| d3-zoom (+ d3-selection, d3-transition) | zoom, arraste e troca de nível |
| d3-scale | escala de cor por quantis e eixos (cores do design system) |
| d3-shape, d3-array | linhas e extremos da série temporal |
| d3-format | números |

O React desenha o SVG. O d3 calcula a geometria e controla o zoom. A geometria vem em GeoJSON (seção 7). Se o mapa municipal
pesar em SVG, o desenho passa para canvas sem mudar o contrato dos componentes.

- Escala de cor por **quantis, em 7 grupos**, calculados com os territórios
  do recorte exibido. Uma escala linear apagaria quase todo o mapa, porque São
  Paulo e as capitais dominam.
- **Legenda:**
  - título pela unidade: "População", "Percentual (%)", "Densidade (hab/km²)"
    ou "Área (km²)";
  - cada corte é aproximado para um número redondo (1; 1,5; 2; 2,5; 3; 4; 5; 6;
    7; 8; 9 × 10ⁿ). Se repetir o anterior, sobe para o redondo seguinte; grupos
    vazios são fundidos; contagens só têm limites inteiros;
  - as pontas são abertas: "Até 4 mil" (≤), "4 mil – 5 mil" (> e ≤) e "Mais
    de 15 mil" (>).

  Os grupos deixam de ter exatamente o mesmo número de territórios, em troca de
  uma leitura direta. Os quantis seguem como base: em recortes com municípios
  muito pequenos e uma capital muito grande, o último grupo concentra a
  capital, e os demais continuam distinguindo os pequenos (`src/lib/scale.ts`).
- O mapa é colorido pelo **Total do KPI**. Colorir por uma categoria ou um
  percentual fica para depois.
- **Ampliação seletiva (recorte).** O mapa abre nas Grandes Regiões. Duplo
  clique, roda do mouse ou `+` num território abre o **recorte** nele:
  - só o recorte se subdivide no nível seguinte e recebe o gradiente;
  - os quantis são calculados só com os territórios do recorte;
  - o resto do país fica no nível do recorte, em cinza neutro
    (`--odbr-map-context`), com as divisas visíveis. O recorte ganha contorno
    forte, e a legenda ganha a entrada "Fora do recorte".

  Exemplo: no Norte, só as 7 UFs do Norte ficam coloridas, e as outras 4 regiões
  ficam em cinza. No Amazonas, só os 62 municípios do estado ficam coloridos, e
  as outras 26 UFs ficam em cinza.

  Tabela, exportação e título acompanham o recorte, que é enviado como `within`
  nos endpoints que já o aceitavam. O recorte fica na URL (`?foco=uf:13`).

  Uma trilha sobre o mapa ("Brasil › Norte › Amazonas") volta a qualquer
  recorte de cima. Os pais vêm de `GET /geographies/{chave}` (`parent_key`).
  Afastar volta ao recorte de cima, e "Ver o Brasil inteiro" ou "Limpar
  filtros" fecham o recorte.

  O gesto é medido em relação à escala em que o recorte atual foi aberto:
  - aproximar 2× abre o recorte no território sob o ponteiro;
  - afastar abaixo de 0,6× sobe um recorte;
  - voltar à escala 1 retorna ao Brasil.

  A projeção é fixada no país inteiro, e o mapa continua montado enquanto o
  recorte seguinte carrega. A regra fica em `src/lib/zoom.ts`.

  Essa abordagem substituiu a primeira versão do zoom, que trocava o nível do
  país inteiro e foi rejeitada na revisão.
- **Sem dicas nativas.** O SVG não tem `<title>`, que gerava um balão do
  navegador por cima do tooltip. O nome acessível fica no `aria-label`. O
  território clicado não ganha contorno de foco: o realce é o traço. O foco
  por teclado continua visível, com o traço em destaque.

### 7. Geometria

Malhas territoriais oficiais de 2022 do `geoftp.ibge.gov.br`:

- **Bronze:** os arquivos originais de UFs e de municípios.
- **Silver** (`territorial_mesh`): polígonos originais em WKB, com o código IBGE.
- **Gold** (`dim_geometry`, em Delta e versionada no release): GeoJSON
  simplificado por nível.

A API de malhas (`servicodados`) está fora do ar (KI-002).

- Grandes Regiões e Brasil são derivados por `union_all` das UFs, agrupadas
  pela hierarquia (a malha de Regiões não tem código). A união por cobertura
  (`coverage_union_all`) falhou nas UFs reais, porque as divisas oficiais não
  têm vértices exatamente coincidentes.
- A simplificação usa `coverage_simplify`, com tolerância de 0,01° (UF e
  município) e 0,02° (Região e Brasil). As coordenadas ficam com 4 casas: com
  3, o arredondamento invalidava 59 municípios. Com 4, 17 municípios precisam
  de reparo (`make_valid` estrutural), com perda de área de no máximo 0,2%.
- Transporte: GeoJSON com compressão gzip na API. A malha municipal tem 5,5 MB,
  ou 1,5 MB comprimida. O TopoJSON fica como otimização futura, se o tempo de
  carga exigir.
- As duas lagoas da malha municipal (4300001 e 4300002) não são municípios e
  ficam de fora. Elas explicam a diferença de área do RS (KI-004).
- Terras indígenas e territórios quilombolas ficam sem mapa no MVP e
  aparecem na tabela.

### 8. API

FastAPI com OpenAPI, sobre o planejador e as regras semânticas da Fase 4, sem
SQL próprio nas rotas. O release ativo é lido do PostgreSQL e informado em
toda resposta. A API tem endpoints de catálogo, de território e de consulta,
mais endpoints feitos para a tela: mapa (um valor por território), detalhe
do tooltip, série e tabela paginada. A exportação (CSV, XLSX, Parquet, JSON)
é síncrona, com limite de linhas e metadados anexos. `/compare` fica para a
Fase 6 (§18.3: sem endpoints fictícios). O container da API monta só a Gold, em
modo somente leitura, e usa o papel `odb_reader`.

Implementação (`apps/api`, [runbook](../runbooks/api.md)):

- **Release por requisição:** o release é resolvido uma vez (`ReleaseResolver`,
  com cache de 5 s) e todas as consultas da requisição usam as mesmas versões
  Delta. O identificador vai no cabeçalho `X-ODB-Release` e no campo
  `provenance` de cada resposta.
- **Metadados vindos do release:** os metadados de indicador vêm do
  `dim_indicator` do release, não do `catalog.indicator`, para ficarem
  coerentes com os dados consultados. Fontes, datasets e licenças vêm do
  PostgreSQL.
- **Cache:** guarda metadados e coleções de geometria com o `release_id` na
  chave. Um release novo invalida o cache.
- **Paginação do `/query`:** devolve `has_more` em vez de um total que exigiria
  uma contagem a mais.
- **Concorrência (§11.5):** é testada com requisições paralelas pela API. O
  motor ocupado responde 503 e o timeout responde 504.
- **Medição local, release `024556cf`:**

  | Consulta | Tempo |
  |---|---|
  | Mapa municipal | 25–55 ms |
  | Detalhe (tooltip) | cerca de 50 ms |
  | Malha municipal com gzip (1,57 MB) | 0,57 s na primeira carga, depois em cache |

### 9. Portal

`apps/portal` ([runbook](../runbooks/portal.md)):

- **Proxy:** o navegador fala com o proxy `/odb-api/*` do portal, com lista fechada
  de prefixos e só `POST /exports`. A API fica na rede interna. Os tipos vêm do
  contrato OpenAPI de referência (`tests/contracts/openapi.json`).
- **Estado na URL:** KPI, nível, período, dimensões e território ficam na URL,
  para o painel poder ser compartilhado.
- **Orientação dos anéis:** a orientação foi normalizada na Gold (RFC 7946,
  `dim_geometry` 1.1.0) e é invertida no portal para o d3-geo, que trabalha na
  esfera. Antes da normalização, alguns polígonos reparados tinham a orientação
  oposta, e o mapa colapsava.
- **Escala de cor:** quantis em 7 grupos, com limites redondos e pontas
  abertas ("Até…", "Mais de…"), o zero em grupo próprio quando é comum e
  limites inteiros para contagens.
- **Exportação:** dados em CSV, XLSX, Parquet e JSON pela API, e imagem do
  mapa em SVG e PNG no navegador, com legenda de fonte e release.
- **Testes:** biblioteca e componentes (Vitest); ponta a ponta com navegador
  real (Playwright, local).

## Consequências

- O gráfico de evolução de KPIs por sexo tem 2010 e 2022 para a população
  geral e só 2022 para as populações especiais. A série longa (2001–2026) é a
  da população estimada, sem sexo.
- Novas dimensões entram por configuração (Gold, exposição do portal e ordem
  de aninhamento), sem mudar os componentes.
- O portal fica local até a licença do IBGE ser confirmada (KI-003).

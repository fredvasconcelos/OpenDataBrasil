# Open Data Brasil — Design System v2.3 (pacote de implementação)

Este pacote leva o Design System ODBr para o portal (`apps/portal`, Next.js 16 + React 19 + d3).
**Os arquivos em `portal/` são uma cópia exata do portal no commit `d304ab0`** (v2 aplicada
mais as revisões da beta) e mantêm todas as classes, rótulos e `aria-*` de que os testes dependem.

## Novidades da v2.3 (sobre a v2.1)

> Versão do pacote: **2.3.11** (arquivo `VERSION`; ajustes da 2.3.1 a 2.3.11 na seção "Ajustes depois da 2.3.0"). Telas de referência em `reference/`.
>
> **O que a API ainda não fornece (não inventado):** o canvas mostra indicadores
> "em preparação" e o filtro de situação; o contrato `/navigation` só traz indicadores
> publicados, então as páginas mostram apenas esses. Para exibir os pendentes é preciso um
> campo/endpoint no backend (decisão do projeto). O botão "Baixar dados (CSV)" da prévia
> também ficou de fora: a exportação exige nível e período, que só existem no Painel.


| Item | Arquivos | Regra |
|---|---|---|
| Eixo X de tempo na evolução temporal | `src/lib/period.ts` (novo) + `period.test.ts`, `SeriesChart.tsx` | Posição proporcional ao tempo; rótulos em passos redondos que cabem na largura; primeiro e último período sempre visíveis e ancorados por dentro; anos não publicados ligados por pontilhado ("Períodos sem publicação"); suporte a AAAAMM e trimestres; eixo ordinal para códigos desconhecidos |
| Tooltip do gráfico que não corta | `SeriesChart.tsx`, `globals.css` (`.series-tip`) | HTML medido dentro de `.series-plot`: direita → esquerda na borda; acima → abaixo no topo; guia tracejada; teclado ← → Home End Esc |
| Tooltip do mapa com muitas variáveis | `DetailTooltip.tsx`, `globals.css` (`.tooltip.matrix`, `.tooltip.columns`, `.tt-grid`…) | Forma **matriz** (resumo + tabela itens × categorias, largo e baixo) e **duas colunas**; mede largura e altura e fica inteiro na janela |
| **Página Início** | `app/page.tsx`, `HomeCatalog.tsx`, `KpiPreview.tsx`, `ThemeIcon.tsx` (novos) | Busca (nome, tema, subtema, nº da tabela), etiquetas de tema com ícone e contagem (filtro), grade compacta de temas em "Todos", lista completa ao escolher tema ou buscar, prévia do indicador em diálogo (metadados, limitações, "Abrir no painel") |
| **Página Sobre os dados** | `app/sobre/page.tsx`, `AboutCatalog.tsx` (novo) | Release ativo + números; busca e etiquetas; acordeão por tema, uma linha por indicador (tabela, situação, detalhar por, outras classificações) que abre com descrição, limitações e metadados |
| **Busca na barra lateral** (proposta A) | `Sidebar.tsx` | Campo sob "Temas e indicadores": filtra a árvore, marca o termo, mostra trecho da descrição; "/" foca, Esc limpa |
| Ícones e cores dos temas | `lib/themes.ts` (novo), `tokens.css` (`--odbr-theme-<família>-*`), `tokens.json` (`themeFamilies`) | 20 ícones; 8 famílias (azul, verde, ocre, petróleo, roxo, laranja, magenta, ardósia), claro e dark; tema reconhecido pelo rótulo (ou `THEME_BY_ID`) |
| Catálogo | `lib/catalog.ts` (novo) + `catalog.test.ts`, `lib/fixtures.ts` (dados de teste) | Busca sem acentos, destaque, períodos ("2001–2026 (22)"), dimensão principal e demais |
| Contato e GitHub no cabeçalho | `Header.tsx`, `ProjectLinks.tsx` (novo), `icons.tsx` (novo), `lib/links.ts` (novo) | Pílula "Contato" + botão redondo com o ícone oficial do GitHub (Bootstrap Icons, MIT); links por variável de ambiente |
| Rodapé | `Footer.tsx` (novo), `app/layout.tsx` | Marinho nos dois temas, logo negativo, "Sobre os dados" · "Contato" · "Código no GitHub"; faixa fina de 44 px no Painel |
| Mensagens | `messages/pt-BR.json` | `dashboard.gapNote`, `seriesKeys`, `seriesMore`, `relativeNote`; `nav.contact`, `nav.repo`, `nav.code`, `nav.footer` |
| Testes | `components.test.tsx`, `lib/period.test.ts` | Matriz, forma normal preservada, pontilhado, tooltip por teclado, ticks sem sobreposição |

**Variáveis de ambiente novas** (acrescente ao `.env.example` do portal, sem valores inventados):

```
NEXT_PUBLIC_CONTACT_URL=   # ex.: mailto: ou página de contato
NEXT_PUBLIC_REPO_URL=      # URL do repositório no GitHub
```

> **Para o Claude Code (páginas):** `app/page.tsx` e `app/sobre/page.tsx` foram escritos
> sobre o contrato atual (`api.navigation()`, `api.release()`, `api.datasets()`). Compare com
> os arquivos do projeto antes de substituir e mantenha o que tiver mudado depois do commit
> de referência. O `IndicatorSearch.tsx` antigo deixa de ser usado pelo Início (a busca está
> no `HomeCatalog`); remova-o só se nada mais o importar.

> **Para o Claude Code:** o tooltip simples do gráfico criado no Codex é **substituído**
> pelo `SeriesChart.tsx` deste pacote (que já inclui tooltip). Compare com `diff` e mantenha
> qualquer outra mudança do projeto. Retire o `<title>` nativo dos pontos, se ainda existir.

## Como a v2.3 entrou no portal (adaptações do projeto)

O pacote v2.3 foi aplicado em `apps/portal` por *merge* de três vias (v2.1 do espelho,
v2.3 do pacote e o portal atual). Os arquivos de `portal/` deste diretório são cópias
do portal em uso. Adaptações feitas na integração:

- **Períodos da Gold:** `lib/period.ts` também lê o mês como a Gold grava (`AAAAMmm`,
  ex.: `2026M09`). O `formatPeriod` de `lib/format.ts` passou a usar `lib/period`, então
  filtro de período, trilha, tabela, tooltip do mapa e gráfico mostram o mesmo texto
  ("set 2026", "T2 2026"; até a 2.3.2, "2º tri 2026").
- **SeriesChart:** substitui o tooltip simples anterior (`.chart-tip`, removido do CSS).
  O alvo do ponteiro é o retângulo `.series-hit`.
- **Rodapé no Painel:** a faixa de 44 px (`--footer-slim-h`) é descontada da altura do
  painel, que continua sem rolagem da página.
- **Links:** `NEXT_PUBLIC_CONTACT_URL` e `NEXT_PUBLIC_REPO_URL` entram no build da imagem
  (`args` do serviço `portal` no Compose, `.env.example`). O repositório público já
  vem preenchido no exemplo; o contato fica vazio até haver endereço oficial.
- **Páginas Início e Sobre (pacote 2.3.0):** o contrato `/navigation` do projeto já traz
  os indicadores em preparação (`planned` em cada subtema, com tabela SIDRA, pesquisa e nota).
  Por isso o portal mostra o que o canvas desenha e o pacote deixou de fora:
  - no Início, número "em preparação", resumo "N indicadores · X em preparação" e
    itens sem ação com a etiqueta;
  - no Sobre, filtro de situação (Todos, Publicados, Em preparação) e linha própria com a
    tabela na fonte;
  - na busca da barra lateral, os itens em preparação também aparecem.

  Funções em `lib/catalog.ts` (`flattenPlanned`, `matchPlanned`). Sem busca, a barra lateral
  mantém os temas recolhidos, com só o tema atual aberto. A fixture de teste ganhou um item
  em preparação e os campos do contrato atual (`filters`, `planned`).
- **Mensagens:** mantidas as chaves do portal (`plannedCount`, `planned`,
  `plannedSource`, legenda "Pessoas") junto com as novas da v2.3.

## Ajustes depois da 2.3.0 (registro para o Claude Design)

Comportamentos definidos no projeto depois do pacote 2.3.0. **Ao gerar a próxima versão,
preserve-os** (nos canvas e nos componentes): os canvas de `reference/canvas/` são
anteriores a estes ajustes e ainda não os mostram.

| Versão | Item | Onde | Regra |
|---|---|---|---|
| 2.3.1 | Busca da barra lateral fixa | `Sidebar.tsx` (`.tree-head`), `globals.css` | Título "Temas e indicadores", campo e resumo ficam fixos no topo da área que rola (a barra até 1599 px; o cartão da árvore em tela cheia). O fundo cobre a árvore que passa por baixo e o recuo de cima; `scroll-padding-top` mantém à vista o item focado pelo teclado. "Filtros" não é fixo. Captura: `reference/screens/busca-barra-lateral-fixa.png`. Especificação: `docs/DESIGN-SYSTEM.md`, "Páginas (v2.3)" |
| 2.3.11 | Rótulos curtos e informação da tabela | `configs/portal/rotulos.toml` (API: `label` curto e `full_label`/`full_name` oficial), `DataTable.tsx` (`InfoIcon`, `.table-info`), `icons.tsx` (`InfoIcon`), `Sidebar.tsx` (`title` com o nome completo; dica dos cruzamentos por grupo), `globals.css` (cabeçalhos com quebra, `.info-button`) | Princípio 80/20: nomes longos da fonte viram rótulos curtos curados (até ~35 caracteres; o termo comum na frente: "Rede geral: forma principal") em Detalhar por, colunas, série, tooltip e legenda do mapa. O nome oficial fica no ⓘ "Sobre esta tabela" (unidade, nomes completos das colunas, como ler os %, linha de totais), no `title` e nas exportações. "% em relação a" vira "Calcular % por". Cabeçalhos quebram linha (9 a 22 ch). Captura: `reference/screens/tabela-rotulos-curtos.png` |
| 2.3.10 | Método no rodapé; tooltip da série | `KpiInfo.tsx` (`.meta-body`, `.method-list`, prop `correction`), `Sidebar.tsx` (sem `details.method`), `SeriesChart.tsx` (`additive`, `.share`), `globals.css`, `messages/pt-BR.json` (`meta.method`, `correctedBy`, `inUse`, `timeAggregation`) | "Como é calculado" sai da barra lateral. O rodapé ganha a seção **Método** ("Sobre este indicador · Método · Limitações (n)"): as correções por índice de preços, com a em uso primeiro e marcada "(em uso)", e a regra de agregação no tempo. Na tela cheia, o rodapé aberto vira um painel opaco acima da linha da fonte (máx. 60vh, com rolagem), sem empurrar o painel. Tooltip da série: valores em `fs-small`/800 (antes 16px/900), rótulos em `caption`, e o % do Total do período em cada categoria (KPIs aditivos), como na tabela. Capturas: `reference/screens/rodape-metodo.png`, `serie-tooltip-percentual.png` |
| 2.3.9 | Tabela em matriz | `DataTable.tsx` (`groupColumns`, `shareBase`, `COLLAPSE_AFTER`), API `ColumnOut.group`/`.parent` e `TableOut.footer`, `messages/pt-BR.json` (`table.share*`, `footer`, `expand`, `collapse`), `globals.css` (`.cell-group`, `.th-unit`, `.share-base`, `tfoot`) | Colunas agrupadas pela categoria da primeira dimensão (Total, Branca, Preta…); dentro da célula do grupo, o valor do grupo em negrito e, embaixo, as categorias das demais dimensões ("Homens 1.318.946 (47,6%)"). O grupo Total traz os totais de linha (Total por sexo). A unidade fica na segunda linha do cabeçalho ("pessoas", "pessoas (%)"). No fim, a linha de totais com o valor publicado do recorte ou do Brasil (não a soma da página). "% em relação a" (`select`): Território (linha, padrão), Grupo, Coluna (o recorte) e Total geral; método em "Como ler os %". % só em KPIs aditivos. Grupos com mais de 12 linhas começam recolhidos ("+ N detalhes"). Primeira coluna fixa na rolagem horizontal. Captura: `reference/screens/tabela-matriz.png` |
| 2.3.8 | Série: Total fora do gráfico com detalhe; pontas do eixo | `SeriesChart.tsx` (`depth`, `plotted`), API `SeriesItemOut.depth`, `lib/period.ts` (`timeTicks`, `slack`), `globals.css` (`.series-tip-total`) | Com "Detalhar por", o gráfico mostra só as combinações mais detalhadas (`depth` máximo): a série do Total (e, com duas dimensões, os subtotais) sai das linhas, da legenda e da escala do eixo Y (achatava as categorias); fica na primeira linha do tooltip, sem cor e com um filete embaixo, e na tabela. Sem detalhe, a linha única continua com área. As categorias têm o mesmo peso (2 px). No eixo de tempo, o primeiro e o último rótulo ficam centralizados no ponto quando cabem na margem; só se ancoram por dentro quando não cabem. Antes, a âncora por dentro tirava 2002 e 2025 de séries anuais (6579). Conferido em 153 KPIs |
| 2.3.7 | Corrigir por (índice de preços) | `Sidebar.tsx` (`fieldset.corrections`, `details.method`), `lib/state.ts` (`correcao=`), `DataTable.tsx` (unidade "R$ de jan/2018"), `Dashboard.tsx` (legenda com índice e mês-base), `messages/pt-BR.json` (`dashboard.correction`, `.nominal`, `.howCalculated`), `globals.css` | Em KPIs com `corrections` da API, o grupo "Corrigir por" (Nominal, IPCA geral, IPCA por grupo de despesa) aparece entre o grão e o Período, com o estilo de `.check`. O método fica recolhido em "Como é calculado" (`details`, `caption`). Com correção, a unidade das colunas vira "R$ de jan/2018", e a legenda acrescenta "· IPCA geral, preços de jan/2018". Captura: `reference/screens/pof-corrigir-por.png`. Regra: ADR-0020 |
| 2.3.6 | Escala do mapa sem colapso | `lib/scale.ts` (`roundestIn`, `niceCuts`) | Cada corte é o número mais redondo dentro da janela entre os quantis vizinhos: grosso com dados espalhados (4 mil, 25 mil), fino com dados concentrados (73,5; 74; 75). Antes, a esperança de vida (7362) ficava em "Até 80 · Mais de 80" no Brasil e num grupo só no Nordeste. Captura: `reference/screens/escala-esperanca-vida-nordeste.png` |
| 2.3.6 | Unidade nas colunas e % do Total | `DataTable.tsx` (cabeçalho "Rótulo (unidade)", `.share`), `lib/format.ts` (`unitShort`, `indexTitle`), `globals.css` (`.data-table td .share`) | Cada coluna mostra a unidade curta: "Total (%)", "Alimentação (R$)", "Total (índice)". Em KPIs aditivos, as categorias mostram também "(12,3%)" do Total do território, em `caption` / `text-muted`. A legenda de um número-índice diz a base: "Índice (2022 = 100)" |
| 2.3.6 | Rótulos limpos | API (`clean_label`, rótulo sem a numeração da fonte) | "2.1.2 Habitação" → "Habitação"; "1.Cereais e leguminosas" → "Cereais e leguminosas"; códigos da CNAE também saem. A hierarquia aparece pelo recuo do tooltip; faixas e contagens ("0 a 4 anos", "1 morador") ficam como estão |
| 2.3.5 | Nota de "Período por" conforme a regra | `Sidebar.tsx` (`.grain-note`), `messages/pt-BR.json` (`grainNotes.sum`, `.mean`, `.last`; sai `dashboard.grainNote`) | O seletor "Período por" aparece também em números-índice (PMC, PMS, PIM), acumulados (IPCA) e estimativas (LSPA). A nota diz como o período maior é calculado, conforme `time_aggregation` da API: soma, média ou último período publicado. Regra: ADR-0017 |
| 2.3.4 | Detalhar por: uma dimensão por vez | `Sidebar.tsx` (`.hint` no `fieldset`), `lib/state.ts` (só a primeira dimensão da URL), `globals.css` (`.sidebar fieldset .hint`), `messages/pt-BR.json` (`dashboard.dimensionsExclusive`) | Em KPIs com dimensões marginais (`exclusive_dimensions` da API: cada detalhe vem com os demais no Total, sem cruzamentos), marcar uma caixa desmarca as outras, e o aviso "Uma por vez: cada detalhe vem com os demais no Total." aparece sob "Detalhar por" (12 px, `text-muted`). Os demais KPIs seguem com várias caixas. Tooltip e tabela não mostram categorias sem dado no período (faixas de rendimento de outra edição da POF). KPI sem nível Brasil (POF de 1987 e 1995) abre no "Total das áreas da POF" (`defaultGeography`), com a tabela nas regiões metropolitanas e o cartão "sem mapa" (`map_levels` vazio na configuração). Captura: `reference/screens/detalhar-uma-por-vez.png`. Regra: ADR-0016 |
| 2.3.3 | Rodapé no fim da janela | `globals.css` (`body`, `#conteudo`) | Com pouco conteúdo, o rodapé fica no fim da janela, e não logo abaixo do cartão (correção pedida pelo mantenedor na página de erro). Painel e Início sem mudança |
| 2.3.3 | Rótulos T/S e eixo agrupado | `lib/period.ts` (`formatPeriod`, `groupedAxis`, `partsFit`, `slotWidth`), `SeriesChart.tsx` | Trimestre "T2 2026" e semestre "S1 2026" em todo o portal, iguais à `dim_period` da Gold (decisão do mantenedor). No gráfico de evolução, trimestres e semestres em duas linhas: a parte do ano em cima e o ano centralizado embaixo, com divisórias entre os anos; sem espaço para as partes, uma linha só com os anos, e o ano com dois dígitos ("26") se o de quatro não couber (salvo na virada do século). Captura: `reference/screens/serie-eixo-semestres.png`. Especificação: `docs/DESIGN-SYSTEM.md`, seção 9 (Séries) |
| 2.3.2 | Período por (grão de tempo) | `Sidebar.tsx` (`fieldset.grains`, `.grain-note`), `Dashboard.tsx`, `ExportMenu.tsx`, `lib/state.ts` (`grao=`, `grainPeriods`), `lib/period.ts` (semestre), `lib/format.ts` (`incomplete_period`), `globals.css`, `messages/pt-BR.json` (`dashboard.grain`, `dashboard.grainNote`, `grains.*`) | Rádios Mês, Trimestre, Semestre e Ano acima do Período, só em KPIs que somam no tempo (`time_grains` da API). Ano, semestre e trimestre são a soma dos meses (valor derivado); período incompleto fica "período incompleto". Padrão: o último período completo. Especificação: `docs/DESIGN-SYSTEM.md`, "Páginas (v2.3)"; regra: ADR-0013 |
| 2.3.1 | Fonte de indicador fora do IBGE | `KpiInfo.tsx`, `messages/pt-BR.json` (`meta.tableOther`) | A linha "Fonte" usa a instituição e o sistema que a API informa (`source.institution`, `source.system`), por exemplo "MJSP · SINESP-VDE"; sem esses campos, continua "IBGE · Tabela SIDRA N" |

## Estado da v2.1: o que o portal tem além da v2

Para o Claude Design: ao gerar a próxima versão, **parta destes arquivos** e preserve os
itens abaixo. A v2 havia perdido os tokens do recorte; eles foram repostos aqui.

| Item | Onde | Regra |
|---|---|---|
| Tokens do recorte | `tokens/` (`map-context`, `map-context-stroke`, `map-focus`) | Fora do recorte em cinza neutro com divisas de 1 px; contorno do recorte com 2 px por cima de tudo (`docs/DESIGN-SYSTEM.md`, seção 9) |
| Recorte seletivo do mapa | `MapView.tsx`, `lib/zoom.ts`, `Dashboard.tsx` | Duplo clique, roda ou `+` abrem o recorte: só ele se subdivide (Região → UF → Município) e recebe o gradiente; trilha "Brasil › Região › UF" sobre o mapa; botões +, − e "Ver o Brasil inteiro" |
| Legenda | `MapView.tsx`, `lib/scale.ts`, `lib/format.ts` | Título pela unidade ("População"…); 7 grupos por quantis dentro do recorte, com limites redondos e pontas abertas ("Até 4 mil" … "Mais de 15 mil"); entrada "Fora do recorte" |
| Tabela localiza o clique no mapa | `DataTable.tsx`, `Dashboard.tsx` | A tabela vai à página do território e rola por dentro até a linha (estado `aria-selected` com barra) |
| Limpar filtros | `Sidebar.tsx` | Botão no fim do bloco "Filtros" |
| Sem rolagem dupla | `globals.css` | `.main` e `.sidebar` com `position: relative` e `min-height: 0`; em tela cheia, gráfico e tabela dividem a altura em frações fixas |
| Gráfico no tamanho real | `SeriesChart.tsx`, `globals.css` | O SVG acompanha o quadro (`.series-plot`), o texto não encolhe |
| Tooltip dentro da janela | `DetailTooltip.tsx` | Mede a própria altura e não passa da borda inferior |
| Página indisponível | `app/error.tsx` | "Dados temporariamente indisponíveis", com nova tentativa automática |
| Sem dicas nativas no mapa | `MapView.tsx` | Sem `<title>` no SVG do mapa; território clicado sem anel de foco (só o traço) |

---

*Texto da v2 (referência):* foi escrito sobre o commit `3a7fb4f` e mantém todas as classes,
rótulos e `aria-*` de que os testes dependem.

> **Para o Claude Code:** leia este arquivo inteiro e depois `docs/DESIGN-SYSTEM.md`.
> Siga a seção "Passo a passo". Os arquivos em `portal/` espelham `apps/portal/`:
> compare cada um com o arquivo atual do projeto antes de substituir (`diff`), e
> preserve qualquer mudança feita no projeto depois do commit acima.

## Conteúdo

```
design-system/
├── README.md                 ← este arquivo (passo a passo e critérios de aceite)
├── docs/DESIGN-SYSTEM.md     ← especificação completa (marca, tokens, estados, componentes, dados)
├── tokens/
│   ├── tokens.css            ← variáveis CSS (claro, dark, prefers-color-scheme)
│   └── tokens.json           ← os mesmos valores em JSON (para outras ferramentas)
├── VERSION                   ← 2.3.11
├── reference/                ← telas do canvas (fontes) e capturas dos componentes
├── assets/brand/             ← logos em SVG (texto convertido em curvas) e ícones PNG
├── assets/icons/             ← github.svg (Bootstrap Icons, MIT) + licença
└── portal/                   ← arquivos prontos, nos mesmos caminhos de apps/portal/
    ├── messages/pt-BR.json
    └── src/
        ├── app/  globals.css · layout.tsx · icon.svg · apple-icon.png
        ├── styles/tokens.css
        ├── lib/  theme.ts (novo) · scale.ts · download.ts
        └── components/
            Logo.tsx (novo) · ThemeToggle.tsx (novo) · Header.tsx · Sidebar.tsx
            MapView.tsx · SeriesChart.tsx · DetailTooltip.tsx · ExportMenu.tsx
            components.test.tsx
```

## O que muda no portal

| Arquivo | Tipo | O que muda |
|---|---|---|
| `src/styles/tokens.css` | novo | Todos os tokens `--odbr-*`, tema claro, dark e preferência do sistema |
| `src/app/globals.css` | substitui | Usa os tokens; estados de hover, pressionado, ativo, foco e desabilitado; tooltip novo; aliases das variáveis antigas (`--ink`, `--line`…) para estilos inline existentes |
| `src/app/layout.tsx` | substitui | Fonte Nunito (`next/font/google`), script que aplica o tema salvo antes da pintura, `themeColor` |
| `src/app/icon.svg`, `apple-icon.png` | novo | Favicon e ícone (convenção de arquivos do App Router) |
| `src/lib/theme.ts` | novo | `SEQ` (7 cores do mapa), `SERIES` (10 cores), `ZERO_COLOR`, `MISSING_COLOR`, `CHART`, `token()`, `resolveSvgColors()` |
| `src/lib/scale.ts` | substitui | `schemeBlues` → `SEQ`. Lógica de quantis intacta |
| `src/lib/download.ts` | substitui | Exportação SVG/PNG resolve `var(--…)` e usa o fundo do tema |
| `src/components/Logo.tsx` | novo | Logo ODBr em texto, cores por token |
| `src/components/ThemeToggle.tsx` | novo | Botão claro/dark (salva em `localStorage`) |
| `src/components/Header.tsx` | substitui | Faixa da marca, logo, abas com estados, botão de tema |
| `src/components/Sidebar.tsx` | substitui | Bloco **Filtros** no topo (Nível territorial, Período, Detalhar por) + Temas e indicadores. Recebe `level`, `period`, `onLevel`, `onPeriod` |
| `src/components/Dashboard.tsx` | substitui | Sem barra de filtros na área central; grade `.dash-grid` com áreas: cabeçalho do mapa (título + SVG/PNG), mapa, cabeçalho de dados ("Gráfico e tabela" + CSV/XLSX/Parquet/JSON), gráfico, tabela, "Sobre este indicador" |
| `src/components/KpiInfo.tsx` | substitui | Linha da fonte sempre visível; descrição, unidade, períodos e limitações em `<details>` (aberto até 1599 px, fechado e como rodapé a partir de 1600 px) |
| `src/lib/useMediaQuery.ts` | novo | `useMediaQuery()` com `useSyncExternalStore`; `WIDE_QUERY = (min-width: 1600px)` |
| `src/components/MapView.tsx` | substitui | `style={{ fill }}`, fundo por token, contorno fino com muitos polígonos, selecionado desenhado por último, hachura para sigilo, `aria-pressed` |
| `src/components/SeriesChart.tsx` | substitui | `schemeTableau10` → `SERIES`; área sob a série principal; até 6 rótulos no eixo X |
| `src/components/DetailTooltip.tsx` | substitui | Tooltip visual: barras, divisão por sexo com ícones, pictograma para "só sexo" |
| `src/components/ExportMenu.tsx` | substitui | Dois componentes: `MapImageExport` (SVG, PNG — vai sobre o mapa) e `DataExport` (CSV, XLSX, Parquet, JSON — vai sobre gráfico e tabela). Cada um com seu "Gerando arquivo…" e erro |
| `src/components/components.test.tsx` | substitui | Testes do tooltip atualizados para o novo layout (DataTable igual) |
| `messages/pt-BR.json` | substitui | `site.name` = "Open Data Brasil"; `theme.toDark/toLight`; `dashboard.figureNote`, `dashboard.filters`, `dashboard.chartAndTable`; `export.download` |

Nenhum arquivo da API, do contrato OpenAPI ou de `lib/api.ts`, `lib/state.ts`, `lib/format.ts`,
`DataTable.tsx` ou `IndicatorSearch.tsx` precisa mudar: o visual deles vem do `globals.css`.

## Layout do painel (regra para todo o portal)

- **Filtros sempre na barra lateral**, no bloco "Filtros", acima de "Temas e indicadores".
  A área central não tem selects.
- **Botões junto do que exportam:** "Imagem do mapa" (SVG, PNG) no cabeçalho do mapa;
  "Baixar dados" (CSV, XLSX, Parquet, JSON) no cabeçalho de "Gráfico e tabela".
- **Até 1599 px** (janela em meia tela): empilhado — título e botões do mapa, mapa,
  "Gráfico e tabela" com os botões de dados, gráfico e tabela lado a lado, "Sobre este indicador".
  Abaixo de 900 px tudo vira uma coluna e a barra lateral vai para o topo.
- **A partir de 1600 px** (tela cheia): sem rolagem da página. Mapa à esquerda ocupando a
  altura toda (legenda no canto inferior esquerdo); à direita, gráfico em cima e tabela
  embaixo (a tabela rola por dentro); fonte do indicador como rodapé, com
  "Sobre este indicador" recolhido.
- Tudo é feito por CSS (`.dash-grid` + `grid-template-areas`); o JSX é o mesmo nas três larguras.

## Passo a passo

1. **Criar uma branch** (ex.: `feat/design-system-odbr`).
2. **Tokens e estilos:** copiar `portal/src/styles/tokens.css` e substituir `src/app/globals.css`.
   Rodar o portal: tudo deve continuar funcionando só com isto (os aliases cobrem os estilos inline).
3. **Fonte, tema e ícones:** substituir `layout.tsx`; copiar `icon.svg` e `apple-icon.png` para
   `src/app/`; criar `lib/theme.ts`, `components/Logo.tsx`, `components/ThemeToggle.tsx`;
   substituir `Header.tsx` e `messages/pt-BR.json` (mesclar se o arquivo tiver chaves novas).
4. **Cores dos dados (d3):** substituir `lib/scale.ts`, `lib/download.ts`, `MapView.tsx` e
   `SeriesChart.tsx`. Regra: em SVG, cor por token vai em `style`, nunca em atributo
   (`style={{ fill }}`, não `fill={…}`), porque `var()` não funciona em atributo de apresentação.
5. **Componentes e layout:** criar `lib/useMediaQuery.ts`; substituir `Sidebar.tsx`,
   `Dashboard.tsx`, `ExportMenu.tsx`, `KpiInfo.tsx`, `DetailTooltip.tsx` e `components.test.tsx`.
   Se `ExportMenu` for importado em outro lugar, trocar por `DataExport` e/ou `MapImageExport`.
6. **Dependência:** `d3-scale-chromatic` deixa de ser usado. Pode sair de `package.json`
   (e `@types/d3-scale-chromatic`) se nenhum outro arquivo importar.
7. **Verificar:** `npm run typecheck`, `npm run lint`, `npm test`, `npm run e2e`.

## Critérios de aceite

- [ ] `typecheck`, `lint`, `test` e `e2e` passam (os e2e não precisam de mudança).
- [ ] Tema claro igual às pranchas; ao clicar no botão de tema, tudo vira dark,
      incluindo mapa, legenda, gráfico, tabela e tooltip; a escolha persiste ao recarregar.
- [ ] Sem escolha salva, o portal segue o tema do sistema operacional.
- [ ] Nível territorial, Período e "Detalhar por" ficam no bloco "Filtros" da barra lateral.
- [ ] SVG/PNG ficam no cabeçalho do mapa; CSV/XLSX/Parquet/JSON no cabeçalho de "Gráfico e tabela".
- [ ] Janela até 1599 px: layout empilhado. Janela ≥ 1600 px: mapa à esquerda, gráfico e
      tabela à direita, rodapé com a fonte, sem rolagem da página (testar em 1920 × 1080).
- [ ] Menu lateral: hover muda fundo e cor; KPI ativo tem fundo selecionado e barra de 3 px
      à esquerda (azul no claro, amarela no dark); `summary` com seta que gira.
- [ ] Abas do cabeçalho: hover com sublinhado claro; página atual com sublinhado de 3 px.
- [ ] Linhas da tabela: hover, pressionado e selecionado (`aria-selected`) com barra.
- [ ] Mapa: contorno 0,5 px (0,25 px em municípios), hover 1,5 px, selecionado 2,5 px
      amarelo por cima dos vizinhos, foco por teclado visível.
- [ ] Tab mostra o anel de foco (3 px, azul no claro, amarelo no dark) em todo controle;
      clique com mouse não mostra o anel.
- [ ] Tooltip: cor ou raça › sexo mostra barras e divisão com ícones; só sexo mostra o
      pictograma; valores sob sigilo aparecem como "X (sigilo)"; abre para cima na metade
      de baixo da tela e não sai pela borda direita.
- [ ] SVG e PNG exportados mantêm as cores do tema atual.
- [ ] Com `prefers-reduced-motion: reduce`, sem transições nem animação do tooltip.

## Observações

- **Nome:** `messages/pt-BR.json` passa a usar "Open Data Brasil" (antes "Dados Abertos do Brasil").
  O título da aba e o logo mudam junto. Reverter só essa chave se o nome oficial ainda não
  estiver decidido.
- **Fonte:** `next/font/google` baixa a Nunito no build e serve do próprio domínio.
  Se o build rodar sem internet, trocar por `next/font/local` com os arquivos da Nunito.
- **Valores do mapa** continuam por quantis (ADR-0009); só as cores mudaram.
- **CSS `:has()`** é usado só para negrito do checkbox marcado (melhoria progressiva).

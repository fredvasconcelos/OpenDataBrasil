# Open Data Brasil — Design System v2.1

Especificação de referência. Os valores exatos estão em `tokens/tokens.css`;
este documento explica o uso e as regras.

## 1. Princípios

1. **Dados em primeiro lugar.** A interface é neutra (azul-marinho, cinzas frios); a cor forte fica nos dados.
2. **Fonte sempre visível.** Todo número leva unidade, período e origem.
3. **Acessível por padrão.** Contraste AA, teclado em tudo, foco visível, nada só por cor.
4. **Um tema, dois modos.** Mesma marcação; claro e dark mudam só tokens.

## 2. Marca

- **Logo:** "ODBr" em Nunito 900, espaçamento −0,035 em. Cores: **O** azul, **D** amarelo, **Br** verde.

| Versão | O | D | Br | Fundo |
|---|---|---|---|---|
| Principal | #1351B4 | #F2B600 | #168821 | claro |
| Negativo | #5992ED | #FFCD07 | #2DB34A | #071D41 |
| Monocromático | #071D41 (tudo) | | | claro |
| Mono branco | #FFFFFF (tudo) | | | azul ou escuro |

- **Assinatura horizontal:** logo + divisor de 2–3 px + "Open Data / Brasil" (900). Abaixo de 900 px de largura, só o logo.
- **Símbolo/favicon:** quadrado azul (#1351B4, raio 25%), "O" branco e ponto amarelo. Em 16 px, só o "O".
- **Faixa da marca:** 4 px no topo do portal e do tooltip; proporção 2 : 1 : 1 (azul, amarelo, verde).
- **Não fazer:** reproduzir a marca do gov.br; mudar a ordem das cores; usar o amarelo #FFCD07 em texto sobre branco.
- Arquivos: `assets/brand/` (SVG com texto em curvas; PNG 32, 180 e 512 px).

## 3. Cores

Primitivas: Azul 500 #1351B4 · Azul 700 #0C326F · Marinho 900 #071D41 · Azul 400 #5992ED ·
Amarelo 600 #F2B600 · Amarelo 400 #FFCD07 · Verde 600 #168821 · Verde 400 #2DB34A.

Tokens semânticos (claro → dark):

| Grupo | Token | Claro | Dark | Uso |
|---|---|---|---|---|
| Superfície | `bg-page` | #F4F6F9 | #071D41 | Fundo da página |
| | `bg-surface` | #FFFFFF | #0B2852 | Cartões, menu, tooltip, mapa |
| | `bg-header` | #FFFFFF | #0C326F | Cabeçalho |
| | `bg-subtle` | #F4F6F9 | #0C326F | Cabeçalho de tabela, desabilitado |
| Interação | `bg-hover` | #F0F4FA | #12376F | Ponteiro em cima |
| | `bg-pressed` | #DCE7F8 | #1A4485 | Clicando |
| | `bg-selected` | #E8F0FC | #163D7A | Ativo / selecionado |
| | `indicator` | #1351B4 | #FFCD07 | Barra do ativo, aba atual |
| | `tab-hover` | #C5D9F5 | #2A5FAE | Sublinhado da aba no hover |
| | `focus` | #1351B4 | #FFCD07 | Anel de foco |
| Texto | `text` | #071D41 | #FFFFFF | Títulos, rótulos |
| | `text-body` | #333E4F | #DCE6F5 | Texto e números |
| | `text-muted` | #555F6E | #C5D4EB | Apoio, eixos |
| | `text-disabled` | #6B7686 | #8FA3C2 | Desabilitado |
| | `text-active` | #1351B4 | #FFFFFF | Item ativo / hover |
| | `link` | #1351B4 | #8DB6F4 | Links |
| Ação | `primary` | #1351B4 | #5992ED | Botão principal |
| | `primary-hover` | #0C3F94 | #7AA8F2 | |
| | `primary-pressed` | #0C326F | #4A7FD6 | |
| | `on-primary` | #FFFFFF | #071D41 | Texto sobre primária |
| Borda | `border` | #DDE3EC | #234476 | Cartões |
| | `border-control` | #C5D0DE | #2A4A80 | Botões secundários |
| | `border-strong` | #9AA6B8 | #5992ED | Campos |
| | `divider` | #EEF1F5 | #1B3A6B | Linhas de tabela |
| Feedback | `success` / `-bg` | #168821 / #E3F5E1 | #2DB34A / #0F3A24 | |
| | `warning` / `-bg` | #5C4300 / #FFF6D6 | #FFE38A / #2E2A12 | Aviso do portal |
| | `danger` / `-bg` | #B3261E / #FCE8E6 | #FF8A80 / #3D1418 | Erros |
| | `info` / `-bg` | #1351B4 / #E8F0FC | #8DB6F4 / #163D7A | |

Por que o foco é azul no claro: amarelo sobre branco tem contraste 1,9:1, abaixo dos 3:1
exigidos para indicadores. No dark, o amarelo tem ótimo contraste e vira o foco.

## 4. Tipografia

Nunito, pesos 600–900. Números tabulares em tabelas, tooltip e eixos (`font-variant-numeric: tabular-nums`).

| Token | Tamanho / peso | Uso |
|---|---|---|
| `fs-page-title` | 30 / 900, −0,5 px | H1 da página |
| `fs-kpi` | 28 / 900 | Total no tooltip |
| `fs-card-title` | 17 / 800 | H2 de cartões |
| `fs-subtitle` | 14 / 800 | H3, grupos |
| `fs-body` | 15 / 600, altura 1,5 | Texto |
| `fs-ui` | 14 / 700 | Menu, abas, campos, tabela |
| `fs-small` | 13 / 600 | Apoio, aviso, paginação |
| `fs-caption` | 12 / 700 | Eixos, rótulos de filtro |
| `fs-micro` | 11 / 700 | Legenda, notas do tooltip |
| sobrelinha | 12 / 800, +1,5 px, maiúsculas | "Temas e indicadores", "Detalhar por" |

## 5. Espaço, forma, elevação

- Espaço (base 4): 4 · 8 · 12 · 16 · 20 · 24 · 32 · 40.
- Raios: 4 (legenda) · 8 (item de menu) · 10 (campos, legenda do mapa) · 14–16 (cartões, tooltip) · pílula (botões).
- Elevação: cartões só com borda; `shadow-1` em menus suspensos; `shadow-2` no tooltip.
- Layout: cabeçalho 64 px + faixa 4 px; barra lateral 260 px (290 px em tela cheia); área com 32 px de respiro; 20 px entre cartões.

### Layout do painel

| Largura da janela | Arranjo |
|---|---|
| < 900 px | Uma coluna; barra lateral no topo (máx. 40% da altura) |
| 900–1599 px | Título + SVG/PNG · mapa · "Gráfico e tabela" + CSV/XLSX/Parquet/JSON · gráfico e tabela lado a lado · "Sobre este indicador" aberto |
| ≥ 1600 px | Tela cheia sem rolagem: [título + SVG/PNG \| "Gráfico e tabela" + exportação] · [mapa \| gráfico] · [mapa \| tabela] · rodapé com a fonte |

Regras fixas: **filtros só na barra lateral** (bloco "Filtros": Nível territorial, Período por, Período, Detalhar por — acima de "Temas e indicadores"); **cada botão de exportação fica junto do que exporta** (imagem → mapa; dados → gráfico e tabela).

## 6. Movimento e cursor

| O quê | Valor |
|---|---|
| Hover (cor, fundo, borda) | 120 ms, `cubic-bezier(.2,0,0,1)` |
| Pressionado | 60 ms |
| Tooltip entra | 160 ms após 80 ms; opacidade + 4 px para cima |
| Tooltip sai | imediato |
| `cursor: pointer` | menu, abas, botões, linhas, territórios |
| `cursor: not-allowed` | desabilitados · `progress` durante exportação |

`prefers-reduced-motion: reduce` zera transições e a animação do tooltip.

## 7. Estados do ponteiro

Regra geral: **hover só muda cor ou fundo, nunca tamanho** (nada pula de lugar).
Ativo leva barra indicadora. Foco por teclado (`:focus-visible`) aparece por cima de qualquer estado.

| Componente | Padrão | Hover | Pressionado | Ativo / marcado | Foco | Desabilitado |
|---|---|---|---|---|---|---|
| Item do menu (`.sidebar li button`) | transparente, texto | `bg-hover`, `text-active` | `bg-pressed` | `aria-pressed=true`: `bg-selected`, 800, barra 3 px `indicator` à esquerda | anel interno | `text-disabled` |
| Grupo do menu (`summary`) | 800, seta › | `bg-hover` | `bg-pressed` | aberto: seta gira 90° | anel interno | — |
| Aba (`.header nav a`) | `text-muted` | `text-active` + sublinhado 3 px `tab-hover` | `bg-hover` | `aria-current=page`: sublinhado 3 px `indicator` | anel interno | — |
| Botão principal (`button.primary`) | `primary` | `primary-hover` | `primary-pressed` | — | anel | `bg-subtle`, `text-disabled` |
| Botão secundário (`button`) | pílula, borda `border-control`, texto `link` | `bg-hover`, borda `primary` | `bg-pressed` | exportando: `aria-busy` | anel | idem |
| Checkbox "Detalhar por" (`.check`) | caixa 16 px | `bg-hover` na linha | — | marcado: caixa `primary`, rótulo 800 | anel | — |
| Linha da tabela | — | `bg-hover` | `bg-pressed` | `aria-selected=true`: `bg-selected`, 800, barra 3 px | anel | — |
| Território (path) | contorno `map-stroke` 0,5 | contorno `map-hover` 1,5 | — | `.selected`: `map-selected` 2,5, desenhado por último | contorno `focus` 3 | sem dado: `map-missing` |
| Campo / select | borda `border-strong` | borda `primary` | — | — | anel | — |

## 8. Componentes

- **Cabeçalho:** faixa da marca, logo + nome, abas, à direita: "Contato" (pílula 36 px, ícone de envelope + texto em `text-active`), botão redondo de 40 px com o ícone do GitHub (rótulo "Repositório do projeto no GitHub" em `aria-label`) e botão de tema. Abaixo de 720 px, "Contato" vira só ícone. Aviso do portal logo abaixo (`role="note"`, fundo `warning-bg`).
- **Rodapé:** marinho nos dois temas (#071D41 claro; #04122A com divisa #1B3A6B no dark), logo nas cores do negativo, links "Sobre os dados", "Contato" e "Código no GitHub" (ícone + texto, #C5D4EB → branco no hover). No Painel de análise, faixa fina de 44 px. Em página curta (ex.: "Dados temporariamente indisponíveis"), o rodapé fica no fim da janela: o `body` é uma coluna com `min-height: 100dvh` e o conteúdo (`#conteudo`) ocupa o espaço livre (v2.3.3).
- **Ícone do GitHub:** sempre o `github` do Bootstrap Icons (MIT, `assets/icons/github.svg`, `viewBox 0 0 16 16`, `fill: currentColor`), sem alterar a forma. Endereços de contato e do repositório vêm de `NEXT_PUBLIC_CONTACT_URL` e `NEXT_PUBLIC_REPO_URL`; sem valor, o link não aparece.
- **Barra lateral:** bloco "Filtros" com borda (selects "Nível territorial" e "Período", 40 px, rótulo acima; "Detalhar por" em `fieldset` com checkboxes na ordem de `dimension_order`; em KPIs com dimensões marginais, `exclusive_dimensions`, marcar uma desmarca as outras, e uma linha `.hint` 12 px `text-muted` abaixo da sobrelinha diz "Uma por vez: cada detalhe vem com os demais no Total." — v2.3.4, ADR-0016); abaixo, "Temas e indicadores" com temas e subtemas em `details/summary` e KPIs como botões `aria-pressed`.
- **Cabeçalho do mapa:** caminho (tema › subtema · nível · período) + H1 do indicador; à direita, "Imagem do mapa" (SVG, PNG).
- **Cabeçalho de dados:** "Gráfico e tabela" (H2); à direita, "Baixar dados" (CSV, XLSX, Parquet, JSON).
- **Cartão:** `bg-surface`, borda, raio 16, padding 24.
- **Exportar:** dois grupos separados, cada um junto do que exporta. Durante a exportação, os botões do grupo ficam desabilitados com "Gerando arquivo…". Falha em texto `danger` (`role="alert"`) logo abaixo do grupo.
- **Erro ao carregar:** caixa `danger-bg` com ícone, mensagem e botão principal "Tentar de novo".
- **Carregando:** `aria-busy="true"` + "Carregando…"; no tooltip, barras de esqueleto.
- **Vazio:** "Escolha um indicador no menu." / "Este nível não tem mapa…".
- **Tabela:** cabeçalho fixo `bg-subtle`, ordenação por botão no título ("↓/↑"), números à direita, paginação "1–20 de 5.570" + Anterior/Próxima.
- **Sobre este indicador:** linha da fonte sempre visível (Fonte · tabela · link oficial · licença · release); "Sobre este indicador" recolhível com descrição, Unidade, Períodos, Versão (mono) e Limitações. Aberto até 1599 px; em tela cheia vira rodapé, fechado.
- **Pular para o conteúdo:** aparece só com Tab.

### Páginas (v2.3)
- **Temas:** cada tema tem um ícone (traço 2 px, viewBox 24, `lib/themes.ts`) e uma família de cor (`--odbr-theme-<família>-band | icon-bg | icon | border`, claro e dark). Famílias: azul, verde, ocre, petróleo, roxo, laranja, magenta, ardósia. A cor fica na faixa do cabeçalho do cartão, no quadro do ícone e na borda — nunca no texto nem nos dados (gráficos e mapa seguem a seção 9).
- **Etiquetas de tema:** pílula 36 px com ícone em círculo de 26 px na cor da família, nome e contagem; selecionada em `primary` com texto `on-primary`. Funcionam como filtro (`aria-pressed`).
- **Início:** título 40/900, lead 17/600, números em pílulas, busca grande (56 px, raio 28, borda 2 px `border-strong`) que procura no nome, tema, subtema e nº da tabela, ignorando acentos. Em "Todos" sem busca: grade de 3 colunas (2 em ≤ 1023 px, 1 em ≤ 639 px) com até 4 indicadores por tema e "Ver todos os N →". Com tema ou busca: um painel por tema com os subtemas em colunas (`columns: 3 260px`).
- **Prévia do indicador:** diálogo modal 760 px, raio 20, véu `--odbr-overlay`; faixa na cor do tema com ícone, caminho (tema › subtema) e situação; nome 26/900, descrição, lista de metadados (Fonte e tabela com link oficial, Detalhar por, Outras classificações, Unidade, Períodos, Níveis com mapa, Licença, Versão dos dados), Limitações, "Abrir no painel". Foco inicial em "Fechar"; Esc e clique no véu fecham; o foco volta ao indicador.
- **Sobre os dados:** cartão do release (id em mono, data de ativação, situação da licença em pílula de aviso) + 3 números; busca e etiquetas; um acordeão por tema (faixa na cor do tema) com cabeçalho de colunas e uma linha por indicador: nome + subtema, tabela, situação, Detalhar por, Outras classificações. A linha abre com descrição, limitações, "Abrir no painel", link da tabela na fonte e os metadados. Em ≤ 899 px a linha mostra só nome e tabela.
- **Busca da barra lateral:** campo 40 px sob "Temas e indicadores" com tecla `/`; resumo "N indicadores em M temas" + "Limpar"; a árvore filtra enquanto digita, o termo vem marcado (`mark` #FFE58A) e, quando o achado está na descrição, aparece um trecho abaixo do nome. Sem resultado: mensagem com dica.
- **Período por (v2.3.2, ADR-0013):** grupo de rádios `fieldset.grains` (Mês, Trimestre, Semestre, Ano) acima do select "Período", com as opções em linha que quebram se faltar espaço e o estilo de `.check`. Só aparece em KPIs com mais de um grão: fluxos (Sinesp, abates), números-índice (PMC, PMS, PIM) e acumulados (IPCA). Taxas sem regra oficial de agregação e séries anuais não mostram o grupo. Escolher um grão leva `grao=` à URL e troca a lista do select pelos períodos do grão; sem período escolhido, vale o último período completo (ex.: o último ano com os 12 meses). Fora do grão publicado, uma nota em `caption` / `text-muted` explica a regra do KPI (`time_aggregation`, v2.3.5, ADR-0017): soma ("Soma dos períodos publicados (valor derivado)…"), média ("Média dos períodos publicados…", números-índice) ou último valor ("Valor do último período publicado…", acumulados em 12 meses). Período incompleto aparece como "período incompleto" no mapa, na tabela e no tooltip. Rótulos (v2.3.3): "T1 2024" e "S1 2024", os mesmos da `dim_period` da Gold (antes, "1º tri 2024").
- **Busca da barra lateral fixa (v2.3.1):** o título "Temas e indicadores", o campo e o resumo formam um bloco fixo (`position: sticky`, `.tree-head`) no topo da área que rola: a barra inteira até 1599 px e só o cartão da árvore (`.themes`) em tela cheia. Ao rolar a árvore, o bloco continua à vista; o fundo `bg-surface` cobre os itens que passam por baixo e também o recuo de cima do contêiner, para nenhum item aparecer acima do bloco. Um item focado pelo teclado não fica escondido atrás do bloco (`scroll-padding-top`). O bloco "Filtros" não é fixo e sai de vista ao rolar.

## 9. Visualização de dados (d3)

### Mapa coroplético (`MapView`, `lib/scale.ts`)
- Quantis em 7 faixas (ADR-0009). Com menos faixas, usar as **últimas** cores da escala.
- Escala claro: #EAF1FC · #C5D9F5 · #9CBEEE · #6E9FE3 · #2F6ACB · #1351B4 · #0A3580.
- Escala dark (clara = mais): #16335F · #1E4785 · #2A5FAE · #3B76D0 · #5992ED · #8DB6F4 · #C5D9FA.
- Zero (classe própria): #F3F0E6 / #1C2B45. Sem dado: #D9DDE3 / #3A4A63. Sigilo: sem dado + hachura 45°.
- Contorno, hover, seleção e foco: ver seção 7. Legenda no canto inferior esquerdo, fundo 92%.
- **Recorte (ampliação seletiva):** ao aproximar uma região ou UF, só o recorte se
  subdivide e leva a escala sequencial (grupos calculados dentro do recorte). O resto do
  país fica no nível do recorte, com `map-context` (#E3E6EA / #253041) e divisas
  `map-context-stroke` (#FFFFFF / #0B2852) de 1 px. O contorno do recorte usa
  `map-focus` (#071D41 / #FFFFFF), com 2 px, por cima de tudo. A legenda ganha a
  entrada "Fora do recorte". O cinza do contexto é neutro (sem matiz) para não ser
  confundido com a primeira classe da escala, que é azulada.
- **Legenda:** título pela unidade do indicador ("População", "Percentual (%)",
  "Densidade (hab/km²)", "Área (km²)"). Os 7 grupos são quantis com limites
  arredondados para números redondos (1; 1,5; 2; 2,5; 3; 4; 5; 6; 7; 8; 9 × 10ⁿ), sem
  grupos vazios; pontas abertas: "Até 4 mil" · "4 mil – 5 mil" · … · "Mais de 15 mil".

### Séries (`SeriesChart`)
- Até 10 cores, nesta ordem — claro: #1351B4 · #168821 · #6E9FE3 · #A87400 · #071D41 · #D9480F · #0E7C86 · #8E44AD · #5C6B82 · #C2185B.
- Dark: #5992ED · #2DB34A · #C5D9FA · #FFCD07 · #8FA3C2 · #FF8A4C · #2EC4C9 · #B98AF0 · #FFFFFF · #F06292.
- As cores seguem a ordem das séries, não o nome da categoria (nenhuma cor deve sugerir tom de pele).
- Série principal 2,5 px com área (opacidade 0,08 / 0,15); demais 1,5 px. Pontos com miolo da superfície. Grade `chart-grid`, eixo zero `chart-axis`, rótulos `chart-label` 12/700. Ausências de valor (sigilo, "…") interrompem a linha.
- **Eixo X de tempo (v2.3, `lib/period.ts`):** a posição é proporcional ao tempo. Códigos aceitos: `AAAA`, `AAAAMM`/`AAAA-MM` (mês), `AAAAT1`/`AAAA-Q1` (trimestre) e `AAAA01…04` como trimestre quando a série inteira usa só 01–04 em mais de um ano. Código não reconhecido → eixo ordinal com a mesma regra de rótulos.
- **Rótulos do eixo X:** menor passo redondo que caiba na largura (ano: 1, 2, 5, 10, 20, 25, 50; semestre: 1, 2, 4, 10…; trimestre: 1, 2, 4, 8…; mês: 1, 2, 3, 6, 12, 24…), mais o primeiro e o último período, sempre visíveis e ancorados por dentro (`start` / `end`). Rótulo interno que encostaria numa ponta é descartado. Em séries mensais com passo ≥ 12, só o ano. Margem esquerda calculada pelo maior rótulo do eixo Y.
- **Eixo agrupado de trimestres e semestres (v2.3.3, `groupedAxis`):** duas linhas. Em cima, a parte do ano (T1…T4, S1/S2, 12/700), uma por período, com marca de 4 px. Embaixo, o ano (12/800), centralizado no trecho que os períodos dele ocupam, e divisórias verticais `chart-grid` entre os anos, que cruzam as duas linhas. As partes só aparecem se todas couberem (fatia ≥ largura de "T4" + 8 px); senão, o eixo volta a uma linha, só com os anos e as divisórias, e a margem inferior volta a 28 px (com as partes, 46 px). Sem espaço para o ano com 4 dígitos em cada grupo, ele fica com 2 ("26"), a pedido do mantenedor, exceto em séries que atravessam a virada do século (lá "97" e "26" seriam ambíguos). Ainda sem espaço, os anos seguem um passo redondo (1, 2, 5, 10…); o ano que encostaria no anterior (ex.: o ano corrente com só dois trimestres) fica sem rótulo. Mês e ano continuam no eixo de uma linha. Captura: `reference/screens/serie-eixo-semestres.png`.
- **Períodos não publicados:** salto maior que 1,5× o passo típico (mediana) liga os pontos com traço `2 4`, 70% de opacidade, e a legenda ganha "Períodos sem publicação".
- **Tooltip da série:** HTML dentro de `.series-plot` (não `<title>` nativo). Mostra o período por extenso, uma linha por série (ponto de cor, rótulo, valor 16/900, até 8 séries + "+N séries · veja a tabela") e a unidade. Abre 12 px à direita do ponto mais alto do período; se não couber, vira para a esquerda; se não couber acima, abre abaixo; nunca sai do quadro (4 px). Guia vertical tracejada `3 3` e pontos do período ampliados (+1,5 px, preenchidos). O período ativo é o mais próximo do ponteiro no eixo de tempo.
- **Teclado:** o gráfico recebe foco; ← → percorrem os períodos, Home/End vão às pontas, Esc fecha; região `aria-live` anuncia período e valores.

### Tooltip do mapa (`DetailTooltip`)
- 340 px, faixa da marca no topo, nome do território + etiqueta do período, total em 28/900 + unidade.
- **Cor ou raça (1 nível):** barra de composição (todas as categorias) + uma linha por categoria (ponto de cor, nome, valor, %, barra da parte do total). Ordem: maior → menor.
- **Cor ou raça › Sexo:** idem, e sob cada categoria uma barra dividida: ícone de homem + % · barra (homens no tom cheio, mulheres no tom claro da cor da categoria) · % + ícone de mulher. Legenda dos tons no topo.
- **Só sexo:** pictograma de 10 figuras (cada uma ≈ 10%), barra dividida (série 1 / série 2) e os dois números grandes com valor absoluto.
- Outros segundos níveis: lista curta sob a categoria.
- Ausentes: texto de `formatValue` ("X (sigilo)", "…", "não se aplica", "sem dado"); nunca zero.
- **Muitas variáveis (v2.3) — largo e baixo.** A forma sai dos dados (`tooltipMode`):
  - **Matriz:** todas as categorias têm os mesmos itens no 2º nível (mesmos rótulos, mesma ordem), mais de 14 linhas no total e até 12 categorias (ex.: POF, classe de rendimento × 11 grupos de despesa). Parte 1 (260 px): categorias numeradas do maior para o menor valor, com barra — parte do total quando há `share_pct`, ou proporção do maior valor quando o KPI não é aditivo (nota "Barras proporcionais ao maior valor"). Parte 2: tabela itens × categorias; colunas pelo número (selo com borda na cor da série), linhas com o código ("2.1.1") em cinza; célula com tom de `series-1` proporcional ao valor dentro da linha (até 22% claro / 30% dark) e o maior da linha em 900. Largura = 260 + 24 + 176 + 62 × colunas + 36. Sem espaço lateral: resumo em 2 colunas em cima e matriz embaixo.
  - **Duas colunas:** mais de 10 categorias sem 2º nível → 560 px, lista em 2 colunas.
  - Cor ou raça › sexo e só sexo continuam na forma normal (340 px).
- Posição: 16 px à direita do ponteiro; vira para a esquerda perto da borda; na metade de baixo da tela abre para cima. Depois de desenhar, mede largura e altura reais e corrige para ficar inteiro na janela (12 px nas laterais, 8 px em cima/embaixo). `pointer-events: none`.
- Nota final: unidade + "Percentuais calculados pela plataforma a partir dos valores publicados."

### Exportação
SVG e PNG exportados devem levar as cores já calculadas (`resolveSvgColors`) e o fundo do tema atual.

## 10. Acessibilidade (CLAUDE.md §19.6)

- Contraste: texto ≥ 4,5:1 (inclusive 11–12 px); elementos gráficos e foco ≥ 3:1.
- Teclado: todo controle alcançável; territórios com `tabIndex=0`, Enter/Espaço selecionam; foco abre o tooltip.
- Estados expostos: `aria-current`, `aria-pressed`, `aria-selected`, `aria-busy`, `role="alert"`, `role="note"`.
- Nada só por cor: % sempre em texto; sexo com ícone e texto (para leitores de tela).
- `prefers-reduced-motion` e `prefers-color-scheme` respeitados.

## Ajustes da 2.3.6 (escala, unidades e rótulos)

- **Escala do mapa:** 7 grupos por quantis do recorte exibido. Cada corte é o número
  mais redondo dentro da janela entre os quantis vizinhos (`roundestIn`). A escala
  não colapsa em dados concentrados, como a esperança de vida de 72 a 80 anos.
- **Unidade nas colunas:** "Rótulo (unidade curta)", ou seja, %, R$, R$ mil,
  R$ milhões, índice, mil pessoas, km² ou hab/km². Em KPIs aditivos, cada categoria
  mostra também o % do Total do território, em texto `caption` / `text-muted`.
- **Legenda de índice:** "Índice (base = 100)", com a base tirada do nome da variável.
- **Rótulos limpos:** sem a numeração de tópicos da fonte; a hierarquia aparece pelo
  recuo.

## Ajustes da 2.3.7 ("Corrigir por")

- **Seletor:** grupo de rádios "Corrigir por" (Nominal, IPCA geral, IPCA por grupo de
  despesa) entre "Período por" e "Período", só em KPIs em moeda com correções.
- **Método:** recolhido em `details` "Como é calculado", em texto `caption`.
- **Unidade:** "R$ de jan/2018" nas colunas; a legenda acrescenta o índice e o
  mês-base. A exportação leva a unidade e a correção nos metadados.

## Ajustes da 2.3.8 (série temporal)

- **Total com detalhe:** com "Detalhar por", o gráfico mostra só as combinações mais
  detalhadas (campo `depth` da API). O Total, e com duas dimensões os subtotais, sai das
  linhas, da legenda e da escala do eixo Y, porque é muito maior que as categorias e
  achata as linhas. O Total continua na primeira linha do tooltip (sem marcador de cor,
  com um filete embaixo), e todos continuam na tabela. As categorias têm o mesmo peso
  de linha.
- **Pontas do eixo:** o primeiro e o último período ficam centralizados no ponto quando
  o rótulo cabe na margem; só se ancoram por dentro do gráfico quando não cabem. Assim
  os vizinhos (2002 e 2025 numa série de 2001 a 2026) não somem.

## Ajustes da 2.3.9 (tabela em matriz)

- **Grupos:** uma coluna por categoria da primeira dimensão de "Detalhar por" (Total,
  Branca, Preta…). Na célula do grupo, o valor do grupo em negrito e, embaixo, uma linha
  por categoria das demais dimensões, com rótulo `caption` à esquerda e "valor (%)" à
  direita. O grupo Total traz os totais de linha (o Total por sexo).
- **Unidade:** na segunda linha do cabeçalho, em `caption`: "pessoas" ou, quando a
  coluna mostra %, "pessoas (%)".
- **Linha de totais:** no fim da tabela (`tfoot`), "Total: Nordeste" ou "Total:
  Brasil", com o valor publicado pela fonte, não a soma das linhas da página (a soma não
  vale para taxas e médias).
- **Base do %:** `select` "% em relação a": Território (linha, padrão), Grupo (a
  categoria dentro do seu grupo), Coluna (o território no total do recorte) e Total
  geral. A explicação fica recolhida em "Como ler os %". Só em KPIs aditivos.
- **Muitas linhas:** grupos com mais de 12 linhas internas começam recolhidos; o
  cabeçalho tem "+ N detalhes" / "− recolher".
- **Rolagem:** a tabela rola nos dois sentidos, com o cabeçalho e a primeira coluna
  fixos.


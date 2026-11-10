# Open Data Brasil — Design System v1.0

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
- Layout: cabeçalho 64 px + faixa 4 px; menu lateral 260 px; área com 32 px de respiro; 20 px entre cartões; abaixo de 900 px o menu vai para cima e os cartões empilham.

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

- **Cabeçalho:** faixa da marca, logo + nome, abas, botão de tema à direita. Aviso do portal logo abaixo (`role="note"`, fundo `warning-bg`).
- **Menu lateral:** sobrelinha "Temas e indicadores"; temas e subtemas em `details/summary`; KPIs como botões `aria-pressed`; bloco "Detalhar por" em `fieldset` com checkboxes na ordem de `dimension_order`.
- **Barra de filtros:** H1 + selects "Nível territorial" e "Período" (44 px de altura, rótulo acima).
- **Cartão:** `bg-surface`, borda, raio 16, padding 24.
- **Exportar:** "Dados" (CSV, XLSX, Parquet, JSON) · separador · "Imagem do mapa" (SVG, PNG). Durante a exportação, botões desabilitados e "Gerando arquivo…". Falha em texto `danger` (`role="alert"`).
- **Erro ao carregar:** caixa `danger-bg` com ícone, mensagem e botão principal "Tentar de novo".
- **Carregando:** `aria-busy="true"` + "Carregando…"; no tooltip, barras de esqueleto.
- **Vazio:** "Escolha um indicador no menu." / "Este nível não tem mapa…".
- **Tabela:** cabeçalho fixo `bg-subtle`, ordenação por botão no título ("↓/↑"), números à direita, paginação "1–20 de 5.570" + Anterior/Próxima.
- **Sobre este indicador:** lista de definição com Fonte, Unidade, Períodos, Licença, Versão (mono) e Limitações.
- **Pular para o conteúdo:** aparece só com Tab.

## 9. Visualização de dados (d3)

### Mapa coroplético (`MapView`, `lib/scale.ts`)
- Quantis em 7 faixas (ADR-0009). Com menos faixas, usar as **últimas** cores da escala.
- Escala claro: #EAF1FC · #C5D9F5 · #9CBEEE · #6E9FE3 · #2F6ACB · #1351B4 · #0A3580.
- Escala dark (clara = mais): #16335F · #1E4785 · #2A5FAE · #3B76D0 · #5992ED · #8DB6F4 · #C5D9FA.
- Zero (classe própria): #F3F0E6 / #1C2B45. Sem dado: #D9DDE3 / #3A4A63. Sigilo: sem dado + hachura 45°.
- Contorno, hover, seleção e foco: ver seção 7. Legenda no canto inferior esquerdo, fundo 92%.
- **Recorte (ampliação seletiva):** ao aproximar uma região ou UF, só o recorte se
  subdivide e leva a escala sequencial (quantis calculados dentro do recorte). O resto do
  país fica no nível do recorte, com `map-context` (#E3E6EA / #253041) e divisas
  `map-context-stroke` (#FFFFFF / #0B2852) de 1 px. O contorno do recorte usa
  `map-focus` (#071D41 / #FFFFFF), com 2 px, por cima de tudo. A legenda ganha a
  entrada "Fora do recorte". O cinza do contexto é neutro (sem matiz) para não ser
  confundido com a primeira classe da escala, que é azulada.

### Séries (`SeriesChart`)
- Até 10 cores, nesta ordem — claro: #1351B4 · #168821 · #6E9FE3 · #A87400 · #071D41 · #D9480F · #0E7C86 · #8E44AD · #5C6B82 · #C2185B.
- Dark: #5992ED · #2DB34A · #C5D9FA · #FFCD07 · #8FA3C2 · #FF8A4C · #2EC4C9 · #B98AF0 · #FFFFFF · #F06292.
- As cores seguem a ordem das séries, não o nome da categoria (nenhuma cor deve sugerir tom de pele).
- Série principal 2,5 px com área (opacidade 0,08 / 0,15); demais 1,5 px. Pontos com miolo da superfície. Grade `chart-grid`, eixo zero `chart-axis`, rótulos `chart-label` 12/700. No máximo 6 rótulos no eixo X. Ausências interrompem a linha.

### Tooltip do mapa (`DetailTooltip`)
- 340 px, faixa da marca no topo, nome do território + etiqueta do período, total em 28/900 + unidade.
- **Cor ou raça (1 nível):** barra de composição (todas as categorias) + uma linha por categoria (ponto de cor, nome, valor, %, barra da parte do total). Ordem: maior → menor.
- **Cor ou raça › Sexo:** idem, e sob cada categoria uma barra dividida: ícone de homem + % · barra (homens no tom cheio, mulheres no tom claro da cor da categoria) · % + ícone de mulher. Legenda dos tons no topo.
- **Só sexo:** pictograma de 10 figuras (cada uma ≈ 10%), barra dividida (série 1 / série 2) e os dois números grandes com valor absoluto.
- Outros segundos níveis: lista curta sob a categoria.
- Ausentes: texto de `formatValue` ("X (sigilo)", "…", "não se aplica", "sem dado"); nunca zero.
- Posição: 16 px à direita do ponteiro; vira para a esquerda perto da borda; na metade de baixo da tela abre para cima. `pointer-events: none`.
- Nota final: unidade + "Percentuais calculados pela plataforma a partir dos valores publicados."

### Exportação
SVG e PNG exportados devem levar as cores já calculadas (`resolveSvgColors`) e o fundo do tema atual.

## 10. Acessibilidade (CLAUDE.md §19.6)

- Contraste: texto ≥ 4,5:1 (inclusive 11–12 px); elementos gráficos e foco ≥ 3:1.
- Teclado: todo controle alcançável; territórios com `tabIndex=0`, Enter/Espaço selecionam; foco abre o tooltip.
- Estados expostos: `aria-current`, `aria-pressed`, `aria-selected`, `aria-busy`, `role="alert"`, `role="note"`.
- Nada só por cor: % sempre em texto; sexo com ícone e texto (para leitores de tela).
- `prefers-reduced-motion` e `prefers-color-scheme` respeitados.

# Open Data Brasil — Design System v1.0 (pacote de implementação)

Este pacote leva o Design System ODBr para o portal (`apps/portal`, Next.js 16 + React 19 + d3).
Foi escrito sobre o código do commit `3a7fb4f` e mantém todas as classes, rótulos e
`aria-*` de que os testes dependem.

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
├── assets/brand/             ← logos em SVG (texto convertido em curvas) e ícones PNG
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
| `src/components/Sidebar.tsx` | substitui | Checkbox de "Detalhar por" com classe `.check` (sem estilo inline) |
| `src/components/MapView.tsx` | substitui | `style={{ fill }}`, fundo por token, contorno fino com muitos polígonos, selecionado desenhado por último, hachura para sigilo, `aria-pressed` |
| `src/components/SeriesChart.tsx` | substitui | `schemeTableau10` → `SERIES`; área sob a série principal; até 6 rótulos no eixo X |
| `src/components/DetailTooltip.tsx` | substitui | Tooltip visual: barras, divisão por sexo com ícones, pictograma para "só sexo" |
| `src/components/ExportMenu.tsx` | substitui | Classe `.export`, separador, `aria-busy` |
| `src/components/components.test.tsx` | substitui | Testes do tooltip atualizados para o novo layout (DataTable igual) |
| `messages/pt-BR.json` | substitui | `site.name` = "Open Data Brasil"; `theme.toDark/toLight`; `dashboard.figureNote` |

Nenhum arquivo da API, do contrato OpenAPI ou de `lib/api.ts`, `lib/state.ts`, `lib/format.ts`,
`DataTable.tsx`, `KpiInfo.tsx`, `IndicatorSearch.tsx` ou `Dashboard.tsx` precisa mudar:
o visual deles vem do `globals.css`.

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
5. **Componentes:** substituir `Sidebar.tsx`, `ExportMenu.tsx`, `DetailTooltip.tsx` e
   `components.test.tsx`.
6. **Dependência:** `d3-scale-chromatic` deixa de ser usado. Pode sair de `package.json`
   (e `@types/d3-scale-chromatic`) se nenhum outro arquivo importar.
7. **Verificar:** `npm run typecheck`, `npm run lint`, `npm test`, `npm run e2e`.

## Critérios de aceite

- [ ] `typecheck`, `lint`, `test` e `e2e` passam (os e2e não precisam de mudança).
- [ ] Tema claro igual às pranchas; ao clicar no botão de tema, tudo vira dark,
      incluindo mapa, legenda, gráfico, tabela e tooltip; a escolha persiste ao recarregar.
- [ ] Sem escolha salva, o portal segue o tema do sistema operacional.
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

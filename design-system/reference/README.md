# Referências visuais (v2.3)

- `canvas/` — fontes das telas do Design System (canvas do Claude Design). O HTML usa estilos
  inline com os valores exatos; os textos entre colchetes (`[DESCRIÇÃO]`, `[PERÍODOS]`) e os
  números de exemplo **não são dados**: no portal tudo vem da API (`/navigation`, `/release`, `/datasets`).
  - `Inicio*.dc.html` — Início (grade, tema escolhido, prévia do indicador) e, com `pagina="sobre"`, Sobre os dados.
  - `BuscaA.dc.html` — busca na barra lateral (proposta adotada).
  - `Dashboard*.dc.html` — Painel de análise (até 1599 px e tela cheia, claro e dark).
  - `TooltipLargo.dc.html`, `SerieTempo.dc.html`, `Tooltip.dc.html` — tooltip do mapa e série temporal.
- `screens/` — os componentes React deste pacote renderizados com os **dados de teste**
  de `src/lib/fixtures.ts` (por isso só 2 temas e 3 indicadores).
  - `busca-barra-lateral-fixa.png` (2.3.1) é a exceção: captura do portal com dados reais,
    barra lateral a 1280 px rolada até o meio da árvore, com a busca fixa no topo.

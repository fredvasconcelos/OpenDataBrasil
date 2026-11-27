# Guia obrigatório do Design System para agentes que alteram o portal

**Para:** agentes de código (Codex e outros) que editam `apps/portal`.
**Vale para:** toda alteração visual ou de navegação do portal, em especial a entrada de
novos indicadores das Contas públicas (Portal da Transparência).
**Versão do DS de referência:** 2.24.0 (`design-system/VERSION` no repositório ops).
**Data:** 27/11/2026.

Leia este guia inteiro antes de mudar qualquer arquivo do portal. Se uma tarefa pedir
algo que contrarie este guia, pare e pergunte ao mantenedor antes de implementar.

---

## 0. Resumo em dez regras

1. **Não crie estilo novo quando já existe um.** Reutilize as classes e os componentes
   listados na seção 4. Uma classe nova só entra para o que não existe, usando tokens
   `--odbr-*`, sem cor, tamanho ou raio escritos à mão.
2. **Cada bloco tem um único botão de entrada no Início.** O botão revela o catálogo do
   bloco, que tem busca, etiquetas de grupo e grade de cartões. Indicador novo entra
   **nesse catálogo**, nunca como cartão, seção, botão ou página solta no Início.
3. **O catálogo das Contas é `ContasCatalog.tsx`** e segue o molde do `HomeCatalog.tsx`
   (Estatísticas). Ele não deve ser substituído, duplicado nem "simplificado".
4. **Os textos ficam em `messages/pt-BR.json`.** Nenhum texto visível fica escrito no
   componente.
5. **Ícones só do Font Awesome Free 6.7.2 sólido**, por `lib/faIcons.ts`.
6. **A cor do tema vai só na faixa, no quadro do ícone e na borda.** Nunca no texto nem nos
   dados.
7. **Tudo funciona no tema claro e no escuro, no teclado e no celular** (320 a 1.920 px).
8. **O navegador não calcula dado.** Valores, totais, percentuais, alertas e classificações
   vêm prontos da API. As lentes das contas nunca se somam.
9. **Edite no worktree público e espelhe no ops** (seção 8). Teste antes de entregar
   (seção 9).
10. **Nada de dados inventados.** Um item do catálogo só existe se a API já o serve no
    release vigente.

---

## 1. Fontes da verdade

Em caso de conflito, vale o item de cima:

| Ordem | Fonte | Onde |
|---|---|---|
| 1 | Decisões do mantenedor e ADRs | `CLAUDE.md` (Prompt Mestre), ADR-0037, ADR-0039, ADR-0040 |
| 2 | Documento e pacote do DS | repositório ops: `design-system/README.md`, `design-system/docs/DESIGN-SYSTEM.md`, `design-system/docs/bloco-2-contas-publicas.md`, `design-system/docs/adr-0039-frontend-dois-blocos.md` |
| 3 | Tokens | `apps/portal/src/styles/tokens.css` (espelho de `design-system/tokens/tokens.css`) |
| 4 | Componentes de referência | `HomeCatalog.tsx`, `contas/ContasCatalog.tsx`, `Sidebar.tsx`, `contas/ContasPanel.tsx`, `BlockCards.tsx`, `BlockChooser.tsx` |
| 5 | Padrões de layout | `docs/development/padroes-visuais.md` |

Antes de propor um componente, procure no `globals.css` e em `src/components/` um
equivalente. A pergunta é sempre "qual componente do DS resolve isto?", não "como
desenho isto?".

---

## 2. Arquitetura de navegação (ADR-0039)

```
Início (/)
├── "O que você quer consultar?" ─ BlockCards: duas caixas, uma por bloco
│     ├── Estatísticas oficiais ─ [Ver indicadores] ─┐
│     └── Contas públicas       ─ [Ver indicadores] ─┤ (um botão por bloco)
│                                                    ▼
└── #indicadores-do-bloco (HomeExplorer) ─ catálogo do bloco escolhido
      ├── estatisticas → HomeCatalog compact
      └── contas       → ContasCatalog
            ├── busca grande com lupa e status de resultados
            ├── etiquetas de grupo (Todos + grupos), com ícone e contagem
            ├── "Todos" sem busca: grade de cartões, 4 itens por cartão + "Ver todos os N →"
            └── grupo escolhido ou busca: painel por grupo com a lista completa em colunas

Cabeçalho: "Painel de análise" ─ BlockChooser (popover; gaveta no celular)
  ├── /estatisticas/painel
  └── /contas/painel   (e /contas/favorecidos/[id])
```

Regras fixas:

- **Não acrescente** uma terceira caixa ao `BlockCards`, a menos que o mantenedor aprove um
  terceiro bloco. Indicadores novos do Portal da Transparência pertencem ao bloco
  **Contas públicas**.
- **Não acrescente** abaixo do catálogo cartões avulsos, botões "Consultar indicador" ou
  listas paralelas. Essa foi a falha corrigida no commit `728d02c`: um cartão solto com
  um campo de busca pequeno, fora do padrão.
- O bloco vem da URL (`/contas/...`, `/estatisticas/...`). Não use estado global, cookie
  nem `?bloco=`.
- O "Painel de análise" do cabeçalho é o único lugar para trocar de bloco.

---

## 3. Como acrescentar indicadores novos das Contas públicas

Este é o caso mais comum e o motivo deste guia.

### 3.1. Antes de codificar

1. Confirme que a rota existe e responde no release vigente: `GET /api/v1/contas/meta` e a
   rota específica (`/contas/table`, `/contas/series`, `/contas/map`, `/contas/execucao`,
   `/contas/busca`, `/contas/favorecidos/{id}`). Rotas atuais:
   `apps/api/src/odb_api/routes/contas.py`.
2. Confirme a lente e o que ela permite (texto em `meta.lenses[].description` e `notes`):
   - **A (Recursos transferidos):** tem território. É a do painel atual.
   - **B (Recebimento por favorecido):** tem território pela **sede** do favorecido. Hoje
     aparece só na ficha.
   - **C (Execução da despesa):** **não tem território**, então não tem mapa. A série com
     território responde 422.
3. As lentes B e C já foram aprovadas (ADR-0044, 27/11). A lente C **por território**
   continua pendente (ADR-0044, "Limite da solicitação territorial"). Qualquer base nova do
   Portal da Transparência (servidores, licitações, contratos, sanções) **exige aprovação
   do mantenedor** (Prompt Mestre, §28.5). Sem aprovação, não implemente.
4. O cliente do portal é `src/lib/api/contas.ts`, com os tipos gerados do OpenAPI
   (`npm run gen:api`; ver `docs/runbooks/portal.md`). Não escreva tipos à mão e não crie
   um segundo cliente.

### 3.2. Onde o indicador entra no catálogo

Arquivo: `apps/portal/src/components/contas/ContasCatalog.tsx`.

O catálogo é uma lista de **grupos** (`Group`). Cada grupo tem **itens** (`Item`), e cada
item é um link para a tela que responde a ele:

```ts
interface Item {
  id: string;      // estável e único no grupo (código da fonte quando houver)
  label: string;   // texto visível, da i18n ou o rótulo oficial da API
  href: string;    // rota interna já no recorte certo (query e #seção)
  terms?: string;  // termos extras de busca (siglas, nomes populares), da i18n
}

interface Group {
  id: "visao" | "tipos" | "areas";  // amplie o union ao criar um grupo
  label: string;   // i18n: contas.catalog.groups.<id>.name
  note: string;    // i18n: contas.catalog.groups.<id>.note (aparece na lista completa)
  icon: FaDef;     // FA.<nome>, de lib/faIcons.ts
  family: ThemeFamily; // azul | verde | ocre | petroleo | roxo | laranja | magenta | ardosia
  terms: string;   // i18n: contas.catalog.groups.<id>.terms (vale para todos os itens)
  items: Item[];
}
```

Grupos atuais (release `e8bb048c`, depois do `b01f3f6`, ADR-0044):

| Grupo | Família | Ícone | Itens | Destino |
|---|---|---|---|---|
| `visao` (Visão geral) | azul | `FA.contas` | 4 fixos | `/contas/painel`, `#onde`, `#quando`, `#quem` |
| `tipos` (Por tipo de transferência) | petroleo | `FA.transferidos` | da API (`group_by=transfer_type`) | `/contas/painel#como` |
| `areas` (Por área de governo) | roxo | `FA.gestao` | da API (`contasApi.areas`) | `/contas/painel?area=<código>` |
| `recebimentos` (lente B) | petroleo → **trocar** (seção 12) | `FA.recebimento` | 1 item | `/contas/painel?lens=B` |
| `execucao` (lente C) | roxo → **trocar** (seção 12) | `FA.gestao` → **trocar** | 6 fases | `/contas/painel?lens=C#fase-<fase>` |

**Para acrescentar um grupo** (ex.: "Recebimento por favorecido", depois de aprovado):

1. Carregue os dados dentro do `useAsync` que já existe no `ContasCatalog`, junto dos
   outros, com `Promise.all`. Use o período padrão de `defaultPeriod(meta)`. Não crie um
   segundo `useAsync` nem um segundo estado de carregamento.
2. Acrescente o objeto ao array `groups`, na ordem em que deve aparecer. Os grupos de visão
   geral vêm primeiro e os de detalhe (tipos, áreas e outras classificações) vêm depois.
3. Use uma família de cor **diferente** das famílias dos grupos vizinhos. Para grupos
   ligados a uma área de governo, use a família de `lib/contas/visual.ts`
   (`functionVisual`): Saúde é magenta nos dois blocos.
4. Escolha um ícone que já está em `FA`. Se precisar de um novo, importe-o
   individualmente em `lib/faIcons.ts` (só `@fortawesome/free-solid-svg-icons`, nada Pro,
   nada de webfont) e acrescente a chave ao objeto `FA`.
5. Ponha os textos em `messages/pt-BR.json`, em `contas.catalog.groups.<id>` (`name`,
   `note`, `terms`) e em `contas.catalog.items.*` para itens fixos.
6. Os itens têm que levar a uma tela que **já mostra** aquilo. Se a tela não filtra pelo
   item (como os tipos hoje), aponte para a seção que o exibe (`#como`) e explique na
   `note` do grupo ("Abre a distribuição por tipo no painel"). Nunca crie um link que
   promete um filtro que não acontece.
7. Os termos de busca ficam **no item** quando só valem para ele. Exemplo: "FPM" está em
   `constitutionalTerms`, não no grupo, para que a busca "fpm" não traga as transferências
   legais.
8. Não mexa na estrutura de renderização (busca, `theme-chips`, `theme-grid`,
   `theme-card`, `theme-panel`, `Chip`, `GroupIcon`, `ItemList`). Ela já faz o que é
   preciso para qualquer número de grupos.

**Para acrescentar um item a um grupo existente:** só acrescente ao array `items`, com
texto na i18n e destino válido.

**Indicadores em preparação:** o catálogo das Estatísticas mostra itens previstos com
`<span className="kpi-pending">…<span className="planned-badge">` e sem link. Use o mesmo
padrão nas Contas só se o mantenedor aprovar mostrar uma lente ou um indicador como
"Em preparação". Nunca liste como pronto o que não tem rota.

### 3.3. Quando um indicador novo precisa de painel próprio

As lentes B e C foram aprovadas pelo mantenedor em 27/11 (ADR-0044) e hoje abrem em
`/contas/painel?lens=B|C` (`FederalDashboard.tsx`). Mantenha esse endereço. Outra lente ou
base nova segue as mesmas regras, com aprovação prévia:

- **A lente vem da URL** (`lens`), lida em `lib/contas/state.ts`. Cada lente tem seu painel
  e seus valores; nada na tela sugere que as lentes se somam.
- **A troca de lente/indicador é feita pela barra lateral**, com a árvore e a busca das
  Estatísticas (ver o item "Mais de um painel nas Contas" abaixo), e não por uma faixa
  de abas acima do painel.
- **Mesma moldura do painel atual:** `div.dashboard.contas-dashboard` →
  `aside.sidebar.contas-sidebar` (componente `ContasSidebar`) + `main.main.contas-content`
  → `ContasPanel` (cabeçalho com `.crumb` e `h1`, destaques, seções `section.contas-section.card`
  com `h2.contas-section-title`, ícone `FaIcon` de 16 px e botão i `ContasInfo`).
- **Filtros só na barra lateral** (`section.filters`, `label.field` + `select`), com
  "Limpar todos os filtros" no pé. No celular, os filtros recolhem atrás do botão
  `.contas-filter-toggle`.
- **Estado na URL**, como em `lib/contas/state.ts` (`readContasState`, `panelHref`). Os
  parâmetros novos entram na lista `PANEL_FIELDS`, ou numa lista própria do novo painel.
- **Lente C:** sem mapa e sem seletor de território. Use tabela e gráfico (seções "Como" e
  "Quando"); a tabela fica no padrão `ContasRankingTable` / `.data-table`.
- **Mais de um painel nas Contas:** a barra lateral passa a ter a seção de indicadores com
  busca, **igual à das Estatísticas** (`Sidebar.tsx`, a partir de `nav.themes`):
  `div.tree-head` com `div.tree-search` (campo de 40 px, tecla `/` foca, Esc limpa),
  `div.tree-status` com `aria-live`, a árvore em `details/summary` por grupo e os
  indicadores como botões ou links com `aria-pressed`/`aria-current`. Os grupos e itens
  vêm da **mesma** definição do `ContasCatalog`: extraia-a para `lib/contas/catalog.ts`,
  em vez de copiá-la. Assim a busca do Início e a da barra lateral acham as mesmas coisas.
- O painel rola até a seção do link (`#onde`, `#como`, `#quando`, `#quem`) depois da
  primeira carga (efeito em `ContasDashboard.tsx`). Painéis novos fazem o mesmo, e cada
  `h2` de seção tem `id` estável.
- Os estados obrigatórios (bloco-2, seção 3) usam os componentes existentes:
  `ContasUnavailable` (503 isolado), `ContasEmpty` (sem dados no recorte),
  `PeriodStatusList` (mês aberto, incompleto ou com complemento do Tesouro), "Carregando…"
  com `aria-busy` e `.contas-update` durante a troca de filtro.

---

## 4. Componentes e classes que devem ser reutilizados

### 4.1. Catálogo (Início)

| Parte | Marcação e classes | Observações |
|---|---|---|
| Contêiner | `section.home-hero` dentro de `section.block-catalog` | O título do bloco é o `h2` do `HomeExplorer` |
| Busca | `div[role=search].home-search` > `label[for]` + `SearchGlyph` + `input[type=search]` + `p.home-search-status[aria-live=polite]` | 56 px de altura, raio 28, borda 2 px `border-strong`. Importe `SearchGlyph` de `HomeCatalog.tsx` |
| Status da busca | sem termo: dica (`hint`); com termo: `catalog.found` (plural ICU) | Não use `role="status"` separado para "nada encontrado" |
| Etiquetas | `section.theme-chips` > `h2.eyebrow` + `div` > `button.theme-chip[aria-pressed]` > `span.theme-chip-icon` + rótulo + `span.theme-chip-count` | Primeiro "Todos" (`catalog.all`) com o total; cor da família via `style={themeStyle(family)}` |
| Grade ("Todos" sem busca) | `div.theme-grid` > `section.theme-card[aria-labelledby]` > `div.theme-card-head` (ícone + `h2` + `span` de contagem) + `ul` de itens + `div.theme-card-foot` > `button.text-btn` | No máximo 4 itens por cartão (`SAMPLE = 4`); rodapé "Ver todos os N →" ou "Ver o grupo →" |
| Lista completa | `section.theme-panel` > `div.theme-panel-head` (ícone 24/46 + `h2` + `span` "N indicadores · nota") + `div.theme-panel-cols` | Com subgrupos: um `div` com `h3` por subgrupo. Sem subgrupos: o `ul` direto dentro de `.theme-panel-cols`, para fluir em colunas |
| Item | `a.kpi-link` (via `next/link`) ou `button.kpi-link` (abre prévia) | Sem sublinhado em repouso; sublinha no hover |
| Vazio | `p.empty` | Texto da i18n que diz o que a busca considera |
| Ícone de grupo | `span.theme-icon` (40 px; 46 px na lista) com `FaIcon` | Use `ThemeIcon` quando o ícone for de `THEME_ICONS` |

### 4.2. Painel

| Parte | Componente / classe |
|---|---|
| Barra lateral | `aside.sidebar` (+ `.contas-sidebar`), `.sb-current` > `.sb-crumb` + `.sb-kpi`, `section.filters`, `.filters-body`, `label.field`, `.filters-foot` > `button.clear` |
| Cabeçalho | `.page-title` > `p.crumb` + `h1` |
| Destaques | `ContasHighlights` (`ul.contas-highlights` > `li.contas-kpi`, `.is-main`) |
| Seções | `section.contas-section.card` + `h2.contas-section-title` + `ContasInfo` (botão i) |
| Mapa | `MapView` (com `map-trail` dentro), tooltip `ContasTooltip` |
| Série | `SeriesChart` com adaptador `toSeries` |
| Tabela | `ContasRankingTable` / `.data-table` (cabeçalho fixo, números à direita, paginação) |
| Rodapé de proveniência | `section.card.meta` > `p.meta-source` + `details.meta-more` + `ContasReferences` |

### 4.3. Botões

| Uso | Classe |
|---|---|
| Ação principal | `.btn-primary` (pílula, 44 px; `.small` = 38 px) |
| Ação secundária | `.btn-outline` |
| Ação de texto | `.text-btn` |
| Entrada do bloco no Início | `.block-card-link` (já existe; não crie outra) |
| Informação | `ContasInfo` / `KpiInfo` (i colorido: azul, amarelo, vermelho, conforme a API) |

---

## 5. Tokens, tipografia e layout

- Use só variáveis `--odbr-*` de `styles/tokens.css`: cores semânticas (`bg-surface`,
  `text`, `text-muted`, `link`, `primary`, `border`, `divider`), espaços (`--odbr-space-*`,
  base 4), raios (`--odbr-radius-*`), escala tipográfica (`--odbr-fs-*`,
  `--odbr-scale-*`), controles (`--odbr-control-h` 40 px, compacto 32 px,
  `--odbr-control-touch-h` 44 px) e larguras (`--odbr-content-wide` 1.600 px,
  `--odbr-content-reading` 72ch).
- **Proibido:** hexadecimal, `px` de fonte, sombra ou raio escritos à mão em componente
  novo. Exceções que já existem (`mark`, mapa) não justificam novas.
- Famílias de tema: `themeStyle(family)` define `--theme-band`, `--theme-icon-bg`,
  `--theme-icon` e `--theme-border`. Não leia `--odbr-theme-*` diretamente no componente.
- Fonte Nunito, pesos 600–900; números com `font-variant-numeric: tabular-nums` em
  tabelas, tooltips e eixos.
- Quebras de layout: 576, 992, 1.280 e 1.600 px. A grade de cartões tem 4 colunas em tela
  larga, 3 em desktop intermediário, 2 até 991 px e 1 até 575 px.
- Foco: `--odbr-focus-ring` (4 px tracejado `#936F38` no claro). Não remova `outline` sem
  colocar o anel.
- Hover muda só cor ou fundo, nunca tamanho. Respeite `prefers-reduced-motion`.
- CSS novo vai no fim de `src/app/globals.css`, num bloco com comentário que diga a versão
  do DS e o propósito. Prefira estender uma classe existente com um modificador (ex.:
  `a.kpi-link`) a criar uma família nova.

---

## 6. Textos, formatos e regras de conteúdo das contas

- Textos em `messages/pt-BR.json`, nos namespaces existentes (`blocks`, `catalog`,
  `contas`, `contas.catalog`, …). Reaproveite as chaves comuns: `catalog.all`,
  `catalog.found`, `catalog.kpiCount`, `catalog.seeAll`, `contas.loading`,
  `contas.unavailable.*`.
- Mantenha o diff do JSON pequeno: indentação de 2 espaços, `ensure_ascii` desligado,
  sem reordenar chaves.
- Use os mesmos nomes do painel: "Constitucionais e royalties" (`contas.highlights.constitutional`),
  e não o rótulo da fonte em caixa de título.
- Moeda: R$ abreviado nos cartões, mapas e eixos ("R$ 25,7 bi"); completo na tabela e no
  tooltip. Use `lib/contas/format.ts`, sem formatar à mão.
- Períodos: `periodLabel` (`2025M03` → "mar/2025").
- Diga "recebido por" ou "para onde vai", nunca "aplicado em".
- Lentes nunca se somam: nem em total, nem em gráfico empilhado, nem na mesma lista sem
  rótulo de lente.
- Privacidade (ADR-0039, seção 8): sem busca por CPF ou CNPJ, sem ranking só de pessoas
  físicas; na lista, só o nome. Os resultados de `/contas/busca` já excluem pessoas
  físicas: não contorne isso.
- Fonte sempre visível: "Fonte: CGU, Portal da Transparência"; com complemento do FPM,
  também o Tesouro Nacional (licença ODbL).

---

## 7. Acessibilidade (obrigatória)

- Todo campo com `label` associado; busca com `role="search"`.
- Etiquetas de filtro são `button` com `aria-pressed`. Botões que abrem conteúdo usam
  `aria-expanded` e `aria-controls`.
- Títulos em ordem (`h1` no painel; no Início, `h1` das caixas, `h2` do bloco e dos
  grupos).
- Ícones decorativos com `aria-hidden="true"` (o `FaIcon` já faz isso).
- Resultado da busca anunciado por `aria-live="polite"`.
- Escape fecha popovers e diálogos e devolve o foco ao botão que os abriu.
- Nada pode depender só de cor: o estado selecionado também muda o fundo ou o peso.

---

## 8. Onde editar e como espelhar

1. **Código vivo:** worktree público `../OpenDataBrasil-revisao-kpis` (vizinho do ops), branch
   `feat/revisao-detalhamento-kpis`, pasta `apps/portal`.
2. **Espelho:** repositório ops `OpenDataBrasil`, pasta
   `design-system/portal` (mesmos caminhos relativos). Antes de copiar, confira que o
   espelho é igual ao `HEAD` do público (`git show HEAD:<arquivo> | sha1sum`). Depois,
   copie e confira byte a byte (`cmp`).
3. **Commits separados:** primeiro no público; depois no ops, com a mensagem
   "Espelha … (público <hash>)". Use `git add` com caminhos explícitos, nunca pastas
   inteiras. Outras sessões trabalham nos mesmos diretórios.
4. **Portal local:** o `localhost:3000` é montado do worktree
   `../OpenDataBrasil-localhost` (branch `localhost`), que recebe o público
   por merge. Monte com um override em `data/logs/<etiqueta>/compose.local.yml` (ver o
   último existente) e `docker compose --profile web … build portal` + `up -d --no-deps portal`.
5. Se a alteração mudar o DS (classe, componente ou regra nova), registre-a no
   `design-system/docs/DESIGN-SYSTEM.md` do ops, numa seção "DS x.y.z", e atualize o
   `design-system/VERSION` só com aprovação do mantenedor.
6. Não faça push, implantação nem ativação de release sem pedido explícito.

---

## 9. Testes e conferência antes de entregar

Imagens fixadas (o `npx` do PATH é o do Windows; não use):

```bash
NODE=node:24.22.1-bookworm-slim@sha256:be8204d4bd327363357f532187b752ff62759c31bedf98e9e18fc08c9cbd605c
cd apps/portal
docker run --rm --user 1000:1000 -e HOME=/tmp -v "$PWD":/app -w /app $NODE \
  sh -c 'npx tsc --noEmit && npx eslint . && npx vitest run'
```

Navegador real, com a pilha `web` no ar:

```bash
docker run --rm --network opendatabrasil_default --ipc=host --user 1000:1000 -e HOME=/tmp \
  -e PORTAL_URL=http://portal:3000 -v "$PWD":/app -w /app \
  mcr.microsoft.com/playwright@sha256:2f05f8a734509a7b3f26a912639488ee08f58a7b292d14d62271bcff9038768f \
  npx playwright test e2e/revisao-home-contas.spec.ts
```

Ao acrescentar um grupo ou item nas Contas, atualize `e2e/revisao-home-contas.spec.ts`
para conferir:

- a quantidade de `.block-catalog .theme-card` na grade;
- o `href` de pelo menos um item do grupo novo;
- a etiqueta do grupo abrindo um único `.theme-panel`;
- uma busca que ache o item novo e uma que **não** traga itens de outro grupo;
- o salto até a seção (`toBeInViewport`) quando o destino tiver `#âncora`.

Para conferir sem mexer no `localhost:3000`, suba um contêiner temporário da imagem nova na
rede `opendatabrasil_default` (`PORTAL_URL=http://<nome>:3000`). **Remova-o ao terminar**
(`docker rm -f`), junto da imagem temporária. Nunca remova serviços da pilha
(`opendatabrasil-*`).

Confira as capturas em 1.440 px e 390 px, nos temas claro e escuro: grade de cartões,
lista de um grupo, busca com resultado e busca sem resultado. Compare lado a lado com o
catálogo das Estatísticas. **A aparência tem que ser a mesma.**

---

## 10. Lista de conferência (copie para o relatório da tarefa)

- [ ] O indicador novo aparece **dentro** do catálogo do bloco, aberto pelo botão "Ver indicadores".
- [ ] Nenhum cartão, botão, campo ou lista solta foi acrescentado ao Início.
- [ ] Busca, etiquetas, grade e lista completa usam as classes da seção 4.1.
- [ ] O grupo tem família de cor, ícone Font Awesome, contagem e textos na i18n.
- [ ] Cada item leva a uma tela que mostra o que ele promete (filtro ou seção certa).
- [ ] Os termos de busca estão no item quando não valem para o grupo inteiro.
- [ ] Nenhuma cor, tamanho ou raio foi escrito à mão.
- [ ] Os temas claro e escuro, o celular (390 px) e o teclado foram conferidos.
- [ ] Nenhum valor é calculado no navegador; as lentes não se somam.
- [ ] `tsc`, `eslint`, `vitest` e o e2e da tela passam.
- [ ] O público foi commitado, o ops espelhado e conferido byte a byte, e os contêineres temporários removidos.
- [ ] O relatório lista o que **não** foi feito e o que depende do mantenedor.

---

## 11. Erros que já aconteceram (não repetir)

| Erro | Correção |
|---|---|
| Catálogo das contas feito como cartão solto, com busca pequena e botão "Consultar indicador" | Substituído por `ContasCatalog`, no molde do `HomeCatalog` (`728d02c`) |
| Lista de um grupo sem subgrupos ficou numa coluna só | O `ul` fica direto dentro de `.theme-panel-cols`, sem `div` envolvendo |
| Termo "FPM" no grupo trouxe também as transferências legais | Termos no item (`constitutionalTerms`) |
| Rótulo da fonte em caixa de título ("Constitucionais e Royalties") diferente do painel | Usar `contas.highlights.*` |
| Link com `#seção` não rolava, porque a seção só existe depois da carga | Efeito de rolagem única em `ContasDashboard.tsx` |
| Edição feita só no espelho do ops; o build não pegou | Editar no público e espelhar no ops na mesma hora |
| Cópia inteira de arquivos compartilhados trouxe mudanças de outras frentes | Espelhar por patch e conferir com `cmp` |

---

## 12. Correções pendentes no commit `b01f3f6` (lentes B e C)

O commit `b01f3f6` pôs as lentes no catálogo, o que está certo, mas criou desvios do DS.
Aplique as correções abaixo **sem mudar dados, rotas da API, regras estatísticas nem o
contrato do ADR-0044**. Cada item diz o arquivo, o problema e o resultado esperado.

### 12.1. Catálogo (`components/contas/ContasCatalog.tsx`)

1. **Termos de busca escritos no código.** `terms: "favorecido pagamento sede …"` e
   `terms: "execução empenhado …"` estão em português dentro do componente. Mova-os para
   `contas.catalog.groups.recebimentos.terms` e `contas.catalog.groups.execucao.terms`. Os
   nomes e notas também vão para `contas.catalog.groups.<id>.name|note`; podem apontar
   para os mesmos textos de `contas.federal.*`, mas a chave do catálogo é a dele.
2. **Cores repetidas.** `recebimentos` usa `petroleo` (igual a `tipos`) e `execucao` usa
   `roxo` + `FA.gestao` (iguais a `areas`). Use famílias que nenhum outro grupo usa:
   `recebimentos` → **`verde`**, `execucao` → **`ocre`**. Para a execução, use o ícone
   **`FA.execucao`** (`faFileInvoiceDollar`, que já existe e está sem uso).
3. **Grupo com um item de mesmo nome.** "Recebimento por favorecido" tem um único item com
   o mesmo rótulo do grupo. Dê ao grupo itens que respondam perguntas, como a Visão geral
   faz, com destinos que já existem na tela da lente B: "Total recebido pelos favorecidos"
   (`?lens=B`), "Recebimentos por sede, no mapa" (`?lens=B#federal-map`), "Evolução mês a
   mês" (`?lens=B#federal-series`) e "Buscar um favorecido (empresas e entidades)"
   (`?lens=B#federal-busca`; a seção de busca ganha um `h2.contas-section-title` com `id="federal-busca"`). Só inclua
   um item se a seção existir na lente B.
4. **Filtro com `as Group[]`.** Troque o `.filter(...) as Group[]` por montar a lista com
   um teste explícito: `const has = (lens) => meta.lenses.some((l) => l.lens === lens)` e
   `...(has("B") ? [grupoB] : [])`. Sem conversão de tipo.
5. A ordem dos grupos fica: Visão geral, Por tipo de transferência, Por área de governo,
   Recebimento por favorecido e Execução da despesa.
6. Atualize o e2e (seção 9): 5 cartões na grade e uma busca "empenhado" que traga só o
   grupo da execução.

### 12.2. Navegação entre lentes (`FederalDashboard.tsx` → `ContasLensNav`)

1. **A faixa `nav.contas-lens-nav`** (abas quadradas com `--odbr-radius-sm` acima do
   painel) não existe no DS. Remova-a e remova o CSS `.contas-lens-nav*`.
2. **No lugar dela,** acrescente à `ContasSidebar` e à barra lateral do `FederalDashboard`,
   abaixo de `section.filters`, a seção de indicadores **igual à das Estatísticas**
   (`Sidebar.tsx`, `nav.themes`):
   - `div.tree-head` com `div[role=search].tree-search` (rótulo `sr-only`, campo de 40 px;
     `/` foca, Esc limpa) e `div.tree-status[aria-live=polite]`;
   - um `details` por grupo do catálogo, com `summary` (ícone do grupo + nome);
   - os itens como links `next/link`, com `aria-current="page"` no item da lente/recorte
     atual.
3. **Um só catálogo:** extraia a montagem dos grupos de `ContasCatalog.tsx` para
   `lib/contas/catalog.ts` (função pura `contasGroups(data, t)` + `matchContas(group,
   item, query)`), com teste unitário. O Início e a barra lateral chamam a mesma função.
4. A barra lateral mantém `.sb-current` com o nome da lente atual. Não acrescente um
   seletor de lente nos filtros.

### 12.3. Painel das lentes B e C (`FederalDashboard.tsx`)

1. **Cabeçalho:** use a mesma marcação do painel A, `div.page-title` > `p.crumb` + `h1`.
   Apague `.contas-federal h1 { font-size: … }`: o título tem o mesmo tamanho nas três
   lentes. A situação do período (`PeriodStatusList`) fica à direita, como na lente A.
2. **Seções:** cada `section.card.contas-section` usa `h2.contas-section-title` com
   `FaIcon` de 16 px e o botão i (`ContasInfo`), como em `ContasPanel` (`head(...)`). Os
   textos de apoio que hoje são `<p>` soltos (`territoryScope`, `filterHint`, `ordered`,
   `tableProfileHint`) passam para dentro do botão i da seção.
3. **Nota da lente:** `p.card.contas-lens-note` vira parte do botão i do cabeçalho ou do
   cartão de destaque. Não use um cartão só de texto.
4. **Destaque da lente B:** use `ul.contas-highlights` > `li.contas-kpi.is-main`, como na
   lente A (valor abreviado + valor completo), e não `div.card.contas-kpi` com
   `strong`.
5. **Fases da lente C:** remova `.contas-phase-cards li:target { outline: 2px solid … }`.
   O destaque do alvo usa o mesmo realce de seleção do DS: `background:
   var(--odbr-bg-selected)` e borda `var(--odbr-primary)`. O anel de foco é exclusivo do
   teclado.
6. **Quebras de layout:** troque `@media (max-width: 800px)` e `(max-width: 420px)` por
   `991px` e `575px`. Troque `min-width: 1250px` da tabela de execução por rolagem
   horizontal no `.table-wrap` sem largura mínima fixa. As colunas numéricas ficam com
   `white-space: nowrap`.
7. **Busca de favorecidos:** use o padrão da busca do DS, `div[role=search]` com lupa
   (`SearchGlyph`), rótulo visível e `p[aria-live=polite]` de status. Não use um `form` com
   `label.field` e um botão "Buscar" à parte. A consulta à API (mínimo de 3 letras) roda
   com atraso de 300 ms depois da digitação, ou com Enter. Os resultados são `a.kpi-link`
   em lista.
8. **Rodapé:** use a mesma `section.card.meta` da lente A (`p.meta-source` com fonte e
   release + `details.meta-more` com notas, tabelas e `ContasReferences`). Não use uma
   seção com `<p>` soltos.
9. **Filtros ativos:** os botões removíveis seguem `.theme-chip` com `aria-pressed="true"`
   e o ícone × como `span` decorativo, com o nome acessível "Remover filtro …". Não use
   `.btn-outline` com "×" no texto.
10. **Paginação:** reutilize a marcação da tabela de recebedores da lente A
    (`ContasRankingTable`: `.contas-pager`, rótulos `who.previous`/`who.next`, "Página X
    de Y"). Não crie uma segunda variante.

### 12.4. Entrega

- Antes e depois, capture 1.440 px e 390 px, claro e escuro, de: Início com as contas
  abertas, `?lens=A`, `?lens=B` (Brasil e uma UF) e `?lens=C`. Compare com
  `/estatisticas/painel`: barra lateral, títulos, cartões e rodapé têm que ser
  equivalentes.
- Rode `tsc`, `eslint`, `vitest`, `e2e/revisao-home-contas.spec.ts` e
  `e2e/contas-lentes.spec.ts`.
- Commit no público, espelho no ops conferido com `cmp`, merge na `localhost` e
  atualização do `AGENTS.md`. Não ative release e não toque na beta.

# ADR-0039 — Portal com dois blocos: Estatísticas oficiais e Contas públicas

- **Situação:** aceita pelo mantenedor em 23/11/2026 (frontend e DS). Numerada 0039 porque
  o ADR-0038 do repositório já é "FPM do Tesouro como segunda fonte".
- **Escopo:** rotas, navegação, camada de dados, tooltips, ícones e privacidade no portal
  (Next.js) e no Design System. Não muda Bronze, Silver, Gold, DuckDB nem a API.

## Contexto

O portal ganhou um segundo produto: as transferências e os pagamentos federais do Portal da
Transparência, servidos pela API das contas (`/api/v1/contas/*`, ADR-0037, release candidato
`e8bb048c`). Os dois blocos têm dados, filtros e regras diferentes e não podem se misturar,
mas dividem a marca, o cabeçalho, o rodapé, o DS e a i18n.

O Portal da Transparência oferece dezenas de recortes. O objetivo aqui é o contrário:
**poucas opções**, guiadas por uma pergunta.

## Decisões

### 1. Dois blocos com nomes fixos

| Bloco | Nome na interface | API |
|---|---|---|
| 1 | **Estatísticas oficiais** | `/api/v1/...` (catálogo, mapa, série, tabela) |
| 2 | **Contas públicas** | `/api/v1/contas/*` |

### 2. Rotas: o bloco vem da URL

| Rota | Conteúdo |
|---|---|
| `/` | Início com as duas caixas, cada uma com uma descrição curta |
| `/estatisticas/painel` | Painel atual; `/dashboard` redireciona com 308, mantendo a query |
| `/contas/painel` | Painel das contas (seção 4) |
| `/contas/favorecidos/[id]` | Ficha do favorecido |

Nada de estado global, cookie ou `?bloco=`: o link diz o bloco, o SSR funciona e cada painel
tem o seu código.

### 3. "Painel de análise" abre a escolha do bloco

O botão do cabeçalho deixa de ser um link e passa a abrir um seletor com as duas opções,
sempre, com o bloco atual marcado (`aria-current`). É o único lugar para trocar de bloco.

- Desktop: popover ancorado no botão (`aria-haspopup="dialog"`, `aria-expanded`), foco no
  primeiro item, Esc e clique fora fecham, o foco volta ao botão.
- Até 991 px: as duas opções aparecem dentro da gaveta do menu, sob "Painel de análise".
- O botão fica marcado (`aria-current="page"`) em qualquer rota de painel.

### 4. Pergunta norteadora das Contas públicas

> **Quanto o governo federal envia para estados e municípios: como, onde e quando?**

O Painel das contas usa **só a lente A (Recursos transferidos)**: ela sozinha responde à
pergunta. Sem seletor de lentes na tela e sem risco de somar lentes.

| Parte | Seção | Rota |
|---|---|---|
| Quanto | Destaques: total do território no período | `/contas/map` (total da UF ou do país), `/contas/series` |
| Onde | Mapa Brasil → UF → município | `/contas/map` |
| Como | Composição por tipo de transferência e por área (função) | `/contas/composition` |
| Quando | Série mensal ou anual | `/contas/series` |
| Quem recebeu | Ranking da lente A | `/contas/ranking?lens=A` |

- **Filtros:** território e período. A área funciona como filtro opcional, clicando na
  composição. Órgão, ação, elemento, modalidade e demais classificações ficam fora.
- **"Onde":** a API informa onde o dinheiro foi recebido (sede do ente). Como o ente gasta
  não está nas bases federais. A interface diz "para onde vai" ou "recebido por", nunca
  "aplicado em", e mantém visível a nota da lente que diz isso.
- **Lente B (Recebimento por favorecido):** aparece só na ficha do favorecido, separada e
  rotulada; os valores não se somam aos da lente A.
- **Lente C (Execução da despesa):** fora da primeira versão; não tem território e não
  responde à pergunta. Pode voltar depois.

### 5. Camada de dados

- Dois clients tipados a partir de cada OpenAPI (`openapi-typescript`): `lib/api` (atual) e
  `lib/api/contas`. Os dois passam pelo proxy `/odb-api`.
- O frontend não agrega, não soma lentes, não calcula per capita nem variação: o que
  aparece vem pronto da API. Total do território vem do campo `total` das rotas.
- Falha isolada: um 503 em `/contas/*` mostra "Contas públicas indisponíveis" só no bloco 2;
  as Estatísticas oficiais seguem funcionando.
- Cache por bloco: as contas têm mês aberto e complemento do Tesouro; respeitam
  `provenance.partial` e `period_notes`.

### 6. Tooltips por adaptador, não por cópia

O `DetailTooltip` mantém a estrutura (título, valor, linhas, notas) e recebe o conteúdo de
um adaptador por bloco:

- **Estatísticas:** unidade, fonte e tabela, período, nota metodológica, comparabilidade.
- **Contas:** valor em R$ (nominal), participação no total, mês de referência, situação do
  período (fechado, parcial, complemento do Tesouro) e a nota da lente.

### 7. Ícones: Font Awesome Free 6.7.2 nos dois blocos

- Segue o Design System do gov.br, que adotou o Font Awesome Free, e o Portal da Transparência.
- Estilo sólido, importado como SVG um a um (`@fortawesome/free-solid-svg-icons`), sem
  webfont nem CSS externo. O `ThemeIcon` continua controlando tamanho e cor.
- Os temas das Estatísticas oficiais migram para os equivalentes; os 22 ícones de
  agropecuária ficam como estão (o Font Awesome Free não os cobre).
- Só entram os ícones usados. Licença CC BY 4.0: atribuição em `assets/icons/LICENSE-font-awesome.txt`
  e na página Sobre. Nada da versão Pro.

### 8. Privacidade e ranking

- O ranking mostra quem mais recebeu, em ordem de valor, como a CGU publica (dados abertos,
  licença do governo federal). Uma pessoa física que esteja entre os maiores aparece como
  qualquer favorecido (`is_natural_person`).
- Sem busca por CPF ou CNPJ, sem ranking só de pessoas físicas, sem cruzamento com outras
  bases. O portal apresenta, não fiscaliza.
- Na lista, só o nome, a sede, a classe e o valor. O CPF mascarado aparece só na ficha de
  pessoa física, com a nota de homônimos que a API envia.
- Isso aplica a seção 23 do Prompt Mestre: nenhum identificador novo, nenhuma reidentificação
  além do que a fonte oficial já publica.

### 9. Fora por agora

Per capita (sem população nas rotas das contas), exportação CSV/XLSX das contas (sem rota),
busca por CPF/CNPJ (por decisão), lente C, local de aplicação (não existe na fonte),
correção pela inflação (valores nominais).

## Consequências

- O DS ganha: `BlockChooser`, `BlockCards`, `ContasHighlights`, `ContasComposition`,
  `ContasRanking`, `RecipientProfile` e os estados do bloco 2; os ícones viram Font Awesome.
- `/dashboard` passa a redirecionar; links antigos continuam funcionando.
- i18n por namespace: `comum.*`, `estatisticas.*`, `contas.*`.
- Testes: unitários dos adaptadores (contas → MapView/SeriesChart), e2e com as amostras de
  `reference/contas/api/`, axe nas telas novas, e o 503 isolado.

## Integração com o contrato existente (24/11/2026)

A CP5 usa o contrato já aceito no ADR-0037, sem ampliar a API:

- Os dois clientes usam os tipos do OpenAPI completo (`api-schema.ts`), gerados pelo
  comando existente `npm run gen:api`; não há uma segunda cópia dos mesmos modelos.
- O ranking aceita somente ano e território. Sua seção informa que mês e área não se
  aplicam. Área filtra o total, o mapa e a série; a composição continua mostrando todas
  as áreas do território e período, com esse contexto explícito.
- O total vem do ponto da série do território, calculado na API; o total de um mapa de
  municípios pode excluir favorecidos estaduais sem município. Não se reconstrói o
  total territorial somando o mapa no navegador.
- A API não fornece CPF mascarado nem URL específica do favorecido. A ficha mantém só
  o nome e as notas de homônimos; seu link leva à página inicial oficial da CGU e isso
  fica explícito. Nenhum identificador é reconstruído.
- Todas as fichas recebem `noindex, nofollow` no HTML e em `X-Robots-Tag`, abrangendo
  as pessoas físicas mesmo antes de uma consulta ao cadastro. O proxy também preserva
  esse cabeçalho quando fornecido pela API.
- Os namespaces existentes das Estatísticas são preservados; `blocks` e `contas`
  acrescentam os textos novos. Os ícones agro próprios continuam em uso.
- Filtros das contas ficam em `geography`, `period`, `area`, `page` e `grain` na URL.
  O período inicial prefere o último ano integral fechado, segundo os metadados;
  sem esse ano, usa o último mês disponível.

A implementação local não autoriza ativação do release das contas nem implantação.

O classificador do log aceita os dois endereços do painel para `kpi_open` e trata
os aliases como a mesma página ao comparar a navegação RSC. Status 308 continua
fora das contagens; não há dupla contagem. A rota agregada de fichas é
`/contas/favorecidos`, sem o identificador da pessoa ou entidade. Não se ampliam
eventos coletados nem se alteram supressões ou dados históricos.

Na revisão visual local de 24/11, o recorte municipal passou a usar as geometrias
das UFs como contexto e o enquadramento existente do MapView. A composição exibe
todos os itens retornados pela API, sem uma segunda rolagem interna no desktop.
Os links de fichas carregam um retorno restrito a `/contas/painel` e aos filtros
conhecidos, preservando território, período, área, grão e página ao voltar.

## Revisão autorizada em 26/11/2026

A [ADR-0042](0042-navegacao-e-contexto-das-contas.md) substitui o comportamento do Início, a lista resumida de áreas e a restrição visual do ranking anual. A rota paginada `/contas/table` já aceita os cruzamentos de função, período e tipo; o portal passa a consumi-la, sem alterar os contratos públicos. Aplicação pelo recebedor permanece indisponível até integração e validação de fonte própria.

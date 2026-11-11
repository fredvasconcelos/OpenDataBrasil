# ADR-0010: Panorama do Brasil, com taxonomia do portal e KPIs do Tier 1

- **Estado:** Aceito como base de avaliação. O mantenedor revisa o resultado e ajusta a lista depois.
- **Data:** 2026-11-10
- **Contexto normativo:** CLAUDE.md §3.3, §7.3, §15, §19.3, §28 e §29

## Contexto

O mantenedor pediu para incorporar o acervo do SIDRA (9.344 tabelas, 70
pesquisas) só com os agregados de interesse, separados por grandes temas e
subtemas. Na primeira fase, o portal deve responder a uma pergunta simples:
**qual é o panorama geral do país?**

O inventário não pôde ser feito de forma automatizada:

- a página do acervo (`sidra.ibge.gov.br/acervo`) responde 403 com desafio do
  Cloudflare;
- a API de agregados (`servicodados`) não responde a partir da Espanha (KI-002).

Nenhum dos dois foi contornado (§7.3: sem VPN, proxy, imitação de navegador ou
endpoints internos). O mantenedor exportou a lista completa pelo menu oficial
do acervo ("Salvar TSV"), no navegador.

## Decisões

### 1. Regra do Tier 1: Total e percentuais, menor detalhe

Regra definida pelo mantenedor em 2026-11-10, com o exemplo das tabelas 417,
418 e 419:

- em cada família de tabelas (o mesmo assunto com detalhamentos diferentes), a
  tabela-base é a de **menor detalhe**. No exemplo, a 417;
- o **KPI é o valor do Total**. As categorias da dimensão principal aparecem
  como **percentual do Total**, e as demais dimensões ficam no Total;
- as variantes da família com uma única dimensão a mais viram **filtros**.
  Cruzamentos ficam de fora, assim como os recortes especiais do Censo
  Agropecuário (MDA, PRONAF, FAO, tipologia, TI, UC, cor do produtor) e as
  séries encerradas ou experimentais que têm substituta.

### 2. Taxonomia versionada: `configs/catalog/panorama.toml`

O arquivo tem **20 grandes temas, 64 subtemas e 150 KPIs de 147 tabelas**. O
plano falava em "cerca de 60" subtemas; a lista final ficou com 64 para não
juntar assuntos diferentes. Cada KPI informa:

- `id` e `label`;
- `tabela`: código oficial do SIDRA;
- `pesquisa`: inferida do título, a confirmar pelos exports por pesquisa;
- `filtros`;
- `kpi`, quando o item já está publicado no portal;
- `nota`, quando houver.

A lista é uma proposta para avaliação. Ela foi feita pela heurística sobre os
títulos (3.765 bases candidatas) e curada à mão para o panorama nacional.

### 3. Filtros comuns, adaptados ao tema

Território e período valem para todos os temas. Os demais filtros (sexo,
idade, cor ou raça, situação do domicílio, instrução, renda, atividade, porte,
produto, espécie, grupo de produtos, bioma, tamanho do município) são
declarados por tema, e um KPI só usa os filtros do seu tema. Por exemplo, a
agropecuária tem produto e espécie, mas não tem cor ou raça.

### 4. Snapshot do acervo com SHA-256

`configs/catalog/sidra_acervo_2026-11-10.csv` é a exportação oficial, sem
alterações:

- formato `id;nome`, sem cabeçalho, em UTF-8 com BOM;
- SHA-256 `a9ec32ee…5c5c`.

O panorama registra o hash. `odb panorama validar` confere o hash e a
existência de cada tabela no snapshot.

### 5. Publicado e planejado na mesma navegação

A API monta `/api/v1/portal/navigation` a partir do panorama
(`ODB_API_PANORAMA_PATH`). Os KPIs publicados entram no lugar indicado por
`kpi`. Os demais saem em `planned` (tabela, pesquisa, filtros e nota). A
mudança no contrato é aditiva: `ThemeOut.filters` e `SubthemeOut.planned`.

Na carga, cada KPI do portal precisa estar em exatamente um item do
panorama, e vice-versa. Na primeira requisição de cada release, a tabela de
origem publicada na Gold precisa ser a declarada no panorama. Uma divergência
gera o erro `portal_config`.

No portal, os temas ficam recolhidos e só o tema do indicador atual abre. Os
KPIs planejados aparecem desativados, marcados "em preparação", com a tabela
SIDRA no `title`. A página inicial mostra quantos indicadores de cada
subtema estão em preparação.

### 6. Verificação na fonte, sem varredura

`odb panorama verificar` consulta `apisidra.ibge.gov.br/values`:

- só para as tabelas do panorama, cujos códigos vêm do acervo oficial;
- com o cliente HTTP da fonte `ibge-sidra` (2 s entre requisições, novas
  tentativas e respeito a 429);
- sem classificações na consulta, então a resposta traz o Total de cada uma.

O resultado vai para `configs/catalog/panorama_verificacao.json`. Para cada
tabela, registra:

- variáveis e unidades;
- tipo e lista de períodos;
- nomes das classificações e categoria Total;
- contagem de territórios em Brasil, Grande Região, UF, Região Metropolitana e
  Município;
- a URL, o status e o SHA-256 de cada requisição.

A descrição usa o primeiro nível que a tabela aceita. A API responde HTTP 400
"nível incompatível" para os outros. Quando passa de 50.000 valores, a
descrição usa o último período.

Os códigos de classificação (`cNNN`) não vêm na resposta. Não são
descobertos por tentativa (nada de varrer códigos): virão da API de metadados,
quando ela voltar a responder, ou serão informados pelo mantenedor e
conferidos com uma única requisição.

## Consequências

- O portal mostra o panorama completo desde já: 12 KPIs publicados e 138 em
  preparação.
- Os KPIs planejados ainda **não** têm dados na Gold. A ingestão segue por
  ondas, com aprovação, gerando `configs/sources`, `configs/indicators` e
  `configs/portal` a partir do panorama verificado.
- Duas restrições pesam nessa ingestão:
  - séries mensais e trimestrais (IPCA, PMC, PMS, PIM, PNAD trimestral, PIB
    trimestral) exigem que a Silver e o calendário aceitem períodos abaixo do
    ano. Hoje só há ano de referência;
  - a decomposição em percentuais por categoria precisa dos ids das
    classificações (decisão 6). O Total já pode ser ingerido.
- `pesquisa` é inferida. A confirmação depende dos exports por pesquisa do
  acervo (`S_<código>.tsv`).
- A verificação de 2026-11-10 consultou 147 tabelas. 146 responderam. A 3926
  (área dos biomas) não aceita nenhum dos níveis consultados: tem nível
  territorial próprio. Os achados que pedem decisão na avaliação estão em
  [`panorama-tier1.md`](../data_catalog/panorama-tier1.md):
  - **20 tabelas têm Total sem valor** (".." na categoria Total). A regra do
    Total não se aplica a elas, e é preciso escolher uma categoria de
    referência. Exemplos:
    - índices mensais (PMC, PMS, PIM, por "Tipos de índice");
    - PIB trimestral (setores);
    - rebanhos (não se somam espécies);
    - séries da PNAD em que a idade não tem Total;
  - **4 tabelas não têm o nível Brasil**:
    - 417, da POF de 1987 a 2008, só com regiões metropolitanas. Pode ser
      trocada por uma equivalente nacional mais recente;
    - 10457 e 896, só por UF;
    - 5945, só por Grande Região;
  - **9 séries terminam antes de 2015**;
  - os tipos de período verificados são **121 anuais, 14 mensais e 11
    trimestrais**.

## Atualização de 2026-11-11: descritores oficiais e onda de Totais

### 7. Descritor oficial da tabela como fonte de metadados

O mantenedor indicou o endpoint `https://apisidra.ibge.gov.br/DescritoresTabela/t/<tabela>`,
da própria apisidra, e decidiu usá-lo para todos os dados (a API de agregados
do `servicodados` segue inacessível daqui, KI-002). O descritor traz:

- variáveis, com unidade e se podem ser somadas entre territórios
  (`PermiteSomaUnidadesTerritoriais`);
- classificações com o **código** (`c339`, `c12190`…), as categorias e a
  indentação hierárquica (`NivelIdentacao`), e se as categorias somam o Total;
- níveis territoriais com o código (por exemplo, a 3926 usa N123 Bioma e
  N1103 Total), períodos, notas (`Nota`) e fonte (`Fonte`).

`odb panorama descrever` grava o descritor de cada tabela do panorama em
`configs/catalog/descritores/t<tabela>.json`, sem alteração, com SHA-256 e data
em `descritores/indice.json`. São 147 requisições (uma por tabela do acervo),
no ritmo da fonte; nada é varrido. Isso resolve a pendência dos códigos de
classificação (decisão 6) e a das notas das tabelas (KI-001) para o panorama.

### 8. Onda de Totais: `odb panorama gerar`

O gerador lê o panorama, a verificação e os descritores e escreve três
**fragmentos**, sem tocar nos arquivos curados:

- `configs/sources/ibge-panorama.toml` (só datasets; fonte e licença vêm de
  `ibge.toml`);
- `configs/indicators/demografia/panorama.toml` (fatos e indicadores);
- `configs/portal/demografia/panorama.toml` (KPIs).

Os carregadores passaram a aceitar fragmentos: um arquivo de fontes sem
instituição; e `<escopo>/*.toml` no catálogo semântico e no portal.

Entra só o KPI cujo valor publicado **é o próprio Total**:

- período anual;
- toda classificação numa categoria única com nome (o Total ou a
  categoria-padrão da tabela);
- nível Brasil, Grande Região, UF ou Município;
- uma variável com unidade única. A variável é a fixada em `variavel` ou a
  primeira que não é coeficiente de variação, intervalo de confiança ou
  distribuição.

As classificações do Total viram `fixed_categories` do fato (nome da
dimensão → código da categoria observado na fonte). A Gold confere que toda
observação está nessa categoria (`semantics.fixed_categories`) e retira a
dimensão. A aditividade vem do descritor. Notas oficiais e fonte entram no
indicador.

Um KPI gerado tem o `id` do item do panorama. Por isso a ligação passou a ser
implícita: o item está publicado quando o portal tem o KPI de `kpi` ou, sem
`kpi`, um KPI com o mesmo id.

Ficam de fora desta onda, com o motivo no catálogo:

- `requer_categoria = true`: 19 KPIs cujo Total é só o universo da tabela.
  Exemplo: "Municípios com Plano Diretor" daria o número de municípios.
  Publicar esse número com esse rótulo seria enganoso;
- tabelas sem categoria Total. A API devolve a categoria "0" sem nome e o
  valor `..`, que na legenda oficial significa **"não se aplica"** (a primeira
  versão desta ADR chamou isso de "não disponível", que é `...`);
- períodos mensais e trimestrais;
- níveis que a Gold ainda não tem (RM, Bioma);
- variáveis em moedas que mudam ao longo da série (Cruzeiro, Cruzado, Real).

### 9. Tabelas como a fonte publica

Decisão do mantenedor (2026-11-11): uma tabela sem o nível Brasil, ou com uma
série encerrada antes de 2015, é apresentada como a fonte a publica. A
limitação aparece nas notas do indicador.

### 10. Tabela 6715 completa (POF 2017-2018)

A pedido do mantenedor, a 6715 entra inteira, curada à mão a partir do
descritor (`configs/indicators/demografia/pof.toml`):

- c339, com 7 classes de rendimento e o Total;
- c12190, com 93 tipos de despesa em 17 partições, que seguem a indentação
  oficial;
- variáveis 1201 (Reais) e 1204 (%).

O descritor diz que as categorias não podem ser somadas e que as variáveis
não somam entre territórios. Por isso as partições são não exaustivas e os
indicadores, não aditivos. No portal, o KPI mostra as classes de rendimento e
os 11 grupos de despesas de consumo.

### 11. Timeouts da fonte: adiar, repescar e pausar

Proposta do mantenedor (2026-11-11). Algumas tabelas demoram muito na fonte.
Na primeira carga, a 4412 (casamentos) não respondia em 120 s nas consultas
municipais. Uma tabela lenta não pode segurar as demais:

- `odb ingest run` adia o dataset na primeira falha transitória (2 tentativas
  por requisição) e o repesca depois dos demais, em até 2 rodadas. A última
  rodada usa as tentativas normais da fonte;
- na repescagem, os períodos já baixados na mesma execução voltam da Bronze
  (`reused`), sem novo download;
- o watermark continua só com a carga completa: a Silver nunca vê dado
  parcial;
- `pausado = "<motivo>"` no panorama tira o KPI da geração do catálogo e do
  portal, mas mantém o dataset nas fontes para repescar. Assim o release não
  espera a tabela lenta;
- o tempo de espera do SIDRA subiu para 300 s: com ele, a 4412 respondeu.

Resultado da carga de 2026-11-11: 76 de 77 tabelas na primeira execução. A
4412 ficou em espera, foi repescada com 300 s e volta ao panorama quando
estiver completa. O release `0128e3fa` foi ativado no ambiente local com 89
KPIs no portal (392 verificações aprovadas e 5,1 milhões de observações).

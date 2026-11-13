# ADR-0016: Séries de tabelas, detalhes marginais e POF de 1987 a 2018

- **Estado:** aceito (2026-11-12). O mantenedor aprovou as decisões da POF e delegou as
  de detalhe ("pode tomar as decisões que considerar"), com revisão no relatório de
  pontos críticos (`docs/relatorios/2026-11-12-pontos-criticos.md`).
- **Contexto normativo:** CLAUDE.md §9.4, §10.4, §13.3, §15.4, §16.2, §19.3 e §28.5.

## Contexto

1. **POF.** A Gold tinha só a POF 2017-2018 (SIDRA 6715). O mantenedor pediu a série
   em reais desde 2002-2003. As edições anteriores ficam em tabelas próprias:
   - 2309 (2002-2003);
   - 1594 (2008-2009);
   - 387, 400 e 414 (1987-1988 e 1995-1996, só percentuais e só nas regiões
     metropolitanas);
   - 417 (aquisição alimentar, de 1987 a 2008).
2. **Detalhes.** Cada KPI gerado do panorama tinha uma dimensão principal; as outras
   classificações ficavam fixas no Total. O mantenedor pediu "todos os detalhes
   possíveis".

## Decisões

### 1. Série de tabelas SIDRA num só fato

- Os datasets de cada edição declaram `silver.series` (o id da série) e
  `silver.series_order` (1, 2, ...). É o mesmo mecanismo do Sinesp VDE (ADR-0012),
  agora também para o transformador `sidra_observation`.
- A tabela, o link e a licença da série são os do membro mais recente. Cada observação
  guarda a tabela de origem (`source_table_id`).
- **Regras por tabela de origem** (`facts.table_rules.<tabela>`):
  - `fixed_categories`: dimensões fixas só nas linhas daquela tabela. A conferência
    passou a ser feita por tabela de origem.
  - `missing_as_total`: classificações do fato que a tabela não tem. As linhas dela
    entram no Total, porque o valor é do universo inteiro.
- **Catálogo operacional:** uma série sem dataset próprio ganha uma linha em
  `catalog.dataset`, a partir do membro mais recente (`series_rows`). O Sinesp continua
  com o dataset real da página de notas.

### 2. POF 2002, 2008 e 2018 em reais

- **Série `ibge-pof-despesa-familiar`:** 2309 → 1594 → 6715, no fato
  `fact_pof_household_expense`.
- **Tipos de despesa (c12190):**
  - 2008 e 2018 têm as mesmas 93 categorias;
  - 2002 tem 89: 71 com os mesmos códigos e 18 próprias, que entram como irmãs nas
    partições e só têm valor em 2002.
- **Classes de rendimento (c339):** só em 2008 e 2018. As faixas em reais mudam, mas
  são as mesmas em salários mínimos (2, 3, 6, 10, 15 e 25 SM; R$ 415 em 2008 e
  R$ 954 em 2018), como o mantenedor aceitou, com notas explicativas.
- **2002:** usa outro conceito de rendimento (c12191) e entra só no Total. A situação
  do domicílio e as classes de 2002 ficam fixas no Total, e a c339 entra como Total
  implícito.
- **Valores nominais:** os valores ficam em reais da época, sem correção pela inflação.
  A correção seria uma regra estatística nova e está no relatório de pontos críticos.
- **Território:** 2002 só tem Brasil e Grandes Regiões; as UFs começam em 2008.

### 3. Mostrar só o que existe no período

- **Tooltip:** a API omite as categorias sem nenhuma observação no período e
  território, como uma faixa de rendimento de outra edição.
- **Tabela:** omite as colunas sem dado no período.
- **Série:** já trazia só os pontos existentes. Ao filtrar uma categoria no gráfico de
  evolução, aparecem só as edições em que ela existe.
- A regra vale para todos os KPIs. A categoria publicada sem valor ("..", "-")
  continua aparecendo com o símbolo, porque tem observação.

### 4. POF de 1987 e 1995 (opção A do mantenedor)

- **Fontes:** 387 (despesa), 400 (despesa com alimentação) e 414 (recebimento), só em
  percentuais, em série separada da nacional. A 417 entra com as quatro edições (1987
  a 2008), sempre nas mesmas áreas.
- **Níveis novos na Gold:**
  - `regiao_metropolitana` (SIDRA n7): o código começa pelo da UF, e a UF é o pai;
  - `areas_pof` (SIDRA n103, "Total das áreas"): pai Brasil.
  - Não há geometria: esses KPIs não têm mapa.
- **Classificações:**
  - Os tipos de despesa (c210) e as origens (c214) não têm hierarquia no descritor.
    Ficam numa partição única, não somável, sem inventar a árvore.
  - A 400 tem outra raiz ("Despesa em alimentação") e usa a classificação própria
    `c210alim` (ADR-0014).
  - As classes de recebimento (c201) são as mesmas nas quatro tabelas, em salários
    mínimos.
- **Portal:**
  - o KPI declara `map_levels = []`, porque na malha municipal só Brasília e Goiânia
    teriam cor;
  - sem nível Brasil, o painel abre no "Total das áreas da POF" (`defaultGeography`),
    com a tabela nas regiões metropolitanas;
  - um território de nível que o KPI não publica volta ao inicial.

### 5. Detalhes marginais nos KPIs gerados

- **Conector:** `extra_sets` (e `extra_levels`) gera uma requisição por classificação
  adicional, com a principal e as demais no Total e sem o Total da adicional, que já
  vem na requisição principal.
  - A partição leva o código da classificação detalhada (`-xc240`), e não a posição
    do conjunto: incluir ou tirar um detalhe não muda as partições dos outros.
  - Na primeira carga, em 2026-11-12, o sufixo era numerado (`-x1`). Com a inclusão de
    um detalhe, a 2609, a 2654 e a 4412 ficaram com a mesma classificação em duas
    partições, e a Silver acusou chave duplicada.
  - As partições numeradas ficaram na Bronze, fora da configuração vigente, e a Silver
    as ignora. Não há cruzamentos: com eles, as consultas se
  multiplicariam além do limite de 50.000 valores.
- **Gerador (`plan_extras`):** entra cada classificação fixa que tem Total no descritor,
  cabe em 45.000 valores por requisição e não conflita com a hierarquia declarada.
  - Os municípios entram só com até três períodos, como na dimensão principal.
  - A classe de tamanho do município fica até UF, porque cada município está numa só
    classe.
  - Uma partição curada serve se contém todas as categorias da tabela.
  - Se os códigos conflitam com os de outra tabela (Total diferente ou faixas
    diferentes), a tabela ganha uma classificação própria (`c2t2609`, `c58t7113`;
    ADR-0014), com o mesmo rótulo no portal. Na fonte, o código continua o do SIDRA.
    Exemplos: o "Sexo" do Registro Civil tem Total 0, e os grupos de idade mudam de
    tabela para tabela.
  - O Total pedido explicitamente, quando não é o padrão da API ("15 anos ou mais"),
    continua na requisição principal.
- **Portal:** o KPI declara `exclusive_dimensions = true`. O portal detalha uma
  dimensão por vez, com o aviso "Uma por vez", e a API recusa duas (422, `semantic_rule`). O indicador
  ganha a nota "Detalhes por …: um de cada vez, com os demais no Total".
- **Resultado em 2026-11-12:** 48 KPIs com 69 classificações a mais, 16 delas próprias
  de uma tabela. A dimensão principal também usa a classificação própria: com isso,
  entraram a 10061 (nível de instrução do Censo) e as categorias da 7461, 6736 e 9949,
  que antes ficavam no Total. Exemplos: idade
  da mãe nos nascidos vivos; mês, local e idade nos óbitos; cor ou raça na
  alfabetização; situação do domicílio em vários indicadores; tipo de inspeção nos
  abates.

## Consequências

- A Gold aceita edições de pesquisa com classificações diferentes sem duplicar
  indicadores, e cada valor continua rastreável até a tabela de origem.
- O usuário pode filtrar uma faixa de rendimento e ver só as edições em que ela
  existe. A comparação entre edições é nominal e está anotada no indicador.
- **Cruzamentos:** os detalhes marginais não permitem cruzar duas classificações. Um
  cruzamento específico precisaria de uma requisição própria (decisão por KPI).
- **Volume:** a primeira versão, com 42 tabelas, somava 417 requisições extras na
  ingestão completa (as maiores: óbitos 2654, com 66, e abates 1092, com 60). A
  atualização incremental só baixa os períodos novos.

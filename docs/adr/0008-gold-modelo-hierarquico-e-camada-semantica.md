# ADR-0008 — Gold: modelo hierárquico, camada semântica e consulta

- **Estado:** Aceito
- **Data:** 2026-11-04
- **Contexto normativo:** CLAUDE.md §10, §11, §13, §15, §16, §17 e §27 (Fase 4)

## Contexto

O mantenedor pediu que os indicadores fossem organizados em duas hierarquias:

- **territorial**, do macro ao micro (Brasil → município), com totais oficiais
  em cada nível;
- **temática e de desagregação**, como no portal Séries Estatísticas do IBGE
  (por exemplo, "Censo 2022 › Pessoas indígenas › Quesito de declaração › Se
  considera indígena").

O universo de municípios muda entre anos (emancipações), e isso é esperado.
O plano foi aprovado com as tabelas 9605, 9718 e 9578. Ficaram para a etapa 4b
a 9970, a 9971, a 9954 e a 9723 (sexo, idade, terras indígenas e territórios
quilombolas como unidades territoriais).

## Decisões

### 1. Pacotes `semantics` e `modeling` (§21)

- `odb_semantics`: catálogo semântico versionado
  (`configs/indicators/<escopo>.toml`), níveis territoriais e planejador de
  consultas com as regras semânticas. Não depende de nenhuma fonte.
- `odb_modeling`: transformação Silver → Gold (Polars), contratos Gold,
  qualidade e construtor. O mapeamento de níveis do SIDRA (`NC` 1, 2, 3, 6)
  fica isolado em `odb_modeling.model.SIDRA_LEVELS`.

### 2. Hierarquia territorial

- `dim_geography`, com chave determinística `nível:código`
  (`municipio:2927408`) e níveis internos `brasil`, `regiao`, `uf`,
  `regiao_intermediaria`, `regiao_imediata` e `municipio`. Os códigos de nível
  do SIDRA para as regiões geográficas não foram verificados e não são usados.
- A árvore vem da DTB vigente. Uma região intermediária ou imediata com mais
  de um pai bloqueia a construção.
- Território observado e ausente da DTB entra com `in_reference = false`. O pai
  é derivado da estrutura do código (UF = 2 primeiros dígitos), e o caso vira
  aviso.
- `bridge_geography_ancestor` traz o fecho transitivo (cada território com
  todos os ancestrais, inclusive ele mesmo).
- Os totais de cada nível são sempre os **publicados**. A Gold não recalcula
  agregados oficiais.

### 3. Hierarquia temática e de desagregação

- `dim_indicator_node`: árvore grupo → indicador → classificação → categoria,
  com os grupos declarados em `path` e as categorias observadas nos dados.
- `dim_classification` e `dim_category`: o Total é a raiz. As categorias filhas
  formam **partições** declaradas no catálogo, exaustivas ou não. Exemplos:
  a c2661 tem duas partições (terras indígenas e territórios quilombolas); a
  c86 é não exaustiva (não publica "sem declaração").
- `dim_breakdown`: combinação de categorias de uma observação
  (`c1714:60026|c2661:32776`), com rótulo e lista das classificações fora do
  Total.
- Uma categoria observada sem posição declarada na hierarquia bloqueia a
  construção (`semantics.category_hierarchy`).

### 4. Indicador = dataset × variável

Cada variável publicada de cada tabela é um indicador com identificador interno
estável. Os totais repetidos entre tabelas (a população residente aparece em
4714, 9605, 9718 e 9578) ficam em indicadores separados, cada um com a sua
desagregação. Isso evita escolher arbitrariamente uma fonte para o mesmo
número. O indicador declara:

- unidade (conferida contra a publicada);
- aditividade: `non_additive` nunca é somado;
- conceito;
- incompatibilidades com motivo (simétricas na Gold);
- alertas, exibidos em toda consulta.

### 5. Fatos temáticos e estrutura universal (§10.3, §10.6)

- `indicator_observation`: indicador × território × período × desagregação,
  com valor oficial, estado, texto original, linhagem Bronze (artefato e
  SHA-256), versão Silver e construção Gold. Particionada por `dataset_id`.
- Fatos temáticos (formato largo, uma medida por indicador), com granularidade
  declarada no catálogo: `fact_population_estimate`, `fact_census_population`,
  `fact_population_by_race`, `fact_indigenous_population` e
  `fact_quilombola_population`. Medida ausente na granularidade tem estado
  `absent`.
- `dim_period`: só anos nesta versão. Período não anual bloqueia até haver
  decisão. Não há `dim_calendar` completa.
- Notas oficiais viram marcação: os municípios com instalação prevista (6579:
  2004, 2008 e 2012) são resolvidos pelo nome publicado no próprio
  dataset/período ("Nome - UF"). O fato recebe `pending_installation`, e a
  observação recebe `flags`. Nome não encontrado ou ambíguo bloqueia.

### 6. Qualidade da Gold

Bloqueiam (`fail`): contrato e chave de cada tabela, integridade referencial,
unidade divergente, nível ou classificação sem mapeamento, categoria sem
hierarquia, nota não resolvida e divergência entre Gold e Silver (contagem e
soma por indicador).

Avisos (`warn`): reconciliação por categoria (partição exaustiva com soma
diferente do Total, ou não exaustiva com soma acima do Total) e territórios
fora da referência. Só entram contextos em que todos os valores são numéricos.

### 7. Construção, idempotência e publicação

- Impressão digital: versões Silver, hash do catálogo semântico, versões dos
  contratos e `MODEL_VERSION`. Igual à da última construção válida: `skipped`,
  sem versão Delta nova.
- Todos os schemas são conferidos antes da primeira escrita. Depois, cada
  tabela é gravada por inteiro (`overwrite`). O volume (cerca de 460 mil
  observações, 6 s) não justifica escrita incremental agora.
- A construção não publica nada. `odb gold build` cria e valida um release
  (ADR-0004) e só ativa com `--activate`. Falha na construção não cria
  release, e o vigente continua ativo.
- Registro: `operations.gold_build`, `quality.gold_check_result` e
  `catalog.indicator` (metadados sincronizados de `dim_indicator`; os valores
  ficam só na Gold). Migração 0005.

### 8. Consulta semântica (`odb query`)

O planejador recebe uma consulta estruturada e gera SQL só com fragmentos
fixos. Os valores entram como parâmetros, e as tabelas como `{{alias}}`
resolvidos pelo release ativo (ADR-0003). Regras:

1. indicador publicado no release;
2. indicadores incompatíveis não são combinados (as duas definições de
   população indígena);
3. nível territorial entre os disponíveis do indicador;
4. desagregação só por classificações do indicador. As classificações não
   pedidas ficam no Total, então totais e categorias nunca se misturam;
5. `--sum-to` (soma até um nível superior) só para indicadores aditivos. O
   resultado é marcado como derivado (`derived_sum` ou `incomplete_sum`) e
   traz a contagem de filhos sem valor e com instalação prevista.

### 9. Ajustes nas fases anteriores

- **Limite do SIDRA:** é de 50.000 valores por consulta, não 100.000. O
  conector ganhou `split_by_variable` e `split_by_classification`, e a chave de
  partição recebe o sufixo do grupo (`n1n2n3n6-p2022-v350-c2661-12869`).
- **Reconciliação da Silver (complementa a ADR-0007):** grupos com filhos sem
  valor numérico (por exemplo, `X`) são incompletos. A soma conhecida abaixo
  do oficial não gera aviso; acima, gera. Isso veio de 148 avisos na
  9718/9578, todos explicados por supressão.

### 10. Exportação para análise local

`odb gold export` copia um release **publicado** (ativo ou por `--release`)
para `data/exports/<escopo>/<release_id>/`, fora do lakehouse. A cópia leva
Parquet por tabela, um `gold.duckdb` autocontido (tabelas e views de análise),
um manifesto com SHA-256 e um aviso de cópia não oficial. A invalidação é por
release, e as pastas antigas podem ser apagadas. Como as exportações do portal
(§19.3), a cópia não é fonte oficial e não é lida pela plataforma.

## Consequências

- O mesmo modelo recebe novas tabelas com classificações cruzadas só por
  configuração (catálogo semântico e fontes), desde que os níveis territoriais
  sejam os já mapeados.
- Recortes que atravessam municípios (terras indígenas, territórios
  quilombolas) exigirão um sistema territorial próprio, ligado aos municípios
  por relação muitos-para-muitos (etapa 4b).
- Os percentuais publicados ficam como indicadores não aditivos. Não há
  indicadores derivados por fórmula nesta fase.
- O release é interno enquanto a licença estiver em `requires_review` (KI-003).

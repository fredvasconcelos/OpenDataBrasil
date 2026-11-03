# ADR-0007 — Silver: modelagem, valores especiais e reconciliação

- **Estado:** Aceito
- **Data:** 2026-11-03
- **Contexto normativo:** CLAUDE.md §9, §13, §16 e §27 (Fase 3)

## Decisões

### 1. Tabela genérica `silver/ibge/sidra_observation`

Uma tabela única para todas as tabelas SIDRA, particionada por `table_id`, no
formato long. A chave é `(table_id, variable_id, territorial_level, territory_id,
period, classification_key)`.

- **O nível territorial faz parte da chave**, porque códigos se repetem entre
  níveis: o Brasil e a região Norte têm ambos o código `1`. Esse caso real foi
  detectado pela validação da ingestão.
- Classificações (sexo, idade, …) ficam em `classifications`, como lista de
  `{dimension, category_id, category_name}`, mais uma `classification_key`
  textual. Os nomes das dimensões vêm do cabeçalho da resposta. Nenhum
  identificador é inventado.
- Contrato `sidra_observation` 1.0.0, em `odb_processing.contracts`.

### 2. Valores especiais pela legenda oficial do SIDRA

| Símbolo | `value_status` | `value` |
|---|---|---|
| número | `valid` | decimal(38,6) |
| `0` | `rounded_zero` | 0 |
| `-` | `true_zero` | 0 |
| `...` | `not_available` | nulo |
| `..` | `not_applicable` | nulo |
| `X` | `suppressed` | nulo |
| A–Z (exceto X) | `range_code` | nulo |
| outro | `conversion_error` (**bloqueia** a escrita) | nulo |

`value_raw` preserva o texto original, e `value_decimals` registra as casas
publicadas, usadas na tolerância de arredondamento. Ausências nunca viram zero.

### 3. Totais oficiais de todos os níveis

A ingestão SIDRA consulta `n1`, `n2`, `n3` e `n6` na mesma requisição. A
reconciliação compara contra o **valor publicado** para o nível superior, e a
Gold poderá usar agregados oficiais em vez de recalculá-los. A chave de
partição inclui a assinatura dos níveis (`n1n2n3n6-p2025`), então mudar os
níveis gera partições novas e preserva as anteriores na Bronze.

### 4. Reconciliação não bloqueia a Silver

Divergência entre a soma dos filhos e o valor oficial do pai gera **`warn`**,
com detalhes por período e território. A Silver reflete a fonte fielmente, e o
tratamento analítico é decidido na Gold (Fase 4). As variáveis somáveis são
declaradas por dataset (`[datasets.silver].additive_variables`):

- `exact`: contagens inteiras (população);
- `rounding`: tolerância `0,5 * 10**-d * (n_filhos + 1)` (área);
- variáveis não declaradas (densidade, razões) nunca são somadas.

### 5. Escrita e idempotência

- Cada build substitui por inteiro a partição do dataset (`replace_where`
  `table_id = …`; na DTB, `reference_year = …`). Linhas removidas pela fonte
  saem da Silver.
- Uma impressão digital (checksums de entrada + contrato + parâmetros Silver)
  igual à da última execução válida gera `skipped`, sem versão Delta nova.
- O SHA-256 dos arquivos Bronze é conferido antes da leitura.
- Verificações `fail` (contrato, nulos obrigatórios, unicidade, domínio de
  códigos, erro de conversão) e mudança de schema incompatível bloqueiam a
  escrita. A versão anterior permanece.

### 6. DTB como referência territorial

`silver/ibge/dtb_municipality`, a partir do ODS oficial. A linha de cabeçalho é
localizada pelo conteúdo e a data base é lida do arquivo. A Grande Região é
derivada do 1º dígito da UF, regra confirmada pelos códigos N2 publicados no
SIDRA (teste `test_regions_convention_matches_sidra_n2`).

### 7. Leitura de ODS e XLS

`fastexcel` 0.21.0 (calamine), via `polars.read_excel`.

## Consequências

- Uma observação é rastreável até o artefato Bronze `stored` (id + SHA-256).
- Datasets com classificações exigirão validar a ordem das dimensões `D4+`
  contra a configuração quando forem incorporados.
- As divergências encontradas estão documentadas em `docs/data_catalog/ibge.md`
  e precisam de decisão na Gold.

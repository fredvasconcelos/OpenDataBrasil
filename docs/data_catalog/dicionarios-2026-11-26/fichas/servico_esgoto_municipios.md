# Municípios com rede coletora de esgoto

Ficha `servico_esgoto_municipios` · indicador `servico_esgoto_municipios` · **disponivel_snapshot**.

## Significado e uso

Municípios com serviço de esgotamento sanitário (Pesquisa Nacional de Saneamento Básico, tabela SIDRA 7461). Tabela sem classificações. Fonte: IBGE - Pesquisa Nacional de Saneamento Básico.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território (Brasil, Grande Região, UF, Município) x ano x condição de funcionamento do serviço.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-7461` | [7461/2601](https://sidra.ibge.gov.br/tabela/7461) | Municípios com serviço de esgotamento sanitário / Unidades | M36 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 7461 / 2601

Pesquisa/produtor: Pesquisa Nacional de Saneamento Básico. Periodicidade: período único. Disponibilidade na fonte: 2017.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A tabela contabiliza um Município sempre que pelo menos uma entidade do Município informa realizar determinada atividade, ou possuir uma dada característica. Um mesmo Município pode ter mais de uma entidade executora do serviço.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["2017"], "uf": ["2017"], "municipio": ["2017"], "brasil": ["2017"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": false, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M36 — PNSB](../pesquisas.md#m36): Serviços coletivos de água e esgotamento e seus prestadores. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M36: Recuperar regras de agregação das entidades para município e comparabilidade dos questionários 2008/2017.

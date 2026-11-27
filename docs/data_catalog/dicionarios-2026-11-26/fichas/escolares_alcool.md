# Escolares de 13 a 17 anos que consumiram bebida alcoólica

Ficha `escolares_alcool` · indicador `escolares_alcool` · **disponivel_snapshot**.

## Significado e uso

Percentual de escolares com idade de 13 a 17 anos que consumiram bebidas alcoólicas pelo menos um dia nos 30 dias anteriores à pesquisa (Pesquisa Nacional de Saúde do Escolar, tabela SIDRA 6358). Tabela sem classificações. Fonte: IBGE - Pesquisa Nacional de Saúde do Escolar.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território (Brasil, Grande Região) x ano x dependência administrativa da escola | sexo | grupo de idade.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-6358` | [6358/8592](https://sidra.ibge.gov.br/tabela/6358) | Percentual de escolares com idade de 13 a 17 anos que consumiram bebidas alcoólicas pelo menos um dia nos 30 dias anteriores à pesquisa / % | M07 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 6358 / 8592

Pesquisa/produtor: Pesquisa Nacional de Saúde do Escolar. Periodicidade: período único. Disponibilidade na fonte: 2015.
Precisão de armazenamento/apresentação no descritor: 8 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2015"], "regiao": ["2015"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": false, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M07 — PeNSE](../pesquisas.md#m07): Fatores de risco e proteção à saúde dos escolares. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M07: Rever questionário e desenho de cada edição vinculada às três variáveis; não transferir universo de 2019 para tabelas de 2015.

# Área territorial de favelas

Ficha `area_favelas` · indicador `area_favelas` · **disponivel_snapshot**.

## Significado e uso

Área territorial de favelas e comunidades urbanas

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Quilômetros quadrados**. Grão: território x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t9888-v9911` | [9888/9911](https://sidra.ibge.gov.br/tabela/9888) | Área territorial de favelas e comunidades urbanas / Quilômetros quadrados | M01 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 9888 / 9911

Pesquisa/produtor: Censo Demográfico. Periodicidade: anual. Disponibilidade na fonte: 2022.
Precisão de armazenamento/apresentação no descritor: 3 / 3 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - Dados do Universo; 2 - Para informações detalhadas a respeito da identificação das Favelas e Comunidades Urbanas, pelo IBGE, e dos critérios de divulgação dos resultados censitários para essas áreas, consultar a publicação Favelas e Comunidades Urbanas: Primeiros Resultados do Universo; 3 - População residente são as pessoas que tinham o domicílio como local de residência habitual e estavam presentes na data de referência da pesquisa, ou ausentes, temporariamente, por período não superior a 12 meses em relação àquela data; e 4 - O cálculo da área territorial das Favelas e Comunidades Urbanas foi feito a partir dos limites dos setores censitários. Por essa razão, a área territorial calculada para algumas Favelas e Comunidades Urbanas pode incluir áreas urbanas próximas não ocupadas, ou seja, sem domicílios ou edificações.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["2022"], "uf": ["2022"], "brasil": ["2022"], "municipio": ["2022"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": false, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M01 — Censo Demográfico](../pesquisas.md#m01): Enumeração de residentes habituais e características de pessoas e domicílios; serve à descrição territorial e ao planejamento. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M01: Verificar os manuais de cada edição histórica e os universos/denominadores de cada razão, mediana e taxa; a fonte geral não resolve essas fórmulas por variável.

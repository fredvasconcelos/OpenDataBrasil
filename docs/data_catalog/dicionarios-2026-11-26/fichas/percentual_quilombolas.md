# Percentual de pessoas quilombolas

Ficha `percentual_quilombolas` · indicador `censo_percentual_quilombolas` · **disponivel_snapshot**.

## Significado e uso

Pessoas quilombolas em relação à população residente, em percentual, publicado pelo IBGE.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território x ano censitário x localização do domicílio.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-9578` | [9578/4728](https://sidra.ibge.gov.br/tabela/9578) | Percentual de pessoas quilombolas no total de população residente / % | M01 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 9578 / 4728

Pesquisa/produtor: Censo Demográfico. Periodicidade: decenal. Disponibilidade na fonte: 2022.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1- Dados do Universo. 2- Definiu-se como quilombola a pessoa residente em localidades quilombolas que se declarou quilombola. 3- Definiu-se como localidades quilombolas aquelas que compõem o conjunto dos Territórios Quilombolas oficialmente delimitados, dos agrupamentos quilombolas e das demais áreas de conhecida ou potencial ocupação quilombola. Para mais detalhes, consultar a documentação metodológica. 4- O conjunto dos Territórios Quilombolas oficialmente delimitados é composto pelos territórios com alguma delimitação formal na data de referência da pesquisa – 31 de julho de 2022, conforme os cadastros do Instituto Nacional de Colonização e Reforma Agrária – INCRA e dos órgãos com competências fundiárias nos Estados e Municípios. Para mais informações, consultar a documentação metodológica. 5- Os dados apresentados foram atualizados em 22/12/23 e referem-se aos dados coletados até o dia 28/05/2023, com a incorporação das revisões realizadas entre 29/05/2023 e 07/07/2023.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2022"], "municipio": ["2022"], "uf": ["2022"], "regiao": ["2022"]}`.

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

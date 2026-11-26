# Pessoas indígenas

Ficha `pessoas_indigenas` · indicador `censo_pessoas_indigenas_sexo_idade` · **disponivel_snapshot**.

## Significado e uso

Pessoas indígenas por sexo, grupos quinquenais de idade, localização do domicílio em relação a terras indígenas e situação urbana ou rural.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Pessoas**. Grão: território x ano censitário x sexo x grupo de idade x localização do domicílio x situação do domicílio.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-9971` | [9971/350](https://sidra.ibge.gov.br/tabela/9971) | Pessoas indígenas / Pessoas | M01 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 9971 / 350

Pesquisa/produtor: Censo Demográfico. Periodicidade: decenal. Disponibilidade na fonte: 2022.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - Dados do Universo. 2 - No Censo Demográfico 2022, definiu-se como indígena a pessoa residente em localidades indígenas que se declarou indígena pelo quesito de cor ou raça ou pelo quesito se considera indígena; ou a pessoa residente fora das localidades indígenas que se declarou indígena no quesito de cor ou raça. Por essa razão, o total de pessoas indígenas é superior ou igual ao total de pessoas de cor ou raça declarada indígena, nos diferentes recortes. 3 - No Censo Demográfico 2022, foram consideradas localidades indígenas aquelas que compõem o conjunto das Terras Indígenas, dos agrupamentos indígenas e das demais áreas de conhecida ou potencial ocupação indígena. Para mais detalhes, consultar a documentação metodológica. 4 - No Censo Demográfico 2022, foram consideradas as Terras Indígenas declaradas, homologadas, regularizadas ou encaminhadas como Reservas Indígenas até 31 de julho de 2022, data de referência da pesquisa, conforme os dados da Fundação Nacional dos Povos Indígenas – FUNAI. Para mais informações, consultar a documentação metodológica.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["2022"], "uf": ["2022"], "municipio": ["2022"], "brasil": ["2022"]}`.

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

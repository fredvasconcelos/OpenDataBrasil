# População residente por quesito de declaração indígena

Ficha `apoio--censo_residentes_declaracao_indigena` · indicador `censo_residentes_declaracao_indigena` · **apoio_no_release_snapshot**.

## Significado e uso

População residente total por quesito de declaração indígena e localização do domicílio em relação a terras indígenas.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Pessoas**. Grão: território x ano censitário x quesito de declaração indígena x localização do domicílio.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-9718` | [9718/93](https://sidra.ibge.gov.br/tabela/9718) | População residente / Pessoas | M01 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 9718 / 93

Pesquisa/produtor: Censo Demográfico. Periodicidade: decenal. Disponibilidade na fonte: 2022.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1- Dados do Universo. 2- No Censo Demográfico 2010, definiu-se como indígena a pessoa residente em terras indígenas que se declarou indígena pelo quesito de cor ou raça ou pelo quesito se considera indígena; ou a pessoa residente fora das terras indígenas que se declarou indígena no quesito de cor ou raça. 3- No Censo Demográfico 2022, definiu-se como indígena a pessoa residente em localidades indígenas que se declarou indígena pelo quesito de cor ou raça ou pelo quesito se considera indígena; ou a pessoa residente fora das localidades indígenas que se declarou indígena no quesito de cor ou raça. 4- No Censo Demográfico 2022, foram consideradas localidades indígenas aquelas que compõem o conjunto das Terras Indígenas, dos agrupamentos indígenas e das demais áreas de conhecida ou potencial ocupação indígena. Para mais detalhes, consultar a documentação metodológica. 5- No Censo Demográfico 2010, o conjunto das Terras Indígenas foi formado por aquelas que estavam na situação fundiária de declarada, homologada, regularizada e em processo de aquisição como reserva indígena até a data de 31 de dezembro de 2010. 6- No Censo Demográfico 2022, foram consideradas as Terras Indígenas declaradas, homologadas, regularizadas ou encaminhadas como Reservas Indígenas até 31 de julho de 2022, data de referência da pesquisa, conforme os dados da Fundação Nacional dos Povos Indígenas – FUNAI. Para mais informações, consultar a documentação metodológica. 7- Os dados apresentados foram atualizados em 22/12/23 e referem-se aos dados coletados até o dia 28/05/2023, com a incorporação das revisões realizadas entre 29/05/2023 e 07/07/2023.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `["2022"]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M01 — Censo Demográfico](../pesquisas.md#m01): Enumeração de residentes habituais e características de pessoas e domicílios; serve à descrição territorial e ao planejamento. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M01: Verificar os manuais de cada edição histórica e os universos/denominadores de cada razão, mediana e taxa; a fonte geral não resolve essas fórmulas por variável.

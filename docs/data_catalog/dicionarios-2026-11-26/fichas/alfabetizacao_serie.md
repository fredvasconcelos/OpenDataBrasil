# Taxa de alfabetização (Censos e PNAD)

Ficha `alfabetizacao_serie` · indicador `alfabetizacao_serie` · **disponivel_snapshot**.

## Significado e uso

Taxa de alfabetização das pessoas de 15 anos ou mais: Censo 2010 (tabela 9841), incluindo municípios, PNAD Contínua anual (tabela 7113, 100 menos a taxa de analfabetismo) até UF de 2016 a 2025, e Censo 2022 (tabela 9543) nos municípios.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território x ano x sexo.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-9841` | [9841/2513](https://sidra.ibge.gov.br/tabela/9841) | Taxa de alfabetização das pessoas de 15 anos ou mais de idade / % | M01 |
| `ibge-sidra-9543` | [9543/2513](https://sidra.ibge.gov.br/tabela/9543) | Taxa de alfabetização das pessoas de 15 anos ou mais de idade / % | M01 |
| `ibge-sidra-7113` | [7113/10267](https://sidra.ibge.gov.br/tabela/7113) | Taxa de analfabetismo das pessoas de 15 anos ou mais de idade / % | M05 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 9841 / 2513

Pesquisa/produtor: Censo Demográfico. Periodicidade: período único. Disponibilidade na fonte: 2010, 2022.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - Dados do Universo. 2 - A variável "taxa de alfabetização" representa o percentual de pessoas com 15 anos ou mais de idade que sabem ler e escrever pelo menos um bilhete simples, no idioma que conhecem, inclusive em língua indígena, na população total residente da mesma faixa etária, em determinado espaço geográfico, no ano considerado. 3 - No Censo Demográfico 2010, definiu-se como indígena a pessoa residente em terras indígenas que se declarou indígena pelo quesito de cor ou raça ou pelo quesito se considera indígena; ou a pessoa residente fora das terras indígenas que se declarou indígena no quesito de cor ou raça. Por essa razão, o total de pessoas indígenas é superior ou igual ao total de pessoas de cor ou raça declarada indígena, nos diferentes recortes. 4 - No Censo Demográfico 2022, definiu-se como indígena a pessoa residente em localidades indígenas que se declarou indígena pelo quesito de cor ou raça ou pelo quesito se considera indígena; ou a pessoa residente fora das localidades indígenas que se declarou indígena no quesito de cor ou raça. Por essa razão, o total de pessoas indígenas é superior ou igual ao total de pessoas de cor ou raça declarada indígena, nos diferentes recortes. 5 - No Censo Demográfico 2022, foram consideradas localidades indígenas aquelas que compõem o conjunto das Terras Indígenas, dos agrupamentos indígenas e das demais áreas de conhecida ou potencial ocupação indígena. Para mais detalhes, consultar a documentação metodológica. 6 - No Censo Demográfico 2010, o conjunto das Terras Indígenas foi formado por aquelas que estavam na situação fundiária de declarada, homologada, regularizada e em processo de aquisição como reserva indígena até a data de 31 de dezembro de 2010. 7 - No Censo Demográfico 2022, foram consideradas as Terras Indígenas declaradas, homologadas, regularizadas ou encaminhadas como Reservas Indígenas até 31 de julho de 2022, data de referência da pesquisa, conforme os dados da Fundação Nacional dos Povos Indígenas – FUNAI. Para mais informações, consultar a documentação metodológica. 8 - A utilização da Divisão Regional do Brasil em Regiões Geográficas Imediatas e Regiões Geográficas Intermediárias (2017) para tabulação dos resultados do Censo 2010 tem fins ilustrativos de comparabilidade das operações censitárias, devendo-se atentar para as transformações territoriais ocorridas no período intercensitário. 9 - Para tabulação dos resultados do Censo 2010, utilizou-se o recorte da Amazônia Legal divulgado pelo IBGE em 2022, considerando-se que não houve alteração na composição municipal do recorte entre os Censos. Deve-se considerar, entretanto, as transformações territoriais ocorridas no período.

### 9543 / 2513

Pesquisa/produtor: Censo Demográfico. Periodicidade: período único. Disponibilidade na fonte: 2022.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - Dados do Universo 2 - No Censo Demográfico 2022, definiu-se como indígena a pessoa residente em localidades indígenas que se declarou indígena pelo quesito de cor ou raça ou pelo quesito se considera indígena; ou a pessoa residente fora das localidades indígenas que se declarou indígena no quesito de cor ou raça. Por essa razão, o total de pessoas indígenas é superior ou igual ao total de pessoas de cor ou raça declarada indígena, nos diferentes recortes. 3 - No Censo Demográfico 2022, foram consideradas localidades indígenas aquelas que compõem o conjunto das Terras Indígenas, dos agrupamentos indígenas e das demais áreas de conhecida ou potencial ocupação indígena. Para mais detalhes, consultar a documentação metodológica. 4 - No Censo Demográfico 2022, foram consideradas as Terras Indígenas declaradas, homologadas, regularizadas ou encaminhadas como Reservas Indígenas até 31 de julho de 2022, data de referência da pesquisa, conforme os dados da Fundação Nacional dos Povos Indígenas – FUNAI. Para mais informações, consultar a documentação metodológica. 5 - A categoria Total de cor ou raça inclui os ignorados omitidos na tabela.

### 7113 / 10267

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua anual. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2016 a 2019, 2022 a 2025.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Taxa de analfabetismo é a razão entre o número de pessoas de determinada faixa etária que não sabem ler e escrever um recado ou bilhete simples no idioma que conhecem e o total de pessoas dessa mesma faixa etária. A partir de 01 de agosto de 2022, as estimativas deste tema passaram a ser divulgadas com base no novo método de ponderação da pesquisa, conforme a Nota Técnica 03/2021. Consequentemente, a série histórica dos indicadores foi atualizada. A partir de 2025, as estimativas deste tema passaram a ser divulgadas com base na nova ponderação da pesquisa, conforme a Nota Técnica 02/2025. Consequentemente, a série histórica dos indicadores foi atualizada.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2010", "2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"], "municipio": ["2010", "2022"], "uf": ["2010", "2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"], "regiao": ["2010", "2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M01 — Censo Demográfico](../pesquisas.md#m01): Enumeração de residentes habituais e características de pessoas e domicílios; serve à descrição territorial e ao planejamento. A população e a edição específicas continuam sendo as da tabela/variável.

[M05 — PNAD Contínua](../pesquisas.md#m05): Estatísticas domiciliares de trabalho, rendimento, educação, moradia e outros módulos; os universos variam. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M01: Verificar os manuais de cada edição histórica e os universos/denominadores de cada razão, mediana e taxa; a fonte geral não resolve essas fórmulas por variável.
- M05: Faltam memória de ponderação/calibração por edição e fórmulas específicas de Gini, informalidade, frequência líquida e rendimentos; registrar IC/CV existentes sem recomputá-los.

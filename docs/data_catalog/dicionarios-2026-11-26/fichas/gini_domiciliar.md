# Índice de Gini do rendimento domiciliar per capita

Ficha `gini_domiciliar` · indicador `gini_domiciliar` · **disponivel_snapshot**.

## Significado e uso

Índice de Gini do rendimento domiciliar per capita, a preços médios do ano (PNAD Contínua anual, tabela SIDRA 7435). Tabela sem classificações. Fonte: IBGE. Pesquisa Nacional por Amostra de Domicílios Contínua, acumulado de primeiras visitas, exceto 2020-2022, acumulado de quintas visitas, devido à pandemia de Covid-19.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Índice**. Grão: território (Brasil, Grande Região, UF) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-7435` | [7435/10681](https://sidra.ibge.gov.br/tabela/7435) | Índice de Gini do rendimento domiciliar per capita, a preços médios do ano / Índice | M05 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 7435 / 10681

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua anual. Periodicidade: anual. Disponibilidade na fonte: 2012 a 2025.
Precisão de armazenamento/apresentação no descritor: 3 / 3 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): O rendimento de trabalho é captado somente para pessoas de 14 anos ou mais de idade. Exclusive as pessoas cuja condição no domicílio era "Pensionista", "Empregado doméstico" ou "Parente de empregado doméstico". A partir de 19 de novembro de 2021, as estimativas deste tema passaram a ser divulgadas com base no novo método de ponderação da pesquisa, conforme a Nota Técnica 03/2021. Consequentemente, a série histórica dos indicadores foi atualizada. Até o 3º trimestre de 2015, as pessoas em licença remunerada na semana de referência da pesquisa e que estavam afastadas por período inferior a 4 meses eram classificadas como "ocupadas". Caso esse afastamento fosse igual ou superior a 4 meses, essas pessoas eram definidas como "fora da força de trabalho" e, portanto, não se investigava o rendimento do trabalho. A partir do 4º trimestre de 2015, em acordo com as recomendações da 19ª Conferência Internacional de Estatísticos do Trabalho - CIET, da OIT, pessoas em licença remunerada, independentemente do tempo de afastamento, passaram a ser classificadas como "ocupadas" e seus rendimentos do trabalho foram coletados normalmente.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"], "uf": ["2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"], "brasil": ["2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M05 — PNAD Contínua](../pesquisas.md#m05): Estatísticas domiciliares de trabalho, rendimento, educação, moradia e outros módulos; os universos variam. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M05: Faltam memória de ponderação/calibração por edição e fórmulas específicas de Gini, informalidade, frequência líquida e rendimentos; registrar IC/CV existentes sem recomputá-los.

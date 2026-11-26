# Taxa de informalidade (trimestral)

Ficha `taxa_informalidade_trimestral` · indicador `taxa_informalidade_trimestral` · **disponivel_snapshot**.

## Significado e uso

Taxa de informalidade das pessoas de 14 anos ou mais de idade ocupadas na semana de referência (PNAD Contínua trimestral, tabela SIDRA 4093). Tabela sem classificações. Fonte: IBGE - Pesquisa Nacional por Amostra de Domicílios Contínua trimestral.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território (Brasil, Grande Região, UF, Município) x trimestre x sexo.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-4093-informalidade` | [4093/12466](https://sidra.ibge.gov.br/tabela/4093) | Taxa de informalidade das pessoas de 14 anos ou mais de idade ocupadas na semana de referência / % | M05 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 4093 / 12466

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua trimestral. Periodicidade: trimestral. Disponibilidade na fonte: 1º trimestre 2012 a 3º trimestre 2026.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A partir do 4º trimestre de 2015, em acordo com as recomendações da 19ª Conferência Internacional de Estatísticos do Trabalho - CIET, da OIT, pessoas em licença remunerada, independentemente do tempo de afastamento, passaram a ser classificadas como "ocupadas" e seus rendimentos do trabalho foram coletados normalmente. Anteriormente, as pessoas em licença remunerada na semana de referência da pesquisa e que estavam afastadas por período inferior a 4 meses eram classificadas como "ocupadas". Caso esse afastamento fosse igual ou superior a 4 meses, essas pessoas eram definidas como "fora da força de trabalho" e, portanto, não se investigava o rendimento do trabalho. Além disso, a partir do 4º trimestre de 2015, também passaram a ser classificadas como "ocupadas" as pessoas que ajudaram, sem receber remuneração, no trabalho remunerado de parente, adicionalmente àquelas que ajudaram no trabalho remunerado de outro morador do mesmo domicílio. Anteriormente, eram consideradas "ocupadas" apenas as pessoas que ajudaram, sem receber remuneração, no trabalho remunerado de outro morador do mesmo domicílio. A partir de abril de 2016, um aspecto do conceito de desocupação foi alterado de forma a se adequar inteiramente à 19ª Conferência Internacional de Estatísticos do Trabalho - CIET, realizada em outubro de 2013, sendo o questionário ajustado. Com a alteração desse aspecto, passam a ser considerados desocupados aqueles que conseguiram proposta de trabalho para começar após a semana de referência e que iriam começar a trabalhar em até 3 meses; os demais, isto é, aqueles que conseguiram proposta para começar a trabalhar após 3 meses da semana de referência, passam a ser contabilizados na população fora da força de trabalho. Anteriormente, eram considerados desocupados todos aqueles que conseguiram proposta de trabalho para começar após a semana de referência, independentemente do tempo em que iniciariam o trabalho que conseguiram. A partir de 15 de agosto de 2025, as estimativas deste tema passaram a ser divulgadas com base na nova ponderação da pesquisa, conforme a Nota Técnica 02/2025. Consequentemente, a série histórica dos indicadores foi atualizada.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"], "municipio": ["2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"], "uf": ["2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"], "regiao": ["2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M05 — PNAD Contínua](../pesquisas.md#m05): Estatísticas domiciliares de trabalho, rendimento, educação, moradia e outros módulos; os universos variam. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M05: Faltam memória de ponderação/calibração por edição e fórmulas específicas de Gini, informalidade, frequência líquida e rendimentos; registrar IC/CV existentes sem recomputá-los.

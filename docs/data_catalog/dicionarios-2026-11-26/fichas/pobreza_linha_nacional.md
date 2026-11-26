# Proporção da população abaixo da linha de pobreza nacional

Ficha `pobreza_linha_nacional` · indicador `pobreza_linha_nacional` · **disponivel_snapshot**.

## Significado e uso

Proporção da população abaixo da linha de pobreza nacional (Objetivos de Desenvolvimento Sustentável, tabela SIDRA 5877). Tabela sem classificações. Fonte: IBGE, Pesquisa Nacional por Amostra de Domicílios Contínua (PNAD Contínua).

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Proporção (%)**. Grão: território (Brasil, Grande Região, UF) x ano | cor ou raça.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-5845` | [5845/9948](https://sidra.ibge.gov.br/tabela/5845) | Proporção da população abaixo da linha de pobreza nacional / Proporção (%) | Não localizado |
| `ibge-sidra-5877` | [5877/9948](https://sidra.ibge.gov.br/tabela/5877) | Proporção da população abaixo da linha de pobreza nacional / Proporção (%) | Não localizado |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5845 / 9948

Pesquisa/produtor: Objetivos de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 2012 a 2024.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Nota 1: Consolidado das primeiras entrevistas de 2012-2019, 2023-2024 e das quintas entrevistas de 2020-2022 . Nota 2: Linha de 8,30 dólares por dia, convertidos pela paridade do poder do compra (PPC-2021) do consumo final de R$2,44983620 por dólar. Nota 3: Depois de convertido, o valor da linha é corrigido pela inflação acordo com os deflatores utilizados pela PNAD Contínua. Nota 4: As estatísticas reportadas se referem a proporção de pessoas com rendimento domiciliar per capita abaixo da linha de pobreza. Nota 5: Nos cálculos são excluidas as pessoas na condição no domicílio de pensionista, empregado doméstico ou parente de empregado doméstico.

### 5877 / 9948

Pesquisa/produtor: Objetivos de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 2012 a 2024.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Nota 1: Consolidado das primeiras entrevistas de 2012-2019, 2023-2024 e das quintas entrevistas de 2020-2022 . Nota 2: Linha de 8,30 dólares por dia, convertidos pela paridade do poder do compra (PPC-2021) do consumo final de R$2,44983620 por dólar. Nota 3: Depois de convertido, o valor da linha é corrigido pela inflação acordo com os deflatores utilizados pela PNAD Contínua. Nota 4: As estatísticas reportadas se referem a proporção de pessoas com rendimento domiciliar per capita abaixo da linha de pobreza. Nota 5: Nos cálculos são excluidas as pessoas na condição no domicílio de pensionista, empregado doméstico ou parente de empregado doméstico.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"], "uf": ["2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"], "brasil": ["2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- PESQUISA: método independente não localizado; consultar produtor identificado na ficha.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.

## Contexto complementar localizado nesta execução

O material histórico usa linha de US$ 6,85/dia PPC-2017, corrigida pela inflação, e rendimento domiciliar per capita com exclusões de condições domiciliares.

O descritor preservado 5845/5877 desta revisão cita US$ 8,30/dia PPC-2021 e fator R$ 2,44983620. São versões diferentes. Não transportar limiar, série ou pesos do caderno antigo à série atual; memória independente específica da revisão atual continua pendente.

Fonte: [produtor oficial](https://www.ibge.gov.br/biblioteca/visualizacao/livros/liv102100.pdf), Caderno Desigualdades, Indicador 1.2.1, p. 16, Notas 1–4; edição: Criando Sinergias entre a Agenda 2030 e o G20; dados PNAD Contínua 2012/2022. Consulta indexada em 2026-11-26; não leitura integral.

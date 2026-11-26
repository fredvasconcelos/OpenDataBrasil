# Impostos, líquidos de subsídios, sobre produtos a preços correntes

Ficha `pib_municipios_v543` · indicador `pib_municipios_v543` · **disponivel_snapshot**.

## Significado e uso

Impostos, líquidos de subsídios, sobre produtos a preços correntes

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil Reais**. Grão: território x ano.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t5938-v543` | [5938/543](https://sidra.ibge.gov.br/tabela/5938) | Impostos, líquidos de subsídios, sobre produtos a preços correntes / Mil Reais | M34 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5938 / 543

Pesquisa/produtor: Produto Interno Bruto dos Municípios. Periodicidade: anual. Disponibilidade na fonte: 2002 a 2023.
Precisão de armazenamento/apresentação no descritor: 3 / 0 casas. Soma de períodos/territórios na fonte: True / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Os dados de 2022 e 2023 estarão sujeitos a revisão na próxima publicação. 2 - Para os anos de 2022 e 2023 foram divulgados apenas o Produto Interno Bruto e o Produto Interno Bruto per capita, conforme a nota técnica 02/2024 do Sistema de Contas Nacionais, que pode ser acessada em https://biblioteca.ibge.gov.br/visualizacao/livros/liv102094.pdf . 3 - Os dados da série retropolada (de 2002 a 2009) também têm como referência o ano de 2010, seguindo a nova referência das Contas Nacionais.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021"], "municipio": ["2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021"], "regiao": ["2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021"], "uf": ["2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": true, "seasonal_sum": true, "accumulation_rule": "sum"}`.

Parecer temporal preservado: `sum_method_supported`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M34 — PIB municipal](../pesquisas.md#m34): Estimativa municipal do PIB e componentes a preços correntes. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M34: Leitura integral da distribuição municipal e denominadores por edição; a abertura setorial anterior não comprova existência em 2023.

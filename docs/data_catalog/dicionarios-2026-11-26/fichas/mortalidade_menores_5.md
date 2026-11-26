# Taxa de mortalidade em menores de 5 anos

Ficha `mortalidade_menores_5` · indicador `mortalidade_menores_5` · **disponivel_snapshot**.

## Significado e uso

Taxa de mortalidade em menores de 5 anos (Objetivos de Desenvolvimento Sustentável, tabela SIDRA 6695). Tabela sem classificações. Fonte: Ministério da Saúde, Sistema de Informações sobre Mortalidade (SIM), Sistema de Informações sobre Nascidos Vivos (SINASC); IBGE. Projeções da População do Brasil e Unidades da Federação: 2000-2070, ed. 2024, Estimativas de Sub-Registro de Nascimentos e Óbitos (2015- ) e Sistema de Estatísticas Vitais, Estudo Complementar à Aplicação da Técnica de Captura-Recaptura (2015-2022).

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Óbitos por mil nascidos vivos**. Grão: território (Brasil, Grande Região, UF) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-6695` | [6695/9731](https://sidra.ibge.gov.br/tabela/6695) | Taxa de mortalidade em menores de 5 anos / Óbitos por mil nascidos vivos | M47 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 6695 / 9731

Pesquisa/produtor: Objetivos de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 2000 a 2023.
Precisão de armazenamento/apresentação no descritor: 4 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"uf": ["2000", "2001", "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"], "regiao": ["2000", "2001", "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"], "brasil": ["2000", "2001", "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M47 — Saúde ODS / mortalidade](../pesquisas.md#m47): Razão materna, mortalidade de menores de 5, mortalidade por DCNT e homicídios exigem métodos diferentes. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M47: Fonte complementar, insuficiente para homologar método nacional. Recuperar fichas nacionais 3.1.1/3.2.1/3.4.1/16.1.1, códigos CID, correções e denominadores por ano.

# População nos Censos (série histórica)

Ficha `populacao_nos_censos` · indicador `populacao_nos_censos` · **disponivel_snapshot**.

## Significado e uso

População (Censo Demográfico, tabela SIDRA 1286). Tabela sem classificações. Fonte: IBGE - Censo Demográfico.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Pessoas**. Grão: território (Brasil, Grande Região, UF) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-1209` | [1209/606](https://sidra.ibge.gov.br/tabela/1209) | População / Pessoas | M01 |
| `ibge-sidra-1286` | [1286/606](https://sidra.ibge.gov.br/tabela/1286) | População / Pessoas | M01 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 1209 / 606

Pesquisa/produtor: Censo Demográfico. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 1872, 1890, 1900, 1920, 1940, 1950, 1960, 1970, 1980, 1991, 2000, 2010, 2022.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Até 1960, população presente. A partir daí, população residente; 2 - Para 1872, os resultados não incluem 181 583 habitantes, estimados para 32 paróquias, nas quais não foi feito o recenseamento na data determinada; 3 - Para 1940, exclusive 16 713 pessoas recenseadas cujas declarações não foram apuradas por extravio do material de coleta; 4 - Para 1950, exclusive 31 960 pessoas recenseadas cujas declarações não foram apuradas por extravio do material de coleta; 5 - Idades em anos completos; no censo de 1872, o grupo de 5 a 9 anos inclui as pessoas de 10 anos e, nos grupos subsequentes, as idades extremas excedem de uma unidade às especificadas para cada grupo; 6 - Para 1900, o grupo de idade de 15 a 19 anos, incluiu as pessoas de 20 anos, e o grupo de idade de 20 a 24 anos, excluiu estas pessoas; 7 - Para 1991, 2000, 2010 e 2022, dados do Universo. 8- Para 2022, os dados referentes aos municípios Abel Figueiredo (PA) e São Pedro da Água Branca (MA) foram corrigidos no dia 22/12/2023, impactando nos totais dos estados do Pará e do Maranhão e nos totais das Grandes Regiões do Norte e Nordeste.

### 1286 / 606

Pesquisa/produtor: Censo Demográfico. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 1872, 1890, 1900, 1920, 1940, 1950, 1960, 1970, 1980, 1991, 2000, 2010.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - Para 1872 até 1950: População presente; 2 - Para 1960 até 1980: População recenseada; 3 - Para 1991 até 2010: População residente; 4 - Para 1940, 1950 e 1960: Os dados referentes ao Brasil e à região Sudeste incluem a população da região de Serra dos Aimorés, área de litigio entre Minas Gerais e Espírito Santo; 5 - Os dados referentes à unidade da federação Pernambuco , referentes aos anos 1950, 1960, 1970 e 1980, incluem os do território federal de Fernando de Noronha; 6 - Os dados referentes à unidade da federação Pernambuco , a partir de 1991, incluem os do distrito estadual de Fernando de Noronha, criado em 06.10.1988; 7 - Para 1940, 1950 e 1960: Os dados para a unidade da federação Minas Gerais incluem a população recenseada na parte da Serra dos Aimorés anexada à unidade da federação Minas Gerais; 8 - Para 1940, 1950 e 1960: Os dados para a unidade da federação Espírito Santo incluem a população recenseada na parte da Serra dos Aimorés anexada à unidade da federação Espírito Santo; 9 - Para 2000: Dados da Sinopse Preliminar; 10 - Para 2010: Dados da Sinopse; 11 - Até 1970: Os dados referentes à unidade da federação Rio de Janeiro incluem os da antiga Guanabara; 12 - A unidade da federação Tocantins foi criada em obediência à Constituição Federal de 1988. Os dados populacionais referentes ao novo estado, para os Censos de 1940 a 1980, foram desmembrados da unidade da federação de origem, neste caso Goiás; 13 - A unidade da federação Mato Grosso do Sul foi criada através da Lei Complementar Nº 31, de 11 de outubro de 1977, e sua instalação em 1º de janeiro de 1979. Para os Censos de 1940 a 1970, seus dados populacionais foram desmembrados da unidade da federação de origem, neste caso Mato Grosso.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["1872", "1890", "1900", "1920", "1940", "1950", "1960", "1970", "1980", "1991", "2000", "2010", "2022"], "uf": ["1872", "1890", "1900", "1920", "1940", "1950", "1960", "1970", "1980", "1991", "2000", "2010", "2022"], "regiao": ["1872", "1890", "1900", "1920", "1940", "1950", "1960", "1970", "1980", "1991", "2000", "2010", "2022"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M01 — Censo Demográfico](../pesquisas.md#m01): Enumeração de residentes habituais e características de pessoas e domicílios; serve à descrição territorial e ao planejamento. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M01: Verificar os manuais de cada edição histórica e os universos/denominadores de cada razão, mediana e taxa; a fonte geral não resolve essas fórmulas por variável.

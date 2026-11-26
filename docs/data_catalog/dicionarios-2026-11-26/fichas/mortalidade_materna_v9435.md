# Óbitos maternos (ODS)

Ficha `mortalidade_materna_v9435` · indicador `mortalidade_materna_v9435` · **disponivel_snapshot**.

## Significado e uso

Número de óbitos de mulheres residentes por causas e condições consideradas de morte materna

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Pessoas**. Grão: território x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t6694-v9435` | [6694/9435](https://sidra.ibge.gov.br/tabela/6694) | Número de óbitos de mulheres residentes por causas e condições consideradas de morte materna / Pessoas | M47 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 6694 / 9435

Pesquisa/produtor: Objetivos de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 2009 a 2023.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1. Última atualização: 25 de julho de 2025 (toda a série da razão de mortalidade materna e inclusão de dados referentes ao ano de 2023). 2. Atualização anterior: 22 de fevereiro de 2024 (inclusão de dados referentes ao ano de 2022). 3. De 2009 a 2023 a RMM foi corrigida utilizando-se a Vigilância de Óbitos de Mulher em Idade Fértil.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"uf": ["2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"], "regiao": ["2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"], "brasil": ["2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `flow_method_review_required`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M47 — Saúde ODS / mortalidade](../pesquisas.md#m47): Razão materna, mortalidade de menores de 5, mortalidade por DCNT e homicídios exigem métodos diferentes. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEMPORAL: método de fluxo pendente; sem nova permissão de soma nesta revisão.
- M47: Fonte complementar, insuficiente para homologar método nacional. Recuperar fichas nacionais 3.1.1/3.2.1/3.4.1/16.1.1, códigos CID, correções e denominadores por ano.

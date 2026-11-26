# Distribuição da despesa monetária e não monetária média mensal familiar

Ficha `apoio--despesa_familiar_distribuicao` · indicador `despesa_familiar_distribuicao` · **apoio_no_release_snapshot**.

## Significado e uso

Participação de cada tipo de despesa na despesa total média mensal das famílias (POF 2002-2003, 2008-2009 e 2017-2018).

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território (Brasil, Grande Região, UF; 26 capitais apenas em 2008) x ano de referência da POF x classe de rendimento x tipo de despesa.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-2309` | [2309/1204](https://sidra.ibge.gov.br/tabela/2309) | Distribuição da despesa monetária e não monetária média mensal familiar / % | M08 |
| `ibge-sidra-1594` | [1594/1204](https://sidra.ibge.gov.br/tabela/1594) | Distribuição da despesa monetária e não monetária média mensal familiar / % | M08 |
| `ibge-sidra-6715` | [6715/1204](https://sidra.ibge.gov.br/tabela/6715) | Distribuição da despesa monetária e não monetária média mensal familiar / % | M08 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 2309 / 1204

Pesquisa/produtor: Pesquisa de Orçamentos Familiares. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2002.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - O termo família está sendo utilizado para indicar a unidade de investigação da pesquisa "Unidade de Consumo". 2 - A categoria Até 400 inclui as famílias sem rendimento.

### 1594 / 1204

Pesquisa/produtor: Pesquisa de Orçamentos Familiares. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2008.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - O termo família está sendo utilizado para indicar a unidade de investigação da pesquisa "Unidade de Consumo". 2 - A classificação Classes de rendimento total e variação patrimonial mensal familiar inclui os rendimentos monetários, não-monetários e variação patrimonial. 3 - A categoria Até 830 Reais inclui as famílias Sem rendimento .

### 6715 / 1204

Pesquisa/produtor: Pesquisa de Orçamentos Familiares. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2018.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - O termo família está sendo utilizado para indicar a unidade de investigação da pesquisa "Unidade de Consumo". 2 - A classificação Classes de rendimento total e variação patrimonial mensal familiar inclui os rendimentos monetários, não-monetários e variação patrimonial. 3 - A categoria Até 1.908 Reais inclui as famílias Sem rendimento .

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `["2002", "2008", "2018"]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M08 — POF](../pesquisas.md#m08): Estrutura dos gastos, recebimentos e consumo das unidades de consumo; apoia estudos de orçamento e ponderação de preços. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M08: Manuais completos e pesos/calibração por edição continuam pendentes; ver análise específica ipca-pof.md, incluindo unidades, faixas e amostras antigas.

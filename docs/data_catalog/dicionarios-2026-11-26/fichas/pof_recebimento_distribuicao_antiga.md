# Distribuição do recebimento familiar (POF 1987 e 1995)

Ficha `pof_recebimento_distribuicao_antiga` · indicador `pof_recebimento_distribuicao_antiga` · **disponivel_snapshot**.

## Significado e uso

Distribuição do recebimento médio mensal familiar por origem e classe de recebimento (POF 1987-1988 e 1995-1996).

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território (Total das áreas da POF, Região Metropolitana, Município) x ano x classe de recebimento x origem do recebimento.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-414` | [414/177](https://sidra.ibge.gov.br/tabela/414) | Percentual do recebimento médio mensal familiar / % | M08 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 414 / 177

Pesquisa/produtor: Pesquisa de Orçamentos Familiares. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 1987, 1995.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1) Em 1987 o valor do piso salarial era cz$ 2.640,00, e em 1996 o salário mínimo correspondia a R$ 112,00. 2) Na classe de recebimento até 2 estão incluídas as famílias sem recebimento. 3) Os percentuais médios foram obtidos segundo o recebimento mensal familiar de cada classe de recebimento mensal familiar dividido pelo número de famílias das classes correspondentes.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"municipio": ["1987", "1995"], "regiao_metropolitana": ["1987", "1995"], "areas_pof": ["1987", "1995"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M08 — POF](../pesquisas.md#m08): Estrutura dos gastos, recebimentos e consumo das unidades de consumo; apoia estudos de orçamento e ponderação de preços. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M08: Manuais completos e pesos/calibração por edição continuam pendentes; ver análise específica ipca-pof.md, incluindo unidades, faixas e amostras antigas.

# Custo do m²: componente mão de obra

Ficha `custo_m2_v2120` · indicador `custo_m2_v2120` · **indisponivel_snapshot**.

## Significado e uso

Custo médio m² - componente mão-de-obra - moeda corrente

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Reais**. Grão: território x mês.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t2296-v2120` | [2296/2120](https://sidra.ibge.gov.br/tabela/2296) | Custo médio m² - componente mão-de-obra - moeda corrente / Reais | M24 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 2296 / 2120

Pesquisa/produtor: Sistema Nacional de Pesquisa de Custos e Índices da Construção Civil. Periodicidade: mensal. Disponibilidade na fonte: março 1986 a outubro 2026.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - A variável Custo médio m² - número índice utiliza como base junho/94 = 100; 2 - Série de custos (moedas) : Devido aos vários planos econômicos que resultaram em mudança da moeda, as séries de custos do SINAPI estão expressas da seguinte forma: março de 1986 à dezembro de 1988: Cz$ (cruzado); janeiro de 1989 à março de 1990: NCz$ (cruzado novo); abril de 1990 à julho de 1993: CR$ (cruzeiro); agosto de 1993 à junho de 1994: CR$ (cruzeiro real); julho de 1994 em diante: R$ (real). 3 - A partir de janeiro de 2011, o custo nacional do SINAPI e os custos relativos às Regiões são calculados com uma nova estrutura de ponderação (número de domicílios com banheiro da PNAD 2009 em relação à PNAD 2004). Por isso, não devem ser comparados com os resultados anteriores que foram obtidos com outra estrutura de ponderação (crescimento populacional resultante do Censo Demográfico). 4 - Os resultados de maio de 2013 refletem a desoneração da folha de pagamento de empresas do setor da construção civil, em vigor desde primeiro de abril deste ano. A desoneração foi regulamentada através da medida provisória nº 601, de 28 de dezembro de 2012, tratando do cálculo dos encargos sociais, que retirou os 20% relativos à contribuição previdenciária incidente na folha de pagamento. Os resultados do mês junho de 2013 refletem o retorno da contribuição previdenciária sobre a folha de pagamento de empresas do setor da construção civil, que havia vigorado nos meses de abril e maio. A desoneração, vigente a partir de primeiro de abril, teve seus efeitos interrompidos em 03 de junho em função da perda de validade da medida provisória que a criou, a MP 601/12, de 28 de dezembro de 2012. Entre outros aspectos, a medida tratou de retirar os 20% da contribuição previdenciária incidente sobre o setor, o que se refletiu integralmente no mês de maio. Os resultados a partir de julho de 2013 refletem a lei 12.844, sancionada em 19 de julho de 2013, que estabelece, entre outras disposições, a desoneração da folha de pagamento retirando do cálculo dos encargos sociais, os 20% relativos à contribuição previdenciária incidente na folha de pagamento. Continuam sendo parte da divulgação, no site do IBGE, os índices e custos que não levam em consideração desoneração da folha de pagamento. 5 - Para obter outros dados sobre o SINAPI consulte a Caixa Econômica Federal no endereço http://www1.caixa.gov.br/gov/gov_social/municipal/programa_des_urbano/SINAPI/index.asp

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: não. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `[]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M24 — SINAPI](../pesquisas.md#m24): Custos e índices da construção, inclusive componentes de material e mão de obra. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- DADOS: KPI configurado ausente da navegação N2 no snapshot; candidato não significa publicado.
- M24: Recuperar base/encargos/desoneração e composição de cada variável da 2296; não completar a unidade só pelo rótulo abreviado do catálogo.

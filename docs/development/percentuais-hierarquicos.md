# Percentuais por grupo no painel

A tabela e os tooltips usam a hierarquia das dimensões do indicador. Com uma
dimensão selecionada, cada categoria é comparada com sua base. Com duas, o
segundo nível usa a base do próprio grupo do primeiro nível. Trocar linhas e
colunas reorganiza a apresentação, preservando essa relação.

O controle **Calcular % por** permite ocultar os percentuais e escolher as bases
compatíveis. Indicadores aditivos conservam também os cálculos por coluna e total
geral. Comparações de médias recebem uma nota explícita de composição dos valores
exibidos, calculada pelo portal, sem representar participação oficial ponderada.

Exemplo: na SIDRA 6715, renda compara as médias exibidas. Despesas de consumo usam
o subtotal oficial de consumo de cada renda. Na Paraíba em 2018, R$ 496,10 de
Alimentação sobre R$ 2.349,91 de consumo resulta em 21,11% (21,1% na apresentação).
O Total oficial de R$ 2.893,59 é preservado separadamente.

O catálogo declara `share_basis` em cada dimensão, com os valores
`published_total`, `published_group`, `displayed_sum` ou `none`. Somente
`published_group` exige `share_base_category`, pertencente à mesma classificação.
Sem declaração, quantidades e indicadores aditivos usam Total publicado; os
demais usam composição comparativa. Isso não altera a aditividade do indicador.

No contrato, `DimensionOut` informa a política, `DetailNodeOut` informa a base dos
filhos e `PivotOut.share_bases` transporta subtotais de referência sem expô-los
como categorias adicionais. Contrato e cliente são gerados pelo fluxo existente.

Método, limites, valores especiais e exemplo numérico completo:
[ADR-0029](../adr/0029-percentuais-hierarquicos-no-portal.md).

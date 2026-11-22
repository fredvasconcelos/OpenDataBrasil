# Métricas do portal

A página apresenta visualizações de página, downloads e países de origem desde
o primeiro dia da coleta. Os cartões mostram diretamente o título e o valor, sem seletor ou texto de período.
Não são contadas pessoas ou visitantes únicos (ADR-0027).

O globo começa parado, com marcadores de países. Arraste com o botão esquerdo
para girar e use a roda para aproximar. Quando o Brasil ocupa a área central
em aproximação suficiente, aparecem as UFs. Ao afastar, voltam os países.
O zoom é ancorado no cursor; em telas de toque, a pinça também aproxima/afasta.
Pelo teclado: setas giram, + e − alteram o zoom e Home restaura a visão inicial.
Os rankings permitem selecionar lugares sem depender do arraste.

O tooltip mostra nome, visualizações e percentual: países em relação ao total
global; estados em relação ao Brasil, independentemente do enquadramento.
O total brasileiro inclui acessos sem UF identificada. Esses acessos permanecem
no ranking, sem posição inventada no mapa. Valores pequenos mantêm a supressão
prevista na ADR-0027.

Os rankings de indicadores mais abertos e mais baixados consultam ordenações
independentes da API. A unidade é o indicador (`kpi_id`), não um arquivo físico.

A API aceita `period=all` nas rotas de métricas. O período começa na data real da
coleta e termina no dia corrente de Brasília. As opções anteriores continuam
aceitas. O cache mantém o ciclo de cinco minutos da agregação.

A visualização usa D3, Natural Earth e os limites do IBGE, com recursos locais.
Não depende de uma requisição de mapas a terceiros.

# ADR-0029 — Percentuais hierárquicos no portal

Estado: aceita pelo mantenedor em 20/11/2026, pelas respostas sobre as bases de renda
e despesas. A entrega é local; esta decisão não autoriza implantação ou dados novos.

## Contexto

O bloqueio global de percentuais para indicadores não aditivos impedia mostrar
composições comparativas de médias. A matriz dos tooltips também omitia os
percentuais dos filhos. Esse bloqueio já existia antes do Plano D; não foi
comprovada uma regressão recente.

Na tabela SIDRA 6715, despesa por classe de renda é média por família. Somar essas
médias não produz o Total oficial nem a participação das famílias. O mantenedor
escolheu comparar os valores exibidos, com identificação explícita do cálculo do
portal. Para despesas, escolheu o subtotal oficial de consumo dentro de cada grupo.

Metadados oficiais: [agregado 6715 do IBGE](https://servicodados.ibge.gov.br/api/v3/agregados/6715/metadados).

## Decisão

Cada dimensão tem uma política de denominador, separada da aditividade:

- `published_total`: Total publicado do grupo, para indicadores que já permitiam
  percentuais. Mantém a regra anterior de quantidades e indicadores aditivos.
- `published_group`: categoria de referência publicada, declarada por
  `share_base_category` na mesma classificação. Na 6715, consumo usa
  `c12190:103538`, enquanto o Total de despesa continua `c12190:103536`.
- `displayed_sum`: composição dos valores exibidos entre categorias irmãs,
  excluindo Total e sem somar novamente os filhos. É o padrão comparativo dos
  indicadores não aditivos; não representa participação oficial ponderada.
- `none`: desabilita percentuais naquela dimensão.

Na 6715, renda (`c339`) usa `displayed_sum`; consumo (`c12190`) usa
`published_group`. N1 divide cada renda pela soma das médias exibidas. N2 divide
cada despesa pelo subtotal de consumo da própria renda. Uma dimensão sozinha usa
apenas a sua base. A ordem semântica das dimensões define a hierarquia,
independentemente da posição nas linhas ou colunas da tabela.

O Total oficial permanece com seu valor original. Quando a base comparativa
difere dele, a interface mostra uma linha separada com a base e 100%, sem atribuir
100% ao Total oficial errado. Todos os modos de tooltip, inclusive matriz,
apresentam os percentuais recebidos. Os controles tradicionais de coluna e total
geral continuam restritos aos indicadores que já admitiam essa soma (ADR-0024).

Uma composição com valor indisponível, sigiloso ou negativo não recebe percentual.
Zero numérico participa da soma; denominador zero não produz divisão. Cruzamento
estruturalmente ausente de outra edição da pesquisa não é convertido em zero.
Valores especiais e seus estados continuam preservados.

API individual, em lote e série temporal compartilham o mesmo cálculo, com Decimal antes da
serialização. A base oficial adicional é lida na mesma consulta Gold. No pivot,
`share_bases` transporta as referências sem criar linhas ou colunas visíveis.
A série informa `share_pct` e `share_base_value` por ponto e `share_methods` para
as notas visíveis no tooltip. A interface reserva espaço para a base e o método,
limitando a lista de séries quando necessário e remetendo o restante à tabela.
A contagem prévia e o teto de células visíveis do Plano D permanecem; a leitura
reserva espaço limitado para as bases e recusa resultados truncados.

## Consequências e limites

Não há escrita Gold, nova publicação, ponderação inventada ou autorização para
somar médias nos filtros. `allows_category_shares` e `filter_totals` conservam suas
regras. Os valores originais de mapas, séries e exportações não mudam por essa política.
Os campos novos do contrato são aditivos e possuem valores padrão.

Para Paraíba/2018, Alimentação é R$ 496,10 e a base oficial de consumo é
R$ 2.349,91: 21,11%. A soma dos itens arredondados exibidos é R$ 2.349,90;
essa diferença de R$ 0,01 não substitui o subtotal publicado. O Total de despesa
permanece R$ 2.893,59. A composição das médias de renda não deve ser interpretada
como distribuição de renda, famílias ou despesa agregada da população.

Correções de preços seguem a ADR-0020: índices específicos podem fazer a soma
dos componentes diferir do subtotal corrigido pelo índice geral. O denominador
continua sendo a referência declarada, com a proveniência da correção.

## Validação

Testes cobrem N1 25/70/5, N2 dentro dos três grupos, Total oficial distinto da
base, zero, sigilo, valores negativos, configuração inválida, matriz e troca de
eixos. A candidata local consulta o release existente somente para leitura e
confere os valores reais da Paraíba, sem ativação de dados.

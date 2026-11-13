# ADR-0020: Correção de valores em moeda pelo IPCA ("Corrigir por")

- **Estado:** aceito (2026-11-13), a pedido do mantenedor (ponto 1 do relatório de
  pontos críticos).
- **Contexto normativo:** CLAUDE.md §10.7, §10.8, §15.5, §19.4 e §28.5.

## Contexto

A despesa média da POF (2002, 2008 e 2018) está em reais da época, e a comparação
entre edições mistura o aumento real com a inflação. O mantenedor pediu:
- os valores "a preços de" corrigidos pelo IPCA, com base no período mais recente da
  série, que avança sozinho quando entram dados novos;
- a correção pelo IPCA geral e pelo IPCA de cada grupo de despesa, com um seletor
  "Corrigir por";
- o método e as fórmulas nas notas.

## Decisões

1. **Índice de preços na Gold:**
   - a variação mensal do IPCA (índice geral e os 9 grupos, c315) entra como série das
     tabelas 655 (ago/1999 a jun/2006), 2938 (jul/2006 a dez/2011), 1419 (2012 a
     2019) e 7060 (2020 em diante), no nível Brasil (ADR-0016);
   - os códigos dos grupos são os mesmos nas quatro estruturas de ponderação;
   - o indicador `ipca_grupos_variacao_mensal` não é KPI do portal: serve à correção.
2. **Fórmula:**
   - valor corrigido = valor × I(mês-base) ÷ I(mês de referência do período);
   - I é o número-índice encadeado das variações mensais, Π(1 + vₘ/100);
   - mês de referência de cada POF: jan/2003, jan/2009 e jan/2018. A data oficial é o
     dia 15, e o IPCA é mensal;
   - mês-base: o do período mais recente do KPI, que avança sozinho;
   - conferência: o fator de 2003 a 2018 (2,3641) e o de 2009 a 2018 (1,6963) são
     exatamente a razão do número-índice oficial do IPCA (tabela 1737, variável 2266).
3. **Por grupo:**
   - cada tipo de despesa usa o grupo do IPCA correspondente, por exemplo alimentação →
     Alimentação e bebidas, telefone e internet → Comunicação, móveis e
     eletrodomésticos → Artigos de residência;
   - os subitens herdam o grupo do item acima, pela árvore da Gold;
   - totais, subtotais e despesas fora do consumo usam o índice geral. Por isso, a soma
     dos itens corrigidos pode diferir do total corrigido; está na nota.
4. **Cálculo na consulta** (como a agregação no tempo, §10.7):
   - a correção não grava valores novos na Gold; a API aplica o fator e marca a
     resposta como derivada (`provenance.correction`, `correction_label`,
     `price_base`);
   - a configuração mora no KPI do portal (`corrections`), junto com o mapeamento dos
     grupos;
   - a conferência portal × release exige o índice no release (ADR-0015).
5. **Portal:**
   - o grupo "Corrigir por" (Nominal, IPCA geral, IPCA por grupo de despesa) aparece
     em KPIs com correções; a escolha vai na URL (`correcao=`);
   - a nota de método fica recolhida em "Como é calculado";
   - mapa, tooltip, série, tabela e exportação usam a correção;
   - a unidade vira "R$ de jan/2018" nas colunas, e a legenda e a exportação dizem o
     índice e o mês-base.

## Consequências

- **Comparação real:** a POF fica comparável em termos reais. A despesa total de 2002,
  de R$ 1.778,03, vale R$ 4.203,49 a preços de jan/2018.
- **Outros KPIs em moeda:** podem receber a mesma correção só com configuração.
- **IPCA por grupo:** o grupo é uma aproximação. A cesta de cada grupo do IPCA não é a
  mesma do tipo de despesa da POF, e isso está registrado na nota.

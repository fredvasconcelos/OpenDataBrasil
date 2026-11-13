# ADR-0017: Agregação no tempo por soma, média e último valor

- **Estado:** aceito (2026-11-13). O mantenedor pediu a dimensão de tempo em todos os
  KPIs possíveis, com o exemplo da SIDRA 8757, variável 7169, e delegou as decisões.
- **Amplia:** ADR-0013, que só permitia somar fluxos.
- **Contexto normativo:** CLAUDE.md §10.7, §14.3, §15.4 e §28.5.

## Contexto

A ADR-0013 deixou fora do escopo a média e o último valor. A variável 7169 da 8757
(PMC, número-índice 2022 = 100) não é um fluxo: somar os índices de 12 meses dá um
número sem sentido. O IBGE, porém, publica o índice anual da PMC, da PMS e da PIM como
a média dos índices mensais. E os índices de preços que o portal mostra, a variação
acumulada em 12 meses, têm no último mês do período o valor do período inteiro: o
IPCA de dezembro acumulado em 12 meses é a inflação do ano.

## Decisões

1. **Três regras:** `time_aggregation` passa a aceitar três valores. O indicador sem
   o campo continua só no grão publicado.

   | Regra | Cálculo | Status do valor | Para |
   |---|---|---|---|
   | `sum` | soma das partes | `derived_sum` | fluxos: ocorrências, óbitos, abates, leite, ovos, PIB a preços correntes |
   | `mean` | média das partes | `derived_mean` | números-índice (PMC, PMS, PIM), custo do m², rendimento médio, massa de rendimento mensal, pessoas ocupadas |
   | `last` | último período publicado | `derived_last` | acumulados em 12 meses (IPCA, INPC, IPCA-15), variação sobre o mesmo mês do ano anterior (IPP) e estimativas revisadas mês a mês (LSPA) |

2. **Período incompleto:** as três regras seguem a regra da ADR-0013. Sem todas as
   partes, o período fica sem valor (`incomplete_period`).
3. **Fica sem agregação:**
   - taxas sem regra oficial de agregação: desocupação, subutilização, investimento,
     poupança;
   - variação trimestral do PIB. A taxa anual oficial não é a média nem o último
     trimestre da taxa contra o mesmo trimestre do ano anterior.
4. **Configuração:**
   - o panorama declara `agregacao_tempo` ("soma", "media" ou "ultimo") por item;
   - o gerador passa a regra ao indicador e acrescenta uma nota explicativa;
   - a decisão é explícita por KPI, e não inferida da unidade, porque é uma regra
     estatística.
5. **Consulta:**
   - o planejador usa `sum`, `avg` ou `arg_max(valor, período)`;
   - a ordem dos códigos de período (`2024M01` < `2024M12`, `2024T1` < `2024T4`) é a
     cronológica dentro do ano;
   - indicadores com regras diferentes não se combinam numa consulta agregada no tempo
     (422).
6. **API e portal:**
   - o `KpiOut` ganha `time_aggregation`;
   - a nota de "Período por" diz a regra: "Soma dos períodos publicados", "Média dos
     períodos publicados" ou "Valor do último período publicado" (design system 2.3.5).

## KPIs com agregação (2026-11-13)

| Regra | KPIs (tabela) |
|---|---|
| soma | abate de bovinos (1092), leite adquirido (1086), ovos produzidos (7524), PIB trimestral a preços correntes (1846) |
| média | vendas de materiais de construção (8757), varejo (8880), varejo ampliado (8881), serviços (5906), turismo (8694), produção física (8888), insumos da construção (8886), custo do m² (2296), massa de rendimento (5606), rendimento médio real (5436), força de trabalho ocupada (4093) |
| último valor | IPCA (1737), INPC (1736), IPCA-15 (3065), IPP (6904), safra estimada (6588) |

Os 6 KPIs do Sinesp continuam com a soma da ADR-0013.

## Consequências

- **Cobertura:** passam a ter trimestre, semestre e ano 20 KPIs gerados a mais.
- **Médias da PNAD Contínua:** a média dos trimestres de pessoas ocupadas e de
  rendimento médio é um valor derivado. O IBGE publica a média anual oficial em outras
  tabelas, como a 10361; a diferença entre as duas está registrada no relatório de
  pontos críticos.
- **Último valor para a safra:** o ano é a estimativa de dezembro. Enquanto dezembro
  não sai, o ano fica incompleto.

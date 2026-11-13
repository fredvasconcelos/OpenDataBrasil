# Mesma medida em duas fontes: Censo × PNAD Contínua

Pergunta do mantenedor (2026-11-13): juntar em uma série a 6805 (Censo 2022, esgoto) e a
7192 (PNAD Contínua anual, esgoto, 2019 a 2025), e procurar outros casos.

## Conclusão: não juntar numa série única; comparar lado a lado

As duas pesquisas medem o mesmo assunto de formas diferentes:
- o Censo é um recenseamento de todos os domicílios, com resultados até o município;
- a PNAD Contínua é uma amostra, com coeficiente de variação, e vai até a UF e as
  capitais. Os seus pesos seguem projeções de população, não o Censo.

Em 2022, o único ano em comum, os valores do Brasil diferem:

| Assunto (tabelas) | Censo 2022 | PNAD 2022 | Diferença | Outras diferenças |
|---|---|---|---|---|
| Esgoto por rede ou fossa ligada à rede (6805 × 7192) | 64,7% | 69,3% | 4,6 p.p. | a PNAD conta só domicílios com banheiro ou sanitário; o Censo inclui os 0,5% sem. A PNAD junta fossa rudimentar, vala, rio e outra forma em "Outro tipo" |
| Lixo coletado (6892 × 6736) | 91,7% | 92,2% | 0,5 p.p. | a PNAD separa coleta direta e em caçamba; o Censo separa "enterrado" |
| Alfabetização, 15 anos ou mais (9543 × 7113) | 93,0% | 94,4% (100 − 5,6) | 1,4 p.p. | uma publica a taxa de alfabetização, a outra a de analfabetismo |
| Nível de instrução (10061 × 7189) | 18 anos ou mais | 25 anos ou mais | — | universos diferentes |
| Água (6803 × 6731) | ligação à rede e forma principal | principal fonte de abastecimento | — | quesitos diferentes; a 6731 não está no portal |
| População (9606 × 6579) | Censo | estimativas anuais | — | a estimativa de 2022 foi substituída pelo Censo; anos distintos |

Uma série única mostraria uma quebra falsa: em 2022, a cobertura de esgoto "cairia"
4,6 pontos só pela troca de fonte. O §15.4 do CLAUDE.md classifica esse caso como
"compatível mediante transformação documentada" no melhor dos casos, e nunca como a
mesma série.

## Proposta (para aprovação)

1. **Ligar os KPIs pares:** "Também medido por: PNAD Contínua (2016 a 2025)" no KPI do
   Censo, e o inverso, com o link para o outro.
2. **Comparar no gráfico de evolução:** a opção "Comparar com outra fonte" desenha a
   outra pesquisa como uma linha à parte, com marcador e legenda próprios ("PNAD
   Contínua, estimativa amostral"). O Censo aparece como um ponto em 2022, e as duas
   nunca se ligam.
3. **Categorias harmonizadas só para comparar,** com a regra na nota. No esgoto:
   - Censo 72110 ("Rede geral ou pluvial") → "Rede geral ou pluvial";
   - Censo 72111 → "Fossa ligada à rede";
   - Censo 72112 → "Fossa não ligada à rede";
   - fossa rudimentar, vala, rio e outra forma → "Outro tipo";
   - "Não tinham banheiro nem sanitário" fica fora (a PNAD não conta esses
     domicílios).
4. **Nota de comparabilidade** em cada par, com a diferença de 2022 acima.

Pares que entrariam: esgoto, lixo e alfabetização (o analfabetismo da PNAD vira
alfabetização como 100 − taxa, um derivado documentado). Ficam de fora a instrução
(universos diferentes) e a água (quesitos diferentes), a menos que a fonte publique um
recorte comum.

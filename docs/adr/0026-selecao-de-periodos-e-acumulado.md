# ADR-0026 — Seleção de vários períodos, Isolar por ano e acumulado

**Data:** 2026-11-16 · **Estado:** aceita (mantenedor, 2026-11-16) · **Estende:** ADR-0013 (grãos de tempo) e ADR-0017 (regras de agregação no tempo)

## Contexto

O filtro Período aceitava um período só. "Isolar período" (DS 2.3.14) somava ou tirava a média da mesma parte do ano entre **todos** os anos, o que misturava anos sem que o usuário escolhesse quais. O mantenedor pediu três coisas:

- escolher períodos numa lista hierárquica com caixas;
- isolar as partes de anos escolhidos;
- acumular os períodos marcados.

## Decisão

1. **Seleção.** O filtro Período é uma árvore (Ano › Semestre › Trimestre › Mês, até o grão de "Período por"). A seleção são as folhas marcadas.
   - URL: `periodo=2025T1,2025T2`.
   - Vazia: o padrão (o último período completo).
2. **Vários períodos sem acumular.**
   - A tabela ganha um grupo de colunas por período. O % é sempre dentro do período, nunca de um período sobre outro.
   - O mapa e o tooltip mostram o período mais recente marcado.
3. **Isolar.** A árvore lista só anos.
   - O mapa mostra o valor do ano, pela regra do KPI.
   - A tabela mostra uma coluna por parte dos anos marcados.
   - O gráfico mostra uma barra por ano em cada parte.
   - Nada é somado nem tem média tirada entre anos.
4. **Acumular** (`acumular=1`) só vale onde a agregação no tempo tem sentido:
   - fluxos (`time_aggregation = sum`): soma;
   - variações % mensais (`compound`): composição, `(prod(1 + v/100) - 1) * 100`;
   - taxas, médias, estoques e números-índice: a caixa fica desabilitada, e a API recusa com `semantic_rule`.

   Os modos:
   - sem Isolar: mapa, tooltip e tabela mostram o acumulado da seleção, e o gráfico mostra a curva acumulada nos períodos marcados;
   - com Isolar: acumulado no ano (jan, jan+fev, …; T1, T1+T2, …).
5. **Lacunas.** Um período sem valor na seleção deixa o acumulado sem valor (`incomplete_period`), sem completar meses. Um período em andamento marca `partial_period`. Outro status (estimativa, provisório) passa adiante.
6. **Onde calcula.** Na API, sobre as observações da Gold do release, em consulta e sem escrita (§10.7):
   - parâmetros `periods` e `accumulate` em mapa, detalhe, série e tabela;
   - a resposta traz `periods` e `accumulated`.

   A regra fica na camada semântica (`odb_semantics.periods.accumulate`, `running`, `covers`). O portal não calcula (§19.7).
7. **Exportação.** Nunca exporta valores acumulados, só os publicados e os derivados pela regra do KPI (ver o B5 do plano).

## Consequências

- **Limite:** uma consulta aceita até 120 períodos (10 anos de meses).
- **Sazonalidade:** o antigo "perfil médio entre todos os anos" deixa de existir. Para ver a sazonalidade, marcam-se os anos desejados.
- **Revisão futura:** a regra de acumulado para índices e % pode ser revista. Hoje eles não acumulam.

## Revisão de 2026-11-16 (DS 2.9): uma tabela só

A pedido do mantenedor, o painel passa a ter só a tabela dinâmica. Saem o "Recorte" e a
"Série completa" como visões separadas:

- a tabela segue os períodos marcados no filtro Período (`GET /kpis/{id}/pivot?periods=`);
  a série completa de um território é a mesma tabela com todos os anos marcados;
- os detalhes de "Detalhar por" entram nas colunas; o usuário rearruma linhas e colunas;
- ordenar, "Calcular % por" e o clique na linha (que seleciona o território) passam para
  a dinâmica. O % é só divisão entre valores publicados; a linha de totais (recorte ou
  Brasil) vem da API, como na tabela antiga;
- a tabela continua **nunca acumulada** (item 7 desta ADR). Com "Acumular", ela mostra cada
  período, e o botão de informação diz que o acumulado está no mapa e no gráfico.

Os endpoints `/table` e `/history` continuam na API (contrato público), sem uso pelo portal.

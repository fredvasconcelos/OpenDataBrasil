# ADR-0023: Regiões, mês como calendário, período parcial, grupos e KPIs por categoria

- **Estado:** aceito (2026-11-13), a pedido do mantenedor (pontos 1 a 4 da rodada 5).
- **Contexto normativo:** CLAUDE.md §10.7 (agregações persistidas na Gold), §14.3,
  §15.4, §15.5 e §28.5.

## Decisões

1. **Regiões pela soma das UFs** (`derived_levels = ["regiao"]` no indicador). Só para
   indicadores somáveis. A região é o primeiro dígito do código da UF (regra do IBGE).
   Ela fica sem valor (`incomplete_sum`) quando alguma UF da região não publica.
   - Status: `derived_sum`; marca `derived_region`.
   - A conferência Gold × Silver ignora as linhas derivadas.
   - Aplicado aos 6 indicadores do Sinesp VDE, que publica Brasil, UFs e municípios.
2. **Período parcial:** com agregação no tempo, o período do grão em andamento (o que
   contém o último mês publicado) mostra o acumulado até esse mês, com o status
   `partial_period` e "(parcial)" no portal. Os incompletos do meio da série continuam
   sem valor.
3. **Mês como calendário** (`month_dimension` na regra da tabela;
   `mes_como_periodo` no panorama). O "Mês de ocorrência" da 2654 (óbitos) e da 4412
   (casamentos) vira o período "AAAAMmm" nos KPIs `*_mensal`. O ano é a soma dos meses.
   - Conferido: igual ao total oficial (óbitos no Brasil: 1.226.594 em 2015, 1.781.370
     em 2021 e 1.490.857 em 2024; "mês ignorado" = 0).
   - Os KPIs anuais perdem o mês como detalhe.
   - Os detalhes (sexo, idade…) continuam anuais: a fonte só publica mês × detalhe no
     cubo, adiado (ver o relatório do cubo).
4. **Grupos de categorias** (`grupos` no panorama, `configs/catalog/grupos/`). As
   lavouras da 5457 ficam em 9 grupos:
   - grãos pelo LSPA/IBGE (grupo "Cereais, leguminosas e oleaginosas") e pela Conab;
   - os demais pelas classes da CNAE 2.0.

   O grupo é a soma dos produtos, só em área e valor (a quantidade muda de unidade).
   Subprodutos (café arábica e canephora) ficam abaixo do total sem entrar na soma.
5. **Um KPI por categoria** (`sufixo` e `unidade` no panorama): tabelas cujas
   categorias não se somam ou mudam de unidade (rebanhos da 3939; produtos de origem
   animal da 74) viram um KPI por categoria. Cada KPI tem dataset próprio e filtra as
   linhas da sua categoria (`keep_categories`).
6. **Feminicídio sem detalhe por sexo:** o crime é contra a mulher. A nota registra os
   poucos registros masculinos (erro na execução, art. 73 do CP, ou de registro) e os
   "não informados" da fonte, ano a ano.
7. **Ordem própria dos detalhes** (`ordem_detalhes`) e o mapa pela dimensão que contém
   a categoria pintada. Assim o Plano Diretor (5882) cruza tamanho × existência com o
   tamanho primeiro.

## Consequências

- A Gold persiste derivados (regiões, grupos) com status e marca próprios. A origem de
  cada valor continua rastreável.
- Os KPIs mensais permitem o "Isolar período" (barras por mês acumuladas entre os anos,
  DS 2.3.14).

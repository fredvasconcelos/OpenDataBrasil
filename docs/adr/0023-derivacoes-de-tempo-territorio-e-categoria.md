# ADR-0023: Regiões, mês como calendário, período parcial, grupos e KPIs por categoria

- **Estado:** aceito (2026-11-13), a pedido do mantenedor (pontos 1 a 4 da rodada 5).
- **Contexto normativo:** CLAUDE.md §10.7 (agregações persistidas na Gold), §14.3,
  §15.4, §15.5 e §28.5.

## Decisões

1. **Regiões pela soma das UFs** (`derived_levels = ["regiao"]` no indicador). Só para
   indicadores somáveis. A região é o primeiro dígito do código da UF (regra do IBGE).
   Composição e cobertura são conferidas na DTB fixada. Desde a decisão de
   2026-11-16, a ausência de UF ou componente mantém o subtotal disponível como
   parcial, com notas e métodos (detalhes na atualização abaixo).
   - Status: `derived_sum` quando completa, `partial_sum` quando parcial; marca `derived_region`.
   - A conferência Gold × Silver ignora as linhas derivadas.
   - Aplicado aos 6 indicadores do Sinesp VDE, ao SIM e às medidas autorizadas de abate, leite e ovos.
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
   **Atualização (2026-11-14):** o grupo é uma classificação própria ("Grupo de
   lavoura", `c782g`, `GroupDimensionRule`), cruzável com o produto em todos os
   níveis. Cada produto aparece no Total dos grupos (detalhe só por produto) e no seu
   grupo (grupo e produto). O tooltip mostra grupo → produtos, com % do grupo.
   Subprodutos (café arábica e canephora) ficam abaixo do total sem entrar na soma.
   Produtos que a PAM não pesquisou no ano ("...", como centeio, linho e juta) ficam
   fora da soma (`ignorar_indisponiveis`, `AggregateRule.ignore_unavailable`): o Total
   da 5457 também não os conta (conferido: Total = soma dos produtos publicados em
   MT, SP e Brasil, 2010 e 2025). Sem isso, quase todo grupo ficava "...". Partes
   suprimidas continuam bloqueando a soma.
5. **Um KPI por categoria** (`sufixo` e `unidade` no panorama): tabelas cujas
   categorias não se somam ou mudam de unidade (rebanhos da 3939; produtos de origem
   animal da 74) viram um KPI por categoria. Cada KPI tem dataset próprio e filtra as
   linhas da sua categoria (`keep_categories`).
   - **Tabela compartilhada na Silver:** a escrita troca a partição lógica do dataset
     (`replace_where`). Com só `table_id`, o build de um KPI apagava os irmãos (no
     primeiro build, só o último de cada tabela ficou com linhas). Quando outro
     dataset pede a mesma tabela, a partição ganha `variable_id` e/ou
     `classification_key` (`shared_table_partition`). Recortes que se sobrepõem
     bloqueiam o build.
   - **Na Gold,** cada dataset lê só as linhas com as suas categorias fixas
     (`DatasetInfo.shared_categories`).
6. **Feminicídio sem detalhe por sexo:** o crime é contra a mulher. A nota registra os
   poucos registros masculinos (erro na execução, art. 73 do CP, ou de registro) e os
   "não informados" da fonte, ano a ano.
7. **Ordem própria dos detalhes** (`ordem_detalhes`) e o mapa pela dimensão que contém
   a categoria pintada. Assim o Plano Diretor (5882) cruza tamanho × existência com o
   tamanho primeiro.

8. **Total derivado e PPM agrupada** (decisão do mantenedor, 2026-11-14;
   `total_somado` e `categorias` no panorama). Quando a fonte não publica o Total, ou
   ele mistura unidades, o Total do KPI pode ser a soma das categorias mostradas, se
   todas têm a mesma unidade. A soma só tem valor com todas as partes publicadas, e a
   nota explica a generalização:
   - **Efetivo de rebanhos (3939):** a soma das cabeças dos 8 tipos de 1º nível. O
     descritor diz que os tipos não se somam; o portal soma porque a unidade é a mesma
     (indivíduos). O Total conta animais, sem equivalência produtiva (não é unidade
     animal), e os galináceos são a maior parte. Matrizes e galinhas ficam fora: já
     estão nos totais de suínos e galináceos.
   - **Produção de origem animal (74):** um KPI por unidade:
     - leite (mil litros);
     - ovos de galinha e de codorna (mil dúzias);
     - mel, lã e casulos (kg; o Total é peso de produtos diferentes).
   - Os três datasets da 74 pedem conjuntos de categorias sem nenhuma em comum. A
     partição da Silver usa `classification_key IN (...)` (`shared_table_partition`).

## Consequências

### Atualização de 2026-11-16 — cobertura regional e subtotais parciais

O mantenedor autorizou regiões derivadas para medidas aditivas durante a conclusão
da cobertura territorial: SIM, abate de bovinos (1092/284), leite (1086/282) e ovos
(7524/29). As três variáveis SIDRA permitem soma territorial no descritor.

A composição oficial da DTB fixada no build distingue soma completa de parcial,
por período e categoria. Conferir apenas as UFs observadas não detectava uma UF
inteiramente ausente. O mantenedor determinou expressamente que uma cobertura
incompleta **não deve esconder os valores disponíveis**: a soma dos componentes
numéricos utilizáveis é publicada como `partial_sum`, com a marca `partial_coverage`,
o rótulo "parcial" e a limitação nas notas e métodos. Uma soma completa continua
`derived_sum`. A regra também vale para o Sinesp já configurado.

UF ausente, indisponível ou em sigilo não vira zero e não é estimada. Quando há
sigilo entre os componentes, o subtotal soma apenas os valores públicos e recebe
`contains_suppressed`; os registros originais `X` permanecem protegidos. Sem nenhum
componente numérico disponível, não existe subtotal: permanece `suppressed` se há
sigilo ou `incomplete_sum` nos demais casos. UFs com registros ambíguos/duplicados
não entram duas vezes na soma. A parcialidade acompanha filtros de categorias,
agregações no tempo, acumulados e exportações. As regras existentes para períodos
inteiramente ausentes não são alteradas. Um valor regional nativo prevalece.

Leite e ovos não publicam Amapá no descritor da captura: não se infere zero; o Norte
mostra o subtotal disponível como parcial. O Brasil oficial é preservado e não é
reconstruído pela soma das regiões. A linhagem dos
componentes pode ser recuperada pelas observações de UF do mesmo indicador, período,
categorias, snapshot Silver e build Gold. A origem individual na linha regional é
representativa; a marca de derivação identifica a necessidade de consultar o conjunto.

- A Gold persiste derivados (regiões, grupos) com status e marca próprios. A origem de
  cada valor continua rastreável.
- Os KPIs mensais permitem o "Isolar período" (barras por mês acumuladas entre os anos,
  DS 2.3.14).

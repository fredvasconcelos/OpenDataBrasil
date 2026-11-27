# ADR-0041 — Acumulado da mesma parte do ano entre anos

- Data: 25/11/2026.
- Estado: implementada e validada em candidata local, após o pedido de continuação
  do mantenedor. Aceite visual final pendente; sem substituir o localhost existente
  nem implantar na beta.
- Pedido: Isolar + Acumular deve apresentar uma barra por parte do ano, totalizando
  o intervalo escolhido, aproveitando parcelas disponíveis e explicando faltas.
  O mantenedor confirmou uma barra por trimestre com o total de 2023–2025.
- Estende a ADR-0026, sem reescrever seu registro histórico; preserva métodos das
  ADRs 0013/0017 e a hierarquia de alertas da ADR-0040.

## Mudança de significado

O comportamento anterior acumulava dentro de cada ano (T1, T1+T2, …), com uma barra
por ano. O novo modo acumula a mesma parte entre anos:

`T1 = T1/2023 + T1/2024 + T1/2025`, e analogamente T2, T3 e T4.

Isolar sozinho continua comparando anos separados. Acumular sozinho é o acumulado
cronológico admitido pela regra do KPI. Ambos ligados selecionam o novo operador;
o valor não é a média entre anos nem o acumulado até o trimestre dentro de cada ano.

O intervalo é inclusivo, do menor ao maior ano, e deve ficar explícito no controle
e na legenda. Anos intermediários não podem desaparecer silenciosamente. É uma
decisão de seleção de intervalo, sem fabricar observações para posições faltantes.

## Frequência, universo e método

O menor grão é o publicado pelo KPI: mês, trimestre, semestre ou ano. Um trimestral
não ganha meses; um semestral tem duas posições; um anual compara anos e, havendo
soma admissível, pode produzir uma barra do intervalo inteiro. Não há KPI semestral
nativo no catálogo local avaliado, mas o protótipo cobre esse calendário.

Somente fluxos de parcelas disjuntas e unidades/universos comparáveis admitem a
soma. Aditividade territorial não comprova aditividade temporal. A validação local
identificou 24 métodos de soma sustentados (12 já declarados e 12 anuais com
permissão oficial), 183 comparações sem soma, 30 fluxos candidatos sem regra
resolvida e quatro índices restritos à composição de intervalo contíguo completo.
Esses números são pareceres metodológicos, não quantidade de controles habilitados.

População e pessoas ocupadas não são eventos novos a cada ano. Taxas, médias,
números-índice e previsões revisadas não viram soma. Compor apenas os T1 de anos
distintos omite os demais trimestres e não representa a inflação acumulada entre
os extremos; os quatro índices preservam a composição válida no intervalo
contíguo completo, sem liberação automática do novo operador sazonal.

Somas monetárias correntes mantêm nota de valor nominal; não são crescimento real.
Área plantada/colhida em safras distintas é atividade acumulada, não extensão
única de terra. Categorias, recortes territoriais e alterações metodológicas exigem
comparabilidade própria; totais oficiais não se somam com suas subdivisões.

## Parcelas ausentes e risco

Para a nova soma, ler as menores parcelas admissíveis disponíveis. Se a base é
mensal, dois meses publicados de T4/2026 entram no subtotal; não descartar ambos
porque a consulta trimestral estrita devolveu período incompleto.

| Situação no agregado pedido | Valor | Alerta |
|---|---|---|
| Todas as parcelas válidas e comparáveis | Soma completa | Nenhum, salvo outro risco |
| Algumas parcelas sem publicação/indisponíveis; outras válidas | Subtotal das conhecidas | Amarelo; identificar parcelas e cobertura |
| Nenhuma parcela com valor | Ausente, sem transformar em zero | Vermelho |
| Sigilo, categoria não aplicável ou incompatibilidade de método/universo | Sem soma automática | Vermelho, com motivo próprio |

Zero verdadeiro e zero arredondado contam como valores presentes. Não preencher
lacunas, ratear sigilo nem reconstruir categorias desconhecidas. Um subtotal
territorial já parcial conserva seu aviso. Vermelho prevalece sobre amarelo e
a cor não é o único sinal; só vermelho abre a explicação automaticamente.

As contagens distinguem parcelas esperadas, com valor, ausentes e bloqueadas,
por parte, território e combinação de categorias. Comparar barras com coberturas
distintas exige aviso visível: T4 com 3/4 anos não tem a mesma base de T1 com 4/4.
Não reduzir todas as barras à cobertura comum sem escolha expressa do usuário.

O alerta do agregado avalia o agregado pedido: uma parcela futura omitida não
vira uma observação publicada com valor zero. Consultas antigas a um período
isolado indisponível continuam com suas recusas/alertas existentes.

## Contrato e apresentação implementados

O cálculo e a severidade ficam na API/camada semântica, sobre a Gold Delta do
release fixado. O gráfico recebe valores, cobertura e alertas estruturados. Não
somar no navegador nem armazenar réplicas de fatos em PostgreSQL/DuckDB.

O contrato distingue resultado por intervalo/parte de uma observação
de um ano: não rotular uma soma 2023–2025 como se fosse apenas 2025T1. A capacidade
de comparar, agregar calendário, acumular cronologicamente e acumular por parte
deve ser independente, incluindo grão único anual/trimestral.

Preservar compatibilidade: os modos/valores padrão dos endpoints atuais não mudam
silenciosamente. A política de subtotal parcial entra no operador explícito novo;
não alterar a composição ou os agregados oficiais por efeito colateral.

Tabela e exportações preservam as observações/derivados já permitidos pela
ADR-0026; este pedido do gráfico não autoriza substituir seus dados por acumulados.
Deve ser possível inspecionar as parcelas que produziram a barra, sem apresentar
o subtotal como célula oficial do SIDRA. Contrato OpenAPI, textos e DS acompanham
a implementação, com prova por recorte e navegador.

`KpiOut.temporal` informa `isolate`, `accumulate`, `seasonal_sum` e
`accumulation_rule`. A API oferece a comparação nos 170 KPIs que têm partes
subanuais ou mais de um ano; os outros 71 só têm um ano anual no release avaliado.
Isso é independente da soma, habilitada em 24 KPIs. Os 17 trimestrais de grão
único podem comparar sem receber agregação anual. Sem grão anual permitido,
o mapa mostra a última parte efetivamente publicada, identificada no rótulo.

`GET /api/v1/kpis/{id}/seasonal` recebe `geography`, `year_from`, `year_to`,
`grain`, `dimensions`, `categories` e `correction`. Retorna séries por combinação
de categorias, com `part`, `value`, `status`, `severity`, `expected`, `present`,
`missing`, `blocked`, `contributors` e `input_partial`, além do grão nativo,
intervalo, notas e linhagem marcada como derivada. A ausência não ganha valor zero.
O novo resultado não se identifica como observação de um ano isolado.

As doze permissões anuais ficam em `configs/portal/demografia/temporal.toml`,
com tabela, variável e nota metodológica explícitas; só valem quando a linhagem
do release coincide integralmente. As doze somas subanuais usam sua regra já
declarada na Gold. Não há alteração de fatos, schema ou manifesto de release.

Cada consulta admite até 120 posições nativas de calendário e 60 mil células
estimadas. Exceder um limite ou receber resultado truncado gera recusa explícita;
nunca uma barra calculada de uma leitura truncada. São até dez anos mensais,
trinta trimestrais, sessenta semestrais ou 120 anuais. O calendário enumera posições
esperadas para medir cobertura, sem fabricar observações da fonte.

## Validação já executada e limites

O auditor `infrastructure/scripts/validacao_acumulado_sazonal.py` avaliou os 241
KPIs com descritores/linhagem fixados e uma série real por KPI. O protótipo fez
64 experimentos de soma em 2023–2025 e 2023–2026, sem publicação. Testes cobrem
ausência, zeros, sigilo, duplicidade, frequências e meses de trimestre incompleto.
Uma série por KPI não homologa todos os municípios ou cruzamentos de categorias.
Os 30 pareceres pendentes não foram convertidos em permissões por suposição.

A API real da candidata reproduziu os 64 experimentos, inclusive valores,
severidade, cobertura e parcelas faltantes, sem truncamento. O relatório
`docs/relatorios/2026-11-25-implementacao-acumulado-sazonal.md` registra testes,
capturas e imagens exatas. O operador usa os detalhes já publicados; mês × sexo/
idade/natureza/local da 2654 e os demais conjuntos ausentes da Gold permanecem
na trilha de captura e processamento. Implementar o operador não os materializa.

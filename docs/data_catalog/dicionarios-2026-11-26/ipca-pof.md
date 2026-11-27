# IPCA e POF — significados, métodos e diferenças entre edições

26/11/2026. Explicação do Open Data Brasil. Esta análise combina descritores oficiais
preservados, pesquisa independente em trechos indexados dos produtores e inspeção
da configuração vigente. **A leitura integral dos manuais não foi concluída:** a
abertura da página do IPCA e do PDF `liv101670.pdf` retornou 403, sem contorno.
As fontes abaixo não significam que novos dados foram incorporados.

## IPCA: quatro conceitos que o arquivo deve distinguir

| Medida | Identificador oficial | Significado e limite |
|---|---|---|
| Número-índice | 1737/2266 | Nível da série, base dezembro/1993 = 100; não é percentual. |
| Variação mensal | 1737/63; 655/63, 2938/63, 1419/63, 7060/63 | Mudança no mês; uma taxa de 1% não é nível de índice 1. |
| Acumuladas | 1737/2263 (3 meses), 2264 (6), 69 (ano), 2265 (12 meses) | Janelas diferentes, potencialmente sobrepostas; não somar taxas nem compor taxas acumuladas com janelas sobrepostas. |
| Peso mensal | 2938/66, 1419/66, 7060/66 | Participação na ponderação; não é inflação nem contribuição em pontos percentuais. Está no descritor, sem ser um novo KPI publicado. |

Os pares, bases e casas decimais vêm dos descritores [1737](https://apisidra.ibge.gov.br/DescritoresTabela/t/1737),
[2938](https://apisidra.ibge.gov.br/DescritoresTabela/t/2938),
[1419](https://apisidra.ibge.gov.br/DescritoresTabela/t/1419) e
[7060](https://apisidra.ibge.gov.br/DescritoresTabela/t/7060), seções `Variaveis`
e `Nota`; consulta preservada de 25/11/2026, identificada por hash em `tabelas.json`.

A metodologia do produtor utiliza ponderações de consumo e fórmula de Laspeyres
nos níveis superiores. Pesos regionais e pesos de itens exercem funções diferentes;
a população-objetivo do IPCA abrange famílias de 1 a 40 salários mínimos nas áreas
urbanas pesquisadas. Não se obtém o Brasil somando índices territoriais. Fonte:
[IBGE, IPCA, Metodologia](https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidoramplo.html),
estrutura baseada na POF 2017–2018, trecho indexado consultado em 26/11/2026;
leitura direta bloqueada. Os pesos e etapas elementares de cada edição ainda
precisam do manual completo, sem substituir tudo por uma média simples.

Relações matemáticas para interpretar as medidas, sem recalcular dados nesta revisão:

```text
v_m = 100 × (I_m / I_(m-1) − 1)
v_[a,b] = 100 × (Π_(m=a..b)(1 + v_m/100) − 1)
I_m encadeado = I_(m-1) × (1 + v_m/100)
```

São relações entre nível e variação. O produto deve conter todos os meses do
intervalo compatível; compor só janeiro de vários anos não mede inflação entre
as datas extremas. Arredondar as taxas antes de encadear pode diferir do índice
calculado pelo produtor com precisão interna. O número-índice oficial deve ser
preservado como tal, separado de um índice reconstruído pelo portal.
O método de composição já aceito no portal está na [ADR-0026](../../adr/0026-selecao-de-periodos-e-acumulado.md),
itens 4/7, e sua restrição sazonal na [ADR-0041](../../adr/0041-acumulado-sazonal-entre-anos.md).

| Estrutura de consumo | Tabela na série configurada | Janela documentada |
|---|---|---|
| POF 1995–1996 | 655 | ago/1999–jun/2006 |
| POF 2002–2003 | 2938 | jul/2006–dez/2011 |
| POF 2008–2009 | 1419 | jan/2012–dez/2019 |
| POF 2017–2018 | 7060 | jan/2020 em diante; 12 meses nessa estrutura desde dez/2020 |

Essas mudanças vêm da `Nota` dos quatro descritores. Continuidade de códigos de
grupo não prova identidade de cesta, produto, peso ou área em todos os anos.
A configuração territorial atual preserva a origem nacional da 1737 e usa as
outras tabelas nas áreas nativas. Região metropolitana, município, UF e Grande
Região precisam de tipos distintos. Ausência de área não representa inflação zero.

INPC atende famílias de 1 a 5 salários mínimos com pessoa de referência assalariada;
não herda a população/ponderação do IPCA. O IPCA-15 tem janela geralmente do dia
16 anterior ao dia 15 de referência e cobertura própria. O IPP observa preços no
produtor, excluindo impostos, tarifas e fretes, com número-índice 6904/10008 em
base dezembro/2018 = 100. Fontes, seções, edições e lacunas em
[M30–M32](pesquisas.md#m30), consulta de 26/11/2026 por índice oficial de pesquisa.

N5 permanece sem aceite: os 345 valores com perda de precisão e os 129 positivos
convertidos em zero são achados da candidata, não dos dados N2. As equivalências
1736/2292, 1737/2265, 3065/1120 e 6904/1394 continuam sem homologação integral.
Esta análise não corrige schema, regra ou dado.

## POF: unidade, edição, amostra e finalidade por variável

“Família”, nas tabelas 2309/1594/6715/6974, significa **unidade de consumo**.
Não substituir automaticamente por domicílio, pessoa ou família de parentesco.
Uma despesa não monetária também pode integrar a medida; não é apenas desembolso
em dinheiro. Fonte: notas 1–3 dos descritores e [POF 2017–2018 — Primeiros resultados](https://www.ibge.gov.br/estatisticas/sociais/populacao/24786-pesquisa-de-orcamentos-familiares-2.html?edicao=25578&t=resultados),
Conceitos e métodos, consulta indexada em 26/11/2026.

| Ficha / tabela e variável | Edição e universo documentado | Unidade e interpretação |
|---|---|---|
| `despesa_familiar` — 2309/1201 | POF 2002–2003, código temporal 2002; Brasil/regiões no recorte configurado | R$ por unidade de consumo/mês; rendimento monetário e não monetário em c12191. |
| Mesma ficha — 1594/1201 | POF 2008–2009, código 2008; Brasil/regiões/UF e recorte municipal próprio da tabela | Média mensal, R$; c339 inclui rendimento total e variação patrimonial; classes em SM de R$ 415. |
| Mesma ficha — 6715/1201 | POF 2017–2018, código 2018; Brasil/regiões/UF | Média mensal, R$; classes c339 em SM de R$ 954; sem estender nível municipal de outra edição. |
| `apoio--despesa_familiar_distribuicao` — mesmas tabelas/1204 | Mesmas edições, com denominador da distribuição de despesa | %; não é uma segunda despesa em reais. |
| `rendimento_familiar` — 6974/388 | POF 2017–2018 | Rendimento total e variação patrimonial médio mensal, R$; inclui componentes diferentes do rendimento do trabalho. |
| `pof_despesa_distribuicao_antiga` — 387/172 | POF 1987–1988 e 1995–1996, códigos 1987/1995 | % de despesa; Total das áreas POF (N103), nove RMs, Brasília/Goiânia; não é Brasil. |
| `pof_recebimento_distribuicao_antiga` — 414/177 | Mesmas edições/áreas antigas | % do recebimento; a nota 3 descreve média por classe. Não é valor monetário nem peso amostral. |
| `pof_despesa_alimentacao_antiga` — 400/174 | Mesmas edições/áreas antigas | % da despesa com alimentação; denominação do total própria. |
| `aquisicao_alimentar` — 417/180 | Códigos 1987, 1995, 2002, 2008, mantendo as áreas antigas | kg por pessoa/ano, aquisição **monetária** domiciliar; não consumo ingerido. Nota 3 converte medida volumétrica em peso 1:1 na própria fonte. |

Fontes: seções `Variaveis`, `Classificacoes`, `Periodos`, `NiveisTerritoriais` e
`Nota` dos [descritores 2309](https://apisidra.ibge.gov.br/DescritoresTabela/t/2309),
[1594](https://apisidra.ibge.gov.br/DescritoresTabela/t/1594),
[6715](https://apisidra.ibge.gov.br/DescritoresTabela/t/6715),
[6974](https://apisidra.ibge.gov.br/DescritoresTabela/t/6974),
[387](https://apisidra.ibge.gov.br/DescritoresTabela/t/387),
[414](https://apisidra.ibge.gov.br/DescritoresTabela/t/414),
[400](https://apisidra.ibge.gov.br/DescritoresTabela/t/400) e
[417](https://apisidra.ibge.gov.br/DescritoresTabela/t/417), coleta preservada de
25/11/2026; correspondências e recortes verificados na configuração nesta revisão.

A POF 2017–2018 utiliza desenho por conglomerados em dois estágios, estratificado:
setores/agrupamentos da Amostra Mestra e domicílios. A unidade sorteada e seus pesos
não devem ser substituídos por uma média simples dos entrevistados. O produtor
informa 57.920 domicílios pesquisados em [apresentação dos primeiros resultados](https://agenciadenoticias.ibge.gov.br/media/com_mediaibge/arquivos/a801a1966c404fdf46e41bfd64d31db8.pdf),
seção da amostra, consulta indexada em 26/11/2026. Isso não é o tamanho de cada
subamostra, classe, UF ou edição anterior. O valor “mais de 75 mil” da
[notícia de início da coleta](https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/10448-ibge-inicia-a-pesquisa-de-orcamentos-familiares-pof-2017-2018)
é previsão de visitas, não número final de entrevistas.

O bloco de consumo alimentar pessoal investiga subamostra e pessoas de 10 anos
ou mais; não é o universo da aquisição monetária domiciliar da 417.
Fonte: [POF, procedimentos de coleta e tratamento](https://www.ibge.gov.br/estatisticas/sociais/saude/24786-pesquisa-de-orcamentos-familiares-2.html?edicao=28708&t=resultados),
seção Metodologia, edição 2017–2018, consulta indexada em 26/11/2026.

Na 6974, nota 4, a média relaciona rendimento de cada célula ao número de famílias
correspondente. A expressão conceitual de uma média ponderada é `Σ(w×x)/Σw`;
essa identidade não fornece os pesos ausentes. A média do Total não é a soma nem
a média simples das médias de classes. Percentuais e aquisições per capita também
exigem denominador específico. Faixas em reais mudam por edição e c12191 não é
c339. Permanecem pendentes os pesos, ajustes, não resposta, tamanhos amostrais
das edições antigas e as memórias completas por variável.

## Operação do portal separada do método do produtor

A correção já configurada é `valor × I(base)/I(referência)`, com janeiro/2003,
janeiro/2009 e janeiro/2018 como meses de referência das três edições, conforme
[ADR-0020](../../adr/0020-correcao-por-indice-de-precos.md). Usa índice geral ou
correspondência curada de grupo; subitens herdam grupo, totais usam índice geral.
Essa correspondência é operação do portal, não nova cesta oficial da POF. Itens
corrigidos por grupos podem não somar o Total corrigido.

O Excel proposto deve registrar índice e origem, base, mês de referência,
mapeamento de grupos e versão. A correção é efetivamente solicitada ao exportador
atual; Isolar/Acumular não. A correção não elimina diferenças de universo,
questionário, cobertura ou classes entre edições e não transforma PIB nominal
em volume oficial.

# Pontos críticos para decisão — 2026-11-12

Relatório pedido pelo mantenedor ao delegar a ampliação dos indicadores ("pode tomar as
decisões que considerar e gere um relatório com os pontos críticos"). Cada ponto traz o
que foi decidido, o risco e o que precisa da decisão dele. A ordem vai do maior impacto
estatístico ao operacional.

Referências: [ADR-0015](../adr/0015-conferencia-portal-release-e-ciclo-de-atualizacao.md)
(conferência portal × release e ciclo de atualização),
[ADR-0016](../adr/0016-series-de-tabelas-e-detalhes-marginais.md) (POF em série e
detalhes marginais) e [plano do dados.gov.br](../data_catalog/dados-gov-br-plano.md).

## O que foi entregue

| Item | Antes (release `0a683906`) | Agora (release `edae0200`, ativo no ambiente local) |
|---|---|---|
| Verificações da Gold | 678 aprovadas, 13 avisos | 828 aprovadas, 25 avisos, nenhuma falha |
| Observações (`indicator_observation`) | 20.586.014 | 20.965.098 |
| KPIs publicados no portal | 148 (9 planejados) | 153 (7 planejados) |
| KPIs com detalhe (dimensões) | 87, com 91 dimensões | 96, com 173 dimensões |
| KPIs com detalhes marginais (uma dimensão por vez) | — | 48 |
| Testes | 355 Python, 64 portal, 21 e2e | 399 Python (com integração), 66 portal, 23 e2e |

Entregas:
- **Conferência portal × release** (ADR-0015):
  - `odb release check`;
  - ativação recusada quando o portal não casa com o release;
  - API tolerante, com `/health` em `degraded`.
- **Ciclo de atualização:** runbook [atualizacao.md](../runbooks/atualizacao.md).
- **POF** (ADR-0016):
  - série 2002, 2008 e 2018 em reais;
  - faixas de rendimento por edição, com nota;
  - POF de 1987 e 1995 nas regiões metropolitanas (tabelas 387, 400, 414 e 417).
- **Detalhes:**
  - todas as classificações com Total que cabem no limite da fonte viraram detalhe;
  - quando os códigos conflitam, a tabela ganha uma classificação própria.
- **Design system 2.3.4:** "Detalhar por" com uma dimensão por vez. Captura:
  `design-system/reference/screens/detalhar-uma-por-vez.png`.
- **Plano do dados.gov.br:** [dados-gov-br-plano.md](../data_catalog/dados-gov-br-plano.md).

## 1. Valores da POF em reais da época, sem correção pela inflação

- **Decidido:** a série 2002, 2008 e 2018 mostra os valores como o IBGE publica, em
  reais da data de referência de cada edição. A nota do indicador diz que a comparação
  é nominal.
- **Risco:** a despesa total sobe de R$ 1.778 (2002) para R$ 2.626 (2008) e para o valor
  de 2018, mas boa parte disso é inflação. Um leitor apressado pode ler como aumento
  real.
- **Para decidir:** criar um indicador derivado "a preços de 2018", corrigido pelo
  IPCA, que já está na Gold desde 1998. Isso exige fixar a regra: a data de referência
  de cada POF (15/01/2003, 15/01/2009 e 15/01/2018) e o índice (IPCA geral ou o de
  cada grupo de despesa). É uma regra estatística nova (§28.5).

## 2. POF 2002-2003: classes de rendimento de fora

- **Decidido:** em 2002, só o Total. A tabela 2309 usa outro conceito de rendimento
  (monetário e não monetário) e outras faixas (10 classes, de "até R$ 400" a "mais de
  R$ 6.000").
- **Para decidir:** incluir essas faixas como dimensão própria de 2002, com o mesmo
  rótulo "Classes de rendimento" e a nota do conceito. O custo é pequeno, porque a
  tabela tem 1.068 linhas.

## 3. POF 2002-2003: 18 tipos de despesa com código próprio

- **Decidido:** os 18 entram como categorias próprias, com valor só em 2002. Exemplos:
  "Energia elétrica" (2.1.2.2.1 em 2002, 2.1.2.3.1 em 2018) e "Viagens", que virou
  "Viagens esporádicas".
- **Risco:** no gráfico de evolução, "Energia elétrica" aparece como duas séries, uma
  com 2002 e outra com 2008 e 2018.
- **Para decidir:** harmonizar só as categorias de nome idêntico entre as edições, com
  uma nota. As renomeadas ficam separadas, porque mudaram de conteúdo.

## 4. POF de 1987 e 1995: sem hierarquia dos tipos de despesa

- **Decidido:** os 68 tipos de despesa (387), os 75 de alimentação (400) e as 20
  origens de recebimento (414) ficam numa lista única. O descritor oficial põe todos no
  mesmo nível, e a árvore não foi inventada.
- **Risco:** subtotais e itens aparecem lado a lado (por exemplo, "Despesas de consumo"
  e "Alimentação"), e a soma passa de 100%. A nota da partição avisa.
- **Para decidir:** montar a árvore pela ordem e pelos nomes da planilha oficial do
  FTP (`SIDRA387.XLS`). Seria uma curadoria manual, a revisar.

## 5. Regiões metropolitanas: pertencem a uma UF

- **Decidido:** cada RM tem como pai a UF do prefixo do código (1501 → PA). Vale para
  as 9 RMs das POF antigas.
- **Risco:** RMs e RIDEs que atravessam UFs, como a RIDE do DF, quebrariam essa regra
  se entrarem no futuro. Hoje, nenhuma verificação automática detecta isso.
- **Para decidir:** nada agora. Rever quando entrar uma tabela com RIDE.

## 6. Detalhes marginais, sem cruzamentos

- **Decidido:** 48 KPIs mostram cada classificação separada, com as demais no
  Total. O portal deixa marcar uma por vez, com o aviso "Uma por vez".
- **Risco:** não dá para ver, por exemplo, óbitos por sexo e idade ao mesmo tempo.
- **Para decidir:** escolher os cruzamentos que valem uma requisição própria. Os
  candidatos naturais são sexo × idade nos óbitos, nos nascidos vivos (idade da mãe)
  e na alfabetização. O custo é de dezenas a centenas de requisições por KPI na carga
  inicial, e a atualização mensal ou anual só baixa os períodos novos.

## 7. Municípios: categorias só até UF nas séries longas

- **Decidido:** as categorias por município entram só em tabelas com até três
  períodos, como os Censos. Nas séries longas, ficam até UF. A regra já valia para a
  dimensão principal e agora vale também para os detalhes.
- **Para decidir:** liberar o município numa série longa específica, aceitando horas
  de ingestão na primeira carga.

## 8. KPIs ainda só com o Total ou fora do portal

- **Só o Total, porque a tabela não tem classificações:** 40 KPIs. Nada a decidir.
- **Só o Total, porque a classificação principal não tem Total:** 11 KPIs. O valor publicado é uma categoria de referência, como o índice de volume nas pesquisas mensais. Para decidir: aceitar a referência como está ou escolher outra categoria por KPI.

| KPI | Tabela | Classificação sem Total |
|---|---|---|
| Esperança de vida ao nascer (projeção para 2026) | 7362 | c1933 Ano |
| Frequência escolar líquida no ensino fundamental | 7141 | c871 Faixa etária ideal por curso frequentado |
| Efetivo de bovinos | 3939 | c79 Tipo de rebanho |
| Produção física industrial | 8888 | c544 Seções e atividades industriais (CNAE 2.0) |
| Volume de vendas de materiais de construção | 8757 | c11046 Tipos de índice |
| Volume de vendas no varejo | 8880 | c11046 Tipos de índice |
| Volume de vendas no varejo ampliado | 8881 | c11046 Tipos de índice |
| Volume de serviços | 5906 | c11046 Tipos de índice |
| Volume das atividades turísticas | 8694 | c11046 Tipos de índice |
| PIB trimestral a preços correntes | 1846 | c11255 Setores e subsetores |
| Taxa de variação do PIB trimestral | 5932 | c11255 Setores e subsetores |

- **Fora do portal (planejados):** 7 KPIs.

| KPI | Tabela | Motivo |
|---|---|---|
| Produção de origem animal | 74 | variável 106: unidade não é única (sem unidade no Total) |
| Produção da extração vegetal | 289 | variável 144: unidade não é única (sem unidade no Total) |
| Produção da silvicultura | 291 | variável 142: unidade não é única (sem unidade no Total) |
| Volume e receita do transporte de passageiros e cargas | 8695 | sem categoria Total em: Tipos de índice, Atividades de serviços (requer categoria de referência) |
| Área dos biomas | 3926 | tabela não verificada na fonte (nenhum dos níveis ['n1', 'n2', 'n3', 'n7', 'n6'] aceito pela tabela) |
| Emissões de gases de efeito estufa | 5911 | sem categoria Total em: Tipo de gás, Setores de emissão de gases (requer categoria de referência) |
| Municípios atingidos por enchentes ou deslizamentos | 8536 | sem categoria Total em: Ano do desastre natural de maior impacto para o município (requer categoria de referência) |

A "Área dos biomas" (3926) usa o nível Bioma (N123), que a Gold ainda não tem. Ele
pode entrar como os níveis das POF antigas (ADR-0016), mas sem geometria, a menos que
se ingira a malha dos biomas.

## 9. dados.gov.br depende de uma chave do mantenedor

- **Verificado:** toda a API do portal responde 401 sem a chave
  `chave-api-dados-abertos`. O documento OpenAPI diz que a chave de "Consumidor" se
  gera em "Minha Conta", com login gov.br.
- **Para decidir:** gerar a chave e aprovar a Onda 0, que é o inventário só de
  metadados, sem baixar dados. O plano completo está em
  [dados-gov-br-plano.md](../data_catalog/dados-gov-br-plano.md).

## 10. Navegação do portal maior

- **Medido em 2026-11-12:** `/portal/navigation` tem 575 KB, ou 62 KB com gzip, e
  responde em cerca de 25 ms. Antes desta rodada eram 491 KB e 52 KB. O crescimento
  vem das dimensões novas.
- **Para decidir:** o plano de otimização proposto antes da POF.
  - tirar a repetição dos períodos no grão mensal (cerca de −30%);
  - a navegação levar só o resumo de cada KPI e o detalhe vir pela rota `/kpis/{id}`
    quando o KPI é aberto.

  Não é urgente: o JSON é lido em cerca de 1 ms. Mas o tamanho cresce com cada fonte
  nova.

## 11. Achados nos dados desta rodada

- **Planilha do FTP × SIDRA (POF 1995):** a planilha `SIDRA387.XLS` do FTP, de 2016,
  dá 80,96% de despesas correntes no Total das áreas. A tabela 387 do SIDRA, que é o
  que a Gold publica, dá 81,26%. A diferença vale para outros itens (alimentação:
  16,39% × 16,61%). A Gold segue a tabela publicada. Fica a pergunta ao IBGE, se for
  preciso explicar a revisão.
- **Situação do domicílio na PNS:** em diabetes, hipertensão e atividade física
  insuficiente, as categorias urbana e rural vêm vazias nas capitais. A nota da
  tabela diz que a classificação só existe em alguns níveis. O Total está certo, e a
  verificação de reconciliação acusa um aviso.
  - **Para decidir:** limitar esse detalhe aos níveis que a nota indica. O gerador
    ainda não lê a nota.
- **Arredondamento:** diferenças de ±1 entre a soma das categorias e o Total (força
  de trabalho, leite, ovos, nível de instrução) vêm de valores publicados
  arredondados. São avisos, não erros.

## 12. Operação

- **Commit e push:** nada desta rodada foi para o Git. Fica tudo na árvore de trabalho
  da branch `feat/panorama-tier1`, à espera da sua autorização.
- **Produção:** a promoção do release estável para produção (Fase 7) ainda não existe.
  O ciclo local está em [atualizacao.md](../runbooks/atualizacao.md).
- **Bronze órfã:** a primeira carga dos detalhes, com o sufixo numerado `-x1`, deixou
  partições fora da configuração vigente. A Silver as ignora, e apagá-las exige a sua
  aprovação (§28.5).
- **Licenças em revisão:** a licença do SIDRA (`ibge-reuso-com-citacao`) e a do SIM
  continuam `requires_review`, e a Pesquisa Perfil do MJSP segue em revisão.

---

# Rodada de 2026-11-13: dimensão de tempo e tabelas-irmãs

Pedido: aplicar mês, trimestre, semestre e ano a todos os KPIs possíveis (exemplo:
SIDRA 8757, variável 7169) e ampliar o detalhe consultando de novo as tabelas na
origem. Decisões em [ADR-0017](../adr/0017-agregacao-no-tempo-media-e-ultimo-valor.md)
e [ADR-0018](../adr/0018-tabelas-irmas-como-detalhe.md).

| Item | Release `edae0200` (12/11) | Release `7e2eb607` (13/11, ativo no ambiente local) |
|---|---|---|
| Verificações da Gold | 828 aprovadas, 25 avisos | 880 aprovadas, 25 avisos, nenhuma falha |
| Observações | 20.965.098 | 20.980.278 |
| KPIs com mês, trimestre, semestre e ano | 6 (Sinesp, soma) | 26: 10 por soma, 11 por média, 5 pelo último valor |
| KPIs com detalhe / dimensões | 96 / 173 | 97 / 222 |
| KPIs com tabelas-irmãs | — | 15, com 49 tabelas |
| Navegação (`/portal/navigation`) | 575 KB (62 KB gzip) | 663 KB (68 KB gzip), ~90 ms na primeira montagem |
| Testes | 399 Python, 66 portal, 23 e2e | 404 Python, 66 portal, 24 e2e |

Conferência com números oficiais:
- o índice anual de 2024 da PMC (8757, média dos meses) dá 102,92;
- o IPCA anual pelo último mês dá 4,62% em 2023 e 4,83% em 2024, as inflações
  oficiais do ano.

Incidentes da rodada, resolvidos:
- Uma tabela-irmã com a unidade "%", contra "Proporção (%)" na base (6825), foi
  barrada pela verificação de unidade da Gold. Ficou recusada.
- A Gold que falhou chegou a gravar uma coluna nova no fato da pobreza. Para seguir,
  foi preciso o novo `odb gold build --reset-schema fact_sidra_5877`, que só troca o
  schema da tabela nomeada; os releases anteriores continuam lendo as versões
  fixadas.
- Uma irmã mudava a classificação de outro KPI (9730) conforme a ordem de registro.
  Agora as irmãs usam uma classificação curada existente ou uma própria, nunca uma
  compartilhada.

## 13. Média dos trimestres × média anual oficial da PNAD Contínua

- **Decidido:** pessoas ocupadas (4093) e rendimento médio real (5436) ganharam ano e
  semestre pela média dos trimestres. É o que se faz com dados trimestrais quando não
  há outro número.
- **Risco:** o IBGE publica médias anuais oficiais em outras tabelas, como a 10361
  (força de trabalho) e a 10378 (taxas), que podem diferir da média dos trimestres.
- **Para decidir:** usar a média anual oficial no grão "ano", combinando a tabela
  anual com a trimestral numa série, ou manter a média calculada com a nota.

## 14. Taxas sem agregação no tempo

- **Decidido:** desocupação, subutilização, investimento, poupança e variação
  trimestral do PIB ficam só no trimestre. A média de taxas não reproduz a taxa anual
  oficial.
- **Para decidir:** publicar as taxas anuais oficiais (10378 e 10379 para a
  desocupação, por idade e por sexo) como KPI anual próprio ou como o grão "ano" do
  KPI trimestral.

## 15. Último valor em estimativas e índices de preço

- **Decidido:**
  - IPCA, INPC e IPCA-15 (acumulado em 12 meses): o ano é dezembro, ou seja, a
    inflação do ano;
  - IPP (variação sobre o mesmo mês do ano anterior): o ano é a variação
    dezembro/dezembro;
  - LSPA: o ano é a estimativa de dezembro.
- **Para decidir:** confirmar a leitura. Outra opção para o IPCA seria mostrar a
  variação mensal e somar no tempo por composição (produto), o que exigiria uma
  quarta regra.

## 16. Tabelas-irmãs recusadas ou pendentes

| Caso | Motivo | Para decidir |
|---|---|---|
| Rendimento médio (10374 a 10376: cor ou raça, idade, instrução) | a unidade é Mil Reais, contra Reais na base (5436) | conferir se é outra medida (massa?) e se vale como KPI próprio |
| PNAD Contínua anual (10361 a 10363, 10378, 10379) | anuais, e a base é trimestral | ver o ponto 13 |
| POF de 1995, recebimento (434 e 435: idade e instrução do chefe) | o KPI 414 é curado à mão, e o gerador não o trata | curar as duas irmãs à mão (custo pequeno) |
| Arranjos domiciliares (9553 a 9558) | as irmãs são de segurança alimentar, outro assunto | incluir a segurança alimentar por arranjo como KPI próprio |
| População do Censo (608, 2079, 136 e outras) | não avaliadas, porque a 9606 já tem sexo, idade e cor ou raça | avaliar a deficiência (3326) como recorte novo |

## 17. Cruzamentos que só existem em outras tabelas

- **Situação:** com as irmãs, cada KPI da PNS ganhou até cinco recortes, mas um de
  cada vez. Cruzar idade com cor ou raça exigiria uma tabela que publique o
  cruzamento.
- **Para decidir:** levantar no acervo as tabelas com o cruzamento e priorizar as de
  interesse.

## 18. Redefinir o schema de tabela da Gold (operação nova)

- **Feito:** `odb gold build --reset-schema <tabela>` permite remover uma coluna de
  uma tabela da Gold por pedido explícito. Foi usado uma vez, na `fact_sidra_5877`,
  por uma coluna que só existia numa construção que falhou.
- **Para decidir:** se a conferência de schema deve comparar com a última versão
  publicada, e não com a última gravada. Assim, construções que falham não
  "contaminariam" o schema, e a opção manual ficaria para casos raros.

---

# Rodada 3 (2026-11-13): respostas do mantenedor e o que foi feito

Plano vivo e estado de cada item: [continuacao.md](continuacao.md).

| Ponto | Decisão do mantenedor | Feito |
|---|---|---|
| 1. POF a preços de | IPCA geral e por grupo, com "Corrigir por" | ADR-0020: IPCA por grupo em série (655, 2938, 1419, 7060); fator igual à razão do número-índice oficial (2,3641 de 2003 a 2018); seletor no portal (DS 2.3.7) |
| 2. POF 2002, faixas | dimensão própria com o rótulo "Classes de rendimento" | faixas da c12191 renomeadas para a dimensão do fato, cada edição com as suas; decisão nas notas |
| 3. POF 2002, 18 tipos | categorias equivalentes e rótulos limpos | 18 recodificadas (12 iguais no nome, 6 aproximadas, nas notas); rótulos sem numeração (DS 2.3.6) |
| 4. POF 1987 e 1995 | sem hierarquia; explicar o que se mostra | nota "o que se mostra" (percentual do total, com exemplo de Belém em 1995); unidade nas colunas ("Total (%)", "(R$)") e % do Total em KPIs aditivos |
| 5. RM | manter; RIDE depois | mantido |
| 6. Cruzamentos | quanto custa? | ver o ponto 19 |
| 7. Municípios | liberar | carga em andamento (contêiner `odb-carga-municipal`, 31 tabelas, cerca de 1.900 requisições) |
| 8. Legenda e índices | corrigir a escala; índice claro | escala sem colapso (`roundestIn`); legenda "Índice (2022 = 100)" |
| 11, 13, 14. Notas | registrar tudo; taxas também agregadas | nota de método na Gold para todo KPI com agregação; taxas pela média com ressalva; arredondamento; divergências entre fontes; detalhe só nos níveis da nota da tabela |
| 15. IPCA | composição, se a literatura usar | composição (Π(1 + v) − 1), que é o método do IBGE para o acumulado; o ano confere com a inflação oficial |
| 16. Irmãs | listar para conferência | [tabelas-irmas-conferencia.md](../data_catalog/tabelas-irmas-conferencia.md) (67 tabelas) |
| 18. Schema | decidir a melhor estratégia | ADR-0019: conferência contra a última versão publicada |

## 19. Cruzamentos completos: a carga (resposta ao ponto 6)

| Opção | Requisições | Situação |
|---|---|---|
| Município, um detalhe por vez | ~1.900 | em carga |
| Cruzamento completo no município | ~1,33 milhão (só a 4412 teria 38 bilhões de valores) | inviável |
| Cruzamento completo até UF | dezenas a centenas por KPI | viável, KPI a KPI |

**Para decidir:** quais cruzamentos até UF entram primeiro. Proposta:
- óbitos (sexo × idade);
- nascidos vivos (idade da mãe × sexo);
- alfabetização (sexo × cor ou raça × idade);
- PNS (sexo × idade).

## 20. Bronze: o que guardar (resposta ao ponto 12)

Medido em 2026-11-13:
- versões vigentes: 20,3 GB (DATASUS 14,9 GB, IBGE 5,0 GB, MJSP 0,4 GB);
- versões antigas: 0,05 GB.

Com a carga municipal, a Bronze deve passar de 40 GB. O histórico pesa pouco; o
espaço vai quase todo para o vigente.

**Recomendação:**
- **Manter a Bronze inteira na máquina local.** É o original preservado (§6) e
  permite reprocessar sem baixar de novo. O espelho do DATASUS levou cerca de 8 h.
- **Cópia externa só como backup** (§25.1), num disco ou num armazenamento de
  objetos, e não num FTP público. Republicar a Bronze esbarraria nas licenças
  (§23).
- **Produção recebe só o release da Gold**, porque o portal não lê Bronze nem Silver
  (§5.3).

**Para decidir:**
- onde fica o backup da Bronze;
- se a Silver também vai para o backup (ela se reconstrói a partir da Bronze).

## 21. Outras perguntas novas

- **Correção pelo IPCA em outros KPIs em moeda**, como rendimento médio, massa de
  rendimento e custo do m². A configuração é pronta, mas cada caso tem a sua regra de
  data de referência.
- **POF de 1995, irmãs 434 e 435** (idade e instrução do chefe): curar à mão.
- **Equivalências aproximadas da POF 2002**, como "viagens" e "viagens esporádicas":
  confirmar.
- **Registros para o fim do projeto:**
  - licenças;
  - teste de carga extensivo e otimização das consultas;
  - OpenTelemetry com verificação de consultas em produção.
- **Próxima onda:** série histórica do Censo Demográfico (pedido de 2026-11-13) e, em
  seguida, a varredura do dados.gov.br (chave no `.env`, validada).

## Rodada 4 (2026-11-13, tarde)

### Respostas do mantenedor e o que foi feito

| Ponto | Decisão | Feito |
|---|---|---|
| 19. Cruzamentos | até UF: de acordo; município KPI a KPI se a carga for por consulta | a carga é **uma vez por ciclo de atualização**, na ingestão; o portal só lê a Gold. Os 38 bilhões de valores seriam o tamanho da Gold e da Bronze, não um custo por consulta, e isso é que inviabiliza o cruzamento completo no município. Plano: cruzamento completo até UF (C1, depois da carga municipal) e, no município, só cruzamentos escolhidos KPI a KPI, com a carga estimada antes |
| 20. Silver | backup só da Bronze; Silver e Gold se reconstroem | `infrastructure/scripts/backup.sh` (Bronze incremental + dump do catálogo, `--verify` confere o SHA-256 de cada artefato). Primeiro backup: 6.278 artefatos conferidos, 24 GB, em `./backups` (fora do Git; `ODB_BACKUP_DIR` no `.env` muda o destino). Runbook: [backup.md](../runbooks/backup.md) |
| 21. IPCA em outros KPIs | onde houver base | custo do m², PIB anual, PIB trimestral, PIB dos municípios e PAS, com o índice do próprio período (mês ou média do ano). Rendimentos da PNAD ficam de fora, porque a fonte já os deflaciona. ADR-0020, atualização |
| Eixo da série (6579) | 2002 e 2025 sumiam | as pontas centralizam quando cabem; conferido em 153 KPIs (DS 2.3.8) |
| Total na série com detalhe (9606) | tirar das linhas, da legenda e do eixo Y | sai das linhas e da escala; fica no tooltip e na tabela (DS 2.3.8) |
| Tabela em matriz (9606) | grupos pela hierarquia do detalhe, totais de linha e coluna, % com notas | feito (DS 2.3.9); ver abaixo |

### 22. Tabela em matriz: impacto nos KPIs

Conferido na API em 257 combinações (todos os KPIs, sem detalhe, com a primeira
dimensão e com as duas primeiras quando o KPI permite cruzar): nenhuma falha.

- **Linha de totais:** aparece em 213. Falta nos 44 em que não há nível acima (tabela
  já no Brasil) ou o KPI não publica o nível do recorte.
- **% só em KPIs aditivos.** Em taxas, médias e índices, a tabela mostra só os valores.
- **Casos extremos (para decidir):**

  | KPI | Grupos × linhas | O que acontece |
  |---|---|---|
  | POF 1987/1995, despesa (c201 × c210) | 12 × 76 | grupos começam recolhidos ("+ 76 detalhes") |
  | POF 1987/1995, alimentação (c201 × c210alim) | 12 × 75 | idem |
  | Produção das lavouras (c782) | 86 colunas | rolagem horizontal |
  | Nascidos vivos (c232) | 62 colunas | idem |

### 23. Outras formas de organizar a tabela (para decidir)

1. **Cabeçalho em dois níveis (matriz do Power BI):** "Branca" sobre as subcolunas
   "Total | Homens | Mulheres". Cada território ocupa uma linha só e cabe mais na
   tela. Fica bom quando a segunda dimensão tem poucas categorias (sexo, situação).
   Com idade (20 grupos) fica muito larga. Proposta: escolher automaticamente, com o
   cabeçalho em dois níveis até 4 categorias internas e as linhas dentro da célula
   acima disso.
2. **Tabela transposta:** com um território só (clique no mapa), as categorias viram
   linhas e os períodos ou territórios viram colunas. É a leitura natural da pirâmide
   etária e da POF.
3. **Tabela em tela cheia:** um botão que abre a tabela ocupando o painel inteiro. O
   painel atual mostra 1 ou 2 territórios por vez quando as células têm várias linhas.
4. **Ordenar por qualquer coluna:** hoje a ordem é pelo Total ou pelo nome. Ordenar
   pelo valor ou pelo % de uma categoria (ex.: UFs pela % de pretos) exige um parâmetro
   novo na API.

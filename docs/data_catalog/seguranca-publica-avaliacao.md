# Segurança pública (MJSP): avaliação, o que foi feito e o que precisa da sua conferência

- **Data:** 2026-11-12.
- **Pedido:** avaliar e incorporar os dados das três páginas do MJSP, decidindo tudo e
  deixando um registro para conferência.
- **Decisões técnicas:** [ADR-0012](../adr/0012-mjsp-sinesp-vde-seguranca-publica.md).
- **Estado (2026-11-12, depois da sua aprovação):** 6 KPIs publicados no portal, no
  release `2f89b1f9`, no tema "Segurança e vitimização". A licença foi confirmada como
  dados abertos (item 1) e a tabela de cobertura foi aplicada (item 2).

## Resumo

| | Resultado |
|---|---|
| Fontes lidas | 3 páginas do MJSP, sem navegador e só com GET; nenhum bloqueio contornado |
| Bronze | 27 arquivos, cerca de 340 MB, com SHA-256: 12 bases anuais do Sinesp VDE (2015 a 2026), a página de notas metodológicas, 3 PDFs do Mapa da Segurança Pública e 11 bases da Pesquisa Perfil |
| Quarentena | 1 arquivo: o link oficial do Mapa 2024 devolve uma página HTML, não o PDF |
| Silver | Sinesp VDE, 12 anos, cerca de 33,8 milhões de observações (`mjsp/sidra_observation`), por município e UF, mês a mês, 31 eventos |
| Municípios | Todos casam com a DTB; 6 grafias da fonte foram resolvidas como aliases (item 8) |
| Testes | 365 testes Python passando, incluindo 5 novos do Sinesp e 1 do conector |
| Licença | Sinesp VDE: dados abertos do PDA do MJSP, com crédito da fonte (item 1, resolvido) |
| Gold e portal | 6 KPIs (homicídio doloso, feminicídio, latrocínio, estupro, morte por intervenção de agente, roubo de veículo); série mensal de jan/2015 a set/2026; mapa municipal nos três primeiros |

## As três páginas

| Página | O que oferece | O que foi feito |
|---|---|---|
| [Sinesp VDE: base de dados e notas metodológicas](https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/dados-nacionais-1/base-de-dados-e-notas-metodologicas-dos-gestores-estaduais-sinesp-vde-2022-e-2023) | Uma planilha por ano, 2015 a 2026 (cerca de 24 MB cada), e o texto das notas de 10 UFs. O título da página diz "2022 e 2023", mas ela traz 2015 a 2026 | Tudo na Bronze; Silver completa |
| [Pesquisa Perfil das Instituições](https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/pesquisaperfil/pesquisa-perfil-das-instituicoes-de-seguranca-publica-1) | Os links "Base de dados" e "Relatório 2022" respondem 404. Funcionam só as 11 bases de pesquisas anteriores (ZIP), sobre academias, corregedorias, DEAMs, guardas municipais, IML e outras unidades | Bronze; sem Silver (item 9) |
| [Mapa da Segurança Pública 2026](https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/dados-nacionais-1/MAPA-2026/) | Só PDFs: publicação, infográficos e edições anteriores | Bronze (3 PDFs); o de 2024 ficou na quarentena |

## O que há no Sinesp VDE

Cada linha da planilha traz:

- **onde e quando:** UF, município (pelo nome, sem código IBGE), evento e mês;
- **detalhe opcional:** agente, arma ou faixa etária;
- **valores:** vítimas por sexo, total de ocorrências ou peso apreendido;
- **abrangência:** Estadual, Polícia Federal ou Polícia Rodoviária Federal.

Os eventos se dividem em três grupos:

- **Por município, em vítimas, com sexo:** homicídio doloso, feminicídio, tentativas de
  homicídio e de feminicídio, latrocínio, lesão corporal seguida de morte, suicídio,
  mortes a esclarecer e mortes no trânsito (estaduais, e PRF em separado).
- **Por município, em contagem:** mandados de prisão cumpridos.
- **Só por UF:** estupro e estupro de vulnerável (vítimas); roubos e furtos de veículo,
  carga e instituição financeira; tráfico de drogas; apreensões de arma (por tipo) e de
  droga (kg); pessoas desaparecidas e localizadas (por faixa etária); mortes e suicídios
  de agentes do Estado (por agente); ocorrências dos bombeiros.

Séries nacionais na Silver, como soma das UFs. Servem para conferência, não são dado
publicado. 2026 vai de janeiro a setembro.

| Ano | Homicídio doloso | Feminicídio | Latrocínio | Morte por intervenção de agente | Estupro | Roubo de veículo |
|---|---:|---:|---:|---:|---:|---:|
| 2015 | 48.374 | 542 | 2.118 | 2.616 | 33.085 | 233.761 |
| 2017 | 55.881 | 1.048 | 2.349 | 4.220 | 29.423 | 283.787 |
| 2019 | 39.228 | 1.331 | 1.603 | 5.627 | 28.358 | 189.895 |
| 2021 | 39.286 | 1.366 | 1.458 | 6.593 | 21.717 | 141.971 |
| 2023 | 37.331 | 1.478 | 1.004 | 6.406 | 24.062 | 134.108 |
| 2024 | 35.136 | 1.501 | 967 | 6.249 | 25.168 | 126.255 |
| 2025 | 31.518 | 1.578 | 805 | 6.601 | 19.909 | 104.539 |

O feminicídio cresce de 542 para 1.578, mas parte disso é cobertura e não aumento real.
Vários estados só passaram a separar o feminicídio em 2017–2019 (itens 2 e 3).

## O que precisa da sua conferência

Os itens estão em ordem de importância.

### 1. Licença: resolvida, são dados abertos (crédito da fonte)

Você indicou a base legal, e eu a conferi nos atos do DOU e no Plano de Dados Abertos do
MJSP:

- **Decreto nº 8.777/2016:** institui a Política de Dados Abertos.
- **IN nº 47/2025 (INDA):** a licença aberta permite usar, reutilizar e redistribuir,
  "estando sujeito, no máximo, a exigência de creditar a sua autoria ou fonte".
- **Portaria MJSP nº 842/2025:** aprova o PDA 2024-2026. O plano lista "Dados
  Ocorrências Criminais – Sinesp" entre as bases abertas, a mais baixada do ministério
  (p. 27), e no inventário como já aberta (item 76).

Com isso:

- **Sinesp VDE:** licença `mjsp-dados-abertos` (aprovada), datasets `public_authorized`.
  A atribuição a usar é "MJSP/Senasp, Sinesp VDE".
- **PDFs do Mapa e página de notas:** continuam sob a licença do portal (CC BY-ND), por
  serem publicações. Ficam só como documentação.
- **Pesquisa Perfil:** não está no PDA e continua em revisão (item 9).
- **Evidência:** o PDF do PDA foi preservado na Bronze (`mjsp-pda-2024-2026`).

Um ponto para você conferir: o PDA cita "Ocorrências Criminais – Sinesp" (SinespJC e
Sinesp Integração). Tratei as planilhas do VDE, publicadas na mesma seção de estatística
do MJSP, como parte dessa mesma política, conforme a sua orientação.

### 2. Zeros que significam "indisponível": corrigido (aprovado)

A tabela de cobertura está em `configs/sources/coverage/sinesp_vde.toml`. São 15
entradas, cada uma com a UF, os eventos, o período e a nota do gestor que a justifica.
Só entram períodos declarados indisponíveis:

| UF | Indicadores | Período indisponível |
|---|---|---|
| TO | arma apreendida, feminicídio, mandados, morte de/por agente, desaparecidos e localizados | 2015–2018 |
| TO | tentativa de feminicídio, estupro de vulnerável | 2015–2019 |
| TO | bombeiros (5 indicadores) | 2015–2022 |
| TO | apreensão de maconha e cocaína | 2015 a mar/2024 |
| MT | feminicídio, tentativa de feminicídio, morte por intervenção | 2015–2018 |
| BA | feminicídio (até 2016), morte por intervenção (até 2019), tentativa de feminicídio (até 2021), bombeiros (até 2017) | — |
| CE | feminicídio e tentativa (até 2017), mandados (até 2020), atendimento pré-hospitalar (até 2018) | — |
| AL | tentativa de feminicídio | 2015 a abr/2018 |
| RS | mandados (2015); atendimento pré-hospitalar, busca e salvamento, combate a incêndios (até 2017) | — |

A Silver marca esses meses como "não disponível" nas linhas estaduais, e a parte federal
não muda. Assim, por exemplo, o feminicídio no Brasil aparece só a partir de jan/2019,
porque antes disso há estados sem o dado.

Pontos para você conferir:

- **Tocantins, apreensão de drogas:** a nota diz "janeiro de 2015 a março de 2024" no
  título e "a abril de 2024" no texto. Usei março.
- **Alagoas, bombeiros 2015 a set/2017:** a nota diz que o gestor extraiu o que havia no
  sistema antigo, então é dado parcial e não indisponível. Ficou fora da tabela.

### 3. Rupturas de série declaradas pelos gestores

Mesmo com a correção do item 2, algumas séries não são comparáveis no tempo dentro da
mesma UF:

- **Mato Grosso:** até 2018, homicídio doloso inclui os feminicídios.
- **Espírito Santo:** a tentativa de homicídio passou a contar só registros com
  procedimento investigativo instaurado.
- **Amazonas:** mandados de prisão cumpridos só de Manaus.
- **Alagoas:** bombeiros ausentes de 2015 a setembro de 2017.
- **Rio Grande do Sul:** mandados da Polícia Civil ausentes em 2015.
- **Rio de Janeiro:** critérios próprios de contagem de roubos.

Isso precisa aparecer nas notas e limitações de cada KPI quando ele for ao portal. A
página com todas as notas está preservada na Bronze (`mjsp-sinesp-vde`).

### 4. Não é a mesma série do IBGE: entra como KPI novo

O portal já tem "Vítimas de homicídio por 100 mil habitantes" (SIDRA 6606, ODS 16.1.1),
que vem das declarações de óbito (SIM), por residência da vítima. O Sinesp é registro
policial, por local da ocorrência, com cobertura variável por UF.

Pela sua regra da ADR-0011, o Sinesp entra como KPI novo, com fonte própria. A comparação
com o SIM ainda não foi feita, porque a Silver do SIM hoje tem só o capítulo da CID-10. É
preciso acrescentar o grupo "agressões" (X85–Y09), o que fica para depois do espelho do
DATASUS.

### 5. Regras de soma que eu decidi (conferir)

- **Linhas repetidas:** são somadas, como manda a nota da página. São cerca de 580 chaves
  por ano.
- **Total com parcela ausente:** fica ausente. Por exemplo, a cocaína do Tocantins tem a
  parte estadual vazia e a da PF preenchida, e o total fica "não disponível".
- **Série da PF ou da PRF vazia o ano inteiro numa UF:** tratada como "não se aplica" e
  fora da soma (por exemplo, a PF em roubo de veículo). Sem isso, todos os totais de
  roubo de veículo ficariam ausentes. A lista está na verificação `sinesp.federal_empty`.
- **Município ausente:** a UF inclui linhas sem município ("NÃO INFORMADO"). Por isso a
  soma dos municípios fica um pouco abaixo da UF (em 2023, 37.302 contra 37.331
  homicídios).

### 6. 2026 é parcial e as planilhas mudam

2026 vai de janeiro a setembro, e os meses mais recentes de algumas UFs ainda estão sem
dado (por exemplo, mandados e armas apreendidas). A fonte revisa anos anteriores: a
ingestão detecta mudanças pelo checksum e guarda a versão nova sem apagar a antiga. Vale
rodar a ingestão mensalmente.

### 7. Links quebrados na fonte

- **Mapa 2024:** o link devolve uma página HTML. Está na quarentena e não entrou.
- **Pesquisa Perfil:** os links "Base de dados" e "Relatório 2022" respondem 404.

Se quiser, isso pode ser comunicado ao MJSP. Quando os links voltarem, basta rodar a
ingestão de novo.

### 8. Aliases de municípios (conferir os 6)

| Grafia no Sinesp | Município na DTB | Código |
|---|---|---|
| MG / BARÃO DE MONTE ALTO | Barão do Monte Alto | 3105509 |
| MT / SANTO ANTÔNIO DO LEVERGER | Santo Antônio de Leverger | 5107800 |
| RN / ARÊS | Arez | 2401206 |
| RN / AÇU | Assú | 2400208 |
| RR / SÃO LUIZ | São Luiz do Anauá (nome anterior) | 1400605 |
| SE / GRACHO CARDOSO | Graccho Cardoso | 2802601 |

Cada um tem correspondência única na DTB 2025. Ficam em `configs/sources/mj.toml`.

### 9. Pesquisa Perfil: vale a pena?

As 11 bases são dados institucionais por unidade: academias, corregedorias, DEAMs, IML,
guardas municipais e outras. Não são indicadores criminais. Ficaram só na Bronze.
Poderiam virar KPIs de capacidade institucional, por exemplo "municípios com guarda
municipal", mas precisariam de uma avaliação própria, porque cada base tem um leiaute.

### 10. Unidades dos eventos de contagem

As unidades escolhidas foram:

- "Ocorrências" como padrão;
- "Armas" para apreensão de arma de fogo;
- "Mandados";
- "Alvarás";
- "Vistorias";
- "Atendimentos".

Os bombeiros (busca e salvamento, combate a incêndios) ficaram como "Ocorrências". Confira
se os nomes servem para o portal.

## Próximos passos propostos

1. ~~Licença~~: resolvida (item 1).
2. ~~Cobertura~~: aplicada (item 2).
3. ~~Gold e KPIs~~: publicados (6 KPIs; detalhe por sexo pendente).
4. **Detalhe por sexo e mais eventos:** a etapa 2 do KI-007 (Gold por dataset) foi
   feita em 2026-11-12 e o volume deixou de ser obstáculo. Falta dar à dimensão "Sexo"
   da Silver do Sinesp um nome próprio, porque o catálogo já usa "Sexo" para a
   classificação c2 do IBGE (ADR-0012, decisão 7).
5. **Comparação com o SIM:** o espelho do DATASUS terminou e o SIM tem KPI próprio (ADR-0011). A comparação com o Sinesp exige separar as agressões (CID-10 X85–Y09) na Silver do SIM.

## Onde está cada coisa

| O quê | Onde |
|---|---|
| Configuração (29 datasets, licenças, aliases) | `configs/sources/mj.toml` |
| Tabela de cobertura (períodos indisponíveis) | `configs/sources/coverage/sinesp_vde.toml` |
| Indicadores e fatos da Gold | `configs/indicators/demografia/seguranca_sinesp.toml` |
| KPIs do portal e itens `externos` do panorama | `configs/portal/demografia/seguranca_sinesp.toml`, `configs/catalog/panorama.toml` |
| Transformador da Silver | `packages/processing/src/odb_processing/sinesp.py` |
| Verificações (`sinesp.*`) | `packages/processing/src/odb_processing/quality.py` |
| Validação de XLSX e PDF no conector | `packages/ingestion/src/odb_ingestion/connectors/http_file.py` |
| Testes | `tests/unit/processing/test_sinesp.py`, `tests/unit/ingestion/test_http_file.py` |
| Decisões | `docs/adr/0012-mjsp-sinesp-vde-seguranca-publica.md` |
| Como rodar | `docs/runbooks/ingestao.md` (seção MJSP) |

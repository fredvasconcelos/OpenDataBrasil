# Plano vivo da rodada 3 (pedido de 2026-11-13)

Respostas do mantenedor aos pontos críticos de
[2026-11-12-pontos-criticos.md](2026-11-12-pontos-criticos.md). Cada bloco termina
com testes verdes, publicação local e a marcação de "feito" abaixo. Se a sessão
acabar, retome pelo primeiro item não marcado.

Ponto de partida: commit `db711cc` (release local `7e2eb607`).

## Ordem e estado

### Bloco A: base (afeta todos os KPIs)

- [x] **A1 (ponto 18):** feito (ADR-0019, verificação `schema.reset`). conferência de schema contra a última versão **publicada**,
  e não contra a última gravada; `--reset-schema` fica para casos raros. Registrar no
  runbook da Gold e numa ADR.
- [x] **A2 (ponto 8):** feito (DS 2.3.6, `roundestIn`; legenda de índice com a base). escala de cores do mapa. Os quantis colapsam quando há poucos
  valores distintos ou o recorte é pequeno (7362, variável 2503, no Nordeste).
  Corrigir no portal e no DS. O índice deve aparecer claramente como índice (unidade
  na legenda e nas colunas).
- [x] **A3 (pontos 4 e 3):** feito (unidade nas colunas, % do Total, `clean_label`; notas da POF antiga). unidade no cabeçalho das colunas ("Total (%)", "(R$)") e
  % por nível onde o Total é moeda; rótulos limpos, sem a numeração ("2.1.2
  Habitação" → "Habitação"); validar o DS.
- [x] **A4 (pontos 11, 13 e 14):** feito (`level_limits` das notas, nota de método na Gold, taxas pela média com ressalva, arredondamento e divergências). Release `e55f2aac`. notas de método em todos os KPIs:
  - agregações no tempo, arredondamentos e divergências entre fontes;
  - detalhe só nos níveis em que a fonte publica (PNS: situação do domicílio);
  - taxas também com agregação no tempo, com a ressalva.

### Bloco B: preços e POF

- [x] **B1 (ponto 15):** feito (`compound`; IPCA anual = oficial). IPCA, INPC, IPCA-15 e IPP pela composição das variações
  mensais, Π(1 + v) − 1, que é o método do IBGE para o acumulado. Com referências
  nas notas.
- [x] **B2 (ponto 2):** feito (`rename_dimensions` na 2309). faixas de 2002 (c12191) como "Classes de rendimento" da
  2309, com a nota do conceito e da decisão.
- [x] **B3 (ponto 3):** feito (`recode_categories`, 18 equivalências nas notas). equivalência das categorias de 2002 com as de 2008 e 2018
  (por exemplo, "Viagens" e "Viagens esporádicas"), conferida nas notas
  metodológicas, e registro nas notas.
- [x] **B4 (ponto 1), achados de 2026-11-13:**
  - IPCA por grupo em cadeia: 655 (de 1999-08 a 2006-06), 2938 (de 2006-07 a
    2011-12), 1419 (de 2012 a 2019) e 7060 (2020 em diante);
  - variável 63 (variação mensal), c315 com o índice geral (7169) e os 9 grupos (7170,
    7445, 7486, 7558, 7625, 7660, 7712, 7766, 7786), com os mesmos códigos nas quatro
    tabelas;
  - entra como série SIDRA (ADR-0016), no nível Brasil;
  - fator de cada edição: Π(1 + v/100) dos meses entre a data de referência da edição
    (15/01/2003, 15/01/2009, 15/01/2018) e a da edição mais recente.
- [x] **B4 (ponto 1):** feito (ADR-0020, DS 2.3.7; fator = razão do número-índice oficial). Release `2442267a`. POF "a preços de" (o último período da série, que avança
  sozinho), pelo IPCA geral e pelo IPCA por grupo de despesa, com o seletor "Corrigir
  por" (Nominal, IPCA geral, IPCA por grupo) e fórmulas nas notas. Gráficos,
  tooltips e tabelas acompanham.

### Bloco C: volume

Estimativa de 2026-11-13, em 50 tabelas com município e detalhe:
- **Município, detalhe a detalhe:** cerca de 1.911 requisições. A fonte leva de 60 a
  120 s por consulta municipal com categorias, o que dá 30 a 60 h de carga, a rodar
  em blocos e de noite.
- **Cruzamento completo no município:** cerca de 1,33 milhão de requisições (só a 4412,
  casamentos, teria 38 bilhões de valores). Inviável.
- **Cruzamento completo até UF:** viável só nas tabelas pequenas (Censo, POF).
- **Decisão:**
  - liberar o município detalhe a detalhe (C2), com a divisão das categorias em lotes
    de requisição (`category_chunk`);
  - cruzamentos (C1/C3) só até UF e por KPI, em blocos.
- **Swagger do dados.gov.br:** <https://dados.gov.br/swagger-ui/index.html> (documento
  em /v3/api-docs).

- [ ] **C1 (ponto 6), aprovado em 2026-11-13:** cruzamento completo até UF em óbitos
  (sexo × idade), nascidos vivos (idade da mãe × sexo), alfabetização (sexo × cor ou
  raça × idade) e PNS (sexo × idade). Começa depois da C2, porque usa as mesmas
  tabelas.
  - **Desenho:** um conjunto a mais por KPI com todas as classificações cruzadas nos
    níveis 1 a 3 (Brasil, região, UF); os detalhes marginais ficam só no município
    (`extra_set_levels`), para não repetir as linhas de UF.
  - **Portal:** `crossed_levels` no KPI. Nesses níveis, as dimensões se cruzam; no
    município, continua uma por vez.
  - **Município:** cruzamento só KPI a KPI, com a carga estimada antes (ponto 19).
  - **Código feito (2026-11-13):** `cross_sets` no conector (sufixo `-c<cids>`, só
    até UF), `cruzar` no panorama, `crossed`/`crossed_levels` no KPI, API com a regra
    por nível e portal ("Neste nível, os detalhes se cruzam"). Óbitos (sexo × idade),
    nascidos vivos (idade da mãe × sexo) e alfabetização (sexo × cor ou raça × idade)
    marcados. **Falta:** ingerir as partições `-c…` depois da C2, construir a Gold e
    conferir. PNS: sexo e idade vêm em tabelas-irmãs diferentes; o cruzamento exige
    pedir a irmã com o sexo aberto (a decidir).
- [ ] **C2 (ponto 7): em andamento.**
  - **Feito no código:** `category_chunk` no conector, `ALL_MUNICIPAL` no gerador e
    testes verdes.
  - **Carga desde 2026-11-13:** contêiner destacado `odb-carga-municipal`, com 31
    datasets (lista em `docs/relatorios/blocoC-datasets.txt`), rodando
    `odb ingest run`, depois `odb silver build` e `odb gold build`.
  - **Acompanhar:** `docker logs --tail 5 odb-carga-municipal` e
    `docker ps -a | grep carga`.
  - **No fim:**
    1. conferir as falhas (`odb ingest status`);
    2. repetir só os que falharam;
    3. conferir a Gold (`odb quality gold`);
    4. `odb release check` e `odb release activate`;
    5. reconstruir a API e o portal;
    6. rodar os testes e marcar este item.
- [ ] **C2 (ponto 7):** liberar o município em todas as séries (divisão das
  requisições por categoria) e otimizar o modelo para as consultas.
- [ ] **C3 (ponto 17), levantamento feito:** 226 tabelas em [cruzamentos-acervo.md](../data_catalog/cruzamentos-acervo.md). Próximo passo: descritores do bloco 1 (sexo × idade, 87), carga e implementação.
- [ ] **C3 (ponto 17):** levantar no acervo as tabelas com cruzamentos, avaliar a
  carga e implementar em blocos.

### Bloco D: documentação e registros

- [x] **D1 (ponto 16):** feito ([tabelas-irmas-conferencia.md](../data_catalog/tabelas-irmas-conferencia.md)). lista de todas as tabelas-irmãs recusadas ou pendentes, para
  a conferência manual.
- [x] **D2 (ponto 12):** feito (relatório, ponto 20). avaliação da Bronze. Comparar o peso de guardar tudo (FTP
  externo para curadoria) com o de guardar só a vigente.
- [x] **D3 (pontos 9, 10, 12 e 5):** registrado (relatório, ponto 21). a chave do dados.gov.br está no `.env` (`ODB_DADOSGOV_API_KEY`, validada com HTTP 200 em 2026-11-13); a varredura começa depois desta rodada. registros:
  - dados.gov.br no fim;
  - teste de carga e OpenTelemetry no fim do projeto;
  - licenças no fim;
  - RM e RIDE (DF) mais tarde.
- [x] **D4:** feito (relatório, rodada 3). relatório de pontos críticos atualizado, com as perguntas novas.

## Rodada 4 (2026-11-13, tarde): feito

- [x] Eixo da série: pontas centralizadas (2002 e 2025 voltaram; 153 KPIs conferidos). DS 2.3.8.
- [x] Série com detalhe: Total fora das linhas, da legenda e do eixo Y; fica no tooltip (`depth` na API). DS 2.3.8.
- [x] Tabela em matriz: grupos, totais de linha, linha de totais, base do % e grupos recolhidos. DS 2.3.9. Alternativas para decidir no relatório (pontos 22 e 23).
- [x] Correção pelo IPCA em mais 5 KPIs (ADR-0020, atualização).
- [x] Backup da Bronze e do catálogo (`infrastructure/scripts/backup.sh`, runbook `backup.md`); primeiro backup conferido.

## Depois desta rodada (ordem do mantenedor, 2026-11-13)

1. **Série histórica completa do Censo Demográfico,** antes do dados.gov.br.
   **Em andamento (2026-11-13):** ADR-0021 (`edicoes` no panorama, conector com
   `periods`); a 1209 traz 2022 para "População nos Censos" (na Bronze, entra no
   próximo build). Inventário e decisões por KPI em
   [censo-serie-historica.md](../data_catalog/censo-serie-historica.md). Próximos:
   descritores de educação e rendimento (em leitura), edições limpas nos KPIs curados
   (1298, 136, 202) e as equivalências que dependem do mantenedor.
   - Referência:
     <https://www.ibge.gov.br/estatisticas/sociais/trabalho/25089-censo-1991-6.html?edicao=25091&t=series-historicas>
   - A página do IBGE responde 403 a clientes automatizados (§7.3). O levantamento
     vai pelo acervo do SIDRA (tabelas das séries históricas dos Censos), pelos
     descritores e pelo FTP oficial.
2. **Varredura do dados.gov.br** (Onda 0, inventário), com a chave no `.env`.

## Comandos de carga (referência)

```bash
cd ~/dev/OpenDataBrasil
docker compose --profile data --profile web build worker api portal
docker compose --profile data run --rm worker odb ingest run <datasets>
docker compose --profile data run --rm worker odb silver build <datasets>
docker compose --profile data run --rm worker odb gold build
docker compose --profile data run --rm worker odb release check <release_id>
docker compose --profile data run --rm worker odb release activate <release_id> && docker compose --profile web up -d api portal
docker compose --profile test run --rm tests pytest -q   # + portal (vitest) e e2e
```

## Séries compostas de fontes distintas (ADR-0022, decisão de 2026-11-13)

- [x] Regra e nota automática no gerador ("Fontes distintas").
- [ ] Transformações de escala (mil unidades → unidades) e de complemento (100 − x) na
  regra da tabela, com teste.
- [ ] Marcar a troca de fonte no gráfico de evolução e no tooltip.
- [ ] Primeiras séries: esgoto (6805 + 7192), lixo (6892 + 6736) e alfabetização
  (9543 + 9841 + 7113). Plano em
  [fontes-comparaveis.md](../data_catalog/fontes-comparaveis.md).

## Depois que a carga municipal (C2) terminar: roteiro

A imagem do contêiner `odb-carga-municipal` é anterior às mudanças da rodada 4. Ao
fim, ele constrói Silver e Gold com as configurações antigas; o build abaixo refaz com
as atuais (edições do Censo, cruzamentos até UF).

```bash
docker logs --tail 40 odb-carga-municipal          # falhas da ingestão e o build
docker compose --profile data run --rm worker odb ingest status
docker compose --profile data build worker          # imagem com as configs atuais
docker compose --profile data run --rm worker odb ingest run \
  ibge-sidra-9841 ibge-sidra-2609 ibge-sidra-2654 ibge-sidra-9543   # edições e partições -c… (C1)
docker compose --profile data run --rm worker odb silver build --all
docker compose --profile data run --rm worker odb gold build
docker compose --profile data run --rm worker odb release check <release_id>
docker compose --profile data run --rm worker odb release activate <release_id>
docker compose --profile web up -d --build api portal
infrastructure/scripts/backup.sh --verify
```

Conferir no portal: óbitos por sexo × idade na UF (cruzados) e no município (um por
vez); "População nos Censos" até 2022; alfabetização com 2010. Depois, testes
(Python, vitest, e2e) e marcar C1 e C2.

## Comando para retomar numa sessão nova do Claude Code

> Continue o plano em docs/relatorios/continuacao.md a partir do primeiro item não
> marcado. Siga o CLAUDE.md, sem commit até o fim do bloco, e termine cada bloco com
> testes verdes, publicação local e o item marcado.

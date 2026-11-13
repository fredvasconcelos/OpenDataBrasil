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

- [ ] **B1 (ponto 15):** IPCA, INPC, IPCA-15 e IPP pela composição das variações
  mensais, Π(1 + v) − 1, que é o método do IBGE para o acumulado. Com referências
  nas notas.
- [ ] **B2 (ponto 2):** faixas de 2002 (c12191) como "Classes de rendimento" da
  2309, com a nota do conceito e da decisão.
- [ ] **B3 (ponto 3):** equivalência das categorias de 2002 com as de 2008 e 2018
  (por exemplo, "Viagens" e "Viagens esporádicas"), conferida nas notas
  metodológicas, e registro nas notas.
- [ ] **B4 (ponto 1), achados de 2026-11-13:**
  - IPCA por grupo em cadeia: 655 (de 1999-08 a 2006-06), 2938 (de 2006-07 a
    2011-12), 1419 (de 2012 a 2019) e 7060 (2020 em diante);
  - variável 63 (variação mensal), c315 com o índice geral (7169) e os 9 grupos (7170,
    7445, 7486, 7558, 7625, 7660, 7712, 7766, 7786), com os mesmos códigos nas quatro
    tabelas;
  - entra como série SIDRA (ADR-0016), no nível Brasil;
  - fator de cada edição: Π(1 + v/100) dos meses entre a data de referência da edição
    (15/01/2003, 15/01/2009, 15/01/2018) e a da edição mais recente.
- [ ] **B4 (ponto 1):** POF "a preços de" (o último período da série, que avança
  sozinho), pelo IPCA geral e pelo IPCA por grupo de despesa, com o seletor "Corrigir
  por" (Nominal, IPCA geral, IPCA por grupo) e fórmulas nas notas. Gráficos,
  tooltips e tabelas acompanham.

### Bloco C: volume

- [ ] **C1 (ponto 6):** carga dos cruzamentos completos nos KPIs com detalhes
  marginais; implementar os que couberem.
- [ ] **C2 (ponto 7):** liberar o município em todas as séries (divisão das
  requisições por categoria) e otimizar o modelo para as consultas.
- [ ] **C3 (ponto 17):** levantar no acervo as tabelas com cruzamentos, avaliar a
  carga e implementar em blocos.

### Bloco D: documentação e registros

- [ ] **D1 (ponto 16):** lista de todas as tabelas-irmãs recusadas ou pendentes, para
  a conferência manual.
- [ ] **D2 (ponto 12):** avaliação da Bronze. Comparar o peso de guardar tudo (FTP
  externo para curadoria) com o de guardar só a vigente.
- [ ] **D3 (pontos 9, 10, 12 e 5):** registros:
  - dados.gov.br no fim;
  - teste de carga e OpenTelemetry no fim do projeto;
  - licenças no fim;
  - RM e RIDE (DF) mais tarde.
- [ ] **D4:** relatório de pontos críticos atualizado, com as perguntas novas.

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

## Comando para retomar numa sessão nova do Claude Code

> Continue o plano em docs/relatorios/continuacao.md a partir do primeiro item não
> marcado. Siga o CLAUDE.md, sem commit até o fim do bloco, e termine cada bloco com
> testes verdes, publicação local e o item marcado.

# ADR-0036: Gold das contas públicas — modelo, conferência A × C e situação do mês

- **Estado:** aceito (2026-11-22), na CP3 aprovada pelo mantenedor ("Mantém o teto de 10 e
  segue com a CP3").
- **Contexto normativo:** CLAUDE.md §10, §12.6, §13.3, §16 e §17; ADR-0013 (grão mensal),
  ADR-0015 (release), ADR-0023 (regiões pela soma das UFs), ADR-0030 a ADR-0035.

## Contexto

A Silver tem três lentes que nunca se somam (ADR-0030):
- A, transferências: 5,68 milhões de linhas;
- B, pagamentos por favorecido: 24,2 milhões;
- C, execução da despesa: 2,32 milhões.

Os meses vão de 2024-01 a 2026-11. O portal precisa de um mapa e um gráfico com o total e o
"detalhar por", de uma tabela paginada e de um ranking contextual (ADR-0034). Tudo isso sem
transformação pesada na requisição (§5.3.8).

A conferência da CP2 achou meses com a lente A até 17% abaixo do pago na lente C. A
investigação desta CP3 (por mês e ação) mostrou que:
- **FPM (ação 0045):** a lente A é igual à lente C até a terceira casa decimal em 30 dos 35
  meses. As exceções são 2025-07, 2025-09, 2025-12, 2026-07 e 2026-09, os meses das
  parcelas adicionais de 1% do FPM (CF, art. 159, I, "d", "e" e "f"). Faltam de R$ 7,8 bi a
  R$ 10,1 bi por mês, e o número de linhas (5.570, uma por município) não muda: a parcela
  adicional não está distribuída por município na lente A. Em 2024, as parcelas adicionais
  estavam presentes;
- **lente B:** o lançamento agregado `TN0000001` (Coordenação-Geral de Transferências
  Intergovernamentais) é exatamente 1,2500 × (FPM + FPE da lente A) nos meses comuns. Ou
  seja, a lente B registra o valor bruto, e a lente A o líquido da retenção de 20% para o
  FUNDEB. Nos meses das parcelas adicionais, a razão vai a 1,52–1,71: a lente B tem a
  parcela, e a lente A não;
- **outras lacunas:** o salário-educação (0369) está ausente da lente A em 2025-12 e
  2026-03, o Piso da Atenção Primária (219A) está parcial em 2025-07, e a compensação
  financeira (0547) está parcial em 2025-12;
- **ruído:** fora dessas lacunas, a razão por ação tem mediana 1,000. A falta mensal fica
  em até 2,4% nos meses sem lacuna conhecida e em 6,7% ou mais nos meses com lacuna.

## Decisões

1. **Escopo próprio `contas`, com release próprio.** A Gold das contas não entra no
   catálogo de indicadores do painel. Ela tem builder próprio (`ContasGoldBuilder`), com o
   mesmo ciclo do `GoldBuilder`:
   - impressão digital: Silvers fixadas, contratos e parâmetros;
   - `skipped` quando nada muda;
   - verificações bloqueantes antes de qualquer release;
   - release por manifesto, validado e ativado à parte (§12.6).

   Comando: `odb gold build --scope contas`.

   | Tabela | Grão | Uso |
   |---|---|---|
   | `dim_recipient` | código + nome do favorecido (ADR-0031, decisão 3) | nome, classe, natureza, CNAE e sede do cadastro PJ |
   | `dim_management_unit` | órgão + UG | nome vigente, órgão superior (das lentes B e C), meses de vigência |
   | `dim_budget_action` | exercício + função + subfunção + programa + ação | funcional-programática por PPA |
   | `dim_expense_nature` | grupo + modalidade + elemento | categoria econômica da lente C |
   | `dim_amendment_author` | autor de emenda (lente C) | — |
   | `fact_federal_transfer` | mês x território x tipo x tipo de favorecido x favorecido x UG x ação x natureza | lente A, `source_lines` conta as linhas da fonte |
   | `fact_federal_payment_recipient` | mês x território da sede x favorecido x UG | lente B (o grão já é o da fonte: 24,2 M linhas) |
   | `fact_federal_budget_execution` | mês x UG x ação x natureza x autor | lente C, seis fases |
   | `agg_contas_territory` | lente x nível x território x mês x dimensão x categoria | mapa e gráfico, com o total e o "detalhar por" |
   | `agg_recipient_rank` | lente x território x ano x posição | ranking contextual, os 1.000 maiores (100 páginas de 10) |
   | `agg_transfer_reconciliation` | mês x ação | conferência A x C |
   | `agg_contas_period_status` | lente x mês | aberto, incompleto ou fechado |
   | `dim_geography`, `bridge_geography_ancestor`, `dim_period`, `bridge_period_ancestor` | os mesmos do painel | cópia do escopo, para o release ser autossuficiente |

   - **Chaves inteiras** nos fatos para o texto repetido; o texto fica nas dimensões. As
     chaves valem dentro do release, que fixa todas as tabelas juntas (§17.4). A chave
     natural continua gravada em cada dimensão.
   - **Períodos no formato da Gold** (`2024M01`, ADR-0013). Trimestre, semestre e ano
     existem só na `dim_period`, e os valores deles são somados na consulta.
   - **Território:** a linha com município entra nos quatro níveis. Sem município, ela
     entra na UF, na região e no Brasil. Sem UF válida (exterior, sem informação,
     múltiplo), só no Brasil. A região é a soma das UFs (ADR-0023).
   - **Particionamento:** os fatos são particionados por ano; os agregados, por lente e
     nível.
2. **Conferência A x C por mês e ação.** A lente A (pagamento realizado) é comparada com o
   pago mais os restos a pagar pagos da lente C nas modalidades de aplicação de
   transferência (30, 31, 35, 36, 40, 41, 45, 46, 50, 60, 70, 71 e 80). A tabela de
   conferência mostra, por ação e mês, os dois valores, a falta e a situação:
   - `conferido`: diferença até 1% ou R$ 1 milhão, o que for maior;
   - `abaixo_da_execucao` ou `acima_da_execucao`;
   - `ausente_nas_transferencias` ou `ausente_na_execucao`.
3. **Situação do mês** (`agg_contas_period_status`):
   - `aberto`: o último mês publicado de cada lente, que a fonte ainda completa;
   - `incompleto` (só na lente A): a falta passa de **5%** do pago na lente C. O limite fica
     entre o maior ruído medido (2,4%) e a menor lacuna real (6,7%). A linha traz as
     principais ações em falta;
   - `fechado`: os demais meses. Nas lentes B e C, isso significa "mês encerrado, sem
     conferência com outra base nesta versão".

   O portal mostra "(parcial)" nos meses `aberto` e `incompleto`, com a nota e as ações em
   falta (ADR-0033, decisão 4). Hoje, a lente A tem 7 meses incompletos (2025-07, 2025-09,
   2025-12, 2026-03, 2026-07, 2026-09 e 2026-10) e 2026-11 aberto.
4. **A lacuna não é preenchida.** A lente C não tem município (ADR-0032, decisão 6). Repartir
   a parcela adicional do FPM pelos municípios seria uma redistribuição sem fonte (§13.3).
   O mapa municipal desses meses fica abaixo do valor real, e o aviso diz isso. O caminho
   para fechar a lacuna é uma segunda fonte oficial por município: a distribuição do FPM
   do Tesouro Nacional, como já previsto no plano (seção 8, "FPM/FPE x Tesouro"), com ADR
   próprio. As revisões retroativas da CGU (ADR-0030, decisão 4) também podem fechá-la, e
   a conferência mostra isso no ciclo seguinte.
5. **Ranking** (ADR-0034, decisão 4):
   - os 1.000 maiores destinatários por lente, território (os quatro níveis) e ano, com o
     total de destinatários do território;
   - ficam fora: lançamentos agregados, unidades gestoras federais, instituições
     financeiras, sigilosos e sem informação (ADR-0031, decisão 2);
   - o exterior entra (é um destinatário real);
   - empate: a ordem do código e do nome decide.

   Filtros e "detalhar por" no ranking são consultas sobre o fato, paginadas (CP4).
6. **Homônimos sem CNPJ na tela.** A `dim_recipient` traz a sede do cadastro PJ (município e
   UF, como na fonte). O portal pode mostrar "Fundo Municipal de Saúde (Sousa/PB)" sem
   mostrar o CNPJ (ADR-0034, decisão 6). Na PB, há vários fundos com o mesmo nome no ranking.
7. **Verificações bloqueantes:**
   - contrato, nulos e chave de cada tabela;
   - chave natural única do favorecido;
   - integridade de território e período;
   - hierarquia territorial;
   - **fidelidade:** soma e linhas de cada mês iguais às da Silver, em decimal exato, nas
     três lentes e nas seis fases;
   - cada dimensão do "detalhar por" soma o total do território e do mês.

   A conferência A x C é aviso: a lacuna é da fonte, e a Gold a expõe.
8. **KPIs do painel adiados.** O plano previa KPIs em `indicator_observation`. O bloco 2 lê
   os próprios agregados (ADR-0034), e a integração com o bloco 1 (por exemplo,
   transferências per capita no painel) fica para depois da CP4, com aprovação.

## Consequências

- A Gold do escopo ocupa 906 MB; a construção leva 1 min 37 s, com pico de 11,4 GB no
  worker (2026-11-22).
- O release candidato fica `validated`. A ativação só acontece com a API da CP4 e a
  aprovação do mantenedor.
- Mudar o limite (5%), a tolerância, as modalidades ou as exclusões do ranking muda a
  impressão digital, e a Gold é refeita.

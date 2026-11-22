# ADR-0030: Contas públicas federais — fonte, ingestão em lote e três lentes

- **Estado:** aceito (2026-11-22) pelo mantenedor nas decisões D1, D2 e D4 do plano de
  inserção de contas públicas (documento de operação). A licença (decisão 6) **aguarda
  aprovação**.
- **Contexto normativo:** CLAUDE.md §3.3, §5.3, §7.3, §7.6, §10.7, §17, §23 e §26;
  ADR-0015 (release estável), ADR-0025 (Fábrica e Vitrine) e ADR-0028 (licenças).

## Contexto

O portal ganha um segundo bloco, "Transparência de contas públicas", para responder:
**para onde vão os recursos federais enviados a estados, municípios e regiões; quais
programas e órgãos os usam; quem os recebe.** A fonte é o Portal da Transparência (CGU).

Medido em 2026-11-22 (amostras de 2025-10 e 2014-01):

- a API (`api.portaldatransparencia.gov.br`) devolve 15 registros por página, com os
  mesmos campos do arquivo de download. Um mês do Brasil em `recursos-recebidos` daria
  cerca de 51 mil requisições;
- os downloads mensais (`dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/`)
  vão de 2014-01 até o mês corrente, com layout idêntico em 2014 e 2025;
- a CGU **regenera arquivos antigos**: o `Last-Modified` de 2014-01 é de novembro de 2026;
- o arquivo "Recebimento de recursos por favorecido", sozinho, dá uma resposta errada:
  o FPM e o FPE aparecem num único pseudofavorecido (`TN0000001`, no DF), há lançamentos
  contábeis agregados (`RB0000003` com +R$ 198,6 bi; quatro linhas `RB` com −R$ 452 bi) e
  bancos aparecem no lugar dos beneficiários;
- o portal da CGU respondeu HTTP 202 sem corpo a leituras seguidas de páginas.

## Decisões

1. **Ingestão em lote na Fábrica (D1).** Os arquivos de download são a fonte dos dados.
   A Vitrine nunca chama a CGU. A API é usada só na Fábrica, para:
   - catálogos sem download equivalente (`orgaos-siafi`, `despesas/funcional-programatica/*`,
     `despesas/tipo-transferencia`);
   - conferências por amostragem na reconciliação.

   A chave (`ODB_PORTAL_TRANSPARENCIA_API_KEY`) nunca vai para a Vitrine.
2. **Três lentes, que nunca se somam (D2):**

   | Lente | Base de download | Responde | Território |
   |---|---|---|---|
   | **A. Transferências** | `transferencias` (Recursos transferidos) | quanto a União pagou a cada ente, fundo ou entidade, por tipo, função, programa e ação | município do favorecido, por código SIAFI |
   | **B. Pagamentos a favorecidos** | `despesas-favorecidos` | quem recebeu pagamento federal, de qual órgão e UG | sede cadastral do favorecido (UF + nome) |
   | **C. Execução orçamentária** | `despesas-execucao` | empenhado, liquidado, pago e restos a pagar por órgão, programa e modalidade | localizador (não usado no mapa) |

   - A lente A é a resposta principal à pergunta. A lente C é controle e contexto.
   - Uma transferência ao Fundo Municipal de Saúde aparece em A e, como pagamento ao CNPJ do
     fundo, em B. Somar lentes conta o mesmo dinheiro duas vezes.
   - A interface mostra uma lente por vez, com nome e nota próprios.
3. **Piloto de 24 meses (D4):** 2024-01 a 2025-12, nas três lentes e nos cadastros de
   apoio. O histórico desde 2014 entra só depois da reconciliação do piloto (etapa CP6).
4. **Revisão retroativa.** A cada ciclo, o conector confere o ETag e o checksum de
   **todos** os meses publicados. Só reprocessa os meses cujo conteúdo mudou e registra a
   diferença no relatório do ciclo (§7.6). Se só os metadados do zip mudarem, compara-se o
   checksum do CSV interno.
5. **Conector genérico.** Um conector `http_periodic` (um arquivo por período, URL com
   `{AAAAMM}` ou `{AAAAMMDD}`, requisição condicional por partição) estende o `http_file`.
   Nada da CGU vai para o núcleo (§3.3). Os downloads são feitos um por vez, com espera
   entre eles e retentativa com recuo. Uma resposta 202 vazia ou um bloqueio **não é
   contornada** (§7.3): a execução para e é registrada como falha.
6. **Licença (aguarda aprovação).** No dados.gov.br, o conjunto "Despesas Públicas" da CGU
   (`16337f91-62b1-405f-89d6-f8f52863b659`, com as quatro bases de despesa) está marcado
   como `dadosAbertos: Sim`, mas com `licenca: notspecified`. **Proposta:** registrar
   `cgu-dados-abertos` com a mesma base da `mjsp-dados-abertos` (Política de Dados Abertos,
   Decreto nº 8.777/2016, e definição de licença aberta da INDA), crédito obrigatório
   "Fonte: Portal da Transparência/CGU" e `review_status = "requires_review"` até a
   aprovação do mantenedor. Os mesmos passos valem para a TABMUN do Tesouro (CKAN:
   "License not specified") e para o cadastro de ações do SIOP (ADR-0035). Sem licença
   aprovada, nada é publicado.

## Consequências

- **Reaproveitado sem mudança:** Bronze, watermark, quarentena, `DeltaWriter`, contratos
  Silver, release, manifesto e health.
- **Domínio novo na Gold:** fatos no grão de entidade (ADR-0034), dimensões de órgão e de
  classificação orçamentária e agregados oficiais.
- **Os KPIs territoriais vão para `indicator_observation`**, para reaproveitar o mapa, a
  série e a exportação.
- **Modelo com códigos inteiros desde o início:** nomes ficam nas dimensões. O texto
  repetido por linha é a causa conhecida dos estouros de memória (replanejamento 2026-11).
- **Volume estimado** (a medir no piloto): Bronze de cerca de 4 GB em zip para o histórico
  completo das três lentes; 80 a 120 milhões de linhas na lente B.

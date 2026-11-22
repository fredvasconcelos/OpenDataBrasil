# ADR-0033: Fases da despesa, transferências e valores em aberto

- **Estado:** aceito (2026-11-22), a pedido do mantenedor: "ainda que tenhamos o
  orçamento enviado, nem todas as despesas foram executadas [...] consultar a LDO para
  entender como funciona o pagamento".
- **Contexto normativo:** CLAUDE.md §9.4, §14.1, §16 e §19.4; ADR-0013 e ADR-0023,
  decisão 2 (período parcial); ADR-0030.

## Contexto (textos conferidos em 2026-11-22)

**Fases da despesa — Lei nº 4.320/1964:**
- art. 35, II: pertencem ao exercício "as despesas nêle legalmente empenhadas";
- art. 58: o **empenho** "cria para o Estado obrigação de pagamento pendente ou não de
  implemento de condição";
- art. 63: a **liquidação** "consiste na verificação do direito adquirido pelo credor";
- art. 64: a **ordem de pagamento** determina que a despesa seja paga;
- art. 36: **restos a pagar** são "as despesas empenhadas mas não pagas até o dia 31 de
  dezembro", processados (já liquidados) ou não processados.

**LDO 2026 — Lei nº 15.321, de 31/12/2025:**
- **art. 150, § 1º:**
  - execução física é a obra, o bem ou o serviço;
  - execução **orçamentária** é "o empenho e a liquidação da despesa, inclusive a sua
    inscrição em restos a pagar";
  - execução **financeira** é "o pagamento da despesa, inclusive dos restos a pagar
    inscritos até o exercício financeiro anterior";
- **art. 97:** a transferência voluntária é a entrega a título de "cooperação, auxílio ou
  assistência financeira", que "não decorra de determinação constitucional, legal ou que
  seja destinada ao SUS" (mesma definição da LRF, art. 25). Para despesas de capital, o
  ente recebedor dá contrapartida financeira, com limites por porte e região (§ 3º);
- **art. 98:** a entrega da transferência voluntária "é caracterizada no momento da
  assinatura do convênio [...], não se confundindo com as efetivas liberações financeiras,
  as quais devem obedecer ao respectivo cronograma de desembolso";
- **art. 72:** cronograma mensal de desembolso por órgão (LRF art. 8º). O § 21 prevê o
  pagamento, até o fim do 1º semestre, de 65% das emendas individuais e de bancada de
  execução obrigatória destinadas às transferências especiais (CF art. 166-A, I) e aos
  repasses fundo a fundo de saúde e assistência social;
- **arts. 75 e 76:** a execução das despesas discricionárias segue limites fiscais
  (limitação de empenho e de movimentação financeira) e para em impedimentos de ordem
  técnica (projeto, licença ambiental, capacidade do ente).

**Nos dados (dicionários da CGU):**
- a lente A é o **pagamento realizado** ("código do favorecido do pagamento realizado");
- a lente B é o pagamento recebido;
- a lente C traz as seis medidas: empenhado, liquidado, pago, restos a pagar inscritos,
  cancelados e pagos.

## Decisões

1. **Cada valor diz a sua fase.** Todo número do bloco 2 é rotulado como empenhado,
   liquidado, pago ou restos a pagar pagos. As lentes A e B são **pagamentos da União**.
   A lente C mostra as fases lado a lado. Nunca se soma empenhado com pago.
2. **"Enviado" não é "gasto pelo município".** O que a União pagou ao ente (lente A) é
   receita do ente. Como ele a executa (empenho, liquidação e pagamento municipais) não está
   nas bases federais: fica no SICONFI/Tesouro (RREO, DCA/Finbra), uma fonte futura com
   ADR próprio. A ficha do território diz isso em nota fixa.
3. **Natureza da transferência na interface:**
   - **constitucionais e legais** (FPM, FPE, FUNDEB, royalties, salário-educação): são
     automáticas e têm critério de rateio em lei;
   - **fundo a fundo** (SUS, SUAS): são regulares e automáticas, para os fundos;
   - **voluntárias** (convênios e contratos de repasse): o valor celebrado ≠ o valor
     liberado (art. 98), e a liberação segue o cronograma;
   - **transferências especiais** (emendas, CF art. 166-A, I): seguem o calendário do
     art. 72, § 21.

   Cada uma tem verbete no dicionário (ADR-0035).
4. **Valores em aberto:**
   - **mês corrente:** o último mês publicado aparece como "(parcial)" e o ano como
     acumulado, com o status `partial_period` (ADR-0023, decisão 2);
   - **exercício aberto:** na lente C, o ano corrente mostra empenhado − pago como "a pagar
     no exercício", e os restos a pagar inscritos aparecem à parte;
   - **revisões:** um mês reprocessado por revisão retroativa (ADR-0030, decisão 4) leva a
     nota "revisado pela fonte em DD/MM/AAAA" no release seguinte;
   - **voluntárias:** quando a base de convênios entrar (onda futura), a ficha mostra o
     celebrado, o liberado e o saldo. Nesta fase, só o liberado (pago) aparece.
5. **Restos a pagar:** o "pago" de um mês inclui só o pagamento do exercício. Os restos a
   pagar pagos são uma medida separada na lente C. A lente A já é o fluxo de caixa
   pago, de qualquer exercício de origem; a nota da lente explica isso.
6. **Valores nominais.** A correção pela inflação depende do IPCA, cuja precisão está em
   revisão (lote N5). Ela entra depois, por ADR. Toda série mostra "valores nominais".

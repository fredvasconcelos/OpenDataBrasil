# Contas públicas — medidas e dicionário em escopo próprio

26/11/2026. O bloco de contas tem manifesto próprio e não integra os 291 KPIs
estatísticos configurados. A revisão não acrescenta seus valores àqueles indicadores.
O registro anterior fixa a candidata `e8bb048c`, validada e não ativada; o banco e
a API não puderam ser reconferidos nesta execução. Esta página complementa o
[catálogo de referências existente](../contas-publicas.md), sem repetir sua varredura.

| Medida / lente | O que mede / uso | Unidade e tempo | Universo e limite |
|---|---|---|---|
| Transferências — A | Pagamento federal transferido ao ente, fundo ou entidade; acompanhamento territorial dos repasses | R$ nominais, mês da transferência | Território do favorecido; não execução do gasto pelo município. |
| Recebimentos — B | Pagamentos recebidos pelos favorecidos e sua vinculação ao órgão/UG | R$ nominais, ano/mês do lançamento | Sede do favorecido; pode conter intermediários/agregados. Não se soma à A. |
| Empenhado — C | Compromisso orçamentário no exercício | R$ nominais; lançamento/exercício | Não comprova liquidação nem pagamento. |
| Liquidado — C | Verificação do direito do credor | R$ nominais | Não equivale ao pago. |
| Pago — C | Pagamento do exercício | R$ nominais | Restos a pagar pagos são fase separada. |
| RP inscritos — C | Obrigações empenhadas não pagas ao encerramento, inscritas em restos a pagar | R$ nominais; exercício de origem precisa ser explícito | Não somar com empenhado/pago para obter uma despesa total. |
| RP cancelados — C | Cancelamento de restos a pagar | R$ nominais | Não interpretar como novo pagamento negativo sem o sinal e a regra da base. |
| RP pagos — C | Pagamento de obrigação de exercício anterior | R$ nominais | A lente A pode incorporar esse fluxo de caixa; não adicionar de novo entre lentes. |
| FPM / complemento Tesouro em A | Parcela municipal proveniente da segunda fonte, identificada no método do portal | R$ por município/mês; valores líquidos conforme contrato | Não é um quarto total somável à lente A já complementada. |

As três páginas CGU foram reabertas nesta revisão, sem download de bases:
[Recursos transferidos](https://portaldatransparencia.gov.br/dicionario-de-dados/recursos-transferidos),
seção COLUNA/DESCRIÇÃO, campos ANO/MÊS, UF, MUNICÍPIO SIAFI e valor;
[Recebimento por favorecido](https://portaldatransparencia.gov.br/dicionario-de-dados/recursos-por-favorecido),
campos código/nome, localização, órgão/UG, ano/mês do lançamento e valor;
[Execução da despesa](https://portaldatransparencia.gov.br/dicionario-de-dados/execucao-despesa),
campos de fases e classificação. Edição dinâmica, sem número de versão do
dicionário; consulta em 26/11/2026. Esses campos sustentam a correspondência de
tempo/localização, sem comprovar a destinação física de cada pagamento.

O código SIAFI não é IBGE. Na A, a ponte TABMUN e as correções aprovadas têm
linhagem própria; na B, o casamento de sede não prova local da obra/serviço.
Programa/ação precisam do exercício/PPA e da descrição oficial correspondente;
nome sozinho não define finalidade, público-alvo ou base legal. Classes de
favorecidos do portal devem permanecer distintas da natureza jurídica oficial.
Prefixos e códigos especiais sem significado oficial confirmado continuam lacunas.

Métodos do portal já documentados, sem alteração nesta revisão:

- [ADR-0033](../../adr/0033-fases-da-despesa-e-valores-em-aberto.md): fases, valores nominais e períodos abertos.
- [ADR-0036](../../adr/0036-gold-das-contas-publicas.md): meses, agregação territorial, reconciliação A × (C pago + RP pago), tolerâncias e completude.
- [ADR-0038](../../adr/0038-fpm-do-tesouro-como-segunda-fonte.md): complemento FPM `Tesouro − CGU` somente nos meses admissíveis, marcado por origem; não redistribuição inferida.

Fonte independente da segunda base: [Tesouro, Transferências obrigatórias por município](https://www.tesourotransparente.gov.br/ckan/dataset/3b5a779d-78f5-4602-a6b7-23ece6d60f27),
seções descrição/licença/início dos dados, consulta indexada em 26/11/2026;
[metadados COINT](https://www.tesourotransparente.gov.br/ckan/dataset/3b5a779d-78f5-4602-a6b7-23ece6d60f27/resource/a3bee117-d467-4374-aefe-bb29b9698c42/download/Metadados---Transferencias-Obrigatorias-da-Uniao---por-Municipio.pdf),
Caracterização dos eventos e alterações de retenção, edição do documento não
reconfirmada. A existência de série desde 1996 não publica esse histórico no portal.

Na futura planilha, cada linha identifica lente, fase, ano/exercício, mês,
territorialidade e origem CGU/Tesouro. Meses abertos/incompletos e complemento
precisam de nota e método. Ranking anual e tabela paginada não são extrato completo.
A rota genérica `/api/v1/exports` é para KPIs do painel; a inspeção das rotas
de contas não encontrou exportador equivalente. Não anunciar Excel das contas
como implementado. Exportar identificadores pessoais continua sujeito ao contrato
próprio: a API atual não entrega CPF mascarado/CNPJ, e a planilha não deve reconstruí-los.

**Lacunas:** catálogo completo de verbetes por código/exercício (ADR-0035), leitura
do MTO/portarias e das leis em suas edições aplicáveis, licenças/citações por base,
regra por categoria/território/mês e conferência ao vivo do manifesto. As referências
normativas da ADR-0033 foram aproveitadas como histórico, sem anunciar revalidação
legal independente nesta execução.

A ampliação desta revisão está em [Códigos e base legal](codigos-contas.md), com
[matriz de 26 domínios por exercício](cobertura-codigos-contas.csv), manifestos
cadastrais e [caso obrigatório 0A53](acao-0A53.md). As relações normativas ali
conferidas não completam a legislação de todas as origens ou o catálogo integral
de códigos; as pendências desta página continuam explícitas.

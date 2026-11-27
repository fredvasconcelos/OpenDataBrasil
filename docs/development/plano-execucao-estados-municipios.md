# Plano de inserção da execução de estados e municípios

Pedido do mantenedor em 27/11/2026: inserir agora a execução federal e seu localizador
orçamentário da CGU; preparar a integração posterior da execução própria dos entes.
Este plano complementa [aplicação pelo recebedor](plano-aplicacao-pelo-recebedor.md).
Não anuncia cobertura estadual/municipal já implementada.

## Objetivo e medidas distintas

1. Execução federal: seis fases da União, com localização orçamentária quando publicada.
2. Execução do ente: orçamento e despesa do estado/município, com seu próprio universo.
3. Aplicação de repasse: subconjunto com ligação demonstrada entre recebimento e execução.

Essas medidas não se somam nem se substituem. Empenhado, liquidado, pago, restos a
pagar, dotação inicial e atualizada são campos independentes. O localizador da CGU
não mede execução local. A existência de um portal também não comprova acesso
automatizado, completude histórica, licença ou identificação de cada repasse.

## Fontes oficiais iniciais e alcance comprovado

- [Siconfi/MSC — Tesouro Nacional](https://www.tesourotransparente.gov.br/temas/contabilidade-e-custos/relatorios-contabeis-e-fiscais-de-estados-df-e-municipios): informações contábeis e fiscais dos entes que entregaram declarações; a página vincula a documentação da API. Inventariar declarações e exercícios realmente disponíveis, incluindo retificações.
- [PNTP — Atricon](https://pntp.atricon.org.br/) e [resultados oficiais de 2026](https://atricon.org.br/blog/pntp-2026-conheca-o-desempenho-dos-portais-publicos-da-sua-regiao/): ponto de partida para localizar portais e evidências de transparência. A avaliação não integra os dados financeiros nem certifica uma API.
- Portais oficiais do Executivo estadual/municipal e Tribunais de Contas: confirmar a autoridade pelo site institucional, registrar o link exato e o acesso oferecido. Não inventar domínio ou endpoint a partir do nome do ente.
- Transferegov: usar instrumentos e chaves reais para o subconjunto rastreável, conforme o plano de aplicação. Não extrapolar transferências discricionárias para todas as despesas.

Fontes consultadas em 27/11/2026. Não foi feita uma varredura de todos os portais.
O inventário terá como alvo todos os entes da referência territorial oficial do
exercício, sem pressupor que todos os links e arquivos estejam disponíveis.

## Etapas e critérios de conclusão

| Etapa | Entrega concreta | Critério de conclusão | Aprovação |
|---|---|---|---|
| E0 — Inventário | Matriz ente × poder × exercício × fonte; URLs oficiais, descritor, licença, formato, calendário, revisões e limites | Cada registro tem evidência; indisponíveis e não pesquisados são distintos | Mantenedor revisa a matriz e o piloto |
| E1 — Base nacional | Avaliação dos relatórios e MSC/Siconfi, dicionários e contas por edição | Universo, nível de detalhe e cobertura de declarações medidos por ente/período | Contrato semântico antes de modelagem |
| E2 — Piloto local | Um estado e um município, depois portes e fornecedores distintos; sugestão inicial PB/Guarabira pela continuidade das contas | Captura pequena e reprodutível, com conferência na consulta oficial; seleção ainda sujeita ao mantenedor | Mantenedor escolhe/aceita o piloto |
| E3 — Contratos e conectores | Identidade do ente, órgão/fundo/UG, exercício, documento/item/evento, fontes/destinações, fases, retificações e linhagem | Sem chave inventada, sobreposição de snapshots ou associação por nome semelhante | ADR e contrato por família de fonte |
| E4 — Gold candidata | Execução própria do ente em Delta, separada das lentes federais | Reconciliação exata, saldos e sinais; cobertura e limitações explícitas | Aceite técnico sem ativação |
| E5 — Ligação com repasses | Piloto instrumento/receita → execução usando chaves oficiais | Mesmo universo e janela; saldos anteriores, contrapartida, rendimentos, devoluções e intermediários tratados | Método concreto aprovado |
| E6 — Exposição gradual | API, exportações e catálogo com disponibilidade por ente/período | Testes de contrato, privacidade, acessibilidade e comparação com a fonte | Revisão local; publicação por pedido próprio |

## Inventário e captura

Guardar, por fonte e exercício: código oficial do ente e sua vigência; poder e esfera;
órgãos e fundos incluídos; URI institucional e URI de acesso; data de verificação;
licença; descritor/dicionário/versão; unidade, moeda e precisão; identificadores
originais; primeiro/último período e calendário esperado; atualizações e retificações;
formato, paginação, limites, bloqueios, hashes e contagens. Portal encontrado,
arquivo disponível, dado reconciliado e vínculo de repasse são quatro estados distintos.

Priorizar arquivos/API oficiais e um conector comum quando o contrato for equivalente.
Respeitar autenticação, CAPTCHA, bloqueios e condições de uso; registrar o impedimento,
sem contorno. Downloads isolados; leitura em Python `-I`. Não começar captura massiva
apenas por este plano.

## Regras a definir antes dos KPIs locais

- Identidade por códigos oficiais, CNPJ institucional e tabelas de correspondência
  documentadas; tratar fundos e mudanças históricas. Nome semelhante não é chave.
- Identificar fluxo versus saldo/acumulado e edição da declaração. Snapshots acumulados
  não se somam entre meses. Retificações substituem a edição correta, com originais
  preservados e trilha de revisão.
- Reconciliar dotação, empenho, liquidação, pagamento e restos a pagar separadamente,
  incluindo anulações, estornos e devoluções. Não reduzir negativos a zero.
- Manter divergências de conceito/abrangência como diagnóstico; não forçar igualdade
  entre Siconfi, portal local e CGU quando os universos diferirem.
- Não calcular percentual de aplicação sobre o total geral quando só parte dos repasses
  for rastreável. Publicar cobertura do subconjunto, sem inferir gasto zero nas lacunas.
- Sem dados pessoais reconstruídos, ranking de PF ou armazenamento de Gold fora de Delta.

## Evidências exigidas do piloto

Descritores e manifesto de captura; extrato pequeno confrontado com a consulta oficial;
reconciliação por documento/fase/período em Decimal; casos com zero legítimo, negativo,
sem informação, retificação e mudança de exercício; fronteiras e vigência territorial;
matriz de cobertura; teste de reexecução idempotente; exportação com códigos, unidades,
edições e lacunas; proposta de atualização e retorno. O aceite de um piloto não
comprova cobertura nacional.

Próximo passo após a revisão deste plano: inventário E0 e escolha do piloto. A beta,
as ativações e a coleta massiva continuam fora desta entrega.

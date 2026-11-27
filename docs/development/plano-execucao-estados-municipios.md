# Plano de inserção da execução de estados e municípios

Pedido do mantenedor em 27/11/2026: inserir agora a execução federal e seu localizador
orçamentário da CGU; preparar a integração posterior da execução própria dos entes.
Este plano complementa [aplicação pelo recebedor](plano-aplicacao-pelo-recebedor.md).
Não anuncia cobertura estadual/municipal já implementada.

Diretriz ampliada pelo mantenedor em 27/11/2026: quando houver rastreabilidade
suficiente, mostrar a composição do orçamento municipal por origem federal,
estadual e própria municipal, a destinação de cada bloco por área e a aplicação
pelo município. Essa visão orienta os futuros contratos, KPIs e cartões.

## Objetivo e medidas distintas

1. Execução federal: seis fases da União, com localização orçamentária quando publicada.
2. Execução do ente: orçamento e despesa do estado/município, com seu próprio universo.
3. Aplicação de repasse: subconjunto com ligação demonstrada entre recebimento e execução.

Essas medidas não se somam nem se substituem. Empenhado, liquidado, pago, restos a
pagar, dotação inicial e atualizada são campos independentes. O localizador da CGU
não mede execução local. A existência de um portal também não comprova acesso
automatizado, completude histórica, licença ou identificação de cada repasse.

## Visão futura — origem, destinação e aplicação do orçamento municipal

**Requisito funcional definido pelo mantenedor; método detalhado e implementação
pendentes.** O resultado esperado é responder, para cada município e exercício:

1. Qual é o total do orçamento e quanto corresponde a recursos federais, estaduais
   e próprios municipais, em valor e participação percentual?
2. A quais áreas se destina cada bloco de origem, com o detalhamento oficial
   admissível por função/subfunção, programa/ação e órgão/fundo executor?
3. Como o município executa esses recursos: quanto foi destinado, empenhado,
   liquidado e pago, em qual período e para qual objeto/documento quando rastreável?

A composição desejada é **federal + estadual + próprio municipal**, com parcelas
mutuamente exclusivas dentro do mesmo universo, exercício e base de valor. O total
deve reconciliar com a referência municipal oficial. Não obter esse total somando
os portais federal, estadual e municipal: eles podem registrar etapas diferentes
do mesmo dinheiro. A decomposição por origem usará o orçamento/receita municipal
reconciliado; as fontes externas fornecerão prova da cadeia de transferências.

### Bases e consolidação necessárias

- **Previsão, arrecadação e despesa:** separar receita prevista, receita efetivamente
  arrecadada/recebida, dotação inicial/atualizada e fases da execução. A composição
  usa uma base declarada por vez; recebido não se adiciona à dotação para formar
  um total. Os percentuais das origens usam o total dessa mesma base e recorte.
- **Origem e intermediário:** preservar a origem do recurso e o ente que o repassou
  imediatamente. Em uma cadeia União → estado → município, o mesmo valor conta
  uma vez na composição municipal; a passagem pelo estado não cria verba estadual
  adicional. O enquadramento da origem depende de evidência e contrato próprio.
- **Receitas próprias e outras parcelas:** classificar por códigos e definições
  oficiais, sem obter verba própria apenas por subtração. Outras origens,
  financiamento ou montantes ainda não classificados devem permanecer explícitos
  na reconciliação; não forçar toda diferença para uma das três origens.
- **Perímetro:** definir Executivo, Legislativo, fundos e demais entidades incluídas.
  Transferências internas ao perímetro não criam receita adicional no total
  consolidado. No futuro, uma consolidação de vários entes também precisará eliminar
  repasses entre os entes abrangidos; não somar totais sem tratar essas duplicações.
- **Tempo e ajustes:** tratar saldos de exercícios anteriores, créditos, retenções,
  contrapartida, rendimentos, devoluções, anulações e revisões de modo documentado.
  Saldo anterior não se torna automaticamente receita nova do exercício; diferenças
  de competência/data de pagamento ficam diagnosticadas, sem igualdade forçada.
- **Vínculo com a execução:** cruzar origem × área × fase somente quando esses
  atributos coexistirem nos registros ou houver ligação oficial comprovada. Não
  distribuir despesas entre origens por proporção nem cruzar apenas totais marginais.
  Distinguir execução por fonte/grupo da rastreabilidade de um repasse individual.

### Pendência futura — revisão para a versão oficial

Por determinação do mantenedor em 27/11/2026, implementar o processo de checagem
jurídica, econômica e contábil **na preparação do lançamento da versão oficial**.
Revisar então todas as regras e bases de consolidação, inclusive as já implementadas,
contra o arcabouço aplicável a cada ente e exercício: PPA, LDO, LOA, anexos, alterações
e atos de programação/execução, além das normas gerais e locais pertinentes.
O objetivo será validar a aderência das lógicas técnicas à lei e à lógica de negócio.

[Registro da pendência futura](protocolo-revisao-juridico-economica-orcamentos.md).
Por enquanto, somente documentação: processo não implementado, sem nova checagem
ou bloqueio para o desenvolvimento e os pilotos atuais.

### Famílias de KPIs e cartões a preparar

Nomes abaixo são requisitos de conteúdo, sem IDs novos nem alteração visual agora.
Cada KPI deverá ter ficha com fonte, fórmula, base, universo, chaves, período,
cobertura, revisão, unidade e critérios de reconciliação antes da habilitação.

| Pergunta | Futuro KPI/cartão | Condição para mostrar valor ou percentual |
|---|---|---|
| Qual o total? | Orçamento municipal total, com base inicial/atualizada identificada; receitas previstas/arrecadadas em medidas próprias | Perímetro definido e total reconciliado com a referência oficial da respectiva base |
| Quanto vem de cada origem? | Valores e participações federal, estadual e própria municipal | Partes sem sobreposição, classificadas por regra oficial e denominador da mesma base; lacunas/outras parcelas explícitas |
| Para onde vai cada bloco? | Destinação por origem × área; valor e participação da área no bloco selecionado | Cruzamento sustentado pela fonte, com denominador restrito ao mesmo bloco/base/período |
| Como o município aplica? | Destinado, empenhado, liquidado e pago por origem × área, com evolução e detalhamento disponível | Fases separadas e vínculo da execução documentado; não somar fases como parcelas |
| Quanto do recurso recebido foi aplicado? | Valor e percentual de aplicação no universo rastreável, acompanhado de sua cobertura | Numerador/denominador compatíveis, saldos e ajustes tratados e método aceito; sem dividir execução parcial pelo total geral |
| Quanto conseguimos explicar? | Cobertura das origens e da ligação com a execução; valores sem classificação/vínculo | Distinguir cobertura da origem, da área e do repasse individual; base de cada percentual explícita |

O desenho dos cartões deverá conservar essa estrutura lógica: **total → origem →
destinação → execução**, com o usuário podendo percorrer a origem e a área sem
mudar silenciosamente o universo do total. Os filtros e as futuras exportações
precisarão preservar essas dimensões, a fase, a base temporal e a cobertura.
O total municipal desta visão terá definição própria, preservando os significados
das lentes federais já existentes.

### Critério de avanço

O piloto Guarabira/Paraíba passa a buscar também receita e despesa compatíveis,
códigos oficiais de origem/destinação e ligações com os repasses federais/estaduais.
Sua próxima proposta de contrato deve trazer uma matriz **origem × área × fase ×
período**, os ajustes de consolidação, os valores não classificados e exemplos de
cadeia direta e intermediada quando disponíveis. Cobertura parcial permite apenas
medidas explicitamente limitadas ao subconjunto comprovado; não autoriza anunciar
o orçamento integralmente explicado ou aplicação zero nas lacunas.

A diretriz autoriza o planejamento dessa evolução. Método estatístico/contábil,
contratos e criação efetiva dos KPIs/cartões continuam sujeitos aos aceites próprios
do plano; a interface futura exige leitura do guia DS e revisão visual. O piloto
atual não ganhou novos indicadores ou cobertura por esta alteração documental.

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
| E0 — Inventário | Matriz ente × poder × exercício × fonte; URLs oficiais, descritor, licença, formato, calendário, revisões e limites | Cada registro tem evidência; indisponíveis e não pesquisados são distintos | Fontes Guarabira/Elmar e PB selecionadas; matriz inicial documentada em 27/11 |
| E1 — Base nacional | Avaliação dos relatórios e MSC/Siconfi, dicionários e contas por edição | Universo, nível de detalhe e cobertura de declarações medidos por ente/período | Contrato semântico antes de modelagem |
| E2 — Piloto local | Guarabira/Elmar e Paraíba escolhidos pelo mantenedor em 27/11; depois portes e fornecedores distintos | Captura pequena e reprodutível, com conferência na consulta oficial; amostras iniciais conferidas, cobertura/metodologia pendentes | Mantenedor aceita o contrato e o resultado do piloto |
| E3 — Contratos e conectores | Identidade do ente, órgão/fundo/UG, exercício, documento/item/evento, fontes/destinações, fases, retificações e linhagem; origem última e repassador imediato | Sem chave inventada, sobreposição de snapshots ou associação por nome semelhante | ADR e contrato por família de fonte |
| E4 — Gold candidata | Execução própria do ente em Delta, separada das lentes federais | Reconciliação exata, saldos e sinais; cobertura e limitações explícitas | Aceite técnico sem ativação |
| E5 — Ligação com repasses | Piloto instrumento/receita → execução usando chaves oficiais | Mesmo universo e janela; saldos, ajustes e intermediários tratados; origem × área × fase sustentadas e total municipal reconciliado | Método concreto aprovado |
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

## Piloto iniciado em 27/11/2026

O mantenedor escolheu Guarabira pela Elmar e indicou o portal estadual da Paraíba.
[Inventário e resultado das amostras](../data_catalog/piloto-execucao-pb-2026-11-27/inventario.md),
com dicionário observado, manifestos e diagnóstico offline reproduzível.
Guarabira: oito linhas de novembro coincidem com a apresentação oficial; a amostra
de julho ainda não tem conferência visual. Paraíba: 334 agregados no recorte
julho/2026 × grupo da despesa × Até o mês, sem extrapolação de cobertura.

Próximo passo: esclarecer licenças, grão, semântica temporal, órgãos/fundos,
retificações e códigos; ampliar a prova limitada, incluindo receita municipal e
origem/destinação, antes de propor contrato E3 conforme a visão futura acima.
A ligação com repasses ainda não foi demonstrada. A beta, as ativações e a coleta
massiva continuam fora desta entrega.

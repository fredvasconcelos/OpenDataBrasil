# Revisão jurídica, econômica e contábil das regras orçamentárias

Diretriz do mantenedor em 27/11/2026. **Revisão obrigatória para homologar regras de
consolidação e KPIs orçamentários, incluindo as lógicas já implementadas.** Este
protocolo define o trabalho exigido; não declara concluída a revisão normativa.
Complementa o [plano dos entes](plano-execucao-estados-municipios.md).

## Alcance e unidade de revisão

Revisar cada regra, base de consolidação, classificação, fórmula, denominador,
chave e tratamento de exceção contra o arcabouço jurídico/econômico/contábil
aplicável à União, ao estado e ao município envolvidos, para **cada exercício e
período de vigência**. O piloto Guarabira/Paraíba não dispensa a esfera federal nem
a revisão das cadeias entre esferas; sua aprovação não homologa outros entes.

O corpus deve incluir todos os instrumentos aplicáveis ao recorte: Constituição e
normas gerais; constituição estadual e lei orgânica municipal; PPA e alterações;
LDO e anexos; LOA, anexos e créditos adicionais; atos de programação orçamentária e
financeira, cronogramas de desembolso, limitação de empenho e suas revisões; normas
contábeis/fiscais e classificações; normas de cada transferência, instrumento e
área/setor quando relevantes. Identificar o que a fonte denomina plano de execução;
não presumir um documento nacional único com esse nome ou regras locais idênticas.

Consultar também os atos, entendimentos e decisões dos órgãos de controle e
tribunais competentes quando afetarem a interpretação, registrando alcance,
eficácia e situação. Manuais/documentação de API não substituem a análise da norma
aplicável; referência federal não comprova automaticamente uma regra estadual ou
municipal. Distinguir norma geral, regra exclusiva de uma esfera e regra local,
respeitando competência, hierarquia e vigência demonstradas.

## Referências oficiais iniciais

Links conferidos em 27/11/2026 para iniciar o inventário; não são lista exaustiva
nem prova de leitura integral ou de aplicabilidade a cada algoritmo.

| Referência | Uso na revisão |
|---|---|
| [Constituição Federal](https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm) | Planejamento e orçamento, competências e transferências; identificar os dispositivos pertinentes |
| [Lei 4.320/1964, texto compilado](https://www.planalto.gov.br/ccivil_03/leis/l4320compilado.htm) | Orçamentos, receitas, despesas, créditos, exercício e demonstrações |
| [LC 101/2000 — LRF](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp101.htm) | Gestão fiscal, programação, limites e transparência, conforme aplicabilidade |
| [MCASP — Tesouro Nacional](https://www.gov.br/tesouronacional/pt-br/contabilidade-e-custos/manuais/manual-de-contabilidade-aplicada-ao-setor-publico-mcasp-1) | Procedimentos e enfoques orçamentário/patrimonial; edição e alterações próprias do período |
| [MDF — Tesouro Nacional](https://www.gov.br/tesouronacional/pt-br/contabilidade-e-custos/manuais/manual-de-demonstrativos-fiscais-mdf) | Métodos e demonstrativos fiscais usados na reconciliação |
| [PCASP — Tesouro Nacional](https://www.gov.br/tesouronacional/pt-br/contabilidade-e-custos/federacao/plano-de-contas-aplicado-ao-setor-publico-pcasp-1) | Contas e classificações por edição, com as normas contábeis correspondentes |
| [MTO — SOF/SIOP](https://www1.siop.planejamento.gov.br/mto/doku.php) | Procedimentos federais e classificações da edição examinada; não substituir instrumentos locais |

Na consulta, o Tesouro apresenta MCASP 11ª edição como vigente e distingue MDF 15ª
edição vigente da 16ª, válida a partir de 2027. A identificação na página não
homologa a regra: preservar a versão e suas alterações efetivamente aplicáveis ao
exercício analisado. Documentos futuros ou textos compilados atuais não devem ser
aplicados retroativamente por inferência.

PPA/LDO/LOA e atos de execução da União, da Paraíba e de Guarabira devem ser
inventariados em suas publicações oficiais, com anexos, alterações e vigências.
**Esse inventário local e sua leitura integral ainda estão pendentes.** Para cada
novo ente/período, repetir o levantamento completo; não limitar a revisão a uma
LDO recente, a ementas ou a exemplos de outro ente.

## Dossiê por regra: da norma ao comportamento executável

Cada regra deve registrar:

1. Identificação estável da regra; pergunta de negócio, escopo territorial,
   órgãos/fundos/poderes, exercício e versão de código/contrato/release examinada.
2. Fontes oficiais e originais preservados com URL, publicação, obtenção, hash,
   dispositivo/anexo, edição, vigência, alterações/revogação e aplicabilidade.
   Documento ausente, inacessível e não aplicável exigem registros distintos;
   não aplicável precisa de justificativa, não de silêncio.
3. Interpretação jurídica e contábil, conceito econômico e regra de negócio:
   unidade/moeda, base bruta/líquida, regime temporal, universo, estágios, vínculo,
   exclusões e hipóteses. Registrar divergências e interpretações alternativas.
4. Correspondência explícita **dispositivo → requisito → campo/código oficial →
   transformação/fórmula → API/exportação/cartão → teste e reconciliação**.
   Citar caminhos/funções e versões reais; não basta descrever a intenção do código.
5. Casos reais reconciliados e casos de fronteira/contraprova, com resultado esperado
   independente da implementação. Igualar um total do portal não prova adequação
   do conceito, e testes que repetem a fórmula não demonstram sua validade.
6. Resultado, evidências, lacunas, responsável/data de revisão e aceite. Questões
   interpretativas precisam de revisão contábil/jurídica qualificada registrada
   antes do fechamento; automação auxilia, sem substituir esse juízo.

## Lista inicial de regras a auditar — todas pendentes

| Grupo | Pergunta que deve ser resolvida no dossiê |
|---|---|
| Total/perímetro | Qual total oficial e quais entidades estão abrangidos? Quais eliminações internas/intergovernamentais são exigidas? |
| Origem dos recursos | Como distinguir origem federal/estadual/própria, repassador imediato, repartição/transferência, receitas vinculadas e outras parcelas, pelos códigos vigentes? |
| Base temporal | Previsão, arrecadação, dotação, competência, empenho, liquidação, pagamento e restos a pagar estão definidos e apresentados separadamente? |
| Ajustes e saldos | Como tratar créditos, superávit/saldos anteriores, rendimentos, contrapartida, retenções, anulações, devoluções e retificações sem criar receitas ou executar dupla contagem? |
| Destinação e aplicação | A origem × área × fase tem vínculo oficial? Quais restrições do instrumento/fonte e quais denominadores são admissíveis? |
| Indicadores e comparações | Valor e percentual respondem à pergunta de negócio na mesma base/universo? Limites legais, índices, inflação ou valores reais têm método próprio quando usados? |
| Implementação existente | As lentes A/B/C, suas classificações/filtros, agregações, saldos, localizadores e exportações preservam esses conceitos nas versões efetivamente servidas? |

O escopo existente inclui os modelos/contratos/construção das contas em
`packages/modeling/src/odb_modeling/contas*.py` e o percurso até as consultas e
exportações, a localizar em cada dossiê. O diagnóstico do piloto confere fidelidade
da amostra; não constitui aprovação jurídica/econômica dessas regras.

## Aceite e reabertura

Estados do dossiê: **pendente**, **em revisão**, **com divergência** ou **validado no
escopo declarado**. Uma referência encontrada, compilação, teste verde ou resposta
da API não permite promovê-lo para validado. Falta de evidência não autoriza
concluir que o gasto público é ilegal nem que a regra já implementada está correta.

O mantenedor aceita o dossiê concreto, com os responsáveis pela revisão e os
pareceres necessários. **Nenhuma regra pendente ou com divergência pode receber
homologação normativa, sustentar novos KPIs de consolidação/aplicação ou ser levada
à publicação como validada.** A revisão das regras existentes é pendência explícita;
este protocolo não altera sozinho regras em execução nem concede aceite retroativo.

Mudanças de legislação, edição de manual, exercício, classificação, perímetro ou
algoritmo reabrem os dossiês afetados. Quando houver divergência, propor correção
com impacto, testes, reconciliação e retorno; seguir o aceite do projeto antes de
mudar regra estatística/contábil ou release publicado. Manter o corpus histórico,
a linhagem e a justificativa dos resultados anteriores.

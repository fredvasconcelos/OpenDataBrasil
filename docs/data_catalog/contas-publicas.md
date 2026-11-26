# Contas públicas — fontes oficiais para entender os dados

Referências da **Controladoria-Geral da União (CGU), Portal da Transparência**,
conferidas em **26/11/2026**. Os dicionários explicam as colunas dos arquivos;
o glossário explica os termos. Os links abaixo são documentação, não novas bases
incorporadas ao portal.

## Bases usadas nas contas públicas

| Base | Dicionário oficial | O que ajuda a entender |
|---|---|---|
| Recursos transferidos (lente A) | [Recursos transferidos](https://portaldatransparencia.gov.br/dicionario-de-dados/recursos-transferidos) | Tipo de transferência e favorecido; município SIAFI; órgão e unidade gestora; função, subfunção, programa, ação, natureza da despesa e valor transferido. |
| Recebimento por favorecido (lente B) | [Recebimento de recursos por favorecido](https://portaldatransparencia.gov.br/dicionario-de-dados/recursos-por-favorecido) | Favorecido, UF/município, órgão superior, órgão, unidade gestora, mês do lançamento e valor recebido. É a referência do arquivo de recebimentos do ZIP de despesas por favorecido. |
| Execução da despesa (lente C) | [Execução da despesa](https://portaldatransparencia.gov.br/dicionario-de-dados/execucao-despesa) | Organização e classificação do gasto; localizador; emenda; valores empenhados, liquidados, pagos e restos a pagar. |
| Cadastro dos favorecidos PJ | [Favorecidos — Pessoa Jurídica](https://portaldatransparencia.gov.br/dicionario-de-dados/favorecidos-pj) | Identificação cadastral, atividade econômica (CNAE), natureza jurídica, tipo de pessoa e endereço; inclui os dicionários das tabelas de CNAE e natureza jurídica. |

As três lentes respondem perguntas diferentes e **não se somam**. O painel atual
usa a lente A; a ficha do favorecido apresenta A e B separadamente. A lente C
tem contrato de dados próprio e não é exibida como outro total do painel.

Para consultar os arquivos, use o [índice oficial de dados abertos](https://portaldatransparencia.gov.br/download-de-dados).
O [Glossário da CGU](https://portaldatransparencia.gov.br/glossario) complementa
os dicionários para termos como ação, empenho, liquidação e restos a pagar.

## Referência histórica

[Transferências — Pagamentos](https://portaldatransparencia.gov.br/dicionario-de-dados/transferencias-pagamentos)
é apresentado pela própria CGU como **histórico**. Descreve função, programa,
ação, favorecido, finalidade, modalidade, convênio e valor de repasse.
Não substitui os dicionários de Recursos transferidos ou de Recebimento por favorecido.

## Dicionários complementares localizados na varredura

As páginas de download oficiais apontam para estes seis dicionários. São
referências para aprofundamento; sua inclusão aqui não habilita consultas a
documentos, convênios, orçamento ou emendas ainda não oferecidas pela interface.

| Referência oficial | Quando consultar |
|---|---|
| [Documento de Empenho](https://portaldatransparencia.gov.br/dicionario-de-dados/empenhos) | Reserva orçamentária, identificação do documento e sua classificação. A CGU informa que atualizações movem o registro para a planilha da última alteração; somar arquivos diários sem essa regra pode duplicar registros. |
| [Documento de Liquidação](https://portaldatransparencia.gov.br/dicionario-de-dados/liquidacao) | Conferência da entrega e relação com empenhos. Um documento pode abranger vários empenhos e apresentar classificações múltiplas. |
| [Documento de Pagamento](https://portaldatransparencia.gov.br/dicionario-de-dados/pagamentos) | Documento, favorecido, classificação e moeda/conversão para reais. Não confundir esse documento com o agregado mensal de recebimentos. |
| [Orçamento da Despesa](https://portaldatransparencia.gov.br/dicionario-de-dados/orcamento-da-despesa) | Exercício e classificação da autorização orçamentária; distingue orçamento de execução e de pagamento. |
| [Convênios](https://portaldatransparencia.gov.br/dicionario-de-dados/convenios) | Concedente, convenente, objeto, situação, vigência, valores do convênio, liberações, contrapartida e ordens bancárias. |
| [Emendas Parlamentares](https://portaldatransparencia.gov.br/dicionario-de-dados/emendas-parlamentares) | Autor, ano, identificador, localidade de destinação e fases da execução; município pode não estar informado. |

## Cuidados na leitura das tabelas

- **Município depende da base.** A CGU descreve o município do favorecido em
  transferências/recebimentos; em execução, a localização informada no plano de
  trabalho. O cadastro PJ descreve o endereço cadastral. Essas definições não
  comprovam o local de aplicação de um pagamento específico.
- **Fases da despesa são diferentes.** Empenhado, liquidado, pago e restos a pagar
  têm definições próprias no dicionário de execução. Não representam valores
  adicionais que possam ser somados para obter um gasto total.
- **Programa e ação têm contexto.** O dicionário explica o campo; a descrição de
  um programa ou de uma ação específica exige o cadastro oficial do exercício,
  como o SIOP, conforme a [ADR-0035](../adr/0035-dicionario-de-contas-publicas.md).
- **Dicionário não substitui o arquivo.** O contrato preserva o cabeçalho recebido.
  Em Recursos transferidos, o código da ação aparece como `AÇÃO` no CSV e como
  `CÓDIGO AÇÃO` no dicionário; `NOME GRUPO DESPESA` corresponde a `GRUPO DE DESPESA`.
  Em execução, o CSV usa `Código Subfução`, descrito como `Código Subfunção`.
  Não corrigir esses cabeçalhos no original nem supor mudança de significado.

A conferência de nomes cobriu 36 campos de transferências, 12 de recebimentos,
47 de execução e 21 do cadastro PJ e suas duas tabelas auxiliares, considerando
as três correspondências acima e normalização de caixa/acentos. Isso confirma
a referência documental dos campos; não valida os valores de cada lançamento.

Os textos desta página são explicações do Open Data Brasil a partir das fontes
vinculadas. As definições oficiais completas permanecem nos links da CGU.
A varredura abrangeu os temas relacionados às contas públicas; não é um inventário
de todos os dicionários de benefícios, servidores, sanções ou outros temas da CGU.

## Valores enviados e aplicação pelo recebedor

O painel usa os valores transferidos da lente A. Área, tipo de transferência, território e período são cruzados pela API sobre a Gold; a classificação da transferência não comprova a área de execução posterior pelo ente. A tabela de recebedores acompanha os mesmos filtros. Não se somam as lentes A/B/C.

O valor e o percentual aplicado pelo estado ou município **ainda não estão disponíveis**. Os cartões com “—” não indicam aplicação zero. Siconfi/MSC e Transferegov são caminhos candidatos para uma integração futura, não fontes já incorporadas. É necessário comprovar a correspondência e a cobertura antes de dividir a execução pelo total transferido; execução de um subconjunto não comprova execução do universo inteiro. Ver [ADR-0042](../adr/0042-navegacao-e-contexto-das-contas.md).

# Dicionário observado nas amostras — versão de diagnóstico 0.1

Referência: 27/11/2026. Não é contrato Silver/Gold aprovado. Descrições da
[documentação Elmar](https://transparencia-api.elmartecnologia.com.br/swagger),
[configuração municipal](https://transparencia.elmartecnologia.com.br/Export/DadosAbertos/?e=201082&module=DespesaFixada),
[Swagger estadual](https://api.dados.pb.gov.br/swagger/) e
[recurso estadual](https://dados.pb.gov.br/dataset/despesas/resource/42915dda-7d92-4449-b202-6dc4bbc51c29).
Preservar nomes/códigos originais. Valores monetários em reais, conforme consulta
oficial municipal e apresentação do portal estadual; JSON numérico lido em Decimal.
Faltam descritores metodológicos completos e códigos/vigências antes da modelagem.

## Guarabira — despesa fixada, objeto `data`

Swagger v2: `GET /api/v{version}/{ctx}/contab/despesas/fixada`. Parâmetros de
consulta: `competencia`, `exercicio`, `exibeConsolidado`; `ctx` e `version` no caminho.
A máscara do formulário oficial da competência é `00/0000`. Piloto: `version=2`,
`ctx=201082`, consolidado falso. Não foi demonstrada paginação/contagem de total.

| Campo JSON | Tipo observado | Descrição/limite |
|---|---|---|
| `sequencia` | inteiro | Identificador de registro retornado; único nas duas amostras. Estabilidade entre revisões não demonstrada |
| `competencia` | texto | Mês/ano do registro; conferir contra a seleção |
| `orgao`, `ecode` | texto | Rótulo com contexto e código da entidade Elmar; não é código IBGE |
| `catEconomica` | texto | Categoria econômica descrita; cadastro/código separado pendente |
| `ficha` | inteiro | Ficha orçamentária; não basta como chave entre órgãos/exercícios |
| `funcaoProgramatica` | texto | Código composto; conservar zeros e composição original |
| `undOrcamentaria` | texto | Código e descrição da unidade orçamentária |
| `classificacao` | texto | Código e descrição de classificação da despesa |
| `codClassificacao` | inteiro | Código também apresentado separadamente; conservar forma original |
| `descClassificacao` | texto | Descrição da classificação |
| `fonteDeRecurso` | texto | Código e descrição da fonte; não equivale a identificador de transferência |
| `dotacaoInicial` | número | Dotação inicial; não somar snapshots mensais |
| `suplementadoNoMes` | número | Suplementado no mês, conforme rótulo oficial |
| `anuladoNoMes` | número | Anulado no mês; confirmar sinal e abrangência com a metodologia |
| `dotacaoAtualizada` | número | Dotação atualizada; data-base e relação com créditos dependem de descritor |
| `empenhado` | número | Empenhado, sem qualificador temporal no nome; não presumir acumulado ou fluxo |
| `liquidadoNoMes` | número | Liquidado no mês, conforme rótulo |
| `pagoNoMes` | número | Pago no mês, conforme rótulo; zeros preservados |
| `saldo` | número | Saldo conforme a fonte; fórmula não homologada |
| `saldoAPagar` | número | Saldo a pagar; não confundir automaticamente com restos a pagar |
| `infoUltimaAtualizacao` | texto no envelope | Informação de atualização exibida pela fonte |
| `dtUltimaAtualizacao` | texto no envelope | Data/hora com deslocamento; nas amostras `2026-11-19T15:52:12-03:00`. É atualização da fonte, não hora da captura |

A interface de dados abertos oferece CSV/XML/TXT/JSON/GRID; a consulta possui
exportadores PDF/RTF/XLS/CSV/TXT. Nesta rodada, só JSON e HTML foram capturados e
conferidos. A existência de um botão não valida o arquivo exportado.

## Paraíba — execução orçamentária, objeto `dados`

`GET /api/v1/despesas/execucao_orcamentaria`; ano/mês obrigatórios, filtros opcionais
por poder, órgão, orçamento democrático, marcador, Covid19 e classificação.
`acumular=Até o mês` acumula janeiro até o mês selecionado, segundo a documentação;
`No mês` é outra modalidade. Paginação `page`, `per_page`, máximo documentado de 1000.

| Campo JSON | Tipo do Swagger | Descrição/limite |
|---|---|---|
| `ano`, `mes` | inteiro | Referência solicitada; conferir em todas as linhas |
| `tipoPoder` | texto | Poder governamental; preservar universo da consulta |
| `cnpjOrgao`, `nomeOrgao` | texto | CNPJ e nome do órgão; CNPJ não é município de aplicação |
| `orcamentoDemocratico` | texto | Classificação do orçamento democrático; dimensão a preservar |
| `marcador` | texto | Marcador; não ignorar ao definir grão |
| `covid19` | texto | Indicador conforme a fonte; não converter em bool sem contrato |
| `codigo`, `classificacao` | inteiro/texto | Código e descrição no nível de classificação escolhido; não comparar códigos de níveis distintos |
| `orcamentoInicial`, `orcamentoAtualizado` | número | Orçamentos inicial/atualizado; snapshots não aditivos entre meses |
| `valorEmpenhado`, `valorLiquidado`, `valorPago` | número | Fases independentes, interpretadas com a modalidade temporal explícita |
| `saldoAPagar` | número | Saldo a pagar; fórmula e tratamento de restos/revisões ainda pendentes |
| `paginacao.total` | inteiro | Quantidade de itens do recorte informada pela API |
| `paginacao.pagina` | inteiro | Página retornada |
| `paginacao.itens_por_pagina` | inteiro | Tamanho solicitado/retornado |
| `paginacao.total_paginas` | inteiro | Total de páginas; conferir contra total/tamanho |

Classificações documentadas: grupo da despesa, unidade orçamentária, função,
subfunção, programa de governo, ação de governo, natureza da despesa, categoria
econômica, modalidade de aplicação, elemento da despesa e fonte de recurso.
Amostra desta rodada usa apenas grupo da despesa; as outras dez não foram homologadas.

[PDF oficial do dicionário estadual](https://api.dados.pb.gov.br/downloads/dicionario/Despesas/execucao_orcamentaria.pdf)
preservado com checksum; leitura textual/completude metodológica ainda pendente.
Não usar apenas os rótulos do Swagger como prova de fórmula ou universo.

# ADR-0044 — Lentes federais B e C no portal

- Data: 27/11/2026.
- Situação: implementação local para revisão; sem publicação na beta.
- Escopo solicitado: concluir B/C, incluindo consulta por estado e município.
- Base: ADRs 0030, 0032, 0033, 0037 e 0042. Nenhuma regra de agregação alterada.

## Contrato de apresentação

A navegação oferece três perspectivas independentes. A mantém os recursos transferidos.
B apresenta pagamentos a favorecidos, com Brasil, UF e município segundo a **sede
cadastral**, usando a hierarquia territorial oficial. C apresenta a execução da União,
com empenhado, liquidado, pago, restos a pagar inscritos, cancelados e pagos em seis
colunas e cartões independentes. Não há soma de fases, soma de lentes ou aplicação
posterior atribuída ao recebedor.

O calendário e as dimensões de cada perspectiva vêm de `/contas/meta`. O período
inicial prefere ano integral fechado da própria lente; sem ele, o último mês disponível.
Ano incompleto mantém a sinalização de cobertura do contrato. Os grupos e os
cruzamentos usam `/contas/table` (B) e `/contas/execucao` (C); uma categoria por dimensão,
com filtros explícitos, removíveis e persistidos na URL. Total e paginação vêm da API.
Na execução, até uma página sem linhas preserva os totais do recorte, em vez de
apresentar zero. São dez registros por página, até cem páginas; o limite é informado ao usuário, sem
apresentar a primeira página como universo completo. Negativos são preservados.

B permite navegar por UF e município no seletor e no mapa. O seletor municipal usa
as feições oficiais completas do recorte, evitando truncamento de UFs com mais de
500 municípios. Mapa e série mostram o território/período inteiro; a tabela pode
receber recortes adicionais de categoria, com essa diferença de universo visível.
O total inclui lançamentos contábeis, internos, bancos e sigilosos; não significa total
exclusivo dos beneficiários finais. As notas da API permanecem disponíveis.

A busca nacional consulta favorecidos PJ, sem pessoas físicas, e não herda os filtros
da tabela. A ficha recebe o ano selecionado; o retorno mantém lente, território,
período, agrupamento e filtros. Os identificadores pessoais não são reconstruídos.
Dados de releases distintos são rejeitados; falhas exibem indisponibilidade e nova
tentativa, nunca zero fictício.

## Limite da solicitação territorial na lente C

A consulta por estado e município foi implementada na B. **Na C, continua pendente**:
o contrato aprovado na ADR-0032, decisão 6, exclui o localizador do mapa. O campo da
fonte descreve a programação orçamentária, não prova a aplicação pelo recebedor.
A amostra histórica citada nessa ADR não mede a cobertura atual inteira.

Expor C territorial exige proposta específica: identificar o vínculo oficial, medir a
cobertura por exercício, separar nacional/multirregional/sem localização, reconciliar
valores e obter aceite do contrato. Não repartir valores nacionais entre municípios,
não usar a sede da B como local de execução da C e não dividir execução parcial pelo
total geral. A aplicação efetiva por estados e municípios permanece na frente A6.

## Fontes e validação

- [Dicionário da execução da despesa — CGU](https://portaldatransparencia.gov.br/dicionario-de-dados/execucao-despesa).
- [Dicionário de recursos por favorecido — CGU](https://portaldatransparencia.gov.br/dicionario-de-dados/recursos-por-favorecido).

Consultados em 27/11/2026. Os dicionários explicam campos; os valores continuam sendo
consultados na Gold identificada pela proveniência. Não houve captura ou ativação.
Testes cobrem isolamento de calendários/dimensões, URLs, cruzamentos, reconciliação dos
seis valores com a API real, UF/município, busca/ficha, falha 503 e acessibilidade.
O aceite visual final permanece com o mantenedor.


## Ampliação autorizada em 27/11/2026

O mantenedor escolheu o localizador orçamentário da CGU para a etapa imediata e pediu
um plano para a execução própria dos estados e municípios. O limite territorial acima
passa a ser tratado pela [ADR-0045](0045-localizador-orcamentario-da-execucao.md): detalhe
original do plano de trabalho, sem mapa nem atribuição de aplicação efetiva. A interface
segue o guia do DS, mantendo `?lens=B|C`, com troca pelo catálogo da barra lateral.

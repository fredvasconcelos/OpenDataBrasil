# ADR-0040 — Alertas de cobertura da tabela dinâmica

- Data: 24/11/2026.
- Estado: implementação local para revisão; publicação depende de autorização.
- Pedido: distinguir cobertura parcial (amarelo) de detalhe indisponível (vermelho),
  com inventário anterior à publicação. Continuação autorizada pelo mantenedor em
  24/11/2026; nenhum release ou ambiente publicado é alterado por esta decisão.

## Problema

A série de um indicador pode reunir tabelas com níveis, períodos e detalhes
diferentes. A tabela precisa explicar esses limites sem esconder observações,
inventar valores ou deixar a decisão estatística no navegador.

## Decisão

A API adiciona `alerts` à resposta de `GET /kpis/{id}/pivot`. Cada alerta contém
`severity`, um código e parâmetros estruturados. Nenhum texto traduzido é enviado
nesse campo. O portal traduz os códigos e usa os links oficiais já fornecidos pelo
catálogo. As consultas e os diagnósticos usam o mesmo release fixado da requisição.

| Caso | Código | Regra |
|---|---|---|
| C1 / C9 | A1 | O nível tem menos períodos que a série, depois de aplicar o grão solicitado. |
| C2 | A2 | Há presença em mais de zero e menos de 100% dos territórios de uma referência válida no período e no recorte. |
| C3 | V1 | A dimensão solicitada não tem categorias neste nível. |
| C4 | A3 | A dimensão tem categorias em menos períodos que o nível. |
| C5 | A3 | Uma categoria aparece em menos territórios que seu Total publicado no mesmo período e cruzamento. |
| C6 | A4 | O resultado já contém `partial_sum`, sem alterar o subtotal existente. |
| C7 | V3 | Um período solicitado não tem linhas ou só tem `absent` / `not_available` no recorte. |
| C8 | V4 | O cruzamento solicitado viola `exclusive_dimensions` / `crossed_levels`. |
| Detalhe só com Total | V2 | A dimensão ativa só trouxe a categoria Total neste recorte. |
| C10 | sem classe automática | Proporções de sigilo, indisponibilidade e zeros são registradas no inventário. |

Vermelho tem precedência visual sobre amarelo. A lista é determinística, vermelhos
primeiro. Somente um diagnóstico vermelho novo abre a explicação automaticamente.
Triângulo e círculo com exclamação, nomes acessíveis e textos distinguem as classes
mesmo sem perceber as cores. O botão continua disponível em uma tabela vazia.

**Ajuste visual solicitado pelo mantenedor em 25/11/2026 (DS 2.23.1):** os botões
da tabela e do gráfico mantêm o símbolo “i”, colorido conforme o alerta, sem fundo,
borda ou sombra externos. Essa escolha substitui as formas de aviso do botão
descritas acima. Nomes acessíveis, títulos e textos da explicação continuam
identificando o risco. A precedência e a abertura automática do vermelho permanecem.

### Referências e limites

A dimensão territorial fixada não tem validade histórica por unidade. Sua contagem
só serve quando o ano da referência coincide com o ano consultado, respeitando os
descendentes do recorte. Para comparação municipal nacional histórica, aceitam-se
apenas visões genéricas do descritor SIDRA com intervalo de anos explícito e
contagens concordantes. Sem referência suficiente, não se calcula A2. Não se usa
a contagem nacional como denominador de uma UF nem se dá nome a subconjuntos por
semelhança de contagens.

A POF municipal de 2008 tem 26 unidades na Gold local; a visão histórica 10 da
tabela 1594 informa 5.564 municípios em 2005–2008. O alerta diz **26 de 5.564**,
sem identificar o subconjunto como capitais. Não se substitui esse universo pela
DTB atual.

A2 conta presença territorial, incluindo células sob sigilo. Não mede proporção de
valores numéricos: converter `X` em ausência territorial aplicaria uma regra de C10
sem decisão metodológica. Zero verdadeiro continua disponível. C5 compara cada
categoria com o Total mantendo as outras dimensões fixas; não une marginais.
Categorias totalmente ausentes não são fabricadas para comparar contagens.

O diagnóstico não filtra células nem altera valores, status, períodos publicados,
regras de soma ou precisão. Uma parte da série ausente no período escolhido não
apaga os outros períodos solicitados.

### Recusas e custo

Um cruzamento conhecido e proibido recebe tabela vazia com V4, sem executar sua
consulta de observações. Níveis, dimensões, categorias, grãos e períodos inventados
continuam sendo recusados. Um período existente na série, mas ausente no nível,
pode receber V3 no pivot; os demais endpoints preservam sua validação anterior.

O índice existente de cobertura passa a guardar períodos por classificação e
nível, no cache do release, com verificação de truncamento. As contagens de
referência têm cache limitado por release, nível e recorte. Os diagnósticos do
recorte usam as observações já lidas pelo pivot, excluindo bases ocultas de
percentuais; não há consulta de valores adicional para cada alerta. Os limites de
células, memória, concorrência e tempo da API permanecem os existentes.

## Inventário e validação

`infrastructure/scripts/cobertura_kpis.py` lê a Gold fixada, com limites, lotes de
períodos e checkpoints identificados por release, versões e hash do script.
`resumo_cobertura.py` confronta períodos e níveis da API, registra os códigos de
risco dos recortes armazenados e separa níveis derivados que exigem consulta
semântica. Nenhuma soma regional é executada pelo inventário para substituir essa
consulta. Os arquivos Parquet, CSV, JSON e seus hashes são evidências locais,
fora da distribuição pública. Categorias mínimas do inventário respeitam as
categorias expostas pela dimensão do portal.

Os testes cobrem séries menores, referência histórica, ausência, sigilo, zeros,
precedência, categoria territorial parcial, recusa sem consulta e determinismo.
O Playwright confere amarelo, vermelho, neutro, links oficiais e dez indicadores
reais, com capturas nos temas claro e escuro. O release destinado à publicação
deve ter inventário próprio antes de qualquer implantação.

## Reversão

Reverter o código restaura a apresentação anterior; nenhuma migração, reingestão,
ativação ou alteração na Gold é necessária. O campo novo tem lista vazia como
padrão para compatibilidade com consumidores e fixtures anteriores.

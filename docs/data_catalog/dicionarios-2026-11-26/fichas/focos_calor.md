# Focos de calor por bioma

Ficha `focos_calor` · indicador `focos_calor` · **disponivel_snapshot**.

## Significado e uso

Número de focos de calor (Indicadores de Desenvolvimento Sustentável, tabela SIDRA 5805). Tabela sem classificações. Fonte: Queimadas: monitoramento de focos. Cachoeira Paulista, SP: Instituto Nacional de Pesquisas Espaciais - INPE, Centro de Previsão de Tempo e Estudos Climáticos - CPTEC. Disponível em: <http://www.dpi.inpe.br/proarco/bdqueimadas/>. Acesso em: jan. 2017.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território (Brasil) x ano.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-5805` | [5805/2142](https://sidra.ibge.gov.br/tabela/5805) | Número de focos de calor / Unidades | M40 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5805 / 2142

Pesquisa/produtor: Indicadores de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 1999 a 2016.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: True / True.
Nota oficial (síntese de contexto não substitui a nota): 1. Dados de focos de calor obtidos pelos satétites NOAA12 Noite (1999 a 2007) e AQUA M-T (2007 a 2016). 2. Os focos com localização indeterminada ou sem informação foram computados em Bioma não definido . 3. Simbologia: - (hífen) indica que não houve focos de calor com localização indeterminada ou sem informação nos anos correspondentes.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["1999", "2000", "2001", "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": true, "seasonal_sum": true, "accumulation_rule": "sum"}`.

Parecer temporal preservado: `sum_method_supported`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M40 — Focos de calor](../pesquisas.md#m40): Detecção de fogo em pixels de imagens de satélite para acompanhar sua distribuição. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M40: Confirmar janelas, mudança de satélite e qualidade de cada ano; a FAQ corrente não atualiza a série publicada.

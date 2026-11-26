# Municípios com legislação ambiental

Ficha `legislacao_ambiental` · indicador `legislacao_ambiental` · **disponivel_snapshot**.

## Significado e uso

Número de municípios com legislação ambiental (Indicadores de Desenvolvimento Sustentável, tabela SIDRA 5608). Tabela sem classificações. Fonte: IBGE, Diretoria de Pesquisas, Pesquisa de Informações Básicas Municipais - Perfil dos Municípios Brasileiros.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território (Brasil, Grande Região, UF) x ano.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-5608` | [5608/6299](https://sidra.ibge.gov.br/tabela/5608) | Número de municípios com legislação ambiental / Unidades | M35 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5608 / 6299

Pesquisa/produtor: Indicadores de Desenvolvimento Sustentável. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2002, 2009, 2013.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2002", "2009", "2013"], "uf": ["2002", "2009", "2013"], "regiao": ["2002", "2009", "2013"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M35 — MUNIC](../pesquisas.md#m35): Estrutura, funcionamento e instrumentos das instituições municipais, especialmente prefeituras. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M35: Rever perguntas e universo de resposta nas edições históricas; não usar número atual de municípios como denominador histórico.

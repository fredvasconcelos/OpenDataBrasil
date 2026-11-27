# Pessoas que se sentem seguras ao andar sozinhas perto de casa

Ficha `sensacao_seguranca` · indicador `sensacao_seguranca` · **disponivel_snapshot**.

## Significado e uso

Pessoas de 15 anos ou mais de idade que se sentem seguras ao andar sozinhas nas redondezas ou arredores do seu domicílio (PNAD Contínua, tabela SIDRA 8713). Tabela sem classificações. Fonte: IBGE - Pesquisa Nacional por Amostra de Domicílios Contínua Anual - 4º trimestre.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil pessoas**. Grão: território (Brasil, Grande Região) x ano x sexo | cor ou raça | nível de instrução | meio de informação sobre crimes na cidade em que reside.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-8715` | [8715/12567](https://sidra.ibge.gov.br/tabela/8715) | Pessoas de 15 anos ou mais de idade que se sentem seguras ao andar sozinhas nas redondezas ou arredores do seu domicílio / Mil pessoas | M05 |
| `ibge-sidra-8717` | [8717/12567](https://sidra.ibge.gov.br/tabela/8717) | Pessoas de 15 anos ou mais de idade que se sentem seguras ao andar sozinhas nas redondezas ou arredores do seu domicílio / Mil pessoas | M05 |
| `ibge-sidra-8724` | [8724/12567](https://sidra.ibge.gov.br/tabela/8724) | Pessoas de 15 anos ou mais de idade que se sentem seguras ao andar sozinhas nas redondezas ou arredores do seu domicílio / Mil pessoas | M05 |
| `ibge-sidra-8713` | [8713/12567](https://sidra.ibge.gov.br/tabela/8713) | Pessoas de 15 anos ou mais de idade que se sentem seguras ao andar sozinhas nas redondezas ou arredores do seu domicílio / Mil pessoas | M05 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 8715 / 12567

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua anual. Periodicidade: período único. Disponibilidade na fonte: 2021.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A categoria Total para "Cor ou raça" inclui as pessoas que se declararam indígenas, amarelas ou sem declaração.

### 8717 / 12567

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua anual. Periodicidade: período único. Disponibilidade na fonte: 2021.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

### 8724 / 12567

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua anual. Periodicidade: período único. Disponibilidade na fonte: 2021.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

### 8713 / 12567

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua anual. Periodicidade: período único. Disponibilidade na fonte: 2021.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["2021"], "brasil": ["2021"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": false, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M05 — PNAD Contínua](../pesquisas.md#m05): Estatísticas domiciliares de trabalho, rendimento, educação, moradia e outros módulos; os universos variam. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M05: Faltam memória de ponderação/calibração por edição e fórmulas específicas de Gini, informalidade, frequência líquida e rendimentos; registrar IC/CV existentes sem recomputá-los.

# Esgotamento sanitário (PNAD e Censo)

Ficha `esgotamento_serie` · indicador `esgotamento_serie` · **disponivel_snapshot**.

## Significado e uso

Domicílios por tipo de esgotamento sanitário: PNAD Contínua anual (tabela 7192) em Brasil, Grandes Regiões e UFs, de 2019 a 2025, e Censo Demográfico 2022 (tabela 6805) nos municípios, nas categorias da PNAD.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território x ano x tipo de esgotamento (harmonizado) | situação do domicílio.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-6805` | [6805/381](https://sidra.ibge.gov.br/tabela/6805) | Domicílios particulares permanentes ocupados / Unidades | M01 |
| `ibge-sidra-7192` | [7192/9986](https://sidra.ibge.gov.br/tabela/7192) | Domicílios com banheiro, sanitário ou buraco para dejeções / Mil unidades | M05 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 6805 / 381

Pesquisa/produtor: Censo Demográfico. Periodicidade: período único. Disponibilidade na fonte: 2022.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Dados do Universo

### 7192 / 9986

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua anual. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2019, 2022 a 2025.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Por motivos de mudança na captação das informações no questionário, os dados de períodos anteriores estão disponibilizados na tabela 6735 . A categoria Outro tipo para "Tipo de esgotamento sanitário" inclui fossa rudimentar, vala, rio, lago ou mar e outras formas de escoadouro. A partir de 2025, as estimativas deste tema passaram a ser divulgadas com base na nova ponderação da pesquisa, conforme a Nota Técnica 02/2025. Consequentemente, a série histórica dos indicadores foi atualizada. A classificação "Situação do domicílio" está disponível apenas para os níveis territoriais Brasil, Grande Região e Unidade da Federação.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2019", "2022", "2023", "2024", "2025"], "municipio": ["2022"], "regiao": ["2019", "2022", "2023", "2024", "2025"], "uf": ["2019", "2022", "2023", "2024", "2025"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M01 — Censo Demográfico](../pesquisas.md#m01): Enumeração de residentes habituais e características de pessoas e domicílios; serve à descrição territorial e ao planejamento. A população e a edição específicas continuam sendo as da tabela/variável.

[M05 — PNAD Contínua](../pesquisas.md#m05): Estatísticas domiciliares de trabalho, rendimento, educação, moradia e outros módulos; os universos variam. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M01: Verificar os manuais de cada edição histórica e os universos/denominadores de cada razão, mediana e taxa; a fonte geral não resolve essas fórmulas por variável.
- M05: Faltam memória de ponderação/calibração por edição e fórmulas específicas de Gini, informalidade, frequência líquida e rendimentos; registrar IC/CV existentes sem recomputá-los.

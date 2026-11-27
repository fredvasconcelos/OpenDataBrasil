# Nível de instrução em quatro grupos (PNAD)

Ficha `nivel_instrucao_capitais` · indicador `nivel_instrucao_capitais` · **disponivel_snapshot**.

## Significado e uso

População de 25 anos ou mais no Brasil, Grandes Regiões, UFs e 27 capitais, nos quatro grupos de instrução publicados pela tabela SIDRA 7270.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil pessoas**. Grão: território (Brasil, Grandes Regiões, UFs e 27 capitais) x ano x nível de instrução agrupado.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-7270-capitais` | [7270/1643](https://sidra.ibge.gov.br/tabela/7270) | Pessoas de 25 anos ou mais de idade / Mil pessoas | M05 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 7270 / 1643

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua anual. Periodicidade: anual. Disponibilidade na fonte: 2016 a 2019, 2022 a 2025.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A categoria Total para "Cor ou raça" inclui as pessoas que se declaram indígenas, amarelas ou sem declaração. A partir de 01 de agosto de 2022, as estimativas deste tema passaram a ser divulgadas com base no novo método de ponderação da pesquisa, conforme a Nota Técnica 03/2021. Consequentemente, a série histórica dos indicadores foi atualizada. A partir de 2025, as estimativas deste tema passaram a ser divulgadas com base na nova ponderação da pesquisa, conforme a Nota Técnica 02/2025. Consequentemente, a série histórica dos indicadores foi atualizada.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"municipio": ["2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"], "brasil": ["2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"], "regiao": ["2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"], "uf": ["2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M05 — PNAD Contínua](../pesquisas.md#m05): Estatísticas domiciliares de trabalho, rendimento, educação, moradia e outros módulos; os universos variam. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M05: Faltam memória de ponderação/calibração por edição e fórmulas específicas de Gini, informalidade, frequência líquida e rendimentos; registrar IC/CV existentes sem recomputá-los.

# Frequência escolar líquida no ensino fundamental

Ficha `frequencia_liquida` · indicador `frequencia_liquida` · **disponivel_snapshot**.

## Significado e uso

Taxa ajustada de frequência escolar líquida (PNAD Contínua anual, tabela SIDRA 7141). Recorte: Sexo: Total; Faixa etária ideal por curso frequentado: 6 a 14 anos no ensino fundamental. Fonte: IBGE - Pesquisa Nacional por Amostra de Domicílios Contínua Anual - 2º trimestre.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território (Brasil, Grande Região, UF) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-7141` | [7141/10282](https://sidra.ibge.gov.br/tabela/7141) | Taxa ajustada de frequência escolar líquida / % | M05 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 7141 / 10282

Pesquisa/produtor: Pesquisa Nacional por Amostra de Domicílios Contínua anual. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2016 a 2019, 2022 a 2025.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Taxa ajustada de frequência escolar líquida é a razão entre o número de pessoas que frequenta escola no nível de ensino adequado à sua faixa etária mais aquelas que já concluíram pelo menos esse nível de ensino e o total de pessoas dessa mesma faixa etária. A partir de 01 de agosto de 2022, as estimativas deste tema passaram a ser divulgadas com base no novo método de ponderação da pesquisa, conforme a Nota Técnica 03/2021. Consequentemente, a série histórica dos indicadores foi atualizada. A partir de 2025, as estimativas deste tema passaram a ser divulgadas com base na nova ponderação da pesquisa, conforme a Nota Técnica 02/2025. Consequentemente, a série histórica dos indicadores foi atualizada.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"], "regiao": ["2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"], "uf": ["2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"]}`.

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

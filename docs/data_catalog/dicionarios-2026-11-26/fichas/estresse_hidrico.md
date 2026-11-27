# Nível de estresse hídrico

Ficha `estresse_hidrico` · indicador `estresse_hidrico` · **disponivel_snapshot**.

## Significado e uso

Proporção entre a retirada de água doce e o total dos recursos de água doce disponíveis (Objetivos de Desenvolvimento Sustentável, tabela SIDRA 7077). Tabela sem classificações. Fonte: Agência Nacional de Águas e Saneamento Básico (ANA) - Sistema Nacional de Informações sobre Recursos Hídricos (SNIRH) Instituição produtora: Agência Nacional de Águas e Saneamento Básico (ANA).

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território (Brasil) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-7077` | [7077/10233](https://sidra.ibge.gov.br/tabela/7077) | Proporção entre a retirada de água doce e o total dos recursos de água doce disponíveis / % | M44 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 7077 / 10233

Pesquisa/produtor: Objetivos de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 2015 a 2024.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M44 — ODS água](../pesquisas.md#m44): Pressão de retirada de água e tratamento seguro de águas residuais são dois indicadores diferentes. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M44: Recuperar edição exata e fórmulas completas; denominador ambiental não pode ser fixado por inferência a partir de relatório de outro exercício.

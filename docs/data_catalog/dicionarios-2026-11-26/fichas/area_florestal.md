# Área florestal em proporção do território

Ficha `area_florestal` · indicador `area_florestal` · **disponivel_snapshot**.

## Significado e uso

Área de floresta como proporção da área total terrestre (Objetivos de Desenvolvimento Sustentável, tabela SIDRA 6843). Tabela sem classificações. Fonte: https://fra-data.fao.org/assessments/fra/2025/BRA/sections/sustainableDevelopment; Resolução nº 1 de 15/01/2013 do IBGE (dado usado no FRA 2015).

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território (Brasil) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-6843` | [6843/9971](https://sidra.ibge.gov.br/tabela/6843) | Área de floresta como proporção da área total terrestre / % | M50 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 6843 / 9971

Pesquisa/produtor: Objetivos de Desenvolvimento Sustentável. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2000, 2005, 2010, 2015, 2020 a 2025.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2000", "2005", "2010", "2015", "2020", "2021", "2022", "2023", "2024", "2025"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M50 — Área florestal](../pesquisas.md#m50): Área de floresta como proporção da área terrestre total (ODS 15.1.1). A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M50: Compatibilizar com FRA 2025/BRA e memória nacional. O documento histórico não homologa a edição atual da tabela.

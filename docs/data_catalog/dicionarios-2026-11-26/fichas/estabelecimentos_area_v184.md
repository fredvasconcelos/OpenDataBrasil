# Área dos estabelecimentos agropecuários

Ficha `estabelecimentos_area_v184` · indicador `estabelecimentos_area_v184` · **disponivel_snapshot**.

## Significado e uso

Área dos estabelecimentos agropecuários

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Hectares**. Grão: território x ano.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t6878-v184` | [6878/184](https://sidra.ibge.gov.br/tabela/6878) | Área dos estabelecimentos agropecuários / Hectares | M16 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 6878 / 184

Pesquisa/produtor: Censo Agropecuário. Periodicidade: anual. Disponibilidade na fonte: 2017.
Precisão de armazenamento/apresentação no descritor: 3 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Agricultura familiar referente ao Decreto 9.064 de 31/05/2017 e PRONAF referente ao MCR/BACEN em 31/12/2017 (MCR - Manual de Crédito Rural). 2 - Pronaf: Programa Nacional de Fortalecimento da Agricultura Familiar. 3 - Pronamp: Programa Nacional de Apoio ao Médio Produtor Rural.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2017"], "municipio": ["2017"], "regiao": ["2017"], "uf": ["2017"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": false, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M16 — Censo Agropecuário](../pesquisas.md#m16): Estrutura dos estabelecimentos agropecuários, áreas e atividades. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M16: Revisar conceito e área de cada edição histórica; contagem de estabelecimentos não é fluxo aditivo entre censos.

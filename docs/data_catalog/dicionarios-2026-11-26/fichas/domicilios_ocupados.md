# Domicílios particulares permanentes ocupados

Ficha `domicilios_ocupados` · indicador `domicilios_ocupados` · **disponivel_snapshot**.

## Significado e uso

Domicílios particulares permanentes ocupados (Censo Demográfico, tabela SIDRA 4712). Tabela sem classificações. Fonte: IBGE - Censo Demográfico.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Domicílios**. Grão: território (Brasil, Grande Região, UF, Município) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-4712` | [4712/381](https://sidra.ibge.gov.br/tabela/4712) | Domicílios particulares permanentes ocupados / Domicílios | M01 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 4712 / 381

Pesquisa/produtor: Censo Demográfico. Periodicidade: período único. Disponibilidade na fonte: 2022.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1- Dados do Universo. 2- Os dados apresentados foram atualizados em 27/10/23 e se referem aos dados coletados até o dia 28/05/2023, com a incorporação das revisões realizadas entre 29/05/2023 e 07/07/2023. 3- Os dados referentes aos municípios Abel Figueiredo (PA) e São Pedro da Água Branca (MA) foram corrigidos no dia 22/12/2023, impactando nos totais dos estados do Pará e do Maranhão e nos totais das Grandes Regiões do Norte e Nordeste.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"uf": ["2022"], "regiao": ["2022"], "brasil": ["2022"], "municipio": ["2022"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": false, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M01 — Censo Demográfico](../pesquisas.md#m01): Enumeração de residentes habituais e características de pessoas e domicílios; serve à descrição territorial e ao planejamento. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M01: Verificar os manuais de cada edição histórica e os universos/denominadores de cada razão, mediana e taxa; a fonte geral não resolve essas fórmulas por variável.

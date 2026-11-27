# Valor das incorporações, obras e serviços da construção

Ficha `empresas_construcao_v1241` · indicador `empresas_construcao_v1241` · **indisponivel_snapshot**.

## Significado e uso

Valor das incorporações, obras e/ou serviços da construção

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil Reais**. Grão: território x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t10442-v1241` | [10442/1241](https://sidra.ibge.gov.br/tabela/10442) | Valor das incorporações, obras e/ou serviços da construção / Mil Reais | M19 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 10442 / 1241

Pesquisa/produtor: Pesquisa Anual da Indústria da Construção. Periodicidade: anual. Disponibilidade na fonte: 2024.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A vari ável Empresas atuantes nas Unidades da Federação refere-se ao número de empresas com atuação na Unidade da Federação e na região. Assim sendo, cada empresa é contada apenas uma vez na Unidade da Federação e na região onde atua. Logo, o número total de empresas numa região é igual ou menor do que a soma dos totais de cada UF dessa região. Pela mesma razão, o número total de empresas no Brasil é igual ou menor do que a soma dos totais de cada região.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: não. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `[]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M19 — PAIC](../pesquisas.md#m19): Estrutura das empresas da construção: pessoal, receitas, custos e obras/serviços. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- DADOS: KPI configurado ausente da navegação N2 no snapshot; candidato não significa publicado.
- M19: Ler integralmente a mudança amostral 01/2026 e as fórmulas por medida; a página localiza a ruptura, não resolve a ligação.

# Número de empresas de serviços não financeiros

Ficha `servicos_nao_financeiros_v630` · indicador `servicos_nao_financeiros_v630` · **indisponivel_snapshot**.

## Significado e uso

Número de empresas

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t2581-v630` | [2581/630](https://sidra.ibge.gov.br/tabela/2581) | Número de empresas / Unidades | M21 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 2581 / 630

Pesquisa/produtor: Pesquisa Anual de Serviços. Periodicidade: anual. Disponibilidade na fonte: 2007 a 2023.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - Os dados referentes a valores econômicos estão expressos em 1 000 R$. 2 - Para a variável Salários, retiradas e outras remunerações : inclusive participação nos lucros (somente a parte distribuída aos empregados) e honorários da diretoria, remuneração de sócios cooperados (somente para as cooperativas de trabalho) e as retiradas pró-labore. 3 - Para a variável Custos das mercadorias revendidas : inclusive custo de vendas de imóveis próprios. 4 - Para a categoria Serviços prestados principalmente às famílias : o conceito adotado na PAS é menos abrangente que o definido nas Contas Nacionais. 5 - Nas variáveis Coeficiente de variação , referentes às estimativas de algumas variáveis, os possíveis indicadores e respectivos significados são os seguintes: A - até 5% - nível de precisão: ótimo B - mais de 5 a 15% - nível de precisão: bom C - mais de 15 a 30% - nível de precisão: razoável D - mais de 30 a 50% - nível de precisão: pouco preciso E - mais de 50% - nível de precisão: impreciso Z - zero - nível de precisão: exato

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: não. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `[]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M21 — PAS](../pesquisas.md#m21): Estrutura empresarial dos serviços não financeiros. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- DADOS: KPI configurado ausente da navegação N2 no snapshot; candidato não significa publicado.
- M21: Ler nota 01/2026 e memória amostral; a divulgação de 2024 não prova comparabilidade ou disponibilidade na candidata local.

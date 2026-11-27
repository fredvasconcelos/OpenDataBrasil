# Quantidade de leite industrializado

Ficha `leite_adquirido_v283` · indicador `leite_adquirido_v283` · **indisponivel_snapshot**.

## Significado e uso

Quantidade de leite cru, resfriado ou não, industrializado

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil litros**. Grão: território x trimestre.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t1086-v283` | [1086/283](https://sidra.ibge.gov.br/tabela/1086) | Quantidade de leite cru, resfriado ou não, industrializado / Mil litros | M13 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 1086 / 283

Pesquisa/produtor: Pesquisa Trimestral do Leite. Periodicidade: trimestral. Disponibilidade na fonte: 1º trimestre 1997 a 2º trimestre 2026.
Precisão de armazenamento/apresentação no descritor: 3 / 0 casas. Soma de períodos/territórios na fonte: True / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Até o 4º trimestre de 2005 os dados das Unidades da Federação com menos de 4 (quatro) informantes estão desidentificados com o caractere X. A partir do 1º trimestre de 2006 a desidentificação passou a ser feita para menos de 3 (três) informantes. 2 - Os dados dos 4 trimestres do ano são preliminares até a divulgação dos dados do 1° trimestre do ano seguinte. 3 - Os resultados do indicador "preço do leite cru pago ao produtor" até março de 2024 são considerados Estatísticas Experimentais.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: não. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `[]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M13 — Leite](../pesquisas.md#m13): Aquisição e industrialização de leite cru/resfriado. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- DADOS: KPI configurado ausente da navegação N2 no snapshot; candidato não significa publicado.
- M13: Identificar exercício de cada revisão do painel e notas específicas dos preços sem atribuir o preço à quantidade.

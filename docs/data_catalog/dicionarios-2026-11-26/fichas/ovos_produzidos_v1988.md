# Galinhas poedeiras nos estabelecimentos pesquisados

Ficha `ovos_produzidos_v1988` · indicador `ovos_produzidos_v1988` · **indisponivel_snapshot**.

## Significado e uso

Número de cabeças de galinhas poedeiras nos estabelecimentos agropecuários

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Cabeças**. Grão: território x trimestre.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t7524-v1988` | [7524/1988](https://sidra.ibge.gov.br/tabela/7524) | Número de cabeças de galinhas poedeiras nos estabelecimentos agropecuários / Cabeças | M14 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 7524 / 1988

Pesquisa/produtor: Produção de Ovos de Galinha. Periodicidade: trimestral. Disponibilidade na fonte: 1º trimestre 1987 a 2º trimestre 2026.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Até o 4º trimestre de 2011: As informações não correspondem às produções totais das Unidades da Federação, uma vez que são pesquisados apenas os estabelecimentos com 10.000 ou mais galinhas poedeiras. 2 - A partir do 1º trimestre de 2012: As informações não correspondem às produções totais das Unidades da Federação, uma vez que são pesquisados apenas os estabelecimentos com capacidade de alojamento de pelo menos 10.000 galinhas poedeiras. 3 - O número de galinhas poedeiras refere-se à média do plantel existente no último dia de cada mês do trimestre. 4 - O número de informantes se repete nos meses de cada trimestre devido à periodicidade de coleta da pesquisa ser trimestral. 5 - Até o 4º trimestre de 2005 os dados das Unidades da Federação com menos de 4 (quatro) informantes estão desidentificados com o caracter X. A partir do 1º trimestre de 2006 a desidentificação passou a ser feita para menos de 3 (três) informantes. 6 - Os dados dos 4 trimestres do ano são preliminares até a divulgação dos dados do 1° trimestre do ano seguinte.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: não. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `[]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M14 — Ovos](../pesquisas.md#m14): Produção de ovos em estabelecimentos do painel pesquisado. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- DADOS: KPI configurado ausente da navegação N2 no snapshot; candidato não significa publicado.
- M14: Fechar comparabilidade histórica do limiar de inclusão e unidades por variável antes de qualquer nova agregação.

# Pessoas indígenas por idade

Ficha `apoio--censo_pessoas_indigenas_idade` · indicador `censo_pessoas_indigenas_idade` · **apoio_no_release_snapshot**.

## Significado e uso

Pessoas indígenas por grupos quinquenais de idade, idades simples e meses de vida, localização do domicílio em relação a terras indígenas e situação urbana ou rural. Publicado pela plataforma para Brasil, Grandes Regiões e UFs.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Pessoas**. Grão: território (Brasil, Grande Região, UF) x ano censitário x idade x localização do domicílio x situação do domicílio.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-9970` | [9970/350](https://sidra.ibge.gov.br/tabela/9970) | Pessoas indígenas por idade / Pessoas | Não localizado |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 9970 / 350

Pesquisa/produtor: ibge-sidra. Periodicidade: decenal. Disponibilidade na fonte: consultar contrato da fonte externa.
Precisão de armazenamento/apresentação no descritor: não informada / não informada casas. Soma de períodos/territórios na fonte: não informada / não informada.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `["2022"]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- PESQUISA: método independente não localizado; consultar produtor identificado na ficha.
- DESCRITOR: tabela 9970 não tem descritor preservado localizado; códigos/definições/metadados oficiais completos pendentes, sem nova tentativa bloqueada.

## Contexto complementar localizado nesta execução

Idade, sexo e situação urbana/rural são recortes distintos; o gráfico apresenta distribuições relativas por grupos de idade.

A publicação não comprova os códigos/medida da tabela 9970. Sem descritor, não ligar percentuais desse gráfico a contagens por idade no apoio nem homologar todas as terras/geografias.

Fonte: [produtor oficial](https://www.ibge.gov.br/biblioteca/visualizacao/livros/liv102155.pdf), Análise demográfica, p. 146, gráfico 4 e contexto de comparação 2010/2022; edição: Censo 2022 — Indígenas: Principais características das pessoas e dos domicílios, por situação urbana ou rural. Consulta indexada em 2026-11-26; não leitura integral.

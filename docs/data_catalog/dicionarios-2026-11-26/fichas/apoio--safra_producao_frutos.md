# Estimativa da safra: produção de abacaxi e coco

Ficha `apoio--safra_producao_frutos` · indicador `safra_producao_frutos` · **apoio_apenas_configurado**.

## Significado e uso

Produção

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil frutos**. Grão: território x mês x produto.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t6588-v35-frutos-g1` | [6588/35](https://sidra.ibge.gov.br/tabela/6588) | Produção / Toneladas | M10 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 6588 / 35

Pesquisa/produtor: Levantamento Sistemático da Produção Agrícola. Periodicidade: mensal. Disponibilidade na fonte: setembro 2006 a outubro 2026.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Para as Unidades da Federação que, por força do calendário agrícola, ainda não dispõem das estimativas iniciais, os dados correspondem a uma projeção obtida a partir das informações de anos anteriores; 2 - As produções de abacaxi e de coco-da-baía são expressas em mil frutos e os seus rendimentos médios em frutos/ha . 3 - Utilizou-se a padronização de 61% para a conversão da produção do algodão em caroço para caroço de algodão, apenas para a totalização da produção dos cereais, leguminosas e oleaginosas. 4 - Possíveis diferenças entre somas de parcelas e respectivos totais são provenientes do critério de arredondamento. 5 - As informações mensais que compõem a série histórica estão disponível a partir de setembro de 2006. 6 - A partir de janeiro de 2018 foram retirados da divulgação os seguintes produtos: abacaxi , alho , cebola , coco-da-baía , guaraná , maçã , malva , pimenta-do-reino , sisal/agave . Os mesmos continuam sendo acompanhados na pesquisa anual da Produção Agrícola Municipal.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: não. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `[]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M10 — LSPA](../pesquisas.md#m10): Previsão e acompanhamento mensal da safra agrícola do ano civil. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M10: Notas/reconciliações LSPA e limites de exportação completa ainda exigem aceite na candidata N4; nenhum bloqueio foi removido.

# Unidades de conservação terrestres

Ficha `unidades_conservacao` · indicador `unidades_conservacao` · **disponivel_snapshot**.

## Significado e uso

Número de unidades de conservação terrestres (Indicadores de Desenvolvimento Sustentável, tabela SIDRA 5619). Tabela sem classificações. Fonte: Ministério do Meio Ambiente, Departamento de Áreas Protegidas, Cadastro Nacional de Unidades de Conservação - CNUC; IBGE. Área Territorial Brasileira. Disponível em: <http://www.ibge.gov.br/home/geociencias/areaterritorial/principal.shtm>. Acesso em: fevereiro de 2017.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território (Brasil) x ano.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-5619` | [5619/6306](https://sidra.ibge.gov.br/tabela/5619) | Número de unidades de conservação terrestres / Unidades | M43 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5619 / 6306

Pesquisa/produtor: Indicadores de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 1992 a 2016.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Dados do Cadastro Nacional de Unidades de Conservação - CNUC atualizados em 09/08/2016; área territorial brasileira: 8.515.767,049 km2; há sobreposição entre unidades de conservação, que ocorre mais intensamente (em termos percentuais) no Bioma Mata Atlântica. 2 - No número de unidades de conservação não foram incluídas as unidades de conservação marinhas. 3 - Na área das unidades de conservação não foram incluídas as áreas de conservação marinhas.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["1992", "1993", "1994", "1995", "1996", "1997", "1998", "1999", "2000", "2001", "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M43 — CNUC](../pesquisas.md#m43): Número e área de unidades de conservação registradas. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M43: Falta metodologia histórica de tratamento de sobreposições e domínios por categoria; não transplantar instantâneo atual para 2016.

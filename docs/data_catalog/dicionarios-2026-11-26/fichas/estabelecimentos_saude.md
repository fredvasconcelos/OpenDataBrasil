# Estabelecimentos de saúde

Ficha `estabelecimentos_saude` · indicador `estabelecimentos_saude` · **disponivel_snapshot**.

## Significado e uso

Estabelecimentos de saúde (Pesquisa de Assistência Médico-Sanitária, tabela SIDRA 211). Tabela sem classificações. Fonte: IBGE - Pesquisa de Assistência Médico-Sanitária.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território (Brasil, Grande Região, UF) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-211` | [211/1665](https://sidra.ibge.gov.br/tabela/211) | Estabelecimentos de saúde / Unidades | M37 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 211 / 1665

Pesquisa/produtor: Pesquisa de Assistência Médico-Sanitária. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 1976 a 1990, 1992, 1999, 2002, 2005.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - A partir de 1992 foram incorporados na pesquisa os estabelecimentos que realizavam exclusivamente Serviços de Apoio à Diagnose e Terapia. 2 - Em 1999 não foram investigados os estabelecimentos que realizavam exclusivamente Análises Clínicas. 3 - A partir de 1983 e até 1987: Inclusive Fernando de Noronha. 4 - A partir de 1988 Fernando de Noronha está incluído na Unidade da Federação Pernambuco.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["1976", "1977", "1978", "1979", "1980", "1981", "1982", "1983", "1984", "1985", "1986", "1987", "1988", "1989", "1990", "1992", "1999", "2002", "2005"], "uf": ["1976", "1977", "1978", "1979", "1980", "1981", "1982", "1983", "1984", "1985", "1986", "1987", "1988", "1989", "1990", "1992", "1999", "2002", "2005"], "brasil": ["1976", "1977", "1978", "1979", "1980", "1981", "1982", "1983", "1984", "1985", "1986", "1987", "1988", "1989", "1990", "1992", "1999", "2002", "2005"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M37 — AMS](../pesquisas.md#m37): Capacidade instalada e oferta de serviços de saúde. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M37: Rever inclusões/exclusões, unidade e alterações de cada edição da tabela 211.

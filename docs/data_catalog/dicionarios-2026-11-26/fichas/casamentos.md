# Casamentos

Ficha `casamentos` · indicador `casamentos` · **disponivel_snapshot**.

## Significado e uso

Número de casamentos (Estatísticas do Registro Civil, tabela SIDRA 4412). Tabela sem classificações. Fonte: IBGE - Pesquisa Estatísticas do Registro Civil.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território (Brasil, Grande Região, UF, Município) x ano x estado civil do primeiro cônjuge | mês de ocorrência | estado civil do segundo cônjuge | grupo de idade do primeiro cônjuge | grupo de idade do segundo cônjuge.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-4412` | [4412/4993](https://sidra.ibge.gov.br/tabela/4412) | Número de casamentos / Unidades | M04 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 4412 / 4993

Pesquisa/produtor: Pesquisa Estatísticas do Registro Civil. Periodicidade: anual. Disponibilidade na fonte: 2013 a 2024.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: True / True.
Nota oficial (síntese de contexto não substitui a nota): Para os casamentos entre cônjuges masculino e feminino considerou-se como primeiro cônjuge o homem e segundo cônjuge a mulher.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"], "municipio": ["2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"], "uf": ["2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"], "regiao": ["2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": true, "seasonal_sum": true, "accumulation_rule": "sum"}`.

Parecer temporal preservado: `sum_method_supported`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M04 — Registro Civil](../pesquisas.md#m04): Estatística de registros administrativos de nascimentos, óbitos, casamentos e divórcios. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M04: Fechar regras de inclusão de registros tardios e janelas por edição/tabela, inclusive fronteiras da série; não generalizar a variável 343 a todas as contagens.

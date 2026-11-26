# Consultaram médico nos últimos 12 meses

Ficha `consulta_medica` · indicador `consulta_medica` · **disponivel_snapshot**.

## Significado e uso

Pessoas que consultaram médico nos últimos 12 meses (Pesquisa Nacional de Saúde, tabela SIDRA 5055). Tabela sem classificações. Fonte: IBGE - Pesquisa Nacional de Saúde.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil pessoas**. Grão: território (Brasil, Grande Região, UF, Município) x ano x sexo | situação do domicílio | cor ou raça | grupo de idade | condição em relação à força de trabalho na semana de referência.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-5061` | [5061/5358](https://sidra.ibge.gov.br/tabela/5061) | Pessoas que consultaram médico nos últimos 12 meses / Mil pessoas | M06 |
| `ibge-sidra-5058` | [5058/5358](https://sidra.ibge.gov.br/tabela/5058) | Pessoas que consultaram médico nos últimos 12 meses / Mil pessoas | M06 |
| `ibge-sidra-5065` | [5065/5358](https://sidra.ibge.gov.br/tabela/5065) | Pessoas que consultaram médico nos últimos 12 meses / Mil pessoas | M06 |
| `ibge-sidra-5055` | [5055/5358](https://sidra.ibge.gov.br/tabela/5055) | Pessoas que consultaram médico nos últimos 12 meses / Mil pessoas | M06 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5061 / 5358

Pesquisa/produtor: Pesquisa Nacional de Saúde. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2013, 2019.
Precisão de armazenamento/apresentação no descritor: 3 / 3 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A classificação "Situação do domicílio" está disponível apenas para o nível territorial Brasil. A categoria Total para "Cor ou raça" inclui as pessoas que se declararam indígenas, amarelas ou sem declaração.

### 5058 / 5358

Pesquisa/produtor: Pesquisa Nacional de Saúde. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2013, 2019.
Precisão de armazenamento/apresentação no descritor: 3 / 3 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A classificação "Situação do domicílio" está disponível apenas para o nível territorial Brasil.

### 5065 / 5358

Pesquisa/produtor: Pesquisa Nacional de Saúde. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2013.
Precisão de armazenamento/apresentação no descritor: 3 / 3 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A classificação "Situação do domicílio" está disponível apenas para o nível territorial Brasil. Foram consideradas apenas as pessoas de 14 anos ou mais de idade. Em 2013, as pessoas em licença remunerada na semana de referência da pesquisa e que estavam afastadas por período inferior a 4 meses eram classificadas como "ocupadas". Caso esse afastamento fosse igual ou superior a 4 meses, essas pessoas eram definidas como "fora da força de trabalho" e, portanto, não se investigava o rendimento do trabalho. A partir de 2019, em acordo com as recomendações da 19ª Conferência Internacional de Estatísticos do Trabalho - CIET, da OIT, pessoas em licença remunerada, independentemente do tempo de afastamento, passaram a ser classificadas como "ocupadas" e seus rendimentos do trabalho foram coletados normalmente.

### 5055 / 5358

Pesquisa/produtor: Pesquisa Nacional de Saúde. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2013, 2019.
Precisão de armazenamento/apresentação no descritor: 3 / 3 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A classificação "Situação do domicílio" está disponível apenas para o nível territorial Brasil.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2013", "2019"], "municipio": ["2013", "2019"], "uf": ["2013", "2019"], "regiao": ["2013", "2019"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M06 — PNS](../pesquisas.md#m06): Saúde, acesso a serviços, doenças declaradas e fatores de risco da população domiciliar. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M06: A leitura integral dos módulos, ponderadores e alterações 2013/2019 permanece pendente; o universo da tabela/variável prevalece sobre a descrição geral.

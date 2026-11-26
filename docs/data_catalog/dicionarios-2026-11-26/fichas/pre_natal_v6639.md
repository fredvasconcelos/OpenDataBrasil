# Mulheres que realizaram pré-natal (%)

Ficha `pre_natal_v6639` · indicador `pre_natal_v6639` · **disponivel_snapshot**.

## Significado e uso

Percentual de mulheres que realizaram pré-natal

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t8288-v6639` | [8288/6639](https://sidra.ibge.gov.br/tabela/8288) | Percentual de mulheres que realizaram pré-natal / % | M06 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 8288 / 6639

Pesquisa/produtor: Pesquisa Nacional de Saúde. Periodicidade: anual. Disponibilidade na fonte: 2019.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Foram consideradas as mulheres de 15 anos ou mais de idade cujo último parto ocorreu no período de referência. Exclusive as pessoas cuja condição no domicílio era "Pensionista", "Empregado doméstico" ou "Parente de empregado doméstico". Em 2013, as pessoas em licença remunerada na semana de referência da pesquisa e que estavam afastadas por período inferior a 4 meses eram classificadas como "ocupadas". Caso esse afastamento fosse igual ou superior a 4 meses, essas pessoas eram definidas como "fora da força de trabalho" e, portanto, não se investigava o rendimento do trabalho. A partir de 2019, em acordo com as recomendações da 19ª Conferência Internacional de Estatísticos do Trabalho - CIET, da OIT, pessoas em licença remunerada, independentemente do tempo de afastamento, passaram a ser classificadas como "ocupadas" e seus rendimentos do trabalho foram coletados normalmente. Caso a mulher tenha tido mais de um parto no período de referência, foi considerado o último parto.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2019"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": false, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M06 — PNS](../pesquisas.md#m06): Saúde, acesso a serviços, doenças declaradas e fatores de risco da população domiciliar. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M06: A leitura integral dos módulos, ponderadores e alterações 2013/2019 permanece pendente; o universo da tabela/variável prevalece sobre a descrição geral.

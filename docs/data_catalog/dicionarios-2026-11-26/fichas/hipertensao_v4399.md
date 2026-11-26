# Diagnóstico de hipertensão arterial (%)

Ficha `hipertensao_v4399` · indicador `hipertensao_v4399` · **disponivel_snapshot**.

## Significado e uso

Percentual de pessoas de 18 anos ou mais de idade que referem diagnóstico médico de hipertensão arterial

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t4418-v4399` | [4418/4399](https://sidra.ibge.gov.br/tabela/4418) | Percentual de pessoas de 18 anos ou mais de idade que referem diagnóstico médico de hipertensão arterial / % | M06 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 4418 / 4399

Pesquisa/produtor: Pesquisa Nacional de Saúde. Periodicidade: anual. Disponibilidade na fonte: 2013, 2019.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A classificação "Situação do domicílio" está disponível apenas para o nível territorial Brasil.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["2013", "2019"], "uf": ["2013", "2019"], "municipio": ["2013", "2019"], "brasil": ["2013", "2019"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M06 — PNS](../pesquisas.md#m06): Saúde, acesso a serviços, doenças declaradas e fatores de risco da população domiciliar. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M06: A leitura integral dos módulos, ponderadores e alterações 2013/2019 permanece pendente; o universo da tabela/variável prevalece sobre a descrição geral.

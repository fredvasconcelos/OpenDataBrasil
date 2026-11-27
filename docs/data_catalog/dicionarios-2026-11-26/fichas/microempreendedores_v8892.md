# Número de microempreendedores individuais (MEIs) (saída)

Ficha `microempreendedores_v8892` · indicador `microempreendedores_v8892` · **disponivel_snapshot**.

## Significado e uso

Número de microempreendedores individuais (MEIs) (saída)

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t9597-v8892` | [9597/8892](https://sidra.ibge.gov.br/tabela/9597) | Número de microempreendedores individuais (MEIs) (saída) / Unidades | M26 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 9597 / 8892

Pesquisa/produtor: Estatísticas dos Cadastros de Microempreendedores Individuais. Periodicidade: anual. Disponibilidade na fonte: 2022.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A fonte de dados da Classificação Nacional de Atividades Econômicas (CNAE 2.0) dos microempreendedores individuais (MEIs) é o Cadastro Nacional de Pessoas Jurídicas (CNPJ) e não passou por procedimento de crítica. Número de microempreendedores individuais (MEIs) (saldo) consiste na diferença entre o total de MEIs do ano de referência e do ano anterior ao de referência. Ele não necessariamente é o mesmo valor das entradas menos as saídas, pois as entradas e saídas não levam em conta mudanças de atividade econômica. Ou seja, um MEI que simplesmente alterou a atividade econômica não é considerado entrada ou saída.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["2022"], "uf": ["2022"], "brasil": ["2022"], "municipio": ["2022"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": false, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `flow_method_review_required`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M26 — MEI](../pesquisas.md#m26): Caracterização cadastral e trajetória dos microempreendedores individuais; estatística experimental. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEMPORAL: método de fluxo pendente; sem nova permissão de soma nesta revisão.
- M26: Recuperar integralmente regras de entrada/saída e denominadores por coorte da 9597; fluxos permanecem metodologicamente pendentes.

# Salário médio mensal em reais

Ficha `empresas_emprego_formal_v10143` · indicador `empresas_emprego_formal_v10143` · **disponivel_snapshot**.

## Significado e uso

Salário médio mensal em reais

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Reais**. Grão: território x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t9509-v10143` | [9509/10143](https://sidra.ibge.gov.br/tabela/9509) | Salário médio mensal em reais / Reais | M25 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 9509 / 10143

Pesquisa/produtor: Cadastro Central de Empresas. Periodicidade: anual. Disponibilidade na fonte: 2022 a 2024.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - Os dados com menos de 3 (três) informantes estão desidentificados com o caracter X. 2 - Esta tabela substitui a tabela 454.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"uf": ["2022", "2023", "2024"], "regiao": ["2022", "2023", "2024"], "municipio": ["2022", "2023", "2024"], "brasil": ["2022", "2023", "2024"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M25 — CEMPRE](../pesquisas.md#m25): Estrutura e dinâmica de empresas, organizações e unidades locais formais ativas. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M25: Fechar critérios de atividade, datas e cálculo do salário médio de cada edição da 9509; não retroprojetar a série atual.

# Resultados das empresas comerciais

Ficha `empresas_comerciais` · indicador `empresas_comerciais` · **disponivel_snapshot**.

## Significado e uso

Receita operacional líquida (Pesquisa Anual de Comércio, tabela SIDRA 10646). Tabela sem classificações. Fonte: IBGE - Pesquisa Anual de Comércio.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil Reais**. Grão: território (Brasil) x ano x divisão de comércio.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-10646` | [10646/643](https://sidra.ibge.gov.br/tabela/10646) | Receita operacional líquida / Mil Reais | M20 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 10646 / 643

Pesquisa/produtor: Pesquisa Anual de Comércio. Periodicidade: período único. Disponibilidade na fonte: 2024.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Outras despesas operacionais e outros custos incluem o custo de fabricação própria e o custo de material de embalagens e outros materiais (de reposição, de peças, etc). 2 - A variável Gastos com pessoal - salários, retiradas e outras remunerações inclui participação nos lucros, honorários da diretoria e remuneração dos sócios. 3 - A categoria Comércio de veículos automotores e motocicletas exclui a cnae 45.2.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2024"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": false, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `flow_method_review_required`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M20 — PAC](../pesquisas.md#m20): Estrutura do segmento empresarial comercial, receitas, custos e pessoal. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEMPORAL: método de fluxo pendente; sem nova permissão de soma nesta revisão.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M20: Rever manual e nota da ruptura de 2024, incluindo âmbito territorial, amostragem e variáveis da 10646.

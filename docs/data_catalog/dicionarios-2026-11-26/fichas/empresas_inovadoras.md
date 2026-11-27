# Empresas que implementaram inovações

Ficha `empresas_inovadoras` · indicador `empresas_inovadoras` · **disponivel_snapshot**.

## Significado e uso

Número de empresas que implementaram inovações de produto e/ou processo, no triênio de referência (Pesquisa de Inovação, tabela SIDRA 5453). Tabela sem classificações. Fonte: IBGE - Pesquisa de Inovação.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território (Brasil) x ano x atividades da indústria, do setor de eletricidade e gás e dos serviços selecionados.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-5453` | [5453/5977](https://sidra.ibge.gov.br/tabela/5453) | Número de empresas que implementaram inovações de produto e/ou processo, no triênio de referência / Unidades | M28 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5453 / 5977

Pesquisa/produtor: Pesquisa de Inovação. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 2008, 2011, 2014, 2017.
Precisão de armazenamento/apresentação no descritor: 8 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - As informações de natureza quantitativa (dispêndios, pessoal ocupado, receita líquida de vendas e % de impactos das inovações) e também de uso de biotecnologia e de nanotecnologia se referem ao último ano do triênio de referência da pesquisa; ao passo que as informações de natureza qualitativa se referem ao triênio de referência da pesquisa.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2008", "2011", "2014", "2017"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M28 — PINTEC](../pesquisas.md#m28): Indicadores empresariais de inovação e atividades inovativas. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M28: Recuperar limiares, pesos e unidades de dispêndio por variável da 5453 e diferenças para edições anteriores.

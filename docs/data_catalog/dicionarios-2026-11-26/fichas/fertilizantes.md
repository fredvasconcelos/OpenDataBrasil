# Fertilizantes entregues ao consumidor final

Ficha `fertilizantes` · indicador `fertilizantes` · **disponivel_snapshot**.

## Significado e uso

Quantidade de fertilizantes entregue ao consumidor final (Indicadores de Desenvolvimento Sustentável, tabela SIDRA 770). Tabela sem classificações. Fonte: Anuário estatístico do setor de fertilizantes 2014, São Paulo: Associação Nacional para Difusão de Adubos, 2015; Produção agrícola municipal 2014 In: IBGE. Sistema IBGE de Recuperação Automática - SIDRA. Rio de Janeiro, 2015. Disponível em: https://sidra.ibge.gov.br/pesquisa/pam. Acesso em: nov. 2015.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Toneladas**. Grão: território (Brasil, Grande Região, UF) x ano x tipo de nutriente.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-770` | [770/2397](https://sidra.ibge.gov.br/tabela/770) | Quantidade de fertilizantes entregue ao consumidor final / Toneladas | M48 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 770 / 2397

Pesquisa/produtor: Indicadores de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 2007 a 2014.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"uf": ["2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014"], "regiao": ["2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014"], "brasil": ["2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `flow_method_review_required`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M48 — Fertilizantes](../pesquisas.md#m48): Entregas de fertilizantes ao mercado, distintas da utilização efetiva no campo. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEMPORAL: método de fluxo pendente; sem nova permissão de soma nesta revisão.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M48: Não localizada a metodologia completa do anuário 2014 citado na tabela; fonte primária atual só sustenta a distinção de unidade, não a equivalência histórica.

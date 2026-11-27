# Comercialização de agrotóxicos

Ficha `agrotoxicos` · indicador `agrotoxicos` · **disponivel_snapshot**.

## Significado e uso

Quantidade comercializada de ingredientes ativos de agrotóxicos e afins (Indicadores de Desenvolvimento Sustentável, tabela SIDRA 5802). Tabela sem classificações. Fonte: IBAMA. Relatórios de Comercialização de Agrotóxicos - Boletim Anual de Produção, Importação, Exportação e Vendas de Agrotóxicos no Brasil. Boletins 2009 - 2014, Brasília, DF: Instituto Brasileiro do Meio Ambiente e dos Recursos Naturais Renováveis, Diretoria de Qualidade Ambiental. Disponível em: <http://www.ibama.gov.br/areas-tematicas-qa/relatorio-de-comercializacao-de-agrotoxicos/pagina-3>. Acesso em: abr. 2016.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Toneladas**. Grão: território (Brasil, Grande Região, UF) x ano x classe de uso de agrotóxicos e afins.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-5802` | [5802/6535](https://sidra.ibge.gov.br/tabela/5802) | Quantidade comercializada de ingredientes ativos de agrotóxicos e afins / Toneladas | M42 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5802 / 6535

Pesquisa/produtor: Indicadores de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 2012 a 2014.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - No nível territorial Brasil, sem especificação de Unidade da Federação são contabilizadas as vendas de algumas empresas titulares de registro, que dispõem de contratos para comercialização de seus produtos por terceiros, e não conhecem com precisão a distribuição dessas vendas. 2 - Vendas com sinal negativo: representa que houve retorno à Indústria/Estoque. 3 - Para o ano de 2014 não constam quantidades comercializadas para os seguintes ingredientes ativos: a) Espalhante, Inseticida; b) Feromônios.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2012", "2013", "2014"], "uf": ["2012", "2013", "2014"], "regiao": ["2012", "2013", "2014"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `flow_method_review_required`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M42 — Comercialização de agrotóxicos](../pesquisas.md#m42): Totais de ingredientes ativos comercializados, consolidados a partir de relatórios dos registrantes. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEMPORAL: método de fluxo pendente; sem nova permissão de soma nesta revisão.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M42: Falta conferir alterações de consolidação nos demais anos; soma temporal continua pendente na trilha autorizada.

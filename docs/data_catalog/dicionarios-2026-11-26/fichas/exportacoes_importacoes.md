# Valor das exportações (2013–2015)

Ficha `exportacoes_importacoes` · indicador `exportacoes_importacoes` · **disponivel_snapshot**.

## Significado e uso

Valor das exportações (Indicadores de Desenvolvimento Sustentável, tabela SIDRA 5945). Tabela sem classificações. Fonte: Ministério de Desenvolvimento Indústria e Comércio Exterior, Secretaria de Comércio Exterior, Estatísticas de comércio exterior. Balança comercial brasileira - Unidades da Federação, BR-BC-201312. Disponível em: <http://www.desenvolvimento.gov.br/sitio/interna/interna.php?area=5&menu=4893&refr=1076>. Acesso em: jan 2016. e IBGE, Diretoria de Pesquisas, Coordenação de Contas Nacionais.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil dólares FOB**. Grão: território (Grande Região, UF) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-5945` | [5945/2153](https://sidra.ibge.gov.br/tabela/5945) | Valor das exportações / Mil dólares FOB | M49 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5945 / 2153

Pesquisa/produtor: Indicadores de Desenvolvimento Sustentável. Periodicidade: anual. Disponibilidade na fonte: 2013 a 2015.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): A soma das Unidades da Federação não corresponde ao total para o Brasil, cujo valor inclui documentos de exportação ou importação em que não consta a declaração da Unidade da Federação.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"uf": ["2013", "2014", "2015"], "regiao": ["2013", "2014", "2015"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `flow_method_review_required`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M49 — Comércio exterior](../pesquisas.md#m49): Exportações, importações e saldo comercial de mercadorias em valor FOB. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEMPORAL: método de fluxo pendente; sem nova permissão de soma nesta revisão.
- M49: Conferir regra territorial e momento de registro na edição da 5945; Brasil inclui documentos sem UF, conforme nota oficial. Soma temporal permanece pendente.

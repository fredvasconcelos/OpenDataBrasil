# Pessoal ocupado nas unidades locais industriais

Ficha `industria_uf_v631` · indicador `industria_uf_v631` · **indisponivel_snapshot**.

## Significado e uso

Pessoal ocupado em 31/12

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Pessoas**. Grão: território x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t10457-v631` | [10457/631](https://sidra.ibge.gov.br/tabela/10457) | Pessoal ocupado em 31/12 / Pessoas | M18 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 10457 / 631

Pesquisa/produtor: Pesquisa Industrial Anual - Empresa. Periodicidade: anual. Disponibilidade na fonte: 2024.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - Exclusive as variações monetárias passivas, as despesas financeiras, os resultados negativos de participações societárias e em sociedades em cota de paraticipação e as despesas não-operacionais. 2 - Para a variável Número de empresas: cada empresa é contada uma vez em cada abertura. Por isso, os totais de grupos, divisões e do Brasil podem ser menores que a soma de suas categorias.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: não. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `[]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M18 — PIA-Empresa](../pesquisas.md#m18): Estatísticas estruturais do segmento empresarial industrial. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- DADOS: KPI configurado ausente da navegação N2 no snapshot; candidato não significa publicado.
- M18: Compatibilizar o método da edição 2024 da tabela 10457 com a nota consultada de 2021; fórmulas e pesos não foram integralmente recuperados.

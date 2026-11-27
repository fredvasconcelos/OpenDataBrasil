# Desflorestamento na Amazônia Legal

Ficha `desflorestamento_amazonia` · indicador `desflorestamento_amazonia` · **disponivel_snapshot**.

## Significado e uso

Desflorestamento bruto anual na Amazônia Legal, em 01/08 (Indicadores de Desenvolvimento Sustentável, tabela SIDRA 896). Tabela sem classificações. Fonte: Projeto PRODES: Monitoramento da Floresta Amazônica Brasileira por Satélite. São José dos Campos: Instituto Nacional de Pesquisas Espaciais - INPE, 2017. Disponível em: <http://www.obt.inpe.br/prodes/index.html>. Acesso em: 26 de maio de 2017; e Área territorial oficial. Rio de Janeiro: IBGE, [2015]. Disponível em: <http://www.ibge.gov.br/home/geociencias/areaterritorial/principal.shtm>. Acesso em: 26 de maio de 2017.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Quilômetros quadrados**. Grão: território (UF) x ano.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-896` | [896/2144](https://sidra.ibge.gov.br/tabela/896) | Desflorestamento bruto anual na Amazônia Legal, em 01/08 / Quilômetros quadrados | M41 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 896 / 2144

Pesquisa/produtor: Indicadores de Desenvolvimento Sustentável. Periodicidade: anos de referência da pesquisa. Disponibilidade na fonte: 1991 a 1992, 1994 a 2015.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): 1 - Os dados para 1994 são referentes ao período entre agosto de 1992 a agosto de 1994 (para 2 anos). Para os demais anos considera-se agosto do ano anterior a agosto do ano de referência. 2 - As áreas desflorestadas no Estado do Maranhão são referentes apenas à porção que faz parte da Amazônia Legal (oeste do Estado). Portanto, como denominador da taxa de desflorestamento foi usada a área desse Estado relativa à Amazônia Legal. 3 - Os dados do desflorestamento bruto acumulado foram gerados somando-se a área desflorestada bruta acumulada até o ano de 1991 (fornecida pelo INPE) com os valores atualizados das áreas desflorestadas anualmente.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"uf": ["1991", "1992", "1994", "1995", "1996", "1997", "1998", "1999", "2000", "2001", "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `flow_method_review_required`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M41 — PRODES](../pesquisas.md#m41): Área de desflorestamento bruto monitorada por satélite na Amazônia Legal. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEMPORAL: método de fluxo pendente; sem nova permissão de soma nesta revisão.
- M41: Rever método de cada edição histórica; os 30 fluxos pendentes incluem desflorestamento e permanecem bloqueados.

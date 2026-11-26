# PIB: variação acumulada no ano

Ficha `variacao_pib_trimestral_v6563` · indicador `variacao_pib_trimestral_v6563` · **disponivel_snapshot**.

## Significado e uso

Taxa acumulada ao longo do ano (em relação ao mesmo período do ano anterior)

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território x trimestre.
- Aditividade territorial configurada: `non_additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t5932-v6563` | [5932/6563](https://sidra.ibge.gov.br/tabela/5932) | Taxa acumulada ao longo do ano (em relação ao mesmo período do ano anterior) / % | M33 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 5932 / 6563

Pesquisa/produtor: Contas Nacionais Trimestrais. Periodicidade: trimestral. Disponibilidade na fonte: 1º trimestre 1996 a 2º trimestre 2026.
Precisão de armazenamento/apresentação no descritor: 1 / 1 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["1996T1", "1996T2", "1996T3", "1996T4", "1997T1", "1997T2", "1997T3", "1997T4", "1998T1", "1998T2", "1998T3", "1998T4", "1999T1", "1999T2", "1999T3", "1999T4", "2000T1", "2000T2", "2000T3", "2000T4", "2001T1", "2001T2", "2001T3", "2001T4", "2002T1", "2002T2", "2002T3", "2002T4", "2003T1", "2003T2", "2003T3", "2003T4", "2004T1", "2004T2", "2004T3", "2004T4", "2005T1", "2005T2", "2005T3", "2005T4", "2006T1", "2006T2", "2006T3", "2006T4", "2007T1", "2007T2", "2007T3", "2007T4", "2008T1", "2008T2", "2008T3", "2008T4", "2009T1", "2009T2", "2009T3", "2009T4", "2010T1", "2010T2", "2010T3", "2010T4", "2011T1", "2011T2", "2011T3", "2011T4", "2012T1", "2012T2", "2012T3", "2012T4", "2013T1", "2013T2", "2013T3", "2013T4", "2014T1", "2014T2", "2014T3", "2014T4", "2015T1", "2015T2", "2015T3", "2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": false, "seasonal_sum": false, "accumulation_rule": null}`.

Parecer temporal preservado: `comparison_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M33 — Contas Nacionais](../pesquisas.md#m33): Produção, renda, despesa, investimento e poupança macroeconômicos. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- M33: Fórmulas de cada taxa e ajuste sazonal, encadeamento e pesos precisam do manual integral; manter parecer temporal de cada variável.

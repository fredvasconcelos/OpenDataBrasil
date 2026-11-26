# Produção de ovos de galinha

Ficha `ovos_produzidos` · indicador `ovos_produzidos` · **disponivel_snapshot**.

## Significado e uso

Quantidade de ovos produzidos (Produção de Ovos de Galinha, tabela SIDRA 7524). Tabela sem classificações. Fonte: IBGE - Produção de Ovos de Galinha.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Mil dúzias**. Grão: território (Brasil, UF) x trimestre x finalidade da produção | referência temporal.
- Aditividade territorial configurada: `additive`; temporal: `sum`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-7524` | [7524/29](https://sidra.ibge.gov.br/tabela/7524) | Quantidade de ovos produzidos / Mil dúzias | M14 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 7524 / 29

Pesquisa/produtor: Produção de Ovos de Galinha. Periodicidade: trimestral. Disponibilidade na fonte: 1º trimestre 1987 a 2º trimestre 2026.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Até o 4º trimestre de 2011: As informações não correspondem às produções totais das Unidades da Federação, uma vez que são pesquisados apenas os estabelecimentos com 10.000 ou mais galinhas poedeiras. 2 - A partir do 1º trimestre de 2012: As informações não correspondem às produções totais das Unidades da Federação, uma vez que são pesquisados apenas os estabelecimentos com capacidade de alojamento de pelo menos 10.000 galinhas poedeiras. 3 - O número de galinhas poedeiras refere-se à média do plantel existente no último dia de cada mês do trimestre. 4 - O número de informantes se repete nos meses de cada trimestre devido à periodicidade de coleta da pesquisa ser trimestral. 5 - Até o 4º trimestre de 2005 os dados das Unidades da Federação com menos de 4 (quatro) informantes estão desidentificados com o caracter X. A partir do 1º trimestre de 2006 a desidentificação passou a ser feita para menos de 3 (três) informantes. 6 - Os dados dos 4 trimestres do ano são preliminares até a divulgação dos dados do 1° trimestre do ano seguinte.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"regiao": ["1987T1", "1987T2", "1987T3", "1987T4", "1988T1", "1988T2", "1988T3", "1988T4", "1989T1", "1989T2", "1989T3", "1989T4", "1990T1", "1990T2", "1990T3", "1990T4", "1991T1", "1991T2", "1991T3", "1991T4", "1992T1", "1992T2", "1992T3", "1992T4", "1993T1", "1993T2", "1993T3", "1993T4", "1994T1", "1994T2", "1994T3", "1994T4", "1995T1", "1995T2", "1995T3", "1995T4", "1996T1", "1996T2", "1996T3", "1996T4", "1997T1", "1997T2", "1997T3", "1997T4", "1998T1", "1998T2", "1998T3", "1998T4", "1999T1", "1999T2", "1999T3", "1999T4", "2000T1", "2000T2", "2000T3", "2000T4", "2001T1", "2001T2", "2001T3", "2001T4", "2002T1", "2002T2", "2002T3", "2002T4", "2003T1", "2003T2", "2003T3", "2003T4", "2004T1", "2004T2", "2004T3", "2004T4", "2005T1", "2005T2", "2005T3", "2005T4", "2006T1", "2006T2", "2006T3", "2006T4", "2007T1", "2007T2", "2007T3", "2007T4", "2008T1", "2008T2", "2008T3", "2008T4", "2009T1", "2009T2", "2009T3", "2009T4", "2010T1", "2010T2", "2010T3", "2010T4", "2011T1", "2011T2", "2011T3", "2011T4", "2012T1", "2012T2", "2012T3", "2012T4", "2013T1", "2013T2", "2013T3", "2013T4", "2014T1", "2014T2", "2014T3", "2014T4", "2015T1", "2015T2", "2015T3", "2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"], "uf": ["1987T1", "1987T2", "1987T3", "1987T4", "1988T1", "1988T2", "1988T3", "1988T4", "1989T1", "1989T2", "1989T3", "1989T4", "1990T1", "1990T2", "1990T3", "1990T4", "1991T1", "1991T2", "1991T3", "1991T4", "1992T1", "1992T2", "1992T3", "1992T4", "1993T1", "1993T2", "1993T3", "1993T4", "1994T1", "1994T2", "1994T3", "1994T4", "1995T1", "1995T2", "1995T3", "1995T4", "1996T1", "1996T2", "1996T3", "1996T4", "1997T1", "1997T2", "1997T3", "1997T4", "1998T1", "1998T2", "1998T3", "1998T4", "1999T1", "1999T2", "1999T3", "1999T4", "2000T1", "2000T2", "2000T3", "2000T4", "2001T1", "2001T2", "2001T3", "2001T4", "2002T1", "2002T2", "2002T3", "2002T4", "2003T1", "2003T2", "2003T3", "2003T4", "2004T1", "2004T2", "2004T3", "2004T4", "2005T1", "2005T2", "2005T3", "2005T4", "2006T1", "2006T2", "2006T3", "2006T4", "2007T1", "2007T2", "2007T3", "2007T4", "2008T1", "2008T2", "2008T3", "2008T4", "2009T1", "2009T2", "2009T3", "2009T4", "2010T1", "2010T2", "2010T3", "2010T4", "2011T1", "2011T2", "2011T3", "2011T4", "2012T1", "2012T2", "2012T3", "2012T4", "2013T1", "2013T2", "2013T3", "2013T4", "2014T1", "2014T2", "2014T3", "2014T4", "2015T1", "2015T2", "2015T3", "2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"], "brasil": ["1987T1", "1987T2", "1987T3", "1987T4", "1988T1", "1988T2", "1988T3", "1988T4", "1989T1", "1989T2", "1989T3", "1989T4", "1990T1", "1990T2", "1990T3", "1990T4", "1991T1", "1991T2", "1991T3", "1991T4", "1992T1", "1992T2", "1992T3", "1992T4", "1993T1", "1993T2", "1993T3", "1993T4", "1994T1", "1994T2", "1994T3", "1994T4", "1995T1", "1995T2", "1995T3", "1995T4", "1996T1", "1996T2", "1996T3", "1996T4", "1997T1", "1997T2", "1997T3", "1997T4", "1998T1", "1998T2", "1998T3", "1998T4", "1999T1", "1999T2", "1999T3", "1999T4", "2000T1", "2000T2", "2000T3", "2000T4", "2001T1", "2001T2", "2001T3", "2001T4", "2002T1", "2002T2", "2002T3", "2002T4", "2003T1", "2003T2", "2003T3", "2003T4", "2004T1", "2004T2", "2004T3", "2004T4", "2005T1", "2005T2", "2005T3", "2005T4", "2006T1", "2006T2", "2006T3", "2006T4", "2007T1", "2007T2", "2007T3", "2007T4", "2008T1", "2008T2", "2008T3", "2008T4", "2009T1", "2009T2", "2009T3", "2009T4", "2010T1", "2010T2", "2010T3", "2010T4", "2011T1", "2011T2", "2011T3", "2011T4", "2012T1", "2012T2", "2012T3", "2012T4", "2013T1", "2013T2", "2013T3", "2013T4", "2014T1", "2014T2", "2014T3", "2014T4", "2015T1", "2015T2", "2015T3", "2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": true, "seasonal_sum": true, "accumulation_rule": "sum"}`.

Parecer temporal preservado: `sum_method_supported`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M14 — Ovos](../pesquisas.md#m14): Produção de ovos em estabelecimentos do painel pesquisado. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M14: Fechar comparabilidade histórica do limiar de inclusão e unidades por variável antes de qualquer nova agregação.

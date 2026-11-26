# Abate de bovinos

Ficha `abate_bovinos` · indicador `abate_bovinos` · **disponivel_snapshot**.

## Significado e uso

Animais abatidos (Pesquisa Trimestral do Abate de Animais, tabela SIDRA 1092). Tabela sem classificações. Fonte: IBGE - Pesquisa Trimestral do Abate de Animais.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Cabeças**. Grão: território (Brasil, UF) x trimestre x tipo de rebanho bovino | tipo de inspeção | referência temporal.
- Aditividade territorial configurada: `additive`; temporal: `sum`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-1092` | [1092/284](https://sidra.ibge.gov.br/tabela/1092) | Animais abatidos / Cabeças | M12 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 1092 / 284

Pesquisa/produtor: Pesquisa Trimestral do Abate de Animais. Periodicidade: trimestral. Disponibilidade na fonte: 1º trimestre 1997 a 2º trimestre 2026.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: True / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Os dados divulgados são oriundos de estabelecimentos que estão sob inspeção sanitária federal, estadual ou municipal. 2 - Os dados das Unidades da Federação com menos de 3 informantes estão desidentificados com o caracter X. 3 - O número de informantes se repete nos meses de cada trimestre devido à periodicidade de coleta da pesquisa ser trimestral. 4 - A pesquisa do abate sofreu alterações conceituais a partir de 2012. As categorias de novilhos precoces, vitelos e novilhos foram fundidos em uma só: novilhos. O mesmo vale para novilhas. 5 - Bovinos - gado doméstico, dividido em categorias conforme sexo e idade: Boi - bovino macho adulto, com 2 anos de idade ou mais. Inclui o macho não castrado (touro). Vaca - bovino fêmea adulta, com 2 anos de idade ou mais, independente de já ter parido ou não. Novilho - bovino macho jovem, com menos de 2 anos de idade. Inclui vitelo, bezerro e novilho (precoce ou não). Novilha - bovino fêmea jovem, com menos de 2 anos de idade. Inclui vitela, bezerra e novilha (precoce ou não). 6 - Peso da Carcaça - peso da carcaça quente (em Kg), entendendo-se como carcaça: o animal abatido, formado das massas musculares e ossos, desprovido de cabeça, mocotós, cauda, couro, órgãos e vísceras torácicas e abdominais, tecnicamente preparado. Nos frangos, é facultativa a retirada dos rins, pés, pescoço e cabeça. Nos suínos a carcaça pode ou não incluir o couro, a cabeça e os pés. 7 - Os dados dos 4 trimestres do ano são preliminares até a divulgação dos dados do 1° trimestre do ano seguinte.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["1997T1", "1997T2", "1997T3", "1997T4", "1998T1", "1998T2", "1998T3", "1998T4", "1999T1", "1999T2", "1999T3", "1999T4", "2000T1", "2000T2", "2000T3", "2000T4", "2001T1", "2001T2", "2001T3", "2001T4", "2002T1", "2002T2", "2002T3", "2002T4", "2003T1", "2003T2", "2003T3", "2003T4", "2004T1", "2004T2", "2004T3", "2004T4", "2005T1", "2005T2", "2005T3", "2005T4", "2006T1", "2006T2", "2006T3", "2006T4", "2007T1", "2007T2", "2007T3", "2007T4", "2008T1", "2008T2", "2008T3", "2008T4", "2009T1", "2009T2", "2009T3", "2009T4", "2010T1", "2010T2", "2010T3", "2010T4", "2011T1", "2011T2", "2011T3", "2011T4", "2012T1", "2012T2", "2012T3", "2012T4", "2013T1", "2013T2", "2013T3", "2013T4", "2014T1", "2014T2", "2014T3", "2014T4", "2015T1", "2015T2", "2015T3", "2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"], "uf": ["1997T1", "1997T2", "1997T3", "1997T4", "1998T1", "1998T2", "1998T3", "1998T4", "1999T1", "1999T2", "1999T3", "1999T4", "2000T1", "2000T2", "2000T3", "2000T4", "2001T1", "2001T2", "2001T3", "2001T4", "2002T1", "2002T2", "2002T3", "2002T4", "2003T1", "2003T2", "2003T3", "2003T4", "2004T1", "2004T2", "2004T3", "2004T4", "2005T1", "2005T2", "2005T3", "2005T4", "2006T1", "2006T2", "2006T3", "2006T4", "2007T1", "2007T2", "2007T3", "2007T4", "2008T1", "2008T2", "2008T3", "2008T4", "2009T1", "2009T2", "2009T3", "2009T4", "2010T1", "2010T2", "2010T3", "2010T4", "2011T1", "2011T2", "2011T3", "2011T4", "2012T1", "2012T2", "2012T3", "2012T4", "2013T1", "2013T2", "2013T3", "2013T4", "2014T1", "2014T2", "2014T3", "2014T4", "2015T1", "2015T2", "2015T3", "2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"], "regiao": ["1997T1", "1997T2", "1997T3", "1997T4", "1998T1", "1998T2", "1998T3", "1998T4", "1999T1", "1999T2", "1999T3", "1999T4", "2000T1", "2000T2", "2000T3", "2000T4", "2001T1", "2001T2", "2001T3", "2001T4", "2002T1", "2002T2", "2002T3", "2002T4", "2003T1", "2003T2", "2003T3", "2003T4", "2004T1", "2004T2", "2004T3", "2004T4", "2005T1", "2005T2", "2005T3", "2005T4", "2006T1", "2006T2", "2006T3", "2006T4", "2007T1", "2007T2", "2007T3", "2007T4", "2008T1", "2008T2", "2008T3", "2008T4", "2009T1", "2009T2", "2009T3", "2009T4", "2010T1", "2010T2", "2010T3", "2010T4", "2011T1", "2011T2", "2011T3", "2011T4", "2012T1", "2012T2", "2012T3", "2012T4", "2013T1", "2013T2", "2013T3", "2013T4", "2014T1", "2014T2", "2014T3", "2014T4", "2015T1", "2015T2", "2015T3", "2015T4", "2016T1", "2016T2", "2016T3", "2016T4", "2017T1", "2017T2", "2017T3", "2017T4", "2018T1", "2018T2", "2018T3", "2018T4", "2019T1", "2019T2", "2019T3", "2019T4", "2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2", "2021T3", "2021T4", "2022T1", "2022T2", "2022T3", "2022T4", "2023T1", "2023T2", "2023T3", "2023T4", "2024T1", "2024T2", "2024T3", "2024T4", "2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": true, "seasonal_sum": true, "accumulation_rule": "sum"}`.

Parecer temporal preservado: `sum_method_supported`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M12 — Abate](../pesquisas.md#m12): Quantidade de animais abatidos e peso das carcaças por espécie. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M12: Rever sigilo por estabelecimento e mudança de painel em cada edição; número de informantes não recebe soma temporal.

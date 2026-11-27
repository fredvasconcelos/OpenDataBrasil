# Índice de Preços ao Produtor

Ficha `ipp` · indicador `ipp` · **disponivel_snapshot**.

## Significado e uso

IPP - Variação mês/mês imediatamente anterior (M/M-1) (Índice de Preços ao Produtor, tabela SIDRA 6904). Tabela sem classificações. Fonte: IBGE - Índice de Preços ao Produtor.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **%**. Grão: território (Brasil) x mes x grandes categorias econômicas.
- Aditividade territorial configurada: `non_additive`; temporal: `compound`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-6904` | [6904/1396](https://sidra.ibge.gov.br/tabela/6904) | IPP - Variação mês/mês imediatamente anterior (M/M-1) / % | M32 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 6904 / 1396

Pesquisa/produtor: Índice de Preços ao Produtor. Periodicidade: mensal. Disponibilidade na fonte: dezembro 2013 a setembro 2026.
Precisão de armazenamento/apresentação no descritor: 2 / 2 casas. Soma de períodos/territórios na fonte: False / False.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `{"brasil": ["2013M12", "2014M01", "2014M02", "2014M03", "2014M04", "2014M05", "2014M06", "2014M07", "2014M08", "2014M09", "2014M10", "2014M11", "2014M12", "2015M01", "2015M02", "2015M03", "2015M04", "2015M05", "2015M06", "2015M07", "2015M08", "2015M09", "2015M10", "2015M11", "2015M12", "2016M01", "2016M02", "2016M03", "2016M04", "2016M05", "2016M06", "2016M07", "2016M08", "2016M09", "2016M10", "2016M11", "2016M12", "2017M01", "2017M02", "2017M03", "2017M04", "2017M05", "2017M06", "2017M07", "2017M08", "2017M09", "2017M10", "2017M11", "2017M12", "2018M01", "2018M02", "2018M03", "2018M04", "2018M05", "2018M06", "2018M07", "2018M08", "2018M09", "2018M10", "2018M11", "2018M12", "2019M01", "2019M02", "2019M03", "2019M04", "2019M05", "2019M06", "2019M07", "2019M08", "2019M09", "2019M10", "2019M11", "2019M12", "2020M01", "2020M02", "2020M03", "2020M04", "2020M05", "2020M06", "2020M07", "2020M08", "2020M09", "2020M10", "2020M11", "2020M12", "2021M01", "2021M02", "2021M03", "2021M04", "2021M05", "2021M06", "2021M07", "2021M08", "2021M09", "2021M10", "2021M11", "2021M12", "2022M01", "2022M02", "2022M03", "2022M04", "2022M05", "2022M06", "2022M07", "2022M08", "2022M09", "2022M10", "2022M11", "2022M12", "2023M01", "2023M02", "2023M03", "2023M04", "2023M05", "2023M06", "2023M07", "2023M08", "2023M09", "2023M10", "2023M11", "2023M12", "2024M01", "2024M02", "2024M03", "2024M04", "2024M05", "2024M06", "2024M07", "2024M08", "2024M09", "2024M10", "2024M11", "2024M12", "2025M01", "2025M02", "2025M03", "2025M04", "2025M05", "2025M06", "2025M07", "2025M08", "2025M09", "2025M10", "2025M11", "2025M12", "2026M01", "2026M02", "2026M03", "2026M04", "2026M05", "2026M06", "2026M07", "2026M08", "2026M09"]}`.

Capacidades temporais do snapshot de implementação: `{"isolate": true, "accumulate": true, "seasonal_sum": false, "accumulation_rule": "compound"}`.

Parecer temporal preservado: `contiguous_compound_only`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M32 — IPP](../pesquisas.md#m32): Mudança dos preços de venda recebidos por produtores domésticos das indústrias extrativas e de transformação. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- TEXTO: descrição contém “Tabela sem classificações”, mas há classificações oficiais; escopo do recorte precisa de revisão editorial.
- M32: Ler fórmula e pesos do manual vigente por edição; equivalência 6904/1394 da candidata permanece não homologada.

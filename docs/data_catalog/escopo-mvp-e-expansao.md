# Escopo de detalhamento do MVP e plano de expansão

**Decisão do mantenedor (2026-11-05):** no MVP, as populações especiais
(indígenas e quilombolas) e a população geral são apresentadas no portal com
**Total e sexo**. **Grupos de idade, idades simples e meses de vida ficam
fora do MVP.** O plano abaixo registra o que já existe, o que falta e
como ampliar o detalhe depois, sem precisar refazer a pesquisa.

Os dados de idade que **já estão** na Gold (tabelas 9971, 9970 e 9954) **não são
apagados**. Eles continuam no release, consultáveis por `odb query` e pela
exportação, mas o portal do MVP não os oferece. Liberá-los no portal será uma
mudança de configuração.

## 1. O que a Gold tem hoje (release `c9c90f26`)

| População | Tabela | Desagregações publicadas | Territórios |
|---|---|---|---|
| Geral | 6579 | nenhuma (2001–2026) | Brasil, Região, UF, Município |
| Geral | 4714 | nenhuma (2022) | Brasil, Região, UF, Município |
| Geral | 9605 | cor ou raça (2010, 2022) | Brasil, Região, UF, Município |
| Indígena | 9718 | quesito de declaração × localização | Brasil, Região, UF, Município |
| Indígena | 9971 | **sexo** × grupos de idade × localização × situação | Brasil, Região, UF, Município |
| Indígena | 9970 | idade simples e meses × localização × situação | Brasil, Região, UF |
| Indígena | 9954 | **sexo** × grupos de idade × situação | Brasil, Região, UF, terras indígenas, partes por UF, Coordenações da Funai, Amazônia Legal |
| Quilombola | 9578 | localização | Brasil, Região, UF, Município |
| Quilombola | 9723 | nenhuma | Brasil, Região, UF, Município, territórios quilombolas, partes por UF, Amazônia Legal |

O sexo das pessoas indígenas já está publicado: na 9971 e na 9954, a categoria
"Total" de idade traz o valor por sexo. **Faltam a população geral por sexo e
os quilombolas por sexo.**

## 2. Tabelas para completar o MVP (sexo)

Conferidas na API `/values` em 2026-11-05 (HTTP 200, cabeçalhos e totais do
Brasil abaixo). Os níveis N134 da 9765 e a descrição completa das tabelas
ainda precisam ser confirmados com o mantenedor (o `desctabapi` responde 403,
ver KI-006).

| Tabela | Conteúdo | Variáveis | Classificações | Conferência |
|---|---|---|---|---|
| **9514** | População residente por sexo, idade e forma de declaração da idade (Censo 2022) | 93 | c2 sexo (6794 Total, 4 Homens, 5 Mulheres), c287 idade (100362 Total), c286 forma de declaração (113635 Total) | Brasil 203.080.756 = 98.532.431 H + 104.548.325 M; N6 com 5.570 municípios; só 2022 |
| **8176** | Pessoas quilombolas por sexo, idade e localização do domicílio | 4709 (e o percentual 1004709, não usado) | c2 sexo, c287 idade (100362 Total), c2661 localização (32776 Total + 2) | Brasil 1.330.186 = 665.353 H + 664.833 M (igual à 9578); N6 com 5.570 municípios |
| **9765** | Pessoas em territórios quilombolas por sexo e idade | 6559, 7079 (e os percentuais 1006559 e 1007079, não usados) | c2 sexo, c287 idade (100362 Total) | Brasil 203.574 residentes (104.555 H + 99.019 M) e 167.769 quilombolas (86.284 H + 81.485 M), iguais à 9723; N1145 495, N145 503, N6 5.570, N131 1 |

Volume para o MVP (Total de idade, limite de 50.000 valores por consulta):

| Tabela | Cálculo | Valores | Requisições |
|---|---|---|---|
| 9514 | 5.603 territórios × 3 sexos | 16.809 | 1 |
| 8176 | 5.603 × 3 sexos × 3 localizações | 50.427 | 3 (`split_by_classification = "c2661"`) |
| 9765 | 6.611 territórios × 2 variáveis × 3 sexos | 39.666 | 1 |

## 3. Expansões futuras catalogadas

Estimativas com a regra `valores = territórios × variáveis × produto das
categorias`. Os grupos de idade das tabelas ainda não ingeridas supõem o Total
mais os 21 grupos quinquenais da c287 (como na 9954), **a confirmar** na
descrição da tabela.

| Detalhe | Tabela | Já ingerido? | Valores estimados | Esforço |
|---|---|---|---|---|
| Indígenas por grupos de idade (municípios) | 9971 | sim | — | só configuração do portal |
| Indígenas em terras indígenas por grupos de idade | 9954 | sim | — | só configuração do portal |
| Indígenas por idade simples (até UF) | 9970 | sim | — | só configuração do portal |
| Indígenas por idade simples nos municípios | 9970 | não | ~6,8 milhões | nova ingestão (nível N6) |
| Indígenas em terras indígenas por idade simples | 9954 | não | ~3,0 milhões | ampliar c287 para `all` |
| 9954 com o nível municipal | 9954 | não | ~16,5 milhões (com idades simples) | ampliar níveis; a 9718 já cobre o total municipal |
| Quilombolas por grupos de idade | 8176 | não | ~1,1 milhão (≥ 23 requisições) | ampliar c287 |
| Territórios quilombolas por grupos de idade | 9765 | não | ~0,87 milhão (≥ 18 requisições) | ampliar c287 |
| População geral por idade | 9514 | não | a dimensionar (c287 completa) | ampliar c287 |
| Série histórica por sexo (Censos anteriores) | a identificar | não | — | pesquisar a tabela; não inventar código |

## 4. Receita para ampliar o detalhe

1. **Descrição da tabela.** Pedir ao mantenedor a descrição do SIDRA
   (níveis, variáveis, classificações e categorias) e, para níveis especiais,
   as listas de unidades. Registrar em [`ibge-niveis-territoriais.md`](ibge-niveis-territoriais.md)
   quando houver níveis novos.
2. **Conferir na API.** Uma consulta pequena em `/values` (nível N1 e Total).
   Não fazer varredura de códigos.
3. **Dimensionar.** Calcular os valores por período. Acima de 50.000, usar
   `split_by_variable` e/ou `split_by_classification` (as categorias divididas
   precisam estar listadas, não `all`). Conferir o espaço em disco.
4. **Fonte.** Editar o dataset em [`configs/sources/ibge.toml`](../../configs/sources/ibge.toml)
   (`classifications`, `territorial_levels`, `estimated_values_per_period`,
   `min_rows`) e a versão reduzida em `tests/fixtures/sources/ibge-test.toml`.
5. **Fixture.** Capturar a resposta real reduzida em `tests/fixtures/ibge/sidra/`
   e registrar em `tests/fixtures/ibge/README.md`.
6. **Semântica.** Em [`configs/indicators/demografia.toml`](../../configs/indicators/demografia.toml):
   classificação e partições (`exhaustive`, `parent` para categorias
   aninhadas), fato e indicador; subir `config_version`.
7. **Pipeline.** `odb ingest run`, `odb silver build`, `odb gold build --activate`,
   `odb quality gold`. Conferir a reconciliação (soma das categorias = Total,
   com `X` tratado como incompleto).
8. **Portal.** Liberar a classificação na configuração de exposição do portal
   (criada na Fase 5).
9. **Documentação.** Atualizar este arquivo, [`ibge.md`](ibge.md) e
   [`gold-demografia.md`](gold-demografia.md).

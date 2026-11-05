# Fixtures do IBGE

Respostas **reais** capturadas em 2026-11-03 com
`curl -A "OpenDataBrasil/0.1 (+https://github.com/fredvasconcelos/OpenDataBrasil)"`.
Não edite: os testes dependem dos bytes exatos.

| Arquivo | URL (`https://apisidra.ibge.gov.br/values` + …) | HTTP | Observação |
|---|---|---|---|
| `sidra/t6579_n1_periods.json` | `/t/6579/n1/all/v/9324/p/all` | 200 | 22 anos (2001–2026, sem 2007, 2010, 2022 e 2023) |
| `sidra/t6579_n3_p2024.json` | `/t/6579/n3/all/v/9324/p/2024` | 200 | 27 UFs |
| `sidra/t6579_n3_p2025.json` | `/t/6579/n3/all/v/9324/p/2025` | 200 | 27 UFs |
| `sidra/t6579_n3_p1900_empty.json` | `/t/6579/n3/all/v/9324/p/1900` | **200** | só o cabeçalho: período inexistente não gera erro HTTP |
| `sidra/t4714_n1_periods.json` | `/t/4714/n1/all/v/93/p/all` | 200 | só 2022 |
| `sidra/t4714_n3_p2022.json` | `/t/4714/n3/all/v/all/p/2022` | 200 | 27 UFs × variáveis 93, 6318, 614 |
| `sidra/error_table_not_found.txt` | `/t/999999/n1/all/v/all/p/all` | **400** | texto `Tabela 999999: Tabela inválida` |
| `sidra/t9605_n1_periods.json` | `/t/9605/n1/all/v/93/p/all/c86/all` | 200 | 2010 e 2022 (capturado em 2026-11-04) |
| `sidra/t9605_n1n2n3_p2010.json`, `…_p2022.json` | `/t/9605/n1/all/n2/all/n3/all/v/93/p/<ano>/c86/all` | 200 | 6 categorias × 33 territórios |
| `sidra/t9718_n1_periods.json` | `/t/9718/n1/all/v/93/p/all/c1714/all/c2661/32776,12869,12870` | 200 | só 2022 |
| `sidra/t9718_n1n2n3_p2022_v<var>_c2661-<cat>.json` | `/t/9718/n1/all/n2/all/n3/all/v/<var>/p/2022/c1714/all/c2661/<cat>` | 200 | 9 arquivos: variáveis 93, 350, 4727 × localizações 32776, 12869, 12870; 4 quesitos × 33 territórios cada |
| `sidra/t9971_n1_periods.json`, `sidra/t9971_n1_p2022.json` | `/t/9971/n1/all/v/350/p/<all\|2022>/c1/all/c2/all/c2661/all/c58/all` | 200 | 513 combinações (situação × sexo × localização × grupo de idade) |
| `sidra/t9970_n1_periods.json`, `sidra/t9970_n1_p2022.json` | `/t/9970/n1/all/v/350/p/<all\|2022>/c1/all/c2661/all/c287/all` | 200 | 1.206 combinações (situação × localização × 134 idades) |
| `sidra/t9723_n1_periods.json`, `sidra/t9723_n1n2n3n131n134n145n1145_p2022.json` | `/t/9723/n1/all/v/6559/p/all` e `/t/9723/n1/all/n2/all/n3/all/n131/all/n134/all/n145/all/n1145/all/v/6559,7079,7080/p/2022` | 200 | níveis especiais: 495 territórios quilombolas, 503 partes por UF, Amazônia Legal e 9 partes de UF (3.123 valores) |
| `sidra/t9954_n1_periods.json`, `sidra/t9954_n1n3n125n1124n1125_p2022_v<var>_c1-6795_c2-6794_c287-100362.json` | `/t/9954/n1/all/v/576/p/all/c1/6795/c2/6794/c287/100362` e `/t/9954/n1/all/n3/all/n125/all/n1124/all/n1125/all/v/<var>/p/2022/c1/6795/c2/6794/c287/100362` | 200 | variáveis 576 e 1432, só os Totais de sexo, idade e situação; 573 terras, 602 partes por UF e 39 Coordenações Regionais da Funai |
| `sidra/t9578_n1_periods.json` | `/t/9578/n1/all/v/4709/p/all/c2661/all` | 200 | só 2022 |
| `sidra/t9578_n1n2n3_p2022_v<var>.json` | `/t/9578/n1/all/n2/all/n3/all/v/<var>/p/2022/c2661/all` | 200 | 3 arquivos: variáveis 4709, 93, 4728; 3 localizações × 33 territórios |
| `sidra/t9606_n1_periods.json`, `sidra/t9606_n1n2n3_p<ano>.json` | `/t/9606/n1/all/v/93/p/all/c2/all/c287/100362/c86/all` e `/t/9606/n1/all/n2/all/n3/all/v/93/p/<2010\|2022>/c2/all/c287/100362/c86/all` | 200 | 2010 e 2022; 6 cores ou raças × 3 sexos × 33 territórios (capturado em 2026-11-05) |
| `sidra/t8176_n1_periods.json`, `sidra/t8176_n1n2n3_p2022.json` | `/t/8176/n1/all/v/4709/p/all/c2/all/c2661/all/c287/100362` e `/t/8176/n1/all/n2/all/n3/all/v/4709/p/2022/c2/all/c2661/all/c287/100362` | 200 | 3 sexos × 3 localizações × 33 territórios (capturado em 2026-11-05) |
| `sidra/t9765_n1_periods.json`, `sidra/t9765_n1n2n3n131n134n145n1145_p2022.json` | `/t/9765/n1/all/v/6559/p/all/c2/all/c287/100362` e `/t/9765/n1/all/n2/all/n3/all/n131/all/n134/all/n145/all/n1145/all/v/6559,7079/p/2022/c2/all/c287/100362` | 200 | 2 variáveis × 3 sexos × 1.041 territórios (6.246 valores; capturado em 2026-11-05) |

Dados **sintéticos** usados nos testes, gerados em código e identificados como tal:

- respostas SIDRA de anos sem fixture: cópia de `t6579_n3_p2025.json` com o
  período trocado (`tests/ingestion_support.py`);
- ZIP da DTB: arquivo com os mesmos nomes de membros do `DTB_2025.zip` real
  e conteúdo fictício. O arquivo real (1,6 MB, SHA-256 `d077a0e4…dad27`) não é
  versionado.

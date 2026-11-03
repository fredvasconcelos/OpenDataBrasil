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

Dados **sintéticos** usados nos testes, gerados em código e identificados como tal:

- respostas SIDRA de anos sem fixture: cópia de `t6579_n3_p2025.json` com o
  período trocado (`tests/ingestion_support.py`);
- ZIP da DTB: arquivo com os mesmos nomes de membros do `DTB_2025.zip` real
  e conteúdo fictício. O arquivo real (1,6 MB, SHA-256 `d077a0e4…dad27`) não é
  versionado.

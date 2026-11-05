# Runbook: exportação da Gold para análise local

`odb gold export` copia um **release publicado** para uma pasta do host, em
Parquet e DuckDB, para exploração no DBeaver, em Python ou em notebooks. A
cópia é **descartável e não oficial**: a fonte oficial continua sendo a Gold
em Delta Lake (ADR-0008, §10.8).

## Gerar

```bash
mkdir -p data/exports                     # uma vez (a pasta fica fora do Git)
docker compose --profile data run --rm worker odb gold export                 # release ativo
docker compose --profile data run --rm worker odb gold export --release <id>  # release específico
docker compose --profile data run --rm worker odb gold export --force         # refaz
```

O worker monta `./data/exports` (ou `ODB_EXPORT_HOST_DIR`) em `/export`. O
resultado fica em:

```text
data/exports/demografia/
  latest.json                     release exportado mais recentemente
  <release_id>/
    gold.duckdb                   tabelas Gold + views `observacoes` e `arvore_indicadores`
    parquet/<tabela>.parquet      tabelas Gold com os tipos originais (decimal(38,6))
    manifest.json                 versões Delta, linhas e SHA-256 de cada arquivo
    LEIAME.txt                    procedência, licença e regras de leitura
```

Cada release tem a sua pasta. Um release novo não altera as exportações
anteriores, e qualquer uma pode ser apagada. O release ativo
(`35489cf6…`, licença em `requires_review`) é
**só para uso interno**.

## DBeaver (Windows)

1. Nova conexão → **DuckDB**. Deixe o DBeaver baixar o driver.
2. *Path*: `\\wsl.localhost\Ubuntu-24.04\home\fredv\dev\OpenDataBrasil\data\exports\demografia\<release_id>\gold.duckdb`
3. Em *Driver properties*, defina `access_mode = READ_ONLY`. Assim o arquivo não
   fica travado e não é alterado por engano.
4. Comece pela view `observacoes`:

```sql
-- Pessoas quilombolas por UF (total oficial, sem desagregação)
SELECT uf_abbreviation, territory_name, value_double AS pessoas
FROM observacoes
WHERE indicator_id = 'censo_pessoas_quilombolas' AND level_id = 'uf' AND non_total_count = 0
ORDER BY pessoas DESC;

-- Cor ou raça nos municípios da Bahia, 2010 e 2022
SELECT territory_name, year, breakdown_label, value_double
FROM observacoes
WHERE indicator_id = 'censo_populacao_cor_raca' AND level_id = 'municipio' AND uf_code = '29'
ORDER BY territory_name, year, breakdown_label;

SELECT * FROM arvore_indicadores;   -- árvore temática
```

## Python (no WSL, com o ambiente do projeto)

```python
import json
from pathlib import Path

import duckdb
import polars as pl

base = Path("data/exports/demografia")
pasta = base / json.loads((base / "latest.json").read_text())["release_id"]

# DuckDB → Polars (ou .df() para pandas)
con = duckdb.connect(str(pasta / "gold.duckdb"), read_only=True)
cor = con.sql("""
    SELECT year, breakdown_label, value_double AS pessoas
    FROM observacoes
    WHERE indicator_id = 'censo_populacao_cor_raca' AND geography_key = 'brasil:1'
      AND non_total_count = 1
""").pl()

# Polars direto do Parquet; valores em decimal: converta para gráficos
from odb_modeling.export import read_observations

obs = read_observations(pasta).filter(pl.col("indicator_id") == "censo_pessoas_indigenas").collect()
```

Bibliotecas de gráfico não fazem parte do ambiente do projeto. Use-as sem
alterar o lockfile:

```bash
uv run --with matplotlib==3.10.0 python minha_analise.py
uv run --with jupyterlab --with matplotlib==3.10.0 jupyter lab   # notebooks
```

## Regras de leitura

- Totais de UF, Grande Região e Brasil são os **oficiais** (`level_id`). Não
  some municípios para obtê-los. Em 2004, 2008 e 2012 a soma da 6579 inclui
  municípios em instalação (`flags` contém `pending_installation`).
- `non_total_count = 0` traz o Total. Com várias classificações, filtre as
  demais no Total, por exemplo pelo `breakdown_key`.
- `additivity = 'non_additive'` (percentuais e densidade) não pode ser somado.
- `value_status` diferente de `valid`, `true_zero` e `rounded_zero` indica
  valor ausente (`suppressed` = `X`). Ausente **não é zero**.
- "Pessoas indígenas" (9718) e a categoria Indígena de cor ou raça (9605) são
  conceitos diferentes.

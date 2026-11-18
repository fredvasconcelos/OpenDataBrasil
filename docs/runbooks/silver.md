# Runbook: camada Silver

Os comandos rodam no worker: `docker compose --profile data run --rm worker <comando>`.

```bash
odb silver build --all            # DTB primeiro (referência territorial), depois as tabelas SIDRA
odb silver build ibge-sidra-6579  # um dataset
odb silver build --all --force    # reconstrói mesmo sem mudança na Bronze
odb quality report ibge-sidra-6579 [--json]
```

| Estado | Significado |
|---|---|
| `succeeded` | nova versão Delta gravada (`delta_version`) |
| `skipped` | entradas Bronze, contrato e parâmetros iguais aos da última execução: nenhuma versão nova |
| `failed` | sem entradas, Bronze corrompida, verificação `fail` ou schema incompatível. A versão anterior permanece |

## Tabelas

| Tabela | URI | Partição | Chave |
|---|---|---|---|
| `sidra_observation` | `file:///lakehouse/silver/ibge/sidra_observation` | `table_id` | tabela, variável, nível, território, período, classificações |
| `dtb_municipality` | `file:///lakehouse/silver/ibge/dtb_municipality` | `reference_year` | ano de referência, município |

A Silver **não é pública** (§9.6). O consumo é pela Gold ([runbook](gold.md)).

## Investigar

```sql
-- últimas execuções
SELECT dataset_id, status, delta_version, stats, error, started_at
FROM operations.transformation_run ORDER BY started_at DESC LIMIT 10;

-- divergências de reconciliação da última execução de um dataset
SELECT c.check_id, d->>'period', d->>'parent_id', d->>'official', d->>'children_sum', d->>'difference'
FROM quality.check_result c
JOIN operations.transformation_run r USING (run_id),
     jsonb_array_elements(c.details->'divergent') d
WHERE r.dataset_id = 'ibge-sidra-6579' AND c.status = 'warn'
ORDER BY r.started_at DESC;
```

- **`values.conversion_error`:** a fonte publicou um símbolo fora da legenda.
  Confirme o significado na fonte e atualize `odb_processing.values` e os
  testes. Não converta para zero.
- **`schema` incompatível:** o contrato mudou de forma destrutiva. Crie uma
  nova versão major do contrato e um ADR.
- **Rastrear uma observação até a origem:** `bronze_artifact_id` →
  `operations.bronze_artifact` (`storage_uri`, `checksum_sha256`, `source_url`).

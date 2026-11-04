# Runbook: camada Gold, publicação e consulta

Os comandos rodam no worker: `docker compose --profile data run --rm worker <comando>`.
Modelo e regras: [ADR-0008](../adr/0008-gold-modelo-hierarquico-e-camada-semantica.md).
Indicadores: [`docs/data_catalog/gold-demografia.md`](../data_catalog/gold-demografia.md).

## Construir e publicar

```bash
odb silver build --all                # pré-requisito: Silver vigente de todos os datasets do escopo
odb gold build                        # constrói, verifica e cria um release *validated*
odb gold build --activate             # idem, e ativa o release (publicação interna)
odb gold build --force                # reconstrói mesmo sem mudança nas entradas
odb release list [--scope demografia]
odb release activate <release_id>     # ativa um release validado; o anterior vira superseded
odb quality gold [--json]             # verificações da última construção
odb gold export [--release <id>]      # cópia Parquet + DuckDB para análise local
```

Exportação, DBeaver e Python: [exportacao.md](exportacao.md).

| Estado da construção | Significado |
|---|---|
| `succeeded` | novas versões Delta das 14 tabelas; release criado e validado |
| `skipped` | Silver, catálogo semântico e contratos iguais aos da última construção: nenhuma versão nova; se o release ativo já aponta para essas versões, nada muda |
| `failed` | verificação `fail`, Silver ausente ou schema incompatível. **Nada é escrito nem publicado**, e o release ativo continua vigente (`active_release` na saída) |

**Reverter** para um release anterior: não há reativação de `superseded`. Corrija
a causa e reconstrua, ou ative outro release `validated`. As versões Delta
antigas continuam legíveis por `release_id` (ADR-0003).

## Consultar

```bash
odb indicators list                   # indicadores, níveis e períodos do release ativo
odb indicators tree                   # árvore temática com os parâmetros de consulta
odb query -i censo_pessoas_quilombolas --level uf -p 2022
odb query -i censo_populacao_cor_raca --level municipio --within uf:29 --by c86 -p 2010 -p 2022
odb query -i censo_pessoas_indigenas --level brasil --by c1714 --by c2661=12869
odb query -i censo_pessoas_quilombolas --level municipio --sum-to uf   # soma derivada
odb query ... --format json|csv --limit 10000
```

- `--level`: `brasil`, `regiao`, `uf`, `regiao_intermediaria`, `regiao_imediata`, `municipio`,
  `territorio_quilombola`, `territorio_quilombola_uf`, `amazonia_legal`, `amazonia_legal_uf`
  (só os publicados para o indicador).
- `--within` e `--sum-to` só aceitam níveis que contêm o nível consultado
  (por exemplo, `--level territorio_quilombola_uf --within uf:29`).
- `--within nível:código`: recorte pela hierarquia (`uf:29`, `regiao:2`).
- `--by cXX` traz todas as categorias. `--by cXX=a,b` filtra. Classificações não
  pedidas ficam no Total.
- Recusas (código de saída 2): indicador não aditivo com `--sum-to`, indicadores
  incompatíveis, nível indisponível ou classificação inexistente.

## Investigar

```sql
-- construções recentes e release associado
SELECT build_id, status, stats->'checks', release_id, error, started_at
FROM operations.gold_build ORDER BY started_at DESC LIMIT 10;

-- avisos e falhas da última construção
SELECT check_id, status, message FROM quality.gold_check_result
WHERE build_id = (SELECT build_id FROM operations.gold_build ORDER BY started_at DESC LIMIT 1)
  AND status <> 'pass';

-- resíduo da partição não exaustiva de cor ou raça (Brasil)
SELECT d FROM quality.gold_check_result,
     jsonb_array_elements(details->'residual_brasil') d
WHERE check_id = 'reconciliation.category.censo_populacao_cor_raca.c86.cor_ou_raca'
ORDER BY created_at DESC LIMIT 2;
```

## Tabelas (`file:///lakehouse/gold/demografia/<tabela>`)

| Tabela | Chave | Conteúdo |
|---|---|---|
| `dim_geography` | `geography_key` | territórios (DTB vigente e observados), pai e códigos da hierarquia |
| `bridge_geography_ancestor` | território, ancestral | fecho transitivo da hierarquia, com distância |
| `dim_period` | `period` | anos observados |
| `dim_classification`, `dim_category` | classificação; categoria | Total, partições e categorias |
| `dim_breakdown` | `breakdown_key` | combinações de categorias |
| `dim_indicator`, `dim_indicator_node` | indicador; nó | catálogo e árvore temática |
| `indicator_observation` | indicador, território, período, desagregação | estrutura universal com linhagem (partição `dataset_id`) |
| `fact_*` | território, período, categorias | fatos temáticos (formato largo) |

# ADR-0005 — Somente leitura no consumo e escritor único por tabela

- **Estado:** Aceito
- **Data:** 2026-11-03

## Contexto

Os §5.3, §11.6 e §23.4 proíbem o DuckDB de escrever em Silver e Gold no
consumo. Os testes mostraram dois fatos:

1. a extensão `delta` do DuckDB 1.5.6 **escreve** via `ATTACH … (TYPE delta)` e
   `INSERT` (`test_duckdb_delta_extension_can_write_risk`);
2. `enable_external_access=false` com `allowed_directories` restringe leituras,
   mas **ainda permite** `ATTACH`/`COPY` dentro dos diretórios permitidos.

## Decisão: leitura (query_engine)

Cinco camadas, todas testadas:

| # | Camada | Teste |
|---|---|---|
| 1 | Só uma instrução, do tipo `SELECT`, classificada por `duckdb.extract_statements` | `test_non_select_statements_rejected` |
| 2 | Tabelas só via `{{alias}}` → `delta_scan(uri, version => n)`, sem `ATTACH` | `test_binding_rules` |
| 3 | URIs restritas às raízes permitidas (Gold por padrão; Silver só por decisão explícita, §9.6) | `test_tables_outside_allowed_roots_rejected` |
| 4 | Sandbox: `enable_external_access=false`, `allowed_directories`, sem autoinstall/autoload, `lock_configuration=true` | `test_sandbox_blocks_direct_file_access` |
| 5 | Gold montada `:ro` nos serviços de consumo e imagem com usuário não root | `test_read_only_mount_blocks_writes_but_allows_reads` |

Limites: `memory_limit`, `threads`, `max_temp_directory_size`, timeout por
`cursor.interrupt()`, limite de linhas com detecção de truncamento e semáforo de
concorrência (`test_timeout_*`, `test_concurrency_limit`,
`test_parallel_queries_are_consistent`).

## Decisão: escrita (lakehouse)

- `DeltaWriter` é o único caminho de escrita: valida o schema contra o perfil,
  verifica o disco (bloqueia a partir de 90%), adquire o lock da tabela,
  verifica o protocolo antes e depois e registra `odb.run_id` no `commitInfo`.
- Lock: `pg_try_advisory_lock(lock_key(uri))` numa sessão dedicada
  (`PostgresAdvisoryLock`). A sessão que cai libera o lock.
- Camadas graváveis: Silver, Gold e tmp. Bronze não recebe tabelas Delta.

## Consequências

- Na Fase 1 não há serviço de consumo, então a montagem `:ro` ainda não aparece
  no `docker-compose.yml`. Ela é obrigatória quando a API for criada (Fase 5).
- Templates SQL são código da plataforma, não entrada de usuário. A API deverá
  montá-los a partir de operações em whitelist.

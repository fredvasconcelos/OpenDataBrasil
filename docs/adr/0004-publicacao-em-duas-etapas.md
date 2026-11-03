# ADR-0004 — Publicação de releases em duas etapas

- **Estado:** Aceito
- **Data:** 2026-11-03

## Contexto

Delta Lake e PostgreSQL não compartilham transação (§12.6). Uma escrita Delta
bem-sucedida não pode significar publicação (§10.9). Em caso de falha, a versão
anterior deve continuar vigente (§16.4).

## Decisão

1. **Etapa 1 (Delta):** pipelines escrevem novas versões, que ficam invisíveis
   ao consumo.
2. **Etapa 2 (PostgreSQL):** um release fixa `(table_id, storage_uri,
   delta_version, contract_version, quality_status)` e passa por:

   ```
   draft ─validate─▶ validated ─activate─▶ active ─▶ superseded
     └─────────────▶ failed ◀──────────────┘
   ```

- `validate` exige qualidade `passed` e versão legível no log Delta, e congela
  o manifesto (`jsonb`).
- `activate` roda numa única transação: `SELECT … FOR UPDATE` do release,
  `pg_advisory_xact_lock` por escopo, ativo anterior para `superseded`, novo
  para `active`, **reverificação das versões Delta dentro da transação** e
  eventos de auditoria. Qualquer exceção desfaz tudo. A falha é registrada
  depois, em transação separada (`failed` + `release_event`).
- O índice único parcial `release_one_active_per_scope` garante, no banco, no
  máximo um release ativo por escopo.
- Releases `superseded` permanecem com o manifesto, para reprodutibilidade.

## Schemas (migrações 0001–0002)

- `publication.release`, `publication.release_table`, `publication.release_event`.
- `operations.pipeline_run`, que registra cada execução (`running` →
  `succeeded`/`failed`).
- Roles: `odb_owner` (DDL/migrações), `odb_pipeline` (escrita operacional) e
  `odb_reader` (somente `SELECT` em `publication.release*`).

## Consequências

- Entre a etapa 1 e a ativação, uma limpeza Delta (VACUUM) poderia remover
  arquivos. Por isso a reverificação ocorre dentro da transação e o VACUUM fica
  desabilitado na Fase 1. A política de retenção precisa preservar todas as
  versões referenciadas por releases `active` e `superseded` retidos.
- Teste de evidência: `test_activation_failure_rolls_back`. A falha injetada na
  reverificação mantém o release anterior `active`, e o novo termina `failed`.

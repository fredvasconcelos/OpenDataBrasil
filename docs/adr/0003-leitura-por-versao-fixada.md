# ADR-0003 — Leitura de tabelas Delta por versão fixada

- **Estado:** Aceito
- **Data:** 2026-11-03

## Contexto

O §17.4 exige que cada consulta use versões coerentes, resolvidas pelo manifesto
de publicação. O plano deixou em aberto, para decisão por teste, a escolha entre
`AT (VERSION => n)` e `PIN_SNAPSHOT`.

Com DuckDB 1.5.6 e extensão `delta` 6059958, as quatro formas funcionaram:

| Forma | Resultado |
|---|---|
| `delta_scan('<uri>', version => n)` | ✅ |
| `ATTACH '<uri>' AS t (TYPE delta, VERSION n)` | ✅ |
| `ATTACH '<uri>' AS t (TYPE delta)` + `FROM t AT (VERSION => n)` | ✅ |
| `ATTACH ... (TYPE delta, PIN_SNAPSHOT)` | ✅ (fixa a versão mais recente no momento do attach) |

## Decisão

Usar **`delta_scan('<uri>', version => n)`**, gerado pelo adaptador a partir de
`{{alias}}` no template e de `PinnedTable(uri, version)` resolvido no catálogo.

Motivos:

1. **Sem `ATTACH`.** A extensão escreve em tabelas anexadas (ver ADR-0005).
   Eliminar `ATTACH` do caminho de consumo remove essa superfície.
2. **Sem estado.** Cada consulta declara a versão. Não há catálogo DuckDB a
   sincronizar com o release vigente, nem risco de reaproveitar um snapshot antigo.
3. **Mesma semântica no Polars:** `scan_delta(uri, version=n)`.
4. `PIN_SNAPSHOT` fixa "a versão no momento do attach", e não a versão do
   manifesto. Não atende ao requisito.

`DeltaReader.scan` exige versão explícita. Não existe "ler a mais recente" no
caminho de consumo.

## Consequências

- Cada consulta relê o log Delta da versão pedida. Se a latência for relevante
  na Fase 5, avaliar cache de metadados com invalidação por release.
- O teste `test_duckdb_reads_published_version_not_latest` comprova que o
  consumo lê a versão publicada (v1) mesmo quando a tabela já está na v2.

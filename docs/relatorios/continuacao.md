# Continuação do trabalho (pedido de 2026-11-13)

**Estado em 2026-11-13, 01h: concluído.** O release `7e2eb607` está ativo no ambiente local,
com todos os testes verdes. As etapas abaixo ficam como referência para uma nova carga.

Roteiro para retomar a rodada "revisão geral dos KPIs" se a sessão acabar no meio. O
estado de cada etapa está no Git (`git status`) e nos logs do worker
(`odb ingest status`, `odb release list`).

## Pedido do mantenedor

1. Aplicar a dimensão de tempo (mês, trimestre, semestre, ano) a todos os KPIs onde
   faz sentido. O exemplo dado foi a SIDRA 8757, variável 7169.
2. Ampliar o detalhe consultando de novo as tabelas na origem: idade, sexo, cor ou
   raça, instrução e outras classificações.
3. Tomar as decisões necessárias e acrescentar as novas perguntas ao relatório
   [2026-11-12-pontos-criticos.md](2026-11-12-pontos-criticos.md).

## Feito no código (sem commit)

- **Agregação no tempo (ADR-0017):** `time_aggregation` com três regras:
  - `sum`: fluxos;
  - `mean`: números-índice e médias por período;
  - `last`: acumulados em 12 meses e estimativas revisadas.

  O campo `agregacao_tempo` no panorama cobre 20 KPIs. A API expõe a regra, e o
  portal mostra a nota de acordo com ela (DS 2.3.5).
- **Tabelas-irmãs (ADR-0018):** o campo `complementos` no panorama. O gerador monta a
  série base + irmãs com regras por tabela. São 15 KPIs e 49 tabelas, com os
  descritores em `configs/catalog/descritores/`.

## Etapas de dados (rodar na ordem; cada uma é retomável)

```bash
cd ~/dev/OpenDataBrasil
docker compose --profile data --profile web build worker api portal
IDS=$(uv run python -I -c "import tomllib;from pathlib import Path;d=tomllib.loads(Path('configs/sources/ibge-panorama.toml').read_text())['datasets'];print(' '.join(x['id'] for x in d if x['silver'].get('series')))")
docker compose --profile data run --rm worker odb ingest run $IDS
docker compose --profile data run --rm worker odb silver build $IDS
docker compose --profile data run --rm worker odb gold build
docker compose --profile data run --rm worker odb release check <release_id>
docker compose --profile data run --rm worker odb release activate <release_id> && docker compose --profile web up -d api portal
```

Depois:

- conferir `/health` (`"portal": "ok"`);
- rodar os testes: `docker compose --profile test run --rm tests pytest -q`, o portal
  (vitest) e os e2e;
- atualizar as ADRs 0017 e 0018, o relatório de pontos críticos e a memória.

## Comando para retomar numa sessão nova do Claude Code

> Continue o trabalho descrito em docs/relatorios/continuacao.md: confira o que já foi
> feito (git status, odb release list, logs) e conclua as etapas que faltarem, sem
> commit, terminando com o relatório de pontos críticos atualizado.

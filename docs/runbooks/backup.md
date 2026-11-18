# Runbook: backup e restauração

Decisão do mantenedor (2026-11-13, pontos 2 e 20 do relatório de pontos críticos):

- **No backup:** a Bronze (dados originais, §6) e o catálogo PostgreSQL (fontes,
  artefatos, checksums, execuções, releases).
- **Fora do backup:** a Silver e a Gold. As duas são reconstruídas a partir da Bronze
  com o código e as configurações do Git. A produção recebe só a Gold do release
  ativo (ADR-0015).
- **Destino:** `ODB_BACKUP_DIR` no `.env`. Vazio, vale `./backups` na raiz do projeto,
  que está fora do Git. A rota definitiva (outro disco, armazenamento de objetos) só
  muda essa variável.

## Fazer o backup

```bash
infrastructure/scripts/backup.sh            # catálogo + Bronze (incremental)
infrastructure/scripts/backup.sh --verify   # e confere o SHA-256 de cada artefato
```

O script:

1. grava o dump do catálogo em `catalog/odb-<instante>.dump` (`pg_dump -Fc`) e mantém
   os 14 mais recentes (`ODB_BACKUP_KEEP_DUMPS`);
2. copia a Bronze para `bronze/`. É incremental: os artefatos são imutáveis (§6.5), e o
   que já está no destino não é copiado de novo nem sobrescrito;
3. com `--verify`, confere o SHA-256 de cada artefato guardado (`ingestion_status =
   'stored'`) contra o catálogo. Uma divergência faz o script falhar.

**Quando rodar:** no fim de cada ciclo de atualização ([atualizacao.md](atualizacao.md)),
depois da ingestão e antes de ativar o release. Rode com `--verify` ao menos uma vez
por ciclo.

## Restaurar

Numa máquina nova, com o repositório clonado e o `.env` preenchido:

```bash
docker compose up -d postgres
# 1. Catálogo (o dump mais recente):
docker compose exec -T postgres pg_restore -U postgres -d odb --clean --if-exists \
  < backups/catalog/odb-<instante>.dump
# 2. Bronze, de volta ao volume:
docker run --rm -v opendatabrasil_lake_bronze:/dst -v "$PWD/backups/bronze:/src:ro" \
  --entrypoint sh opendatabrasil/odb:dev -c 'cp -a /src/. /dst/'
# 3. Silver e Gold a partir da Bronze, e o release:
docker compose --profile data run --rm worker odb silver build --all
docker compose --profile data run --rm worker odb gold build
docker compose --profile data run --rm worker odb release check <release_id>
```

Depois, siga a ativação do runbook [gold.md](gold.md).

## Por que a Silver não entra no backup

| Camada | Tamanho (2026-11-13) | Reconstrução |
|---|---|---|
| Bronze | 22,8 GB | impossível: as fontes mudam e revisam os dados |
| Silver | 1,4 GB | `odb silver build` a partir da Bronze |
| Gold | 1,8 GB | `odb gold build` a partir da Silver |

A Silver continua no disco local entre os ciclos. Ela é a entrada da Gold e ocupa só
6% da Bronze. Apagá-la ao fim de cada ciclo liberaria pouco espaço e obrigaria a
reconstruir as 300 tabelas da Silver a cada ciclo, em vez de só as que mudaram.

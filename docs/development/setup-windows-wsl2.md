# Ambiente local: Windows 11 + WSL2 + Docker Desktop

## 1. Pré-requisitos

- Windows 11 com WSL2 e a distribuição **Ubuntu 24.04**.
- Docker Desktop com integração WSL2 habilitada para a distribuição
  (Settings → Resources → WSL integration).
- Recursos do WSL em `C:\Users\<usuario>\.wslconfig` (referência do ambiente
  original):

  ```ini
  [wsl2]
  memory=40GB
  processors=16
  swap=8GB

  [experimental]
  sparseVhd=true
  ```

  Depois de alterar o arquivo, rode `wsl --shutdown` no PowerShell.

## 2. Repositório no filesystem Linux

Clone **dentro** do WSL (ADR-0001, decisão 6), nunca em `/mnt/c/...`:

```bash
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/fredvasconcelos/OpenDataBrasil.git
cd OpenDataBrasil
git config core.autocrlf input
```

No VS Code, use **"Connect to WSL"**. Abrir via `\\wsl.localhost\...` no
Windows gera o erro `dubious ownership` no git e deixa o I/O lento.

## 3. uv (desenvolvimento no host)

```bash
curl -LsSf https://astral.sh/uv/0.13.2/install.sh | sh   # versão fixada
uv sync --all-packages                                   # cria .venv a partir do uv.lock
uv run python -c "import duckdb; duckdb.execute('INSTALL delta')"   # extensão para testes locais
```

## 4. Configuração

```bash
cp .env.example .env
chmod 600 .env
# troque todas as senhas, por exemplo:
python3 -c 'import secrets; print(secrets.token_urlsafe(24))'
```

`.env` nunca é versionado. Valores não secretos por ambiente ficam em
`configs/environments/{dev,test}.toml`.

## 5. Subir e validar

```bash
docker compose --profile data --profile test build
docker compose --profile data up -d postgres
docker compose --profile data run --rm migrate                   # alembic upgrade head
docker compose --profile data run --rm worker odb doctor         # tudo [OK]
docker compose --profile data run --rm worker odb smoke lakehouse
docker compose --profile test run --rm tests                     # suíte completa + cobertura
```

Profiles: `data` (postgres, migrate, worker), `test` (postgres, tests), `dev`
(postgres e shell com código montado: `docker compose --profile dev up -d dev`,
depois `docker compose exec dev bash`) e `web` (reservado para a Fase 5).

## 6. Desenvolvimento no host contra o PostgreSQL do Compose

```bash
set -a; . ./.env; set +a
export ODB_PG_HOST=localhost ODB_PG_USER=odb_owner ODB_PG_PASSWORD=$ODB_OWNER_PASSWORD \
       ODB_PG_DATABASE=odb_test ODB_TEST_PIPELINE_PASSWORD=$ODB_PIPELINE_PASSWORD \
       ODB_TEST_READER_PASSWORD=$ODB_READER_PASSWORD
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest --cov
```

Sem `ODB_PG_*`, os testes de integração são pulados. Com
`ODB_REQUIRE_INTEGRATION=1`, a indisponibilidade do banco vira falha.

## 7. Volumes e dados

| Volume | Montagem | Conteúdo |
|---|---|---|
| `lake_bronze` / `lake_silver` / `lake_gold` / `lake_tmp` | `/lakehouse/*` | camadas do lakehouse |
| `odb_logs` | `/var/log/odb` | logs |
| `pg_data` | `/var/lib/postgresql/data` | cluster PostgreSQL |
| `pg_backups` | `/backups` | destino de backups (procedimento previsto para a Fase 7) |

Os volumes ficam no disco virtual do Docker Desktop (ext4, NVMe).
`docker compose down -v` **apaga todos os dados**.

## 8. Problemas conhecidos

| Sintoma | Causa e solução |
|---|---|
| `fatal: detected dubious ownership` | repositório acessado via `\\wsl.localhost`. Abra pelo WSL |
| `odb doctor`: `[FAIL] duckdb.delta` | extensão ausente. No host, rode o `INSTALL delta` (seção 3). No container, refaça o build |
| `permission denied for table alembic_version` | banco abaixo da revisão 0002. Rode `migrate` |
| Script de init do PostgreSQL não roda | só roda com `pg_data` vazio. Para recriar: `docker compose down` e `docker volume rm opendatabrasil_pg_data` (**apaga o catálogo**) |
| `cpu` no doctor mostra 16 CPUs com limite de 8 | `os.cpu_count()` ignora a cota do cgroup. Vale o `POLARS_MAX_THREADS` |

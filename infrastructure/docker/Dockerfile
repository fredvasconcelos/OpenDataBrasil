# syntax=docker/dockerfile:1.7
# Imagem única da plataforma (Fase 1), com dois alvos:
#   runtime -> worker e migrate (sem dependências de desenvolvimento)
#   test    -> runtime + ferramentas de teste + tests/
# Imagens base fixadas por digest (ADR-0001). Atualize de forma deliberada.

ARG PYTHON_IMAGE=python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.2@sha256:b9fddcde095a7aeafd499024adb8927df6619c7c5672f5ff7126474715f62ba4

FROM ${UV_IMAGE} AS uv

# ---------------------------------------------------------------- base
FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    TZ=UTC
COPY --from=uv /uv /usr/local/bin/uv
RUN groupadd --gid 1000 odb && useradd --uid 1000 --gid odb --create-home odb \
 && mkdir -p /lakehouse/bronze /lakehouse/silver /lakehouse/gold /lakehouse/tmp/duckdb \
             /var/log/odb /opt/duckdb/extensions \
 && chown -R odb:odb /lakehouse /var/log/odb
WORKDIR /app

# Camada de dependências: só os manifestos, para aproveitar o cache.
COPY pyproject.toml uv.lock .python-version ./
COPY packages/common/pyproject.toml packages/common/pyproject.toml
COPY packages/lakehouse/pyproject.toml packages/lakehouse/pyproject.toml
COPY packages/query_engine/pyproject.toml packages/query_engine/pyproject.toml
COPY packages/catalog/pyproject.toml packages/catalog/pyproject.toml
COPY packages/cli/pyproject.toml packages/cli/pyproject.toml
COPY packages/ingestion/pyproject.toml packages/ingestion/pyproject.toml

# ---------------------------------------------------------------- runtime
FROM base AS runtime
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --all-packages
COPY packages packages
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --all-packages --no-editable
# Extensão Delta do DuckDB pré-instalada. Em execução não há download nem autoload.
RUN python -c "import duckdb; c = duckdb.connect(config={'extension_directory': '/opt/duckdb/extensions'}); c.execute('INSTALL delta'); c.execute('LOAD delta'); print(c.execute(\"select extension_version from duckdb_extensions() where extension_name='delta'\").fetchone())" \
 && chmod -R a+rX /opt/duckdb
COPY configs configs
ARG ODB_CODE_VERSION=unknown
ENV ODB_CODE_VERSION=${ODB_CODE_VERSION} \
    ODB_DUCKDB_EXTENSION_DIRECTORY=/opt/duckdb/extensions
USER odb
CMD ["odb", "--help"]

# ---------------------------------------------------------------- test
FROM runtime AS test
USER root
# Instalação editável: a cobertura mede o código em /app/packages.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-packages
COPY tests tests
RUN chown -R odb:odb /app
USER odb
CMD ["pytest"]

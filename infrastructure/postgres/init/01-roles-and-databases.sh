#!/usr/bin/env bash
# Executado uma única vez pelo entrypoint oficial do postgres, quando o volume
# de dados está vazio. Cria os roles da aplicação e o banco de testes.
#
#   odb_owner    -> dono dos bancos e schemas; usado só por migrações
#   odb_pipeline -> escrita operacional (execuções, publicação)
#   odb_reader   -> leitura do catálogo (API futura)
#
# Os privilégios sobre tabelas são concedidos pelas migrações Alembic.
set -euo pipefail

: "${ODB_OWNER_PASSWORD:?defina ODB_OWNER_PASSWORD}"
: "${ODB_PIPELINE_PASSWORD:?defina ODB_PIPELINE_PASSWORD}"
: "${ODB_READER_PASSWORD:?defina ODB_READER_PASSWORD}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v db="$POSTGRES_DB" \
  -v owner_pw="$ODB_OWNER_PASSWORD" \
  -v pipeline_pw="$ODB_PIPELINE_PASSWORD" \
  -v reader_pw="$ODB_READER_PASSWORD" <<'SQL'
CREATE ROLE odb_owner    LOGIN PASSWORD :'owner_pw';
CREATE ROLE odb_pipeline LOGIN PASSWORD :'pipeline_pw' CONNECTION LIMIT 20;
CREATE ROLE odb_reader   LOGIN PASSWORD :'reader_pw'   CONNECTION LIMIT 20;

ALTER DATABASE :"db" OWNER TO odb_owner;
CREATE DATABASE odb_test OWNER odb_owner;

REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
REVOKE ALL ON DATABASE odb_test FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db"    TO odb_owner, odb_pipeline, odb_reader;
GRANT CONNECT ON DATABASE odb_test TO odb_owner, odb_pipeline, odb_reader;

ALTER SCHEMA public OWNER TO odb_owner;
\connect odb_test
ALTER SCHEMA public OWNER TO odb_owner;
SQL

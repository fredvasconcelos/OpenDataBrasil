#!/usr/bin/env bash
# Banco de métricas de acesso (ADR-0027): odb_metrics, separado do catálogo.
#
# Fica fora do banco do catálogo de propósito: o deploy da Vitrine restaura o catálogo
# da Fábrica com `pg_restore --clean`, e um banco separado nunca entra nesse dump.
#
#   odb_metrics_writer -> só o agregador do log de acesso (INSERT/UPDATE das somas)
#   odb_metrics_reader -> só a API (SELECT)
#   odb_owner          -> dono do banco e da tabela (mesmo dono do catálogo)
#
# Roda sozinho na primeira inicialização (volume vazio), depois do 01. É idempotente:
# para criar ou atualizar o banco numa instalação existente, rode de novo
#   docker compose exec -T postgres bash /docker-entrypoint-initdb.d/02-metrics-database.sh
# (as senhas vêm do ambiente do contêiner e são reaplicadas a cada execução).
set -euo pipefail

: "${ODB_METRICS_WRITER_PASSWORD:?defina ODB_METRICS_WRITER_PASSWORD}"
: "${ODB_METRICS_READER_PASSWORD:?defina ODB_METRICS_READER_PASSWORD}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v writer_pw="$ODB_METRICS_WRITER_PASSWORD" \
  -v reader_pw="$ODB_METRICS_READER_PASSWORD" <<'SQL'
SELECT 'CREATE ROLE odb_metrics_writer LOGIN CONNECTION LIMIT 5'
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'odb_metrics_writer')\gexec
SELECT 'CREATE ROLE odb_metrics_reader LOGIN CONNECTION LIMIT 20'
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'odb_metrics_reader')\gexec
ALTER ROLE odb_metrics_writer PASSWORD :'writer_pw';
ALTER ROLE odb_metrics_reader PASSWORD :'reader_pw';

SELECT 'CREATE DATABASE odb_metrics OWNER odb_owner'
 WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'odb_metrics')\gexec
REVOKE ALL ON DATABASE odb_metrics FROM PUBLIC;
GRANT CONNECT ON DATABASE odb_metrics TO odb_owner, odb_metrics_writer, odb_metrics_reader;

\connect odb_metrics
ALTER SCHEMA public OWNER TO odb_owner;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

SET ROLE odb_owner;
-- Somas diárias de acessos, sem dado pessoal: nenhum IP, user agent ou cookie.
-- Uma linha por dia, evento, local, rota, indicador, formato e domínio de origem.
CREATE TABLE IF NOT EXISTS public.access_daily (
    day             date        NOT NULL,
    event           text        NOT NULL,
    country         char(2)     NOT NULL DEFAULT 'ZZ',
    uf              smallint    NOT NULL DEFAULT 0,
    route           text        NOT NULL,
    kpi_id          text        NOT NULL DEFAULT '',
    format          text        NOT NULL DEFAULT '',
    referrer_domain text        NOT NULL DEFAULT '',
    count           bigint      NOT NULL,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT access_daily_pk
        PRIMARY KEY (day, event, country, uf, route, kpi_id, format, referrer_domain),
    CONSTRAINT access_daily_event CHECK (event IN ('page_view', 'kpi_open', 'download')),
    CONSTRAINT access_daily_country CHECK (country ~ '^[A-Z]{2}$'),
    CONSTRAINT access_daily_uf CHECK (uf = 0 OR uf BETWEEN 11 AND 53),
    CONSTRAINT access_daily_uf_br CHECK (country = 'BR' OR uf = 0),
    CONSTRAINT access_daily_format CHECK (format IN ('', 'csv', 'xlsx', 'parquet', 'json')),
    CONSTRAINT access_daily_download_format CHECK ((event = 'download') = (format <> '')),
    CONSTRAINT access_daily_count CHECK (count >= 0)
);
COMMENT ON TABLE public.access_daily IS
    'Somas diárias de acessos ao portal (ADR-0027). Sem IP, user agent nem cookie.';
COMMENT ON COLUMN public.access_daily.day IS 'Dia no fuso America/Sao_Paulo.';
COMMENT ON COLUMN public.access_daily.country IS 'ISO 3166-1 alfa-2; ZZ = país não identificado.';
COMMENT ON COLUMN public.access_daily.uf IS 'Código IBGE da UF (11 a 53); 0 = fora do Brasil ou UF não identificada.';
COMMENT ON COLUMN public.access_daily.route IS 'Caminho da página, sem a consulta (ex.: /dashboard).';
COMMENT ON COLUMN public.access_daily.kpi_id IS 'Indicador aberto ou exportado; vazio quando não há.';
COMMENT ON COLUMN public.access_daily.referrer_domain IS 'Domínio do site anterior, sem caminho; vazio = acesso direto.';
CREATE INDEX IF NOT EXISTS access_daily_kpi ON public.access_daily (kpi_id, day) WHERE kpi_id <> '';

-- Arquivos do log de acesso já somados (`odb metrics aggregate`). Gravado na mesma
-- transação das somas: se o agregador cair antes de apagar o arquivo, a próxima rodada
-- o reconhece e só o apaga, sem contar duas vezes.
CREATE TABLE IF NOT EXISTS public.access_log_file (
    file_name    text        PRIMARY KEY,
    sha256       char(64)    NOT NULL,
    lines        integer     NOT NULL CHECK (lines >= 0),
    counted      integer     NOT NULL CHECK (counted >= 0),
    processed_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.access_log_file IS
    'Arquivos do log do Caddy já agregados em access_daily (ADR-0027). Sem conteúdo do log.';

GRANT USAGE ON SCHEMA public TO odb_metrics_writer, odb_metrics_reader;
GRANT SELECT, INSERT ON public.access_log_file TO odb_metrics_writer;
GRANT SELECT, INSERT, UPDATE ON public.access_daily TO odb_metrics_writer;
GRANT SELECT ON public.access_daily TO odb_metrics_reader;
RESET ROLE;
SQL

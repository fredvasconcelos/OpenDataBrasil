# ADR-0002 — Seleção de versões e fixação de dependências

- **Estado:** Aceito
- **Data:** 2026-11-03

## Contexto

O §4.3 proíbe adotar automaticamente a versão mais recente e exige validação por
execução. Na data da seleção:

- Polars 2.0.0 (2026-10-06) e 2.1.0 (2026-10-25) estavam disponíveis;
- DuckDB 2.0.0 tinha sido lançado em 2026-10-21 (13 dias), e o PyPI exibia
  builds `dev` como "latest";
- o plano aprovado previa Polars 1.41.x e DuckDB 1.5.x.

## Decisão

- **Polars 1.44.2:** última versão da série 1.x, publicada há mais de 14 dias.
  Supera a 1.41.x prevista sem mudar de major.
- **DuckDB 1.5.6:** última da série 1.5.x. A extensão `delta` é instalada no
  build da imagem e carregada sem autoload.
- **deltalake 1.6.6, pyarrow 26.0.0, SQLAlchemy 2.0.55** (série 2.0 em vez da
  2.1, por conservadorismo), **Alembic 1.20.0, psycopg 3.3.6**.
- Imagens base fixadas por digest. Os digests de 2026-10-28 são rebuilds de
  segurança de versões estáveis (Python 3.12.16, PostgreSQL 17.11).
- `uv.lock` versionado; o uv é fixado em `tool.uv.required-version`.

## Consequências

- Recursos exclusivos do Polars 2.x e do DuckDB 2.x ficam indisponíveis.
- A migração para essas majors exige: ADR, atualização do lock, os 13 contratos
  de interoperabilidade verdes e a matriz atualizada.

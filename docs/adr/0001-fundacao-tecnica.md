# ADR-0001 — Fundação técnica da Fase 1

- **Estado:** Aceito
- **Data:** 2026-11-03
- **Contexto normativo:** Prompt Mestre v1.1 (`CLAUDE.md`), §4, §20, §21, §27 e §28

## Contexto

A Fase 1 precisa de um ambiente local reproduzível que execute escrita e leitura
Delta, consulta DuckDB e conectividade PostgreSQL. Antes da implementação foram
aprovadas nove decisões que ajustam ou detalham a especificação.

## Decisões

1. **Python 3.12** nos containers e no workspace local (`.python-version`).
2. **PostgreSQL 17** como banco operacional.
3. **uv workspace** como gerenciador de dependências. A raiz é virtual (não
   instalável) e cada pacote em `packages/` declara suas dependências. O
   `uv.lock` é versionado, e a versão do uv é fixada em `tool.uv.required-version`.
4. **Perfil Delta conservador:** `minReaderVersion=1` e `minWriterVersion=2`, sem
   deletion vectors, column mapping, `timestampNtz`, liquid clustering, V2
   checkpoints ou type widening. Todos os instantes são gravados como
   `timestamp` em UTC. O objetivo é maximizar a leitura por DuckDB, Databricks e
   Fabric. Qualquer recurso adicional exige novo ADR e teste de interoperabilidade.
5. **Raiz do repositório = `OpenDataBrasil`**, no lugar do `brasil-open-data/`
   sugerido no §21. Os pacotes `lakehouse` (escrita e leitura Delta, protocolo,
   locks) e `catalog` (PostgreSQL, migrações, publicação) foram acrescentados ao
   conjunto do §21. Os demais pacotes do §21 só serão criados quando tiverem
   código e teste.
6. **Repositório no filesystem Linux do WSL2** (`~/dev/OpenDataBrasil`), porque
   montagens Windows degradam I/O e geram problemas de propriedade no git.
7. **Orçamento de recursos:** 32 GB de RAM e 16 threads para o projeto inteiro
   (limites por serviço em `docker-compose.yml`).
8. **Sem API e sem portal na Fase 1.**
9. **Licença de dados registrada por dataset no catálogo.** A licença MIT do
   repositório cobre apenas o código.

## Seleção de versões

Regra: versão estável, publicada há pelo menos 14 dias na data da seleção e
validada por teste executado. A matriz oficial fica em
`docs/development/compatibility-matrix.md` e só é preenchida depois que os testes
de interoperabilidade passam.

Desvios conscientes em relação às versões mais recentes (2026-11-03):

- **Polars 1.44.x, e não 2.x:** a 2.0.0 foi lançada em 2026-10-06. É uma versão
  major recente, e a migração deve ser avaliada em ADR próprio.
- **DuckDB 1.5.x, e não 2.0.0:** a 2.0.0 foi lançada em 2026-10-21, há menos de 14 dias.

## Consequências

- Recursos Delta modernos ficam indisponíveis até aprovação explícita.
- O `uv.lock` fixa todas as dependências transitivas. Atualizações são deliberadas.
- A estrutura do monorepo diverge do nome sugerido no §21. Este ADR é a decisão
  documentada exigida por aquela seção.

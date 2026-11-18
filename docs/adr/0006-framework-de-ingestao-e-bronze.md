# ADR-0006 — Framework de ingestão e camada Bronze

- **Estado:** Aceito
- **Data:** 2026-11-03
- **Contexto normativo:** CLAUDE.md §6, §7 e §27 (Fase 2)

## Contexto

A Fase 2 exige obter um dataset oficial, preservá-lo, identificá-lo por
checksum e reexecutar sem duplicação indevida. O núcleo não pode conter regras
de nenhuma fonte (§3.3).

## Decisões

### Contrato de conectores (`odb_ingestion.contract`)

- `BaseConnector`, uma ABC, implementa `discover`, `describe` e `extract`. Cada
  conector implementa `plan`, `validate_raw` e `healthcheck`, e declara
  `capabilities` em vez de simular recursos ausentes na fonte. O SIDRA não tem
  requisição condicional; o geoftp tem.
- `get_watermark` (§7.2) é responsabilidade do framework
  (`IngestionRegistry`). O conector só interpreta o watermark no `plan`.
- Parâmetros específicos (`[datasets.params]`) são validados pelo conector na
  construção. Configuração inválida falha antes de qualquer download.

### Configuração (`configs/sources/*.toml`)

- Um arquivo por instituição: licenças, fontes (com política HTTP) e datasets.
- O checksum canônico da configuração de cada dataset fica em `catalog.dataset`.

### HTTP (`odb_ingestion.http`)

- `httpx` 0.28.1, com timeouts, novas tentativas com backoff exponencial e
  jitter para 429, 5xx e erros de transporte, e respeito a `Retry-After`. Se o
  `Retry-After` passar do máximo configurado, a requisição falha: o projeto
  nunca contorna limites da fonte. Erros 4xx não são repetidos.
- Uma requisição por vez por host, com intervalo mínimo configurável (2 s no
  IBGE).
- Download em streaming com SHA-256 calculado durante a escrita, limite de
  tamanho e criação exclusiva do arquivo.
- O User-Agent identifica o projeto e não contém dados pessoais.
- Downloads retomáveis (`Range`) **não** foram implementados: os artefatos
  atuais têm de 1,5 a 5 MB. Serão reavaliados para fontes com arquivos grandes.

### Bronze (`odb_ingestion.bronze`)

```
bronze/<source_id>/<dataset_id>/<AAAAMMDDtHHMMSSz>-<ingestion8>/<artefato>
bronze/<source_id>/<dataset_id>/quarantine/<…>/<artefato>
```

- Os nomes de artefato são definidos pela plataforma (§6.4), e a URL original
  fica nos metadados.
- Staging em `tmp/ingestion/<ingestion_id>`. A Bronze só recebe arquivos
  completos, copiados com criação exclusiva, verificados por SHA-256 e marcados
  como somente leitura.
- **Deduplicação global por checksum:** o índice único parcial
  `bronze_artifact_stored_checksum_uq` garante uma única cópia de bytes
  `stored`. Uma reexecução com conteúdo idêntico registra `reused`, apontando
  para o artefato original, sem gravar bytes. Uma corrida entre processos é
  resolvida como `reused`.
- Conteúdo inválido vai para a **quarentena**: é preservado para investigação
  e não entra no watermark.

### Execução (`odb_ingestion.runner`) e catálogo (migração 0003)

- Estados de artefato: `stored`, `reused`, `not_modified`, `quarantined` e
  `failed`.
- O watermark avança **somente** quando todas as requisições da ingestão têm
  sucesso. Ingestões parciais terminam `failed` (§7.5).
- `run_many` isola cada dataset, então a falha de um não interrompe os demais.
- Schemas: `catalog.{institution, license, source, dataset}` e
  `operations.{ingestion, bronze_artifact, watermark}`. O `odb_reader` lê
  `catalog`, mas não `operations`.
- O `odb_catalog` depende do `odb_ingestion` apenas pelos tipos do contrato
  (`IngestionRegistry`). O framework não conhece PostgreSQL.

### Detecção de mudanças

| Fonte | Mecanismo |
|---|---|
| SIDRA (sem ETag/Last-Modified) | checksum por partição (período). Os `refresh_recent_periods` mais recentes são baixados de novo a cada execução, porque podem ter sido revisados (§7.6). `--full` baixa tudo |
| geoftp (com ETag/Last-Modified) | `If-None-Match` / `If-Modified-Since`. O `304` gera o registro `not_modified` |

## Consequências

- Cada versão revisada de uma partição gera um novo arquivo, e as anteriores
  são preservadas (teste `test_revised_content_is_stored_as_new_version`).
- Uma Bronze com checksums globais simplifica a deduplicação, mas o caminho
  físico de um conteúdo reutilizado pertence à primeira ingestão que o gravou.
  Consumidores devem sempre resolver `storage_uri` pelo catálogo.
- A licença do IBGE está em `requires_review`. Publicação pública depende de
  confirmação do texto oficial (§23).

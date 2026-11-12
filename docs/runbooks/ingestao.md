# Runbook: ingestão para a Bronze

Todos os comandos rodam no worker:
`docker compose --profile data run --rm worker <comando>`.

## Operação normal

```bash
odb sources list                        # datasets configurados
odb sources health                      # disponibilidade das fontes (sai com 1 se alguma falhar)
odb ingest plan ibge-sidra-6579         # requisições previstas, sem baixar dados
odb ingest run --all                    # todos os datasets habilitados
odb ingest run ibge-sidra-6579 --full   # ignora o watermark e baixa todas as partições
odb ingest status [dataset] --limit 20  # últimas ingestões e contagens por estado
```

- O código de saída é `1` quando algum dataset falha. Os demais são processados
  normalmente.
- Toda execução fica em `operations.pipeline_run` (`command = 'ingest.run'`).

### Timeouts: adiar e repescar

A fonte pode demorar em algumas tabelas (no SIDRA, as consultas com nível municipal
levam de 10 a 120 s, com timeouts eventuais). Por padrão, `odb ingest run`:

1. dá **2 tentativas** a cada requisição (`--tentativas-iniciais`). Uma falha
   transitória (timeout, conexão, 429 ou 5xx) **adia** o dataset: a ingestão
   termina `failed` com o erro `adiada: …`, e o dataset vai para o fim da fila;
2. depois dos demais, faz até **2 rodadas** com os adiados (`--rodadas`), com
   **60 s** de pausa entre elas (`--pausa`). A última rodada usa as tentativas
   normais da fonte (`[sources.http] max_attempts`);
3. na repescagem, as partições já baixadas e validadas **na mesma execução**
   voltam da Bronze como `reused` (`validation.resumed_from_checkpoint`), sem
   novo download.

O watermark continua sendo gravado só com o dataset completo, então a Silver
nunca vê carga parcial. Recusas da fonte (4xx) não são adiadas. Com
`--rodadas 0`, o comportamento antigo volta: uma passada, sem adiamento.

```bash
odb ingest run --rodadas 3 --pausa 120 ibge-sidra-4412 ibge-sidra-5457
```

Uma interrupção (Ctrl+C ou SIGINT) registra a ingestão como `failed`, com o erro
`interrompida (KeyboardInterrupt)`. Use `docker kill --signal=SIGINT`, e não
`docker stop`.

## Estados de artefato

| Estado | Significado | Bytes gravados |
|---|---|---|
| `stored` | conteúdo novo e válido | sim |
| `reused` | conteúdo idêntico a um `stored` existente (`reused_from`) | não |
| `not_modified` | servidor respondeu 304 | não |
| `quarantined` | conteúdo inválido, preservado em `…/quarantine/…` | sim (na quarentena) |
| `failed` | erro HTTP ou de rede após as tentativas | não |

## Investigar uma falha

```sql
-- últimas ingestões com erro
SELECT ingestion_id, dataset_id, started_at, error
FROM operations.ingestion WHERE status = 'failed' ORDER BY started_at DESC LIMIT 10;

-- artefatos problemáticos de uma ingestão
SELECT partition_key, ingestion_status, http_status, error, storage_uri, validation
FROM operations.bronze_artifact
WHERE ingestion_id = '<id>' AND ingestion_status IN ('failed', 'quarantined');
```

- **`quarantined`:** abra o arquivo em `storage_uri` e leia
  `validation.errors`. Uma resposta SIDRA com apenas o cabeçalho indica
  período inexistente ou consulta vazia. Se a fonte mudou de formato, ajuste o
  conector e os testes. Não edite o arquivo.
- **`failed` com 429/503:** a fonte está limitando o ritmo ou indisponível.
  Aguarde e reexecute. Se for recorrente, aumente `min_interval_s` em
  `configs/sources/*.toml`. Nunca reduza abaixo do padrão para "acelerar".
- **Disco:** a ingestão é bloqueada a partir de `ODB_DISK_BLOCK_PERCENT` (90%).
  Veja `odb doctor`.

Uma ingestão com falha **não avança o watermark**: a próxima execução refaz o
plano completo, e a deduplicação evita bytes repetidos.

## Verificar a integridade da Bronze

```bash
# no host: lista checksum + caminho dos artefatos stored
docker compose exec -T postgres psql -U odb_owner -d odb -At -F ' ' -c \
  "SELECT checksum_sha256, replace(storage_uri,'file://','') FROM operations.bronze_artifact WHERE ingestion_status='stored'" > sums.txt
docker compose --profile data run --rm -T -v "$PWD/sums.txt:/tmp/sums.txt:ro" worker \
  sh -c 'awk "{print \$1\"  \"\$2}" /tmp/sums.txt | sha256sum -c --quiet && echo OK'
```

## Regras

- Não apague nem edite arquivos da Bronze: eles são somente leitura e
  referenciados pelo catálogo.
- Novos datasets entram por configuração (`configs/sources/*.toml`), com
  identificadores verificados na fonte e documentados em `docs/data_catalog/`.
- Não contorne autenticação, CAPTCHA ou limites de taxa (§7.3).

## DATASUS (FTP)

O conector `ftp_file` (ADR-0011) espelha pastas do FTP oficial do DATASUS na
Bronze. Os 32 datasets estão em `configs/sources/datasus.toml`, um por pasta do
SIM e do SINASC (~18 GB).

```bash
docker compose --profile data run --rm worker odb ingest run $(grep -o 'id = "datasus-[a-z0-9-]*"' configs/sources/datasus.toml | cut -d'"' -f2 | grep -v datasus-ftp)
docker compose --profile data run --rm worker odb silver build datasus-sim-cid10-dores
docker compose --profile data run --rm worker odb fontes comparar-obitos
```

- **Ritmo:** a transferência medida foi de ~0,56 MB/s, com uma conexão só e
  reaproveitada entre arquivos. Não abra conexões paralelas: é um servidor
  público.
- **Mudança:** detectada pela listagem (tamanho e data). Uma nova execução só
  baixa arquivos novos ou revisados.
- **Nomes:** na Bronze, minúsculos e com sufixo de hash. O nome original fica
  em `partition_key` e em `source_url`.
- **Mudança de regra:** a impressão digital da Silver considera a Bronze e as
  configurações, não o código. Depois de mudar uma regra de transformação (por exemplo,
  a UF de residência do SIM), reconstrua com `odb silver build <dataset> --force`; sem
  isso, o build é pulado (`skipped`).
- **Privacidade:** os microdados (`.dbc`) ficam só na Bronze, com
  `access_classification = "restricted"`. A Silver do SIM guarda óbitos por
  município de residência e por UF: o Total e cada dimensão separadamente
  (sexo, faixa etária, cor ou raça, capítulo da CID-10, local de ocorrência).

## MJSP: segurança pública (`mjsp-estatistica`)

A fonte usa downloads diretos do portal gov.br, com um arquivo por dataset (`http_file`).
Avaliação e pendências: `docs/data_catalog/seguranca-publica-avaliacao.md`; decisões: ADR-0012.

```bash
# Bronze: 12 bases anuais do Sinesp VDE, notas, PDFs do Mapa e bases da Pesquisa Perfil
docker compose --profile data run --rm worker odb ingest run \
  $(grep -o '^id = "mjsp-[a-z0-9-]*"' configs/sources/mj.toml | cut -d'"' -f2 \
    | grep -v -x -e mjsp-estatistica -e mjsp-portal-cc-by-nd)

# Silver do Sinesp VDE (um dataset por ano; a DTB precisa estar na Silver)
docker compose --profile data run --rm worker odb silver build \
  $(for y in $(seq 2015 2026); do printf "mjsp-sinesp-vde-%s " $y; done)
```

- **Rodar mensalmente:** a planilha do ano corrente muda ao longo do ano, e a fonte revisa
  anos anteriores. Arquivo igual é reaproveitado pelo checksum; arquivo diferente vira
  versão nova.
- **HEAD 403:** o servidor recusa HEAD, mas responde ao GET normal. O conector só usa GET.
- **Quarentena esperada:** o link do Mapa 2024 devolve HTML, e a validação de PDF o
  rejeita. Isso é registrado e não interrompe os outros datasets.
- **Município sem correspondência:** a verificação `sinesp.municipality_names` lista os
  nomes. Para cada um, procure o código na DTB (correspondência única) e acrescente em
  `[datasets.silver.aliases]` dos 12 datasets em `configs/sources/mj.toml`. Depois,
  reconstrua a imagem do worker, porque a configuração vai embutida nela, e a Silver.
- **Uso interno:** a licença está em `requires_review` (CC BY-ND do portal). Nada vai para
  a Gold até a confirmação.

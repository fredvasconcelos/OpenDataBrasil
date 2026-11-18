# Runbook: ciclo de atualização dos dados

Decisão e motivos: [ADR-0015](../adr/0015-conferencia-portal-release-e-ciclo-de-atualizacao.md).

**Regra:** tudo é construído na máquina local. Só vai para produção um release que
passou por todas as etapas abaixo. A produção não baixa nem constrói dados.

Os comandos rodam no worker: `docker compose --profile data run --rm worker <comando>`.

## Etapas

1. **Imagens com o código e a configuração atuais.** Worker e API sempre juntos:

   ```bash
   docker compose --profile data --profile web build worker api
   ```

2. **Consultar as fontes e baixar só o que é novo.** O padrão é incremental (o
   Sinesp VDE, por exemplo, publica um mês novo). O conteúdo igual ao já guardado é
   reconhecido pelo checksum e não se duplica.

   ```bash
   odb ingest run --all                  # --full rebaixa todas as partições
   odb ingest status --limit 50          # nenhuma falha sem explicação
   ```

3. **Conferir a Bronze.** Veja os artefatos em quarentena e os erros em
   [ingestao.md](ingestao.md#investigar-uma-falha).

4. **Reconstruir a Silver.** Só os datasets cuja Bronze mudou são refeitos.

   ```bash
   odb silver build --all
   odb quality report                    # nenhum fail
   ```

5. **Construir a Gold e conferir o portal.**

   ```bash
   odb gold build                        # release validated; skipped se nada mudou
   odb quality gold                      # nenhum fail; avisos conhecidos em known-issues.md
   odb release check <release_id>        # código 0
   ```

6. **Ativar localmente e revisar.**

   ```bash
   odb release activate <release_id> && docker compose --profile web up -d api
   curl -s localhost:8000/health         # "portal": "ok", "unavailable_kpis": {}
   ```

   Abra o portal local e confira os KPIs que mudaram.

7. **Promover para produção.** Ainda não existe (Fase 7).

## Quando algo falha

- O release ativo, local e de produção, continua vigente.
- Corrija a causa e recomece da etapa que falhou.
- Uma construção da Gold com `failed` deixa versões Delta sem release, o que é
  esperado (ver [gold.md](gold.md)).

## Pendências

- O comando único `odb atualizar`, que encadeie as etapas 2 a 5 e relate o que mudou:
  datasets com dados novos, períodos novos, linhas e verificações por dataset.
- A promoção para produção: o pacote com as versões Delta fixadas do release e a
  imagem da API (Fase 7).

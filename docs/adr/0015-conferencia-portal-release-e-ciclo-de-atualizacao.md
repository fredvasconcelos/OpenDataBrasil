# ADR-0015: Conferência portal × release (rígida no worker, tolerante na API) e ciclo de atualização

- **Estado:** aceito (2026-11-12), a pedido do mantenedor.
- **Contexto normativo:** CLAUDE.md §7.5, §10.9, §12.6, §16.4, §17.4 e §28.5.

## Contexto

A configuração do portal (`configs/portal/*.toml` e o panorama) vai embutida nas imagens
do worker e da API, e cada KPI aponta para um indicador da Gold. Até aqui, a API
conferia a configuração inteira contra o release ativo na primeira requisição. Bastava
um KPI incoerente para a conferência falhar: `/portal/navigation` respondia 500, e todas
as páginas do portal mostravam "Dados temporariamente indisponíveis".

Isso aconteceu em 2026-11-12, por alguns minutos. O release novo, já sem o indicador da
tabela 9514, foi ativado antes de a API ser reiniciada com a configuração nova. Os dados
estavam certos. Só a ordem da publicação estava errada, e ainda assim o portal inteiro
saiu do ar.

O mantenedor definiu também o modo de operação:

- a Bronze, a Silver e a Gold são construídas na máquina local;
- só vai para produção um release estável, conferido localmente;
- de tempos em tempos, um ciclo de atualização consulta as fontes, baixa o que for novo
  (o Sinesp VDE, por exemplo, é mensal), confere a Bronze e a Silver, reconstrói a Gold
  e publica de novo.

## Decisões

### 1. Conferência rígida no worker, antes de ativar

- `odb release check [<release_id>]` confere o portal e o panorama do worker contra um
  release. São os mesmos arquivos que vão na imagem da API. O comando lê `dim_indicator`
  e `dim_category` nas versões fixadas do release e sai com código 1 se houver problema.
- `odb release activate` e `odb gold build --activate` rodam a mesma conferência e
  **recusam a ativação** se algum KPI não casar com o release. Nesse caso, o release fica
  `validated`, e o ativo anterior continua vigente (§7.5, §16.4).
- `--skip-portal-check` ativa mesmo assim. É para o caso raro de publicar os dados antes
  da configuração; a API esconde os KPIs afetados (decisão 2).
- **O que é conferido, por KPI:**
  - o indicador está publicado no release;
  - o indicador tem cada classificação exposta;
  - a partição exposta existe;
  - com o panorama, a tabela de origem publicada é a que o item declara.
- **Onde fica o código:** a conferência saiu da API para `odb_semantics.portal`, de modo
  que o worker a usa sem depender do pacote da API.
- **Caminhos no worker:** `ODB_PORTAL_CONFIG_DIR` e `ODB_PANORAMA_PATH`, com padrões
  `configs/portal` e `configs/catalog/panorama.toml`.

### 2. Conferência tolerante na API

- A API faz a mesma conferência, uma vez por release, mas não derruba a navegação:
  - o KPI com problema sai da navegação, sem aparecer nem como "planejado";
  - as rotas dele respondem 404 (`KPI indisponível no release ...`);
  - os demais KPIs seguem no ar.
- O problema aparece em dois lugares:
  - no log, com o evento `portal.kpis_indisponiveis` (release, KPIs e problemas);
  - no `/health`, com `portal: "degraded"` e `unavailable_kpis` (KPI → problemas).
- O `/health` continua respondendo 200: o serviço está de pé, e o healthcheck do Docker
  não deve reiniciar a API por causa de um KPI.
- **Por quê:** a falha de um item não pode interromper os demais (§7.5). A trava contra
  configuração errada fica na ativação (decisão 1), onde a ação ainda é reversível sem
  afetar quem está usando o portal.
- Erros de estrutura da configuração, como TOML inválido, KPI repetido ou panorama sem
  cobertura, continuam impedindo a API de subir. Eles não dependem do release e são
  barrados pelos testes.

### 3. Ciclo de atualização: local até estar estável, depois produção

| Etapa | Onde | Comando hoje | Critério para seguir |
|---|---|---|---|
| 1. Consultar as fontes e baixar só o novo | local | `odb ingest run --all` (incremental; `--full` rebaixa tudo) | `odb ingest status` sem falhas |
| 2. Conferir a Bronze | local | `odb ingest status`, quarentena e checksums ([ingestao.md](../runbooks/ingestao.md)) | nenhum artefato em quarentena sem explicação |
| 3. Reconstruir a Silver | local | `odb silver build --all` (pula o que não mudou) | `odb quality report` sem `fail` |
| 4. Construir a Gold | local | `odb gold build` (release `validated`) | verificações sem `fail` |
| 5. Conferir o portal | local | `odb release check <release_id>` | código 0 |
| 6. Ativar localmente e revisar | local | `odb release activate <release_id>` e reinício da API | portal local conferido, `/health` com `portal: ok` |
| 7. Promover para produção | produção | **ainda não existe** (Fase 7) | — |

- **Regra:** só vai para produção o release que passou pelas etapas 1 a 6 localmente. A
  produção não constrói nada: recebe as versões Delta fixadas do release e a imagem da
  API com a mesma configuração.
- **Se uma etapa falhar:** o release ativo, local e de produção, continua vigente
  (§7.5). Corrige-se a causa e o ciclo recomeça da etapa que falhou.
- **Ficam para depois, e precisam de aprovação:**
  - a etapa 7, que é o pacote e a promoção para a VPS (Fase 7, ADR próprio);
  - um comando único (`odb atualizar`) que encadeie as etapas 1 a 5 e produza um
    relatório do que mudou: datasets com dados novos, períodos novos, linhas e
    verificações por dataset.

## Consequências

- Uma configuração incoerente não chega a ser ativada pelo worker. Se chegar, pela ordem
  de reinício ou por `--skip-portal-check`, a API esconde só os KPIs afetados.
- O risco que sobra é um KPI sumir sem ninguém notar. Por isso o `/health` mostra o
  estado `degraded`, e a etapa 6 do ciclo exige `portal: ok` antes da promoção.
- `HealthOut` muda o contrato do `/health`: os campos `portal` e `unavailable_kpis` são
  novos, e os antigos ficam como estavam.

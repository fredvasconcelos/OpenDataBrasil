# ADR-0037: API das contas públicas (`/api/v1/contas`)

- **Estado:** aceito (2026-11-22), na CP4 aprovada pelo mantenedor ("Aprovo o limite de 5%,
  segue com a CP4").
- **Contexto normativo:** CLAUDE.md §5.3, §11.4, §11.5, §17.4, §18 e §23; ADR-0015 (release),
  ADR-0031 (pessoas físicas), ADR-0034 (mapa, gráfico, tabela e ranking), ADR-0036 (Gold).

## Contexto

A Gold do escopo `contas` (ADR-0036) tem release próprio. O portal precisa de rotas para o
mapa, o gráfico, a tabela paginada, o ranking, a ficha do favorecido, a busca e a execução
da despesa, com estes requisitos:
- nenhuma transformação pesada na requisição;
- só nomes na tela;
- `noindex` nas fichas de pessoa física.

## Decisões

1. **Rotas** (só GET, parâmetros estruturados, sem SQL nem caminhos):

   | Rota | Lê | Uso |
   |---|---|---|
   | `/contas/meta` | `agg_contas_period_status` | lentes, dimensões, meses e situação de cada mês |
   | `/contas/map` | `agg_contas_territory` | total por território; com `dimension` + `categories`, a soma das escolhidas |
   | `/contas/composition` | idem | as 10 maiores categorias do território e "demais" |
   | `/contas/series` | idem | série mensal ou anual, do total ou de até 10 categorias + "demais" |
   | `/contas/ranking` | `agg_recipient_rank` | páginas de 10, até 100, por território e ano |
   | `/contas/table` | fatos A e B | agrupa por território-filho, dimensão ou favorecido; filtros `dimensão:código`; 10 por página, até 100 |
   | `/contas/favorecidos/{recipient_id}` | fatos A e B | ficha: totais por ano, série mensal, 10 maiores órgãos |
   | `/contas/busca` | dimensões | favorecidos PJ, órgãos, programas e ações (mínimo de 3 letras) |
   | `/contas/execucao` | fato C | as seis fases por categoria, sem território |

   Toda resposta informa o release (`X-ODB-Release`), as tabelas e versões, os meses usados
   e `partial` com as notas dos meses abertos ou incompletos (ADR-0036, decisão 3).
2. **Release próprio.** A API tem um segundo resolvedor, para o escopo `contas`
   (`ODB_API_CONTAS_SCOPE`). Sem release, as rotas respondem 503, e o painel não é
   afetado. Para a **homologação local**, `ODB_API_CONTAS_RELEASE_ID` fixa um release
   `validated` ou `active` do escopo. Um release reprovado nunca é servido. Em produção,
   essa variável fica vazia e vale o release ativo.
3. **Cache por release.** As rotas das contas entram no cache de respostas com a chave do
   release das contas, e a troca de release nunca serve dado antigo (§17.4). O cache
   preserva `X-Robots-Tag`.
4. **Só o nome** (ADR-0034, decisão 6):
   - nenhuma resposta traz CNPJ, CPF mascarado ou código do favorecido;
   - o favorecido é identificado por `recipient_id`: 16 hex do SHA-256 de código + nome,
     o mesmo em todos os releases, para links estáveis (`dim_recipient` 1.2.0);
   - para distinguir homônimos de PJ, a resposta traz a sede do cadastro PJ;
   - as exportações com códigos ficam para depois, como já previsto.
5. **Pessoas físicas** (ADR-0031):
   - a ficha de PF responde com `X-Robots-Tag: noindex, nofollow`;
   - ranking, tabela e ficha com PF trazem o aviso de homônimo;
   - a busca não encontra pessoas físicas (plano, seção 9). Elas aparecem nos totais, nas
     tabelas e nos rankings dos territórios.
6. **SQL só de fragmentos fixos:**
   - dimensões, agrupamentos e níveis vêm de listas fechadas;
   - meses, anos, lente, nível e UF entram como literais **depois** de conferidos contra o
     release ou as listas, o que permite ao DuckDB podar partições;
   - códigos e textos do usuário vão como `$parâmetros`;
   - o motor continua com os limites de concorrência, tempo e linhas da API (§11.4, §11.5).
7. **Organização física para a consulta** (medida no k6, decisão 8):
   - os fatos A e B passam a ser particionados por **ano e UF**, como o ADR-0034 previa
     (contratos 1.1.0);
   - os agregados e o ranking são gravados ordenados por território, e a consulta de um
     território lê um só grupo de linhas;
   - a troca de particionamento de uma tabela existente só acontece com a troca de schema
     pedida pelo operador (`odb gold build --reset-schema <tabela>`) e a tabela inteira
     sobrescrita. As versões anteriores continuam legíveis.
8. **Desempenho medido** (2026-11-22; API local com cache, 2 CPU, 3 GB; k6 com metade das
   visitas no painel e metade nas contas; p95 em ms):

   | VUs | painel (todas) | painel detalhe | contas ranking | contas tabela | contas ficha | 5xx nas contas |
   |---:|---:|---:|---:|---:|---:|---:|
   | 10 | 628 | 452 | 172 | 307 | 385 | 0 |
   | 25 | 721 | 862 | 408 | 534 | 776 | 0 |
   | 50 | 636 | 1.983 | 626 | 1.225 | 1.749 | 0 |

   - **Aceite do ADR-0034, decisão 8:**
     - com 10 e 25 VUs, atendido: a tabela e o ranking ficam abaixo do p95 do painel;
     - com 50 VUs, o ranking fica no limite (626 contra 636), e a tabela fica acima do p95
       geral do painel (1,2 s contra 0,64 s, que é puxado pelas rotas em cache), mas abaixo
       da rota mais pesada do painel (o detalhe, com 2,0 s);
     - não houve nenhum 5xx.
   - A organização da decisão 7 reduziu o p95 da tabela, com 50 VUs, de 4,3 s para 1,2 s,
     e o da ficha de 5,5 s para 1,7 s. Antes dela, 0,8% das requisições das contas
     respondiam 503 com 50 VUs.
   - A medida definitiva é na Vitrine, na homologação (CP7).

## Consequências

- O portal (CP5) tem o contrato em `tests/contracts/openapi.json`, e os tipos em
  `apps/portal/src/lib/api-schema.ts`. As rotas do painel não mudaram.
- A ativação do release das contas e a implantação na Vitrine continuam dependendo de
  aprovação.

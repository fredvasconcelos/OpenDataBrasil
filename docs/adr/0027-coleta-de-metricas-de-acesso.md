# ADR-0027: Coleta de métricas de acesso

- **Estado:** aceita (2026-11-17), pelo mantenedor: **sem cookies** (sai "visitantes
  únicos"), **limiar de supressão de 5**, exceção da Vitrine e banco separado
  `odb_metrics` aprovados; origem da UF pela Cloudflare (`cf-region-code`), conferida no
  painel em 2026-11-17. Implementado (2026-11-17): banco `odb_metrics` (item 4), página
  `/metricas` (DS 2.12), log do Caddy sem IP, agregador e endpoints (itens 1, 2, 3 e 7).
  Falta só ligar a transformação da Cloudflare e conferir o primeiro dia (pendências).
- **Motiva:** a página Métricas (`/metricas`), descrita em `proposta-metricas.md` do
  design system e no mockup de 5 telas (Mundo claro e escuro, Grande Região, Estado,
  celular).
- **Relaciona-se com:** ADR-0025 (Fábrica e Vitrine), CLAUDE.md §5.3, §12, §18.5, §23 e §26.

## Contexto

A página Métricas mostra quantos acessos o portal recebe e de onde eles vêm, em três
níveis: País › Grande Região › Estado. Ela também mostra os conjuntos de dados mais vistos
e mais baixados. Hoje **não existe nenhuma coleta**: nem logs de acesso guardados, nem
tabela, nem endpoint.

Quatro restrições moldam a decisão:

1. **A Vitrine é somente leitura** (ADR-0025). Ela serve releases prontos e "nunca
   transforma dados". A API conecta no PostgreSQL com o papel `odb_reader`.
2. **O catálogo da Vitrine é substituído a cada implantação.** O `deploy.sh` faz
   `pg_restore --clean --if-exists` do dump inteiro da Fábrica. Qualquer tabela de métricas
   que também exista na Fábrica seria apagada a cada implantação.
3. **LGPD e §23.** O IP é dado pessoal. A localização não pode ser mais fina que a UF.
   Contagens pequenas podem identificar pessoas.
4. **Sem custo e sem serviço proprietário no núcleo.** A Cloudflare gratuita já está na
   borda (ADR-0025, item 5) e é opcional.

## Decisões propostas

### 1. Fonte: o log de acesso do Caddy, sem script no navegador

Tudo o que interessa passa pelo Caddy: páginas, chamadas da API (`/odb-api/*`) e
exportações. Ele grava um log em JSON, que é a única fonte da coleta sem cookie. Não há
script de rastreamento no navegador nesta fase.

Contamos:

| Evento | Como se reconhece no log |
|---|---|
| Visualização de página | `GET` de página do portal (não `/_next/*`, não `/odb-api/*`), status 200, sem cabeçalho de *prefetch* do Next.js |
| Abertura de indicador | Visualização de `/dashboard` com `?kpi=<id>` |
| Download | `GET` do endpoint de exportação, com o formato (CSV, XLSX, Parquet, JSON) |
| Consulta à API | Só quando houver API pública (§18.6). Até lá, o cartão não aparece |

Requisições de robôs são descartadas na agregação, pela lista de *user agents* conhecidos.
O *user agent* não é guardado.

**Regras implementadas** (`packages/cli/src/odb_cli/access_log.py`, conferidas com um
navegador real atrás do Caddyfile da Vitrine em 2026-11-17):

- *Prefetch* do Next.js (`Next-Router-Prefetch: 1`) e do navegador (`Sec-Purpose:
  prefetch`) não contam: só a página inicial dispara cerca de 20.
- Uma navegação sem recarregar (requisição RSC, cabeçalho `RSC: 1`) só conta como
  visualização quando muda de rota em relação ao `Referer`. Trocar filtros no painel faz
  `router.replace` na mesma rota e não é página nova.
- Abertura de indicador: `/dashboard` cujo `kpi` difere do `kpi` do `Referer` (ou vindo de
  outra página, ou carga direta). O navegador atualiza o `Referer` depois de cada troca;
  cada troca de indicador gera uma requisição só. O painel aberto sem `?kpi=` mostra o
  primeiro indicador, que não é contado (o log não diz qual é).
- Download: a exportação é `POST` e o corpo não aparece no log. A API devolve
  `X-ODB-KPI` e `X-ODB-Format`, que o Caddy grava.
- Arquivos de `public/` (com extensão), `/_next/*`, `/odb-api/*` e status diferente de
  200 não são páginas. O `Referer` vira só o domínio, e vazio quando é o próprio portal.

### 2. IP: nunca gravado em disco; localização no máximo por UF

- **Decisão do mantenedor:** a origem é confirmada na Cloudflare ao fim da implementação.
  O código aceita as duas origens abaixo, e a escolhida fica registrada aqui.
- **Com a Cloudflare na frente**, por túnel configurado pelo operador:
  - o país vem do `CF-IPCountry`, que a Cloudflare envia em todos os planos;
  - a UF vem do `cf-region-code`, da transformação gerenciada *Add visitor location
    headers*. **Conferido pelo mantenedor em 2026-11-17:** existe no plano gratuito
    (Rules → Settings → Managed Transforms). Ligada, ela envia também cidade, CEP,
    coordenadas, `cf-metro-code` e fuso; por isso só é ligada depois de o filtro abaixo
    estar no ar. O código vem como a parte da subdivisão ISO 3166-2 (`SP`); o agregador
    aceita também `BR-SP`. O formato real é conferido no primeiro dia de coleta.
  - Um túnel temporário fora da zona configurada não recebe as mesmas transformações: lá
    não há `cf-region-code` e a UF fica desconhecida.
  - O filtro de log do Caddy **apaga** antes de gravar: IP remoto, `client_ip`, porta,
    `CF-Connecting-IP`, `X-Forwarded-For`, `Cookie`, `Authorization` e os cabeçalhos de
    cidade, CEP e coordenadas (`cf-ipcity`, `cf-postal-code`, `cf-iplatitude`,
    `cf-iplongitude`, `cf-metro-code`).
  - Implementado como `format filter` que apaga `request>headers` e `resp_headers`
    inteiros (não uma lista de nomes: cabeçalho novo com IP também sai), mais
    `remote_ip`, `remote_port`, `client_ip`, `tls` e `user_id`. Os campos necessários
    entram um a um por `log_append`. A cidade, o CEP, as coordenadas e o
    `CF-Connecting-IP` também não seguem para o portal (`header_up -…`).
  - Prova: `infrastructure/scripts/caddy_log_check.sh` (no CI) sobe o Caddyfile real
    na imagem fixada (2.11.9), manda IP, cookie, credencial e localização fina, e falha
    se algo disso aparecer no arquivo. Com o filtro sabotado, ele falha.
- **Sem a Cloudflare** (só se a VPS um dia for servida sem ela; não implementado):
  uma base GeoIP local e aberta, a DB-IP Lite
  (CC BY 4.0), consultada dentro do Caddy ou de um módulo de agregação em memória. O IP é
  usado só para a consulta e não chega ao arquivo.
  - MaxMind GeoLite2 fica de fora: exige conta e aceite de licença própria.
- A sigla ISO 3166-2 da UF (ex.: `BR-SP`) vira a chave do portal (`uf:35`). A Grande
  Região sai do 1º dígito do código IBGE.
- Acessos sem localização entram como "Brasil, UF não identificada" ou "país não
  identificado", nunca distribuídos entre lugares.
- **Precisão (ressalva):** a localização por IP é aproximada. Em internet móvel e com
  CGNAT, o IP pode ser o da saída da operadora e o acesso cair no estado da sede dela
  (ou ficar sem UF); VPN mostra o lugar da VPN. A página diz isso em "Como contamos".

### 3. Agregação na Vitrine, com exceção explícita à ADR-0025

Um processo pequeno (`odb metrics aggregate`, na imagem da API; serviço
`metrics-aggregator` do `compose.yaml` da Vitrine) roda a cada 5 minutos:

1. lê o log rotacionado (`access-*.log`; o `access.log` em uso fica para depois);
2. soma por dia (fuso `America/Sao_Paulo`), evento, país, UF, rota, `kpi_id` e formato;
3. grava as somas no banco de métricas (item 4);
4. apaga o trecho já processado.

O log bruto, já sem IP, fica no máximo 24 horas:

- o Caddy roda o arquivo de hora em hora (`roll_interval 1h`), mas **só na primeira
  escrita depois do intervalo** (conferido na 2.11.9). Sem visitantes, linhas velhas
  ficariam no arquivo ativo; o healthcheck do Caddy chama `/_odb/tick` a cada 5 min e
  garante a escrita;
- o nome do arquivo somado vai para `access_log_file` na mesma transação das somas: se o
  agregador cair antes de apagar o arquivo, a rodada seguinte só o apaga;
- arquivo que não pôde ser somado em 23 h (banco fora do ar) é apagado assim mesmo, e o
  `roll_keep_for 24h` do Caddy é a última rede de segurança;
- o agregador roda como root **sem nenhuma capacidade**, com sistema de arquivos só
  leitura: só para ler e apagar os arquivos do Caddy (dono root, modo 0640).

Isso é uma **exceção delimitada à regra "a Vitrine nunca transforma dados"**: a regra
continua valendo para os dados oficiais (Bronze, Silver e Gold). Métricas de acesso são
dado operacional do próprio portal, geradas na Vitrine, e não entram em releases. Se
aprovada, a exceção deve ser registrada também no CLAUDE.md §26.1.

### 4. Armazenamento: PostgreSQL, num banco próprio da Vitrine (`odb_metrics`)

| Critério | PostgreSQL (`odb_metrics`) | Delta |
|---|---|---|
| Natureza | Dado operacional (§12.2) | Formato da Silver e da Gold, produtos da Fábrica |
| Quem escreve | A Vitrine, em pequenas somas a cada 5 min | Só a Fábrica (§5.3, §11.6, ADR-0025) |
| Escrita incremental contínua | Simples (`INSERT … ON CONFLICT DO UPDATE`) | Gera muitos arquivos pequenos e exige manutenção |
| Sobrevive ao `deploy.sh` | Sim: banco separado, fora do dump da Fábrica | n/a |

- **Decisão:** PostgreSQL. Um banco separado, `odb_metrics`, porque o restore do catálogo
  com `--clean` nunca toca outro banco.
- **Criação:** `infrastructure/postgres/init/02-metrics-database.sh`, idempotente. Roda
  sozinho com o volume vazio e, numa instalação existente, pelo
  `docker compose exec -T postgres bash /docker-entrypoint-initdb.d/02-metrics-database.sh`;
  o `deploy.sh` o executa a cada implantação. Senhas em `ODB_METRICS_WRITER_PASSWORD` e
  `ODB_METRICS_READER_PASSWORD`.
- **Papéis:** `odb_metrics_writer` (SELECT, INSERT, UPDATE) só para o agregador;
  `odb_metrics_reader` (SELECT) só para a API. Nenhum dos dois apaga. O `odb_reader` e o
  `odb_pipeline` do catálogo nem conectam no `odb_metrics`.
- **Tabela:** `access_daily(day, event, country, uf, route, kpi_id, format,
  referrer_domain, count, updated_at)`, com chave primária nas oito primeiras colunas e
  somas por `INSERT … ON CONFLICT DO UPDATE`.
  - `event`: `page_view`, `kpi_open` ou `download`.
  - `country`: ISO 3166-1 alfa-2; `ZZ` = não identificado.
  - `uf`: código IBGE (11 a 53) só quando `country = 'BR'`; `0` = fora do Brasil ou UF
    não identificada.
  - `format`: só em `download` (`csv`, `xlsx`, `parquet`, `json`).
  - Os totais por Grande Região e por país saem dela; nenhuma coluna guarda dado pessoal.
  - Teste: `tests/integration/test_metrics_db.py`.
- **Retenção:** somas diárias sem prazo (não têm dado pessoal); log bruto até 24 h.
- **Backup:** `pg_dump` próprio do `odb_metrics`, junto do backup do catálogo da Vitrine.

### 5. Sem cookies (decisão do mantenedor, 2026-11-17)

O portal não grava cookie de medição nem pede consentimento. Por isso:

| Medida | Situação |
|---|---|
| Visualizações, downloads, aberturas de indicador, país, UF | Coletadas (item 1) |
| Origem do tráfego (domínio do site anterior, pelo `Referer`) | Coletada; o caminho e a busca do site anterior são descartados |
| Visitantes únicos, retorno | **Fora do escopo.** O cartão e o campo do tooltip saem da página |
| Buscas no catálogo | Fora do escopo: a busca roda no navegador e exigiria um evento enviado por script. Pode voltar numa ADR futura, sem cookie |

- **Alternativa recusada:** contar visitantes únicos sem cookie, por *hash* diário de IP
  + *user agent* (modelo do Plausible). Ela exigiria o IP no agregador, contrariando o
  item 2.
- A página diz "visualizações", nunca "pessoas" ou "visitantes".

### 6. Ferramenta: coleta própria, gratuita e auto-hospedada

| Ferramenta | Licença | Por que não |
|---|---|---|
| Umami | MIT | Script no navegador; localização até a cidade (MaxMind); mais um serviço |
| GoatCounter | EUPL 1.2 | Mais próxima (importa logs do Caddy), mas não tem a Grande Região nem o `kpi_id`, e acrescenta um serviço |
| Plausible CE | AGPL 3.0 | Exige ClickHouse, pesado para a Vitrine |
| Matomo | GPL 3.0 | PHP e MySQL, outra pilha inteira |

**Decisão:** coleta própria, com o log do Caddy, o agregador em Python e o PostgreSQL.
Tudo é aberto e não acrescenta serviço permanente. O GoatCounter fica como alternativa,
caso um painel pronto passe a valer mais que o recorte País › Grande Região › Estado.

### 7. Endpoints (FastAPI, só leitura do `odb_metrics`)

Parâmetro comum, `period`: `7d`, `30d`, `12m`, ou `custom` com `from` e `to` (AAAA-MM-DD,
até 366 dias). Toda resposta traz `period` (início e fim reais), `generated_at` e
`collection_started_at`, para a página dizer desde quando há coleta.

**`GET /api/v1/metrics/summary?period=30d`**

```json
{"period": {"from": "2026-10-18", "to": "2026-11-16"}, "generated_at": "…",
 "collection_started_at": "…", "views": 0, "kpi_opens": 0, "downloads": 0,
 "countries": 0, "api_calls": null}
```

`null` significa que a medida não é coletada (hoje, só `api_calls`, enquanto não houver
API pública). É diferente de zero.

**`GET /api/v1/metrics/geo?level=pais|regiao|uf&within=<chave>&period=30d`**

- `level=pais`: países, chave ISO 3166-1 alfa-2 (`pais:PT`).
- `level=regiao`: exige `within=pais:BR` (`regiao:1` … `regiao:5`).
- `level=uf`: aceita `within=pais:BR` ou `regiao:N` (`uf:11` … `uf:53`).

```json
{"level": "uf", "within": "regiao:3", "period": {…},
 "items": [{"geography_key": "uf:35", "name": "São Paulo", "views": 0,
            "share_pct": 0.0, "status": "ok"}]}
```

`status`:

- `ok`: valor publicado;
- `suprimido`: entre 1 e 4 visualizações; `views` vem `null` e a página mostra "menos
  de 5";
- `sem_acessos`: zero, pintado com `--odbr-map-zero`.

O `share_pct` é calculado sobre o total do recorte, com os suprimidos incluídos no total.

**`GET /api/v1/metrics/datasets?sort=views|downloads&period=30d&limit=10`**

```json
{"sort": "views", "period": {…},
 "items": [{"kpi_id": "populacao_estimada", "title": "População estimada",
            "theme": "População e demografia", "views": 0, "downloads": 0,
            "api_calls": null}]}
```

- A unidade é o **indicador** (`kpi_id`), que é o que o portal abre e exporta. O título e
  o tema vêm do catálogo do release ativo.
- O `dataset_id` da proposta (conjunto da Silver ou Gold) não é o que o visitante vê.
- O `limit` vai até 50.
- Indicadores com menos de 5 visualizações não entram no ranking.

**Cache e limites:**

- As respostas não entram no cache por release, que só serve dado imutável do release.
  Usam um cache próprio de 5 minutos, igual ao ciclo do agregador.
- O limite por visitante continua valendo (ADR-0025, V5).

**Sem coleta** (Fábrica, desenvolvimento, ou banco ainda vazio): os três endpoints
respondem **404** (`not_found`), e a página mostra "a coleta de acessos ainda não
começou". Isso substitui a ideia inicial de listas vazias, que a página mostraria como
zeros. Fixtures, marcadas como exemplo, só nos testes.

**Detalhes implementados:** `7d`, `30d` e `12m` terminam hoje (fuso de Brasília,
incluído); `custom` não passa de hoje. Os níveis `regiao` e `uf` trazem os lugares com
zero (o mapa pinta), mais `regiao:0`/`uf:0` ("Estado não identificado") e `pais:ZZ`
("Não identificado") quando houver. Nomes dos países em pt-BR do CLDR (módulo gerado
`apps/api/src/odb_api/countries.py`). No ranking de downloads só entram indicadores com
5 aberturas ou mais e ao menos um download.

### 8. Se a UF não vier da Cloudflare

Resolvido: o `cf-region-code` existe no plano gratuito (conferido em 2026-11-17). A DB-IP
Lite fica só para uma VPS servida sem a Cloudflare.

## Consequências

**Positivas:**

- Nenhum IP em disco.
- Nenhum script de terceiros e nenhum cookie, então não há banner de consentimento.
- Os dados ficam no nosso PostgreSQL e saem pela nossa API, com o mesmo cuidado de
  supressão que o projeto aplica aos dados oficiais.
- A troca de servidor ou de provedor (§26.2) leva junto só o banco `odb_metrics`.

**Negativas:**

- Sem cookie não há "visitantes únicos" nem buscas no catálogo; a página mostra
  visualizações.
- Os números contam a partir do dia em que a coleta começar; não há como recuperar o
  passado.
- Há um processo novo na Vitrine (o agregador) e uma exceção à regra de que ela não
  transforma dados.
- A localização depende da Cloudflare ou de uma base GeoIP, as duas com erro de algumas
  UFs (VPN, redes móveis).

## Decisões e pendências

| Ponto | Situação |
|---|---|
| Origem da UF (Cloudflare ou DB-IP Lite) | Cloudflare `cf-region-code` (transformação disponível no plano gratuito, conferida pelo mantenedor em 2026-11-17) |
| Ligar *Add visitor location headers* | Só depois de o filtro do Caddy estar no `beta`; no 1º dia, conferir o formato do código e se as UFs batem (mantenedor) |
| Supressão complementar | **Pendente de decisão.** Com um só lugar suprimido num recorte, o valor sai por subtração do total do nível acima. Suprimir também o menor publicado exigiria outro rótulo, porque a página diz "menos de 5" para todo suprimido. Hoje: só a primária |
| Cookies e consentimento | Não implementar; "visitantes únicos" sai (mantenedor, 2026-11-17) |
| Limiar de supressão (menos de 5) para UF, país e indicador | Confirmado (mantenedor, 2026-11-17) |
| Exceção da Vitrine (item 3) e banco separado `odb_metrics` (item 4) | Aprovados (mantenedor, 2026-11-17); banco criado na Fábrica |

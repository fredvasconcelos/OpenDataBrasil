# ADR-0012: Segurança pública do MJSP, com o Sinesp VDE na Silver e o resto preservado na Bronze

- **Estado:** aceito (2026-11-12). O mantenedor delegou as decisões e revisa ao final:
  ver [`seguranca-publica-avaliacao.md`](../data_catalog/seguranca-publica-avaliacao.md).
- **Contexto normativo:** CLAUDE.md §6, §7.3, §9, §15.4, §23 e §28. Segue o desenho da
  [ADR-0011](0011-datasus-ftp-espelho-e-agregados.md) (DATASUS).

## Contexto

O mantenedor pediu para avaliar e incorporar os dados de segurança pública do Ministério
da Justiça e Segurança Pública (MJSP), a partir de três páginas:

- **Sinesp VDE:** base de dados e notas metodológicas dos gestores estaduais;
- **Pesquisa Perfil:** perfil das instituições de segurança pública;
- **Mapa da Segurança Pública:** edição 2026.

Elas foram lidas em 2026-11-12, sem navegador e com GET simples. O servidor recusa HEAD
(403), mas responde ao GET normal. Não há autenticação, CAPTCHA nem bloqueio a contornar
(§7.3).

## Decisões

### 1. Fonte `mjsp-estatistica`, conector `http_file`

Os arquivos são downloads diretos do portal gov.br, então basta um dataset por arquivo.
O conector `http_file` ganhou a validação de dois formatos:

- **XLSX:** ZIP íntegro com `xl/workbook.xml`;
- **PDF:** assinatura `%PDF-`.

Uma página de erro em HTML ou um download truncado falha antes de entrar na Bronze.

### 2. O que entra, e até onde

A configuração está em `configs/sources/mj.toml`, com 28 datasets:

| Conjunto | Datasets | Bronze | Silver | Motivo |
|---|---:|---|---|---|
| Sinesp VDE `bancovde-AAAA.xlsx`, 2015 a 2026 | 12 | sim | sim | É a base estruturada: município × evento × mês |
| Página de notas metodológicas do VDE | 1 | sim | não | Texto por UF sobre cobertura e mudanças de registro; preservado como documentação |
| Mapa da Segurança Pública (2026, infográficos 2026, 2024, 1º sem. 2023) | 4 | sim | não | Só PDF, sem base estruturada; referência para conferência |
| Pesquisa Perfil, bases de pesquisas anteriores (ZIP) | 11 | sim | não | Dados institucionais (unidades, efetivo), sem relação direta com os indicadores; avaliar depois |

Sobre a Pesquisa Perfil, os links "Base de dados" e "Relatório 2022" da página principal
respondem 404, então só as bases de pesquisas anteriores estão disponíveis.

### 3. Silver do Sinesp VDE (`sinesp_vde`)

A Silver usa o contrato de observação do SIDRA, como o SIM.

- **Variáveis:** uma por evento, 31 em 2023. A unidade é a da medida publicada:
  - "Vítimas" (`total_vitima`);
  - "Quilogramas" (`total_peso`, apreensão de drogas);
  - contagem em `total`, com nome específico: "Ocorrências", "Armas", "Mandados",
    "Alvarás", "Vistorias" e "Atendimentos".
- **Território:**
  - **município (nível 6):** casado com a DTB pelo nome normalizado (sem acento,
    apóstrofo ou hífen) e pela UF. Seis grafias da fonte foram registradas como `aliases`
    (por exemplo, "AÇU" → Assú e "SÃO LUIZ" → São Luiz do Anauá), cada uma com
    correspondência única conferida na DTB;
  - **UF (nível 3):** soma de todas as linhas da UF, inclusive "NÃO INFORMADO" e nomes sem
    correspondência. Por isso não há reconciliação entre níveis.
- **Classificações:** Total e a distribuição de cada dimensão, com as demais no Total e sem
  cruzamento:
  - sexo das vítimas (colunas `feminino`, `masculino` e `nao_informado`);
  - agente;
  - arma;
  - faixa etária;
  - abrangência, só nos eventos com linhas da PF ou da PRF. Nos outros, "Estadual"
    repetiria o Total.
- **Valores:**
  - linhas repetidas da mesma chave são somadas, conforme a nota da página de download;
  - valor ausente vira "..." (não disponível) e nunca zero;
  - zero informado vira zero verdadeiro: na legenda do SIDRA, "0" é arredondamento,
    o que não vale aqui.
- **Partição:** um `table_id` por ano (`SINESP-VDE-AAAA`), porque cada ano é um dataset.
  As variáveis são as mesmas entre os anos.
- **Verificações:**
  - as do contrato SIDRA;
  - aviso para municípios sem correspondência;
  - aviso para chaves repetidas;
  - registro da medida usada por evento.

### 4. Classificação de acesso e licença

Esta decisão foi revista em 2026-11-12, com a base legal indicada pelo mantenedor.

- **Dados do Sinesp VDE: dados abertos, licença `mjsp-dados-abertos`, aprovada.** São
  dados públicos autorizados que integram a política nacional de dados abertos:
  - o **Decreto nº 8.777/2016** institui a Política de Dados Abertos;
  - a **IN nº 47/2025** (INDA) define "licença aberta" como a que permite a qualquer
    pessoa utilizar, reutilizar e redistribuir os dados, "estando sujeito, no máximo, a
    exigência de creditar a sua autoria ou fonte";
  - a **Portaria MJSP nº 842/2025** (DOU de 16/01/2025) aprova o Plano de Dados Abertos
    2024-2026. O plano lista "Dados Ocorrências Criminais – Sinesp" (Senasp) entre as
    bases abertas (p. 27) e no inventário (item 76, abertura "não se aplica", isto é, já
    aberta).

  O PDF do plano está preservado na Bronze (`mjsp-pda-2024-2026`). A exigência é creditar
  a fonte: "MJSP/Senasp, Sinesp VDE". Os datasets ficam em `public_authorized`.
- **Publicações e páginas (PDFs do Mapa, página de notas, o próprio PDA):** são conteúdo
  editorial do portal, sob CC BY-ND 3.0 (`mjsp-portal-cc-by-nd`). Servem de
  documentação e não viram dado publicado.
- **Pesquisa Perfil:** não consta do PDA e segue em `requires_review`.

A Bronze guarda a licença conhecida no momento de cada download. Os artefatos do Sinesp
baixados antes desta revisão registram a licença anterior, como histórico; o catálogo
(`catalog.dataset`) já reflete a licença aprovada.

### 5. Relação com o que já existe: KPI novo, não complemento

O panorama já tem "Vítimas de homicídio por 100 mil habitantes" (tabela SIDRA 6606, ODS
16.1.1), que vem das declarações de óbito. O Sinesp VDE é registro policial, por local da
ocorrência e com cobertura que varia por UF e ano (notas metodológicas). Pela regra do
mantenedor (ADR-0011, decisão 5), o Sinesp entra como KPI novo, com fonte própria, e não
completa a série do IBGE.

A comparação com o SIM ainda não é possível. A Silver do SIM hoje traz só o capítulo da
CID-10, e a comparação precisa do grupo "agressões" (X85–Y09). Ela vai para o relatório
de avaliação antes de qualquer uso conjunto.

### 6. Ausências: o que a planilha marca e o que ela esconde

As regras de ausência foram definidas depois de conferir os 12 anos contra as notas
metodológicas dos gestores.

- **Total com parcela ausente fica ausente.** Exemplo: na apreensão de cocaína do
  Tocantins, a parte estadual vem vazia de 2015 a março de 2024, enquanto a da PF vem
  preenchida. Somar só o que existe daria um total incompleto com aparência de completo.
- **Série federal vazia o ano inteiro é "não se aplica".** Quando a PF ou a PRF não
  informam um evento numa UF durante o ano todo (por exemplo, a PF em roubo e furto de
  veículo), essa série sai da soma. A UF e o evento ficam registrados na verificação
  `sinesp.federal_empty`. Sem essa regra, todos os totais de roubo de veículo ficariam
  ausentes.
- **Zeros que significam "indisponível": corrigidos pela tabela de cobertura.** As
  notas dizem que alguns indicadores não existem em certos períodos, mas a planilha
  publica 0 em todos os municípios. Exemplos:
  - Tocantins, feminicídio, 2015–2018;
  - Mato Grosso, tentativa de feminicídio, 2015–2018. Até 2018, os feminicídios de MT
    estão somados em homicídio doloso.

  O mantenedor aprovou a correção em 2026-11-12. A tabela curada
  `configs/sources/coverage/sinesp_vde.toml` traz 15 entradas (UF, eventos, período e
  a nota de origem), só com períodos declarados indisponíveis. A Silver marca como "não
  disponível" as linhas estaduais desses meses, antes da soma; a parte federal não muda.

  O SHA-256 do arquivo entra na impressão digital da Silver, e a verificação
  `sinesp.coverage` conta as linhas afetadas por entrada. O valor publicado continua na
  Bronze. Coberturas parciais (região metropolitana, capital) e mudanças de metodologia
  ficam como limitações dos KPIs, não na tabela.

### 7. Série de datasets e nível Brasil

- **Série:** os 12 datasets anuais têm `silver.series = "mjsp-sinesp-vde"`. O dataset
  `mjsp-sinesp-vde` (a página da série, com as notas) é o registro a que os indicadores
  se referem. A Gold lê as tabelas anuais de todos os membros (`DatasetInfo.table_ids`)
  e passou a aceitar mais de uma Silver (IBGE e MJSP), cada uma na sua versão.
- **Brasil (nível 1):** derivado na Silver, como soma de todas as linhas do mês. Fica
  "não disponível" se qualquer parcela faltar; a fonte não publica o total nacional.
- **Primeira versão:** a Gold leva o Total de cada evento.
  - O scan lazy descarta as linhas fora das categorias fixas dos fatos.
  - O detalhe por sexo ficou para depois da etapa 2 do KI-007 (volume municipal ×
    mensal). A etapa 2 foi feita em 2026-11-12: o volume deixou de ser o obstáculo.
    O conflito de nome com a c2 do IBGE foi resolvido na ADR-0014 (classificação
    própria `sexosinesp`, com o rótulo "Sexo"). Desde 2026-11-12, os 5 KPIs de vítimas
    detalham por sexo.

### 8. KPIs no portal

São seis KPIs no subtema "Vitimização e violência" do tema "Segurança e vitimização":

| KPI | Níveis |
|---|---|
| Homicídio doloso | município, UF e Brasil |
| Feminicídio | município, UF e Brasil |
| Latrocínio | município, UF e Brasil |
| Estupro | UF e Brasil |
| Morte por intervenção de agente do Estado | UF e Brasil |
| Roubo de veículo | UF e Brasil |

- **Configuração:** `configs/indicators/demografia/seguranca_sinesp.toml` e
  `configs/portal/demografia/seguranca_sinesp.toml`.
- **Panorama:** ganhou a lista `externos` por subtema, para KPIs curados fora do
  SIDRA. Essa lista fica fora do gerador e da conferência no acervo, e só a ligação com o
  portal é conferida.
- **Rodapé "Fonte":** a API informa a instituição e o sistema de cada fonte
  (`KpiSourceOut.institution` e `.system`, a partir de `configs/sources`). O portal
  escreve "MJSP · SINESP-VDE" em vez do texto fixo do IBGE/SIDRA.

## Consequências

- **Preservação:** a Bronze guarda as 12 bases anuais, as notas, os PDFs do Mapa e as 11
  bases da Pesquisa Perfil, com SHA-256.
- **Silver:** passa a ter segurança pública por município e mês (`mjsp/sidra_observation`),
  com cerca de 2,85 milhões de observações por ano completo, 93% delas zeros informados.
- **Gold:** publicada no release `2f89b1f9`, com 659 verificações aprovadas e os mesmos
  13 avisos anteriores.
- **Gold com várias Silvers:** feita (decisão 7). O processamento por dataset (KI-007,
  etapa 2) foi feito em 2026-11-12: pico do processo de 9,4 GiB, com o Sinesp e o SIM.
- **Atualização:** a planilha de 2026 é do ano corrente e muda ao longo do ano. A
  ingestão detecta a mudança pelo checksum e guarda a versão nova sem apagar a anterior.

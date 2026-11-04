# Problemas conhecidos e pendências

Registro de falhas e limitações que precisam de ação futura. Atualize o estado
ao resolver.

## KI-001: notas das tabelas SIDRA não são obtidas automaticamente

- **Estado:** aberto
- **Detectado em:** 2026-11-03
- **Impacto:** as notas oficiais explicam valores (municípios com instalação
  prevista, populações judiciais, correções) e são necessárias para
  interpretar e reconciliar os dados (exemplo: divergências da 6579 em 2004,
  2008 e 2012).

**Diagnóstico:**

1. A página `https://sidra.ibge.gov.br/tabela/<id>` contém
   `<div id="notas-tabela">` (XPath `//div[@id="notas-tabela"]` ou
   `/html/body/div[4]/div/div/div[2]`), mas o servidor entrega o elemento
   **vazio**.
2. O conteúdo é montado no navegador por `Scripts/editor-tabela.js`
   (`ID_NOTAS_TABELA`, `_preencherNotas`), a partir de
   `/Ajax/JSon/Tabela/1/<id>`.
3. Esse endpoint (e `apisidra.ibge.gov.br/desctabapi.aspx`) responde **HTTP 403
   a clientes automatizados**, atrás do Cloudflare.

**Decisão:** não contornar o bloqueio (§7.3): sem imitação de cabeçalhos,
navegador automatizado ou credenciais pessoais.

**Caminho de correção:**

1. Testar `https://servicodados.ibge.gov.br/api/v3/agregados/<id>/metadados`
   quando o serviço voltar (ver KI-002) e verificar se traz as notas.
2. Se não voltar ou não trouxer as notas, o mantenedor fornece as notas
   manualmente e elas são registradas como configuração versionada, com
   procedência (ver `docs/data_catalog/notas/`).

## KI-002: API `servicodados.ibge.gov.br` indisponível

- **Estado:** aberto
- **Detectado em:** 2026-11-03
- **Sintoma:** `ECONNREFUSED`/timeout a partir do WSL, do Windows e de serviço
  externo (agregados v3 e localidades).
- **Impacto:** sem metadados estruturados (KI-001) e sem a API de localidades.
- **Ação:** retestar periodicamente e, quando voltar, avaliar um conector de
  metadados.
- **Retestes:** 2026-11-04, ainda sem resposta (HTTP 000).

## KI-003: licença do IBGE em `requires_review`

- **Estado:** aberto
- **Detectado em:** 2026-11-03
- **Sintoma:** o texto oficial de termos de uso respondeu 403. As condições
  vieram de fontes secundárias (reuso com citação obrigatória).
- **Impacto:** bloqueia publicação pública (§23) até a confirmação.
- **Ação:** o mantenedor confirma o texto oficial e atualiza
  `configs/sources/ibge.toml` (`review_status = "approved"`).

## KI-004: área municipal do RS diverge da área da UF (tabela 4714)

- **Estado:** aberto
- **Detectado em:** 2026-11-03
- **Sintoma:** a soma das áreas municipais do RS (268.621,283 km²) é
  13.085,868 km² menor que a área da UF (281.707,151 km²).
- **Hipótese não verificada:** superfícies de água (lagoas dos Patos e Mirim)
  entram na área da UF e não na dos municípios.
- **Ação:** confirmar nas notas da tabela 4714 ou na metodologia de áreas
  territoriais do IBGE. Até lá, a Gold usa a área oficial publicada por nível.

## KI-005: portal Séries Estatísticas bloqueia clientes automatizados

- **Estado:** aberto (sem ação de contorno)
- **Detectado em:** 2026-11-04
- **Sintoma:** `seriesestatisticas.ibge.gov.br` responde 403, com desafio do
  Cloudflare.
- **Decisão:** não contornar (§7.3). As séries equivalentes (Censo 2022: cor ou
  raça, indígenas e quilombolas) foram localizadas no SIDRA (9605, 9718, 9578,
  9970, 9971, 9954 e 9723) e conferidas na API oficial.
- **Impacto:** a lista de séries do portal não é usada como fonte automática do
  catálogo temático. A árvore temática é curada em
  `configs/indicators/demografia.toml`.

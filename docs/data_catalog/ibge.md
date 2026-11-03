# Fontes e datasets do IBGE

Tudo aqui foi verificado por requisição real em **2026-11-03**. Configuração:
[`configs/sources/ibge.toml`](../../configs/sources/ibge.toml).

## Situação das fontes pesquisadas

| Fonte | Estado | Uso na plataforma |
|---|---|---|
| API SIDRA (`apisidra.ibge.gov.br/values`) | ✅ disponível | conector `sidra` |
| API de agregados v3 e de localidades (`servicodados.ibge.gov.br`) | ❌ indisponível (`ECONNREFUSED`/timeout a partir do WSL, do Windows e de serviço externo) | não utilizada; reavaliar |
| Downloads de geociências (`geoftp.ibge.gov.br`) | ✅ disponível, com `ETag`/`Last-Modified` | conector `http_file` |
| Estimativas em arquivo (`ftp.ibge.gov.br/Estimativas_de_Populacao/`) | ✅ disponível | não utilizada (o SIDRA cobre a série) |
| Página de ajuda da API SIDRA | ⚠️ responde 403 a clientes automatizados | consultada via busca |

## Comportamentos da API SIDRA (com fixtures em `tests/fixtures/ibge/`)

- Formato: lista JSON. O primeiro elemento é o cabeçalho (`NC, NN, MC, MN, V, D1C, D1N, …`).
- Período inexistente: **HTTP 200 com apenas o cabeçalho**. O conector trata como erro e envia para a quarentena.
- Tabela inexistente: HTTP 400 com texto simples (`Tabela 999999: Tabela inválida`).
- Sem `ETag`/`Last-Modified`; `cache-control: no-cache`.
- Limite de 100.000 valores por consulta (página de ajuda, via busca). O plano usa uma requisição por período.

## Datasets

### `ibge-sidra-6579`: População residente estimada

| Item | Valor |
|---|---|
| Tabela / variável | 6579 / 9324 "População residente estimada" (unidade: Pessoas) |
| Níveis | N1 (Brasil), N2 (Grandes Regiões), N3 (UF) e N6 (município), na mesma consulta (desde a Fase 3) |
| Períodos | 22 anos: 2001–2006, 2008, 2009, 2011–2021, 2024–2026. **Não há** 2007, 2010, 2022 nem 2023, e esses anos não serão interpolados (§14.3) |
| Linhas por período | 5.604 = 1 + 5 + 27 + **5.571 municípios em todos os anos**, inclusive os que ainda não existiam |
| Valores especiais | `...` para municípios inexistentes no ano: 11 em 2001–2003, 7 em 2004–2006, 6 em 2008–2011, 1 em 2012–2024, 0 em 2025–2026 |
| Volume | 33,2 MB (22 arquivos JSON) |

O caso conhecido de mudança territorial é **Boa Esperança do Norte (MT, 5101837)**:
ele aparece na estimativa de 2025, não existe no Censo 2022 (tabela 4714) e
aparece com `...` em 2024.

### `ibge-sidra-4714`: Censo 2022, população, área e densidade

| Item | Valor |
|---|---|
| Variáveis | 93 População residente (Pessoas), 6318 Área da unidade territorial (km²), 614 Densidade demográfica (hab/km²) |
| Níveis / período | N1, N2, N3 e N6 / 2022 |
| Linhas | 16.809 = 3 variáveis × (1 + 5 + 27 + 5.570 municípios) |
| Total Brasil (N1) | 203.080.756 pessoas |
| Volume | 4,7 MB |

### `ibge-dtb`: Divisão Territorial Brasileira 2025

| Item | Valor |
|---|---|
| URL | `https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/divisao_territorial/2025/DTB_2025.zip` |
| Conteúdo | 8 planilhas (ODS e XLS): municípios, distritos, subdistritos e distritos/subdistritos novos e extintos |
| `Last-Modified` | Thu, 26 Mar 2026 21:07:36 GMT |
| SHA-256 | `d077a0e48c36cf18bcc96268b4a436200c014c6b8522c1a62d894acaf39dad27` |
| Volume | 1,6 MB |
| Histórico disponível | diretórios por ano, de 1940 a 2025 |

## Licença

Registrada como `ibge-reuso-com-citacao`, em **`requires_review`**. O texto
oficial não pôde ser lido (403). Fontes secundárias indicam uso permitido com
citação obrigatória do IBGE e identificação do responsável por transformações.
Os datasets estão classificados como `public_conditional`. **Confirme o texto
oficial antes de qualquer publicação pública.**

## Resultado da primeira ingestão real (2026-11-03)

| Execução | 6579 | 4714 | DTB | Bytes gravados |
|---|---|---|---|---|
| 1ª | 22 `stored` | 1 `stored` | 1 `stored` | 39,5 MB |
| 2ª | 2 `reused` (janela 2025–2026) | 1 `reused` | 1 `not_modified` (304) | **0** |

Integridade: os 24 SHA-256 do disco conferem com o catálogo.

## Legenda oficial de símbolos (sidra.ibge.gov.br, 2026-11-03)

`...` não disponível · `..` não se aplica · `-` zero absoluto · `0` zero por
arredondamento · `X` inibido · letras A–Z (exceto X) faixa de valores.
Classificação na Silver: [ADR-0007](../adr/0007-silver-modelagem-valores-especiais-reconciliacao.md).

## Reconciliação com os totais oficiais (Silver, 2026-11-03)

### 6579: população estimada (exata)

| Par | Resultado |
|---|---|
| UF → Brasil, Região → Brasil, UF → Região | **confere em todos os 22 anos** |
| Município → Brasil | confere em 19 anos; **diverge em 2004, 2008 e 2012** |
| Município → UF | 8 de 594 totais divergem, todos em 2004, 2008 ou 2012 |

A soma dos municípios **excede** o total oficial. As diferenças por UF somam
exatamente a diferença nacional:

| Ano | UF (código) | Soma dos municípios − total oficial da UF |
|---|---|---|
| 2004 | Piauí (22) | +2.561 |
| 2004 | Mato Grosso do Sul (50) | +2.908 |
| 2004 | Mato Grosso (51) | +6.499 |
| 2008 | Piauí (22) | +7.817 |
| 2012 | Pará (15) | +15.018 |
| 2012 | Santa Catarina (42) | +20.552 |
| 2012 | Rio Grande do Sul (43) | +2.578 |
| 2012 | Mato Grosso do Sul (50) | +4.723 |

- Testado também com a biblioteca `sidrapy` 0.1.4: valores idênticos. A
  biblioteca consulta a mesma API, então a divergência está nos dados publicados.
- As notas da tabela não puderam ser lidas: os endpoints de metadados
  respondem 403 a clientes automatizados, e o bloqueio não foi contornado.
- **Causa não confirmada.** Verificar as notas da tabela 6579 no navegador
  antes de decidir o tratamento na Gold.

### 4714: Censo 2022

| Variável | Resultado |
|---|---|
| 93, população (exata) | **confere** em todos os pares (203.080.756) |
| 6318, área (tolerância de arredondamento) | UF → Brasil e Região → Brasil conferem. **Município → UF diverge só no Rio Grande do Sul (43)**: soma municipal 268.621,283 km² contra 281.707,151 km² da UF (−13.085,868 km²) |
| 614, densidade | não somável; não reconciliada |

Hipótese para a área do RS, **não verificada**: superfícies de água (lagoas
dos Patos e Mirim) entram na área da UF e não na dos municípios.

### Cobertura territorial

Os 5.571 municípios com valor em 2025 (6579) e os 5.570 do Censo 2022 (4714)
existem na DTB 2025. Boa Esperança do Norte (5101837) aparece como `...` até
2024 e com 5.877 habitantes em 2025.

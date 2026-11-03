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
| Nível | N6 (município) |
| Períodos | 22 anos: 2001–2006, 2008, 2009, 2011–2021, 2024–2026. **Não há** 2007, 2010, 2022 nem 2023, e esses anos não serão interpolados (§14.3) |
| Linhas por período | **5.571 em todos os anos**, inclusive municípios que ainda não existiam |
| Valores especiais | `...` para municípios inexistentes no ano: 11 em 2001–2003, 7 em 2004–2006, 6 em 2008–2011, 1 em 2012–2024, 0 em 2025–2026 |
| Volume | 33,2 MB (22 arquivos JSON) |

O caso conhecido de mudança territorial é **Boa Esperança do Norte (MT, 5101837)**:
ele aparece na estimativa de 2025, não existe no Censo 2022 (tabela 4714) e
aparece com `...` em 2024.

### `ibge-sidra-4714`: Censo 2022, população, área e densidade

| Item | Valor |
|---|---|
| Variáveis | 93 População residente (Pessoas), 6318 Área da unidade territorial (km²), 614 Densidade demográfica (hab/km²) |
| Nível / período | N6 / 2022 |
| Linhas | 16.710 (5.570 municípios × 3 variáveis) |
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

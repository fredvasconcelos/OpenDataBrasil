# Fontes e datasets do IBGE

Tudo aqui foi verificado por requisição real em **2026-11-03** (tabelas 6579,
4714 e DTB) e **2026-11-04** (tabelas 9605, 9718 e 9578). Configuração:
[`configs/sources/ibge.toml`](../../configs/sources/ibge.toml).

## Situação das fontes pesquisadas

| Fonte | Estado | Uso na plataforma |
|---|---|---|
| API SIDRA (`apisidra.ibge.gov.br/values`) | ✅ disponível | conector `sidra` |
| API de agregados v3 e de localidades (`servicodados.ibge.gov.br`) | ❌ indisponível (`ECONNREFUSED`/timeout a partir do WSL, do Windows e de serviço externo; retestado em 2026-11-04) | não utilizada; reavaliar (KI-002) |
| Downloads de geociências (`geoftp.ibge.gov.br`) | ✅ disponível, com `ETag`/`Last-Modified` | conector `http_file` |
| Estimativas em arquivo (`ftp.ibge.gov.br/Estimativas_de_Populacao/`) | ✅ disponível | não utilizada (o SIDRA cobre a série) |
| Página de ajuda da API SIDRA | ⚠️ responde 403 a clientes automatizados | consultada via busca |
| Portal Séries Estatísticas (`seriesestatisticas.ibge.gov.br`) | ⚠️ desafio Cloudflare (403) para clientes automatizados; **não contornado** (§7.3) | as séries equivalentes foram localizadas no SIDRA |

## Comportamentos da API SIDRA (com fixtures em `tests/fixtures/ibge/`)

- Formato: lista JSON. O primeiro elemento é o cabeçalho (`NC, NN, MC, MN, V, D1C, D1N, …`).
- Período inexistente: **HTTP 200 com apenas o cabeçalho**. O conector trata como erro e envia para a quarentena.
- Tabela inexistente: HTTP 400 com texto simples (`Tabela 999999: Tabela inválida`).
- Sem `ETag`/`Last-Modified`; `cache-control: no-cache`.
- **Limite efetivo de 50.000 valores por consulta.** A ajuda cita 100.000, mas a API respondeu
  HTTP 400 `Quantidade de valores solicitados: 67236 excedeu o limite: 50000` em 2026-11-04.
  O plano usa uma requisição por período e, quando necessário, por variável
  (`split_by_variable`) e por categoria de uma classificação (`split_by_classification`).
- Classificação inexistente na tabela: HTTP 400 `Parâmetro Cxx (Classificação) incompatível
  com a tabela`. Os códigos `c86`, `c1714` e `c2661` foram conferidos assim (HTTP 200).
- Os códigos de classificação foram localizados no catálogo não oficial
  [Quantilica Fish](https://quantilica.com/fish/tabelas/9718) e **confirmados na API oficial**.

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

### `ibge-sidra-9605`: População residente por cor ou raça (Censos 2010 e 2022)

| Item | Valor |
|---|---|
| Variável | 93 População residente (Pessoas). A 1000093 (percentual do total geral) é derivada e não é ingerida |
| Classificação | c86 Cor ou raça: 95251 Total, 2776 Branca, 2777 Preta, 2778 Amarela, 2779 Parda, 2780 Indígena |
| Níveis / períodos | N1, N2, N3 e N6 / 2010 e 2022 (5.570 municípios nos dois anos) |
| Linhas | 33.618 por período = 6 categorias × 5.603 territórios |
| Volume | 20,2 MB (2 arquivos) |

**As cinco categorias não somam o Total**: a tabela não publica a categoria
"sem declaração". No Brasil, faltam 6.608 pessoas em 2010 e 11.119 em 2022. A
partição é declarada não exaustiva (`exhaustive = false`).

### `ibge-sidra-9718`: Censo 2022, população total e indígena

| Item | Valor |
|---|---|
| Variáveis | 93 População residente, 350 Pessoas indígenas, 4727 Percentual de pessoas indígenas (%). 1000093 e 1000350 (percentuais do total geral) não são ingeridas |
| Classificações | c1714 Quesito de declaração indígena: 60024 Total, 60025 Cor ou raça indígena, 60026 Se considera indígena, 60029 Não se declarou indígena; c2661 Localização do domicílio: 32776 Total, 12869 Em terras indígenas, 12870 Fora de terras indígenas |
| Divisão | 3 variáveis × 3 localizações = 9 requisições de 22.412 valores (limite de 50.000) |
| Linhas | 201.708 = 3 × 12 combinações × 5.603 territórios |
| Brasil | 1.694.836 pessoas indígenas (1.227.642 por cor ou raça + 467.194 que se consideram indígenas); 689.532 residentes em terras indígenas |
| Valores especiais | 522 valores municipais `X` (suprimidos para não identificar o informante) |
| Volume | 76,5 MB (9 arquivos) |

"Pessoas indígenas" (9718) e a categoria Indígena de cor ou raça (9605) são
**conceitos diferentes**. O catálogo semântico impede combinar os dois.

### `ibge-sidra-9578`: Censo 2022, população total e quilombola

| Item | Valor |
|---|---|
| Variáveis | 4709 Pessoas quilombolas, 93 População residente, 4728 Percentual de pessoas quilombolas (%). 1004709 não é ingerida |
| Classificação | c2661 Localização do domicílio: 32776 Total, 60027 Em territórios quilombolas, 60028 Fora de territórios quilombolas |
| Divisão | uma requisição por variável (16.809 valores) |
| Brasil | 1.330.186 pessoas quilombolas (segunda apuração; a primeira divulgação informou 1.327.802); 203.574 residentes em territórios quilombolas |
| Valores especiais | 144 valores municipais `X` |
| Volume | 16,6 MB (3 arquivos) |

A classificação c2661 é a mesma nas duas tabelas, com categorias diferentes:
terras indígenas na 9718 e territórios quilombolas na 9578. Na hierarquia de
categorias, cada par forma uma partição própria do Total.

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

**Causa confirmada** pelas notas oficiais da tabela
([resumo e verificação](notas/ibge-sidra-6579.md)): nesses anos, a tabela inclui
**municípios com instalação prevista** para o ano seguinte. A população deles
também está no município de origem, então a soma municipal conta essas pessoas
duas vezes, enquanto os totais oficiais de UF e Brasil contam uma vez. Cada
diferença acima é igual à população desses municípios:

| Ano | Municípios ainda não instalados |
|---|---|
| 2004 | Aroeiras do Itaim-PI (2.561), Figueirão-MS (2.908), Ipiranga do Norte-MT (2.445), Itanhangá-MT (4.054) |
| 2008 | Nazária-PI (7.817) |
| 2012 | Mojuí dos Campos-PA (15.018), Pescaria Brava-SC (9.416), Balneário Rincão-SC (11.136), Pinto Bandeira-RS (2.578), Paraíso das Águas-MS (4.723) |

Os dados não estão errados. **Somar municípios para obter totais de UF ou
Brasil nesses anos produz um valor incorreto.** Use os totais oficiais
publicados (níveis N1, N2 e N3). A biblioteca `sidrapy` 0.1.4 retorna valores
idênticos, porque consulta a mesma API.

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

### 9718 e 9578: valores suprimidos no nível municipal (Silver, 2026-11-04)

Na primeira execução, a soma dos municípios ficou abaixo do total oficial da UF
e do Brasil em 148 grupos, sempre nas categorias "em/fora de terras indígenas"
ou "em/fora de territórios quilombolas". A verificação nos dados mostrou que:

- **todos** os 148 grupos têm municípios com valor `X` (suprimido);
- em nenhum grupo a soma conhecida passa do total oficial.

Conclusão: a diferença é o valor suprimido, e não uma divergência. Desde então,
a reconciliação trata grupos com filhos sem valor numérico como **incompletos**.
A soma conhecida só pode ficar abaixo do oficial; se passar, é aviso. Os
totais oficiais de UF e Brasil continuam sendo a referência.

### 9605: categorias de cor ou raça (Gold, 2026-11-04)

Em todos os 11.201 contextos (território × ano) com valores numéricos, a soma
das cinco categorias fica **abaixo ou igual** ao Total, como esperado para uma
partição não exaustiva. O resíduo nacional é de 6.608 pessoas (2010) e 11.119
(2022).

# Plano: dados.gov.br como catálogo de descoberta

Pedido do mantenedor (2026-11-12): usar o Portal de Dados Abertos do governo federal
(<https://dados.gov.br/home>) para traçar a inserção de informação nova.

## O que foi verificado (2026-11-12, a partir da Espanha)

| Recurso | Resultado |
|---|---|
| `https://dados.gov.br/home` | 200: página de aplicação (JavaScript); o conteúdo não vem no HTML |
| Documento OpenAPI `https://dados.gov.br/v3/api-docs` | 200: "API REST do Portal de Dados Abertos" (CGU), 1.0, licença Decreto 8.777/2016 |
| Toda a API (`/dados/api/publico/conjuntos-dados`, `/organizacao`, `/temas`, `/tags`, `/formatos`) | **401** sem chave |
| `robots.txt` | 401 |

A API exige o cabeçalho `chave-api-dados-abertos`. Segundo o próprio documento
OpenAPI, quem tem perfil **Consumidor** gera a chave entrando no portal (login gov.br)
e abrindo **"Minha Conta"**. É uma autenticação documentada e gratuita, não um
bloqueio. Ainda assim, ela depende da conta do mantenedor e não será contornada
(§7.3).

Endpoints de leitura que interessam:

| Método e caminho | Uso |
|---|---|
| `GET /dados/api/publico/organizacao?pagina=` | órgãos publicadores |
| `GET /dados/api/publico/conjuntos-dados?pagina=&idOrganizacao=&dadosAbertos=` | conjuntos de dados (paginado) |
| `GET /dados/api/publico/conjuntos-dados/{id}` | metadados e recursos (arquivos e links) de um conjunto |
| `GET /dados/api/temas`, `GET /dados/api/tags?nome=` | taxonomia do portal |

Os arquivos de cada conjunto ficam, em geral, no site do órgão publicador. Baixá-los
não passa pela API, e cada fonte segue as próprias condições.

## Plano em ondas (cada onda precisa de aprovação)

### Onda 0: chave e inventário (só metadados)

1. **Chave (mantenedor):** gerar a chave de Consumidor e gravá-la no `.env` local como
   `ODB_DADOSGOV_API_KEY`. Ela não vai para o Git nem para os logs (§23).
2. **Conector `dadosgov_catalog`:**
   - lista os órgãos e os conjuntos (paginado, com limite de requisições);
   - guarda as respostas JSON na Bronze, como já se faz com os descritores do SIDRA;
   - não baixa os dados dos conjuntos.
3. **Inventário (`docs/data_catalog/dados-gov-br-inventario.md`):**
   - órgão, conjunto, formatos, licença, última atualização, periodicidade
     declarada e se há API;
   - presença de chave territorial: código IBGE de município ou UF.

### Onda 1: triagem

A triagem é automática, com revisão do mantenedor.

- **Prioridade:**
  - formatos legíveis por máquina (CSV, JSON, API);
  - atualização regular;
  - código IBGE de município ou UF;
  - licença aberta declarada;
  - órgãos do §3.1.
- **Fica de fora:**
  - só PDF ou planilhas de apresentação;
  - dados pessoais ou com risco de reidentificação (§23);
  - conjuntos que replicam fontes que já ingerimos na origem (IBGE, DATASUS, MJSP).
    A origem vem sempre primeiro.
- **Licença:** cada conjunto escolhido ganha uma entrada de licença com
  `review_status`, como foi feito com o Sinesp.

### Onda 2: novas fontes (candidatas)

Os identificadores ainda não foram verificados: entram na lista só depois da Onda 0.

| Tema do portal | Órgão (§3.1) | Por que |
|---|---|---|
| Educação | INEP | Censo Escolar e indicadores educacionais por município (o portal tem só o Censo do IBGE) |
| Economia e finanças | Banco Central | séries temporais (juros, crédito, inflação esperada) por API pública própria |
| Gestão e finanças públicas | Tesouro Nacional (Siconfi) e CGU (Portal da Transparência) | receitas e despesas municipais, transferências |
| Saúde | Ministério da Saúde | CNES e vacinação, complementando SIM e SINASC (ADR-0011) |
| Infraestrutura | ANATEL, ANEEL | acesso a banda larga e energia por município |

Cada fonte nova segue o caminho de sempre:
- ADR;
- conector com fixtures;
- Bronze e Silver;
- Gold com a regra de agregação de cada indicador;
- portal.

Os ciclos de atualização seguem o runbook [atualizacao.md](../runbooks/atualizacao.md).

## Decisões para o mantenedor

1. Gerar a chave de Consumidor e liberar a Onda 0 (inventário, sem dados).
2. Confirmar a ordem dos temas da Onda 2 ou indicar outra.
3. Confirmar a regra "a origem vem primeiro" para conjuntos que replicam fontes já
   ingeridas.

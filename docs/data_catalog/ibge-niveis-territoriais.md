# Níveis territoriais do SIDRA usados pela plataforma

Os códigos de nível (`/n<código>/all` na API) e de unidade vêm da descrição de
cada tabela (`https://apisidra.ibge.gov.br/desctabapi.aspx?c=<tabela>`) e das
listas de unidades (`LisUnitTabAPI.aspx?c=<tabela>&n=<nível>`). Essas páginas
respondem 403 a clientes automatizados (KI-006), então os códigos foram
**fornecidos pelo mantenedor** a partir do navegador e **conferidos na API
oficial** (`/values`), que respondeu HTTP 200 com as contagens abaixo.

## Níveis administrativos (todas as tabelas usadas)

| Nível SIDRA | Nome | Unidades | Nível interno |
|---|---|---|---|
| N1 | Brasil | 1 | `brasil` |
| N2 | Grande Região | 5 | `regiao` |
| N3 | Unidade da Federação | 27 | `uf` |
| N6 | Município | 5.570 (Censo 2022) | `municipio` |

## Níveis especiais da tabela 9723 (territórios quilombolas)

Fonte: descrição da tabela 9723 e PDFs de unidades fornecidos pelo mantenedor
em 2026-11-04. Conferido na API no mesmo dia.

| Nível SIDRA | Nome | Unidades | Nível interno | Pai na hierarquia | Outros ancestrais |
|---|---|---|---|---|---|
| N1145 | Território Quilombola | 495 | `territorio_quilombola` | `brasil` | |
| N145 | Território Quilombola por Unidade da Federação | 503 | `territorio_quilombola_uf` | `uf` | `territorio_quilombola` |
| N131 | Amazônia Legal | 1 (código 131) | `amazonia_legal` | `brasil` | |
| N134 | Amazônia Legal de Unidade da Federação | 9 | `amazonia_legal_uf` | `uf` | `amazonia_legal` |

Regras de código, verificadas em todas as unidades:

- **N145 = código da UF (2 dígitos) + código do território (3 dígitos)**. Por
  exemplo, `27282` = Alagoas (27) + Abobreiras (282); `11001` = Rondônia (11) +
  Quilombola de Jesus (1). Toda unidade N145 tem território N1145 correspondente.
- **N134 = código da UF**, por exemplo `21` = Amazônia Legal do Maranhão. O
  Maranhão e o Mato Grosso estão só em parte na Amazônia Legal.
- Os nomes N145 e N134 vêm com o sufixo " - UF" (por exemplo, "Pedras Negras -
  RO"). Os nomes N1145 vêm sem sufixo, e há nomes repetidos com códigos
  diferentes ("Alto da Serra" 132 e 289, ambos no RJ).

**8 territórios atravessam divisas estaduais** (têm duas unidades N145):
Itamoari (PA 15003, MA 21003), Ilha de São Vicente (PA 15275, TO 17275),
Mocambo - SE (AL 27098, SE 28098), Serra da Guia (SE 28173, BA 29173), Porto
Velho (SP 35321, PR 41321), Varzeão (SP 35375, PR 41375), São Roque (SC 42250,
RS 43250) e Mesquita (GO 52128, DF 53128). Por isso o território quilombola não
cabe na árvore UF → município: ele é um sistema territorial próprio, ligado às
UFs pelas partes N145.

Lista completa (1.008 unidades, gerada da resposta da API de 2026-11-04):
[`referencias/sidra-9723-unidades-territoriais-especiais.csv`](referencias/sidra-9723-unidades-territoriais-especiais.csv).

### Notas oficiais da tabela 9723 (transcritas da descrição)

1. Dados do Universo.
2. Definiu-se como quilombola a pessoa residente em localidades quilombolas
   que se declarou quilombola.
3. Localidades quilombolas: o conjunto dos Territórios Quilombolas oficialmente
   delimitados, dos agrupamentos quilombolas e das demais áreas de conhecida ou
   potencial ocupação quilombola.
4. Os Territórios Quilombolas oficialmente delimitados são os que tinham alguma
   delimitação formal em 31/07/2022, conforme os cadastros do INCRA e dos órgãos
   fundiários dos Estados e Municípios.
5. Dados atualizados em 22/12/2023, referentes à coleta até 28/05/2023, com as
   revisões de 29/05/2023 a 07/07/2023.

Variáveis: 6559 Pessoas residentes em territórios quilombolas (Pessoas, 0
casas); 7079 Pessoas quilombolas residentes em territórios quilombolas
(Pessoas, 0 casas); 7080 Percentual de pessoas quilombolas residentes em
territórios quilombolas (%, 2 casas). Última atualização da tabela:
2024-05-14.

## Níveis especiais da tabela 9954 (terras indígenas)

Fonte: descrição da tabela 9954 e PDFs de unidades fornecidos pelo mantenedor
em 2026-11-04. Conferido na API no mesmo dia.

| Nível SIDRA | Nome | Unidades | Nível interno | Pai na hierarquia | Outros ancestrais |
|---|---|---|---|---|---|
| N1125 | Terra Indígena | 573 | `terra_indigena` | `brasil` | |
| N125 | Terra Indígena por Unidade da Federação | 602 | `terra_indigena_uf` | `uf` | `terra_indigena` |
| N1124 | Coordenação Regional da Funai | 39 (códigos 19001 a 19039) | `coordenacao_regional_funai` | `brasil` | |
| N131, N134 | Amazônia Legal e Amazônia Legal de UF | 1 e 9 | (como na 9723) | | |

Regras de código, verificadas em todas as unidades:

- **N125 = código da UF (2 dígitos) + código da terra indígena (5 dígitos)**.
  Por exemplo, `1209482` = Acre (12) + Alto Rio Purus (9482); `2935000` = Bahia
  (29) + Kiriri (35000). Toda unidade N125 tem terra indígena N1125
  correspondente.
- **27 terras indígenas atravessam divisas estaduais**, por exemplo Parque do
  Aripuanã (RO 1101406, MT 5101406), Yanomami (AM, RR), Trombetas/Mapuera (AM,
  PA, RR) e Kariri de Serra Grande (BA, PE, PI).
- Há nomes repetidos com códigos diferentes (por exemplo, "Buriti" 50157 e 50781,
  "Rio Gregório" 9466 e 50799). O código é a identidade, nunca o nome.
- A ligação entre terra indígena e Coordenação Regional da Funai **não está nos
  códigos**. As coordenações entram como recorte próprio, sem vínculo com as
  terras.

Conferência na API (Total de sexo, idade e situação, 2022):

| Variável | Brasil | Soma das terras | Soma das partes por UF | Soma das coordenações |
|---|---|---|---|---|
| 576 Pessoas residentes em terras indígenas | 689.532 | 689.532 | 689.532 | 689.532 |
| 1432 Pessoas indígenas residentes em terras indígenas | 622.844 | 621.659 (25 terras com `X`) | 621.659 | 508.384 (5 coordenações com `X`) |

Classificações (iguais às das tabelas 9970 e 9971): C2 Sexo, C287 Idade (134
categorias), C1 Situação do domicílio.

Lista completa (1.214 unidades, gerada da resposta da API de 2026-11-04):
[`referencias/sidra-9954-unidades-territoriais-especiais.csv`](referencias/sidra-9954-unidades-territoriais-especiais.csv).

### Notas oficiais da tabela 9954 (transcritas da descrição)

1. Dados do Universo.
2. Indígena é a pessoa residente em localidades indígenas que se declarou
   indígena pelo quesito de cor ou raça ou pelo quesito "se considera
   indígena", ou a pessoa residente fora das localidades indígenas que se
   declarou indígena no quesito de cor ou raça. Por isso, o total de pessoas
   indígenas é maior ou igual ao de pessoas de cor ou raça indígena, em
   qualquer recorte.
3. Localidades indígenas: as Terras Indígenas, os agrupamentos indígenas e as
   demais áreas de conhecida ou potencial ocupação indígena.
4. Terras Indígenas consideradas: declaradas, homologadas, regularizadas ou
   encaminhadas como Reservas Indígenas até 31/07/2022, conforme a FUNAI.

Variáveis: 576 Pessoas residentes em terras indígenas e 1432 Pessoas indígenas
residentes em terras indígenas (Pessoas, 0 casas). Última atualização da
tabela: 2024-12-19.

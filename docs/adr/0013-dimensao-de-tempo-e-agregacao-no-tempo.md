# ADR-0013: Dimensão de tempo detalhada e soma no tempo (mês, trimestre, semestre, ano)

- **Estado:** aceito (2026-11-12), a pedido do mantenedor.
- **Contexto normativo:** CLAUDE.md §10.5, §10.7, §10.8, §14.3, §15.4, §19.3 e §28.5.

## Contexto

As planilhas do Sinesp VDE (ADR-0012) são mensais. O mantenedor pediu uma dimensão de
tempo detalhada que funcione como as classificações do Censo, como cor ou raça e sexo:
o painel passa a oferecer o detalhe por mês, trimestre, semestre e ano. O ano é a soma
dos meses do ano, e o trimestre, a soma dos três meses dele. Cada período precisa de um
rótulo por extenso e de um abreviado, como "1º trimestre de 2024" e "T1 2024".

Até aqui, a Gold guardava cada série só na frequência publicada pela fonte (`AAAA`,
`AAAAMmm`, `AAAATt`). A `dim_period` tinha o tipo, o ano e as datas, mas não a
hierarquia nem os rótulos.

## Decisões

### 1. A hierarquia vive na Gold; os valores somados, na consulta

- **`dim_period` 1.1.0:**
  - colunas novas: `month`, `quarter`, `semester`, `label` (por extenso) e
    `short_label` (abreviado);
  - um mês observado traz também o trimestre, o semestre e o ano dele, para que a
    consulta agregada tenha chave e rótulo.

  | Grão | Código | `label` | `short_label` |
  |---|---|---|---|
  | mês | `2024M01` | janeiro de 2024 | jan 2024 |
  | trimestre | `2024T1` | 1º trimestre de 2024 | T1 2024 |
  | semestre | `2024S1` | 1º semestre de 2024 | S1 2024 |
  | ano | `2024` | 2024 | 2024 |

- **`bridge_period_ancestor` (nova):** cada período observado aponta para os períodos
  maiores que o contêm e informa quantas partes o maior precisa ter (`parts`: 3 meses
  no trimestre, 6 no semestre, 12 no ano). É o mesmo desenho da ponte territorial
  (`bridge_geography_ancestor`).
- **Soma na consulta (§10.7):** o trimestre, o semestre e o ano são somados pelo DuckDB
  na hora da consulta. Eles não são gravados como valores oficiais da Gold, que continua
  guardando só o que a fonte publica. O resultado vem marcado como derivado
  (`provenance.derived`, status `derived_sum`), como a soma territorial (`sum_to`).
- **Um só código:** a Gold e a API usam o mesmo módulo
  (`odb_semantics.periods`) para a hierarquia, as partes e os rótulos.

### 2. Só fluxos são somados no tempo

"Aditivo" no catálogo quer dizer que os valores se somam entre territórios e
categorias, não ao longo do tempo. Somar a população ou as pessoas ocupadas de quatro
trimestres daria um número sem sentido.

- O indicador declara `time_aggregation = "sum"` quando é um fluxo, como ocorrências,
  vítimas, óbitos ou nascimentos.
- Estoques (população, ocupados), taxas e índices (como o IPCA) não declaram e ficam
  só no grão publicado.
- A `dim_indicator` 1.1.0 registra `time_aggregation` e `time_grains`, que são os grãos
  oferecidos, do publicado ao menos detalhado.
- Hoje declaram a soma os 6 KPIs do Sinesp.

### 3. Período incompleto fica sem valor

- **Regra:** o período maior só tem valor quando todas as partes têm valor. Faltando
  uma parte, sem valor ou ainda não publicada, ele fica sem valor, com status
  `incomplete_period`, e a resposta informa quantas partes vieram
  (`parts_with_value` e `parts_expected`).
- **Exemplo:** com meses até setembro de 2026, o ano de 2026 e o 4º trimestre de 2026
  ficam sem valor, e o portal mostra "período incompleto".
- **Por quê:** é a regra que o projeto já usa no Sinesp (total com parcela ausente fica
  ausente, ADR-0012, decisão 6). Ela evita comparar um ano parcial com anos completos.
- **Período padrão:** o painel abre no último período completo do grão (em 2026, o
  ano de 2025).

### 4. API e portal

- **API:**
  - `grain` (`mes`, `trimestre`, `semestre` ou `ano`) no mapa, no detalhe, na série,
    na tabela e na exportação;
  - o `KpiOut` lista `time_grains`, com os períodos e os períodos completos de cada
    grão;
  - um grão que o KPI não oferece é recusado (400), assim como a soma de territórios e
    de períodos na mesma consulta;
  - o mapa em % de uma categoria (`map_share`) fica no grão publicado.
- **Portal:**
  - o bloco "Filtros" ganha o grupo "Período por" (Mês, Trimestre, Semestre, Ano), só
    para KPIs com mais de um grão;
  - o grão vai na URL (`grao=`), e o seletor de período lista os períodos do grão;
  - uma nota curta avisa que o valor é derivado;
  - os rótulos são os abreviados da Gold: "T2 2026" e "S1 2026" (decisão do
    mantenedor; antes, "2º tri 2026");
  - no gráfico de evolução, trimestres e semestres têm o eixo em duas linhas: a parte
    do ano em cima (T1…T4, S1/S2) e o ano embaixo, centralizado no trecho dele, com
    divisórias entre os anos (design system 2.3.3). Sem espaço para as partes, fica
    uma linha só com os anos e as divisórias. Se o ano com quatro dígitos não couber,
    ele fica com dois ("26"), salvo em séries que atravessam a virada do século.

## Consequências

- **Volume:** a Gold ganha uma tabela pequena (2.032 linhas no release `c02878a3`) e
  mais linhas na `dim_period` (921). O pico do build segue em 9,4 GiB.
- **Novos indicadores:** um indicador mensal ou trimestral que seja fluxo ganha o
  detalhe só declarando `time_aggregation = "sum"`, sem mudar código.
- **Rótulos:** o portal e a Gold usam os mesmos rótulos abreviados ("T2 2026",
  "S1 2026", "set 2026"). O rótulo por extenso da Gold ("2º trimestre de 2026") fica para
  exportações e leitura de tela.
- **Fora do escopo:** média ou último valor no tempo, para estoques e taxas, exigiria
  regra própria por indicador, e não foi feito.

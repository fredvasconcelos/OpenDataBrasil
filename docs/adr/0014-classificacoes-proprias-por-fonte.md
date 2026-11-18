# ADR-0014: Classificações próprias por fonte, com o mesmo rótulo no portal

- **Estado:** aceito (2026-11-12), a pedido do mantenedor.
- **Contexto normativo:** CLAUDE.md §9.4, §10.5, §15.4 e §19.5.

## Contexto

O mantenedor pediu o detalhe por sexo nos KPIs do SIM e do Sinesp e perguntou se não
daria para usar a mesma dimensão "Sexo" do IBGE.

O catálogo liga cada dimensão da Silver a uma classificação pelo nome. As três fontes
chamam a dimensão de "Sexo", mas com códigos diferentes:

| Fonte | Total | Masculino | Feminino | Sem informação |
|---|---|---|---|---|
| IBGE (c2) | 6794 | 4 (Homens) | 5 (Mulheres) | não existe |
| SIM | T | 1 | 2 | 9 (Ignorado) |
| Sinesp | T | masculino | feminino | nao-informado |

## Decisão

Cada fonte de registro administrativo tem a sua classificação, com o mesmo rótulo
("Sexo") no portal. Foi a segunda opção sugerida pelo mantenedor.

- **Configuração:** a classificação ganhou `datasets`, a lista de datasets em que ela
  lê a dimensão. Nesses datasets, ela tem precedência sobre a classificação geral de
  mesmo nome.
  - `sexosim` (`datasus-sim-cid10-dores`): 1, 2 e 9, cuja soma é o Total.
  - `sexosinesp` (`mjsp-sinesp-vde`): masculino, feminino e nao-informado. A soma é
    igual ao Total nos 2.278.097 casos conferidos na Silver.
  - O catálogo recusa duas classificações gerais para a mesma dimensão, ou duas para a
    mesma dimensão no mesmo dataset.
- **Por que não a mesma classificação:**
  - unir as três exigiria recodificar duas fontes para os códigos de uma. A Silver
    perderia o código publicado (§9.4);
  - seria preciso inventar na c2 uma categoria "sem informação" que o Censo não tem;
  - a regra de soma muda de fonte para fonte: no Censo, o Total é homens mais mulheres;
    nos registros, também entra o "não informado".
  - Para quem usa o portal, o resultado é o mesmo: a caixa "Sexo" em "Detalhar por".
- **Códigos do Sinesp:** a Silver do Sinesp usava o nome como código ("Não informado",
  com acento e espaço), o que o catálogo e a API não aceitam. O código passou a ser o
  nome sem acento nem espaço (`nao-informado`, `policia-federal`, `arma-de-fogo`), e o
  nome publicado continua em `category_name`. A Silver foi reconstruída com `--force`.
- **Portal:** `dimension_order` ganhou `sexosim` e `sexosinesp`, depois da c2. Os 5 KPIs
  de vítimas do Sinesp e o de óbitos do SIM detalham por sexo; o roubo de veículo, que
  conta ocorrências, não. O detalhe por sexo funciona também com o grão de tempo
  (ADR-0013): a soma no tempo é feita por categoria.

## Consequências

- **Outras dimensões em conflito:** o "Cor ou raça" e a "Faixa etária" do SIM, e o
  "Faixa etária" do Sinesp, entram do mesmo jeito quando forem liberados.
- **Comparações entre fontes por sexo:** não são feitas. As fontes medem coisas
  diferentes (registro policial, declaração de óbito, Censo), e os indicadores
  continuam separados (ADR-0011, decisão 5).
- **Unificação no futuro:** se um dia for preciso cruzar fontes por sexo, a saída é uma
  tabela de correspondência documentada entre as classificações (§15.4, "compatível
  mediante transformação"), sem recodificar a Silver.

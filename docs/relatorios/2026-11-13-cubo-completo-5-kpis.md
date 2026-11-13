# Cubo completo × portal atual: os 5 KPIs de maior volume

Resumo de 2026-11-13 para decidir o nível de detalhe das próximas cargas (ver
[continuacao.md](continuacao.md), "Cubo completo"). Números calculados dos descritores
oficiais do SIDRA e da configuração atual. A Bronze ocupa ~380 bytes por valor (medido:
o JSON do SIDRA repete nomes de território, variável e categorias em cada linha).

## As duas formas de carregar

- **Portal hoje (detalhes marginais):** cada detalhe vem sozinho, com os demais no
  Total, em todos os níveis até o município. Em óbitos e nascidos vivos, também sexo ×
  idade cruzados até a UF (C1). Responde "quantos óbitos de mulheres?" ou "quantos
  óbitos aos 67 anos?", mas não "quantos óbitos de mulheres de 67 anos?" no
  município.
- **Cubo completo (sem teto):** todas as combinações de todos os detalhes, em todos os
  níveis e anos. Responde qualquer combinação, em qualquer município.

O tamanho do cubo é o **produto** das categorias, e o de hoje é a **soma**. Por isso
cresce tão rápido.

| KPI (tabela) | Combinações por território e ano: hoje → cubo | Valores hoje | Valores no cubo | Bronze hoje → cubo | Vezes maior |
|---|---|---|---|---|---|
| Casamentos (4412) | 99 → 570.375 | 6,7 milhões | 38,3 bilhões | 2,5 GB → 14,6 TB | 5.761× |
| Óbitos (2654) | 106 → 136.080 | 13,2 milhões | 16,8 bilhões | 5,0 GB → 6,4 TB | 1.267× |
| Divórcios (1695) | 64 → 36.000 | 5,7 milhões | 3,2 bilhões | 2,2 GB → 1,2 TB | 562× |
| Nascidos vivos (2609) | 110 → 11.408 | 13,7 milhões | 1,4 bilhão | 5,2 GB → 534 GB | 103× |
| Estabelecimentos agropecuários (6878) | 35 → 23.040 | 0,2 milhão | 129 milhões | 0,07 GB → 49 GB | 658× |
| **Os 5 juntos** | | **39 milhões** | **60 bilhões** | **15 GB → 23 TB** | **~1.500×** |

Disco livre hoje: 922 GB.

## O que cada um permite, no máximo

Territórios: Brasil, 5 regiões, 27 UFs e 5.570 municípios.

### 1. Casamentos (4412), 2013 a 2024

| Detalhe | Categorias (com o Total) |
|---|---|
| Mês de ocorrência | 15 |
| Estado civil do 1º cônjuge | 5 |
| Estado civil do 2º cônjuge | 5 |
| Grupo de idade do 1º cônjuge | 39 |
| Grupo de idade do 2º cônjuge | 39 |

- **Cubo:** "casamentos em Salvador, em março de 2019, entre um cônjuge solteiro de 25
  a 29 anos e outro divorciado de 30 a 34 anos".
- **Hoje:** casamentos em Salvador por mês, ou por estado civil, ou por idade de cada
  cônjuge, um de cada vez.
- **Peso:** as duas idades (39 × 39) e o mês (15) multiplicam o resto. Um único ano
  no município são 3,2 bilhões de valores.

### 2. Óbitos (2654), 2003 a 2024

| Detalhe | Categorias |
|---|---|
| Mês de ocorrência | 14 |
| Natureza do óbito | 5 |
| Sexo | 4 |
| Idade (anos simples e grupos) | 81 |
| Local de ocorrência | 6 |

- **Cubo:** "óbitos de mulheres de 67 anos, por causa natural, em hospital, em agosto
  de 2021, em Feira de Santana".
- **Hoje:** cada detalhe sozinho no município, mais sexo × idade cruzados até a UF.

### 3. Divórcios (1695), 2009 a 2024

| Detalhe | Categorias |
|---|---|
| Tempo de casamento até o divórcio | 32 |
| Regime de bens | 5 |
| Idade do marido | 15 |
| Idade da mulher | 15 |

- **Cubo:** "divórcios em Curitiba, em 2022, de casais com 10 a 14 anos de casamento,
  em comunhão parcial, marido de 40 a 44 e mulher de 35 a 39 anos".
- **Hoje:** cada detalhe sozinho.

### 4. Nascidos vivos (2609), 2003 a 2024

| Detalhe | Categorias |
|---|---|
| Ano de nascimento | 62 |
| Idade da mãe | 46 |
| Sexo | 4 |

- **Cubo:** "meninas nascidas em 2024, de mães de 16 anos, em Manaus".
- **Hoje:** cada detalhe sozinho no município, mais idade da mãe × sexo até a UF.
- **O mais barato dos cinco:** com 3 detalhes, o cubo é "só" 103 vezes maior que hoje.

### 5. Estabelecimentos agropecuários (6878), Censo Agro 2017

| Detalhe | Categorias |
|---|---|
| Tipologia (agricultura familiar) | 8 |
| Grupo de atividade econômica | 10 |
| Sexo do produtor | 4 |
| Classe de idade do produtor | 9 |
| Condição do produtor em relação às terras | 8 |

- **Cubo:** "estabelecimentos de agricultura familiar em pecuária, com produtora
  mulher de 35 a 44 anos, proprietária, em Chapecó".
- **Hoje:** cada detalhe sozinho.
- **Cabe no disco** (49 GB): um ano só.

## O que isso significa

1. **O cubo completo dos 5 não cabe:** 23 TB contra 922 GB livres. Só os casamentos
   seriam 14,6 TB.
2. **A maior parte do cubo é zero.** Num município pequeno, quase todas as
   combinações de casamento (mês × estado civil × idade × idade) não têm nenhum caso,
   e o SIDRA devolve cada zero como uma linha de ~380 bytes. Guardar só os valores
   diferentes de zero, ou compactar a Bronze sem perda (~10× menor), muda a conta.
3. **Caminho por etapas** (registrado no plano):
   - todos os cruzamentos até a UF: pequenos, cabem com folga;
   - pares de detalhes no município (sexo × idade, idade da mãe × sexo), KPI a KPI;
   - cubo completo no município só onde couber depois da compactação (estabelecimentos
     agropecuários, nascidos vivos).

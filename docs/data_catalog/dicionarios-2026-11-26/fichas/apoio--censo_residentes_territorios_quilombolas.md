# Pessoas residentes em territórios quilombolas

Ficha `apoio--censo_residentes_territorios_quilombolas` · indicador `censo_residentes_territorios_quilombolas` · **apoio_no_release_snapshot**.

## Significado e uso

Pessoas residentes em territórios quilombolas oficialmente delimitados em 31/07/2022 (cadastros do INCRA e de órgãos fundiários estaduais e municipais), quilombolas ou não.

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Pessoas**. Grão: território (níveis administrativos, Amazônia Legal, territórios quilombolas e suas partes por UF) x ano censitário.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-sidra-9723` | [9723/6559](https://sidra.ibge.gov.br/tabela/9723) | Pessoas residentes em territórios quilombolas / Pessoas | Não localizado |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 9723 / 6559

Pesquisa/produtor: ibge-sidra. Periodicidade: decenal. Disponibilidade na fonte: consultar contrato da fonte externa.
Precisão de armazenamento/apresentação no descritor: não informada / não informada casas. Soma de períodos/territórios na fonte: não informada / não informada.
Nota oficial (síntese de contexto não substitui a nota): Sem nota no descritor preservado; isso não prova ausência de restrições no manual.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: sim. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `["2022"]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- PESQUISA: método independente não localizado; consultar produtor identificado na ficha.
- DESCRITOR: tabela 9723 não tem descritor preservado localizado; códigos/definições/metadados oficiais completos pendentes, sem nova tentativa bloqueada.

## Contexto complementar localizado nesta execução

A publicação distingue população quilombola, residentes em territórios oficialmente delimitados e status fundiário; segunda apuração revisa a anterior.

Contexto conceitual localizado; descritor 9723 e vínculo de cada variável/categoria/denominador não recuperados. Não confundir população quilombola com toda população residente nos territórios.

Fonte: [produtor oficial](https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html?edicao=37415&t=resultados), Quilombolas — Primeiros Resultados, segunda apuração; Territórios quilombolas; edição: Censo 2022, tabelas atualizadas em 22/12/2023. Consulta indexada em 2026-11-26; não leitura integral.

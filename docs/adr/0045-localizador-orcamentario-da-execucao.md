# ADR-0045 — Localizador orçamentário da execução federal

- Data: 27/11/2026.
- Pedido do mantenedor: localizador CGU agora e plano para execução estadual/municipal.
- Situação: candidata local em preparação; sem ativação nem publicação na beta.
- Complementa ADRs 0032, 0033, 0036, 0037 e 0044. O localizador continua sem mapa.

## Significado

UF e município são os campos do plano de trabalho descritos no
[dicionário oficial da CGU](https://portaldatransparencia.gov.br/dicionario-de-dados/execucao-despesa),
consultado em 27/11/2026. Não medem a despesa executada pelo próprio estado/município,
a sede do favorecido ou o local efetivo de aplicação do recurso. Município é texto da
fonte, sem código IBGE atribuído por inferência. Homônimos de UFs diferentes não se unem.

Nenhuma UF ou município é deduzido do nome do localizador. Valores nacionais,
multirregionais, campos vazios e códigos especiais conservam o registro da fonte.
Campo vazio não significa automaticamente Nacional. No agrupamento por UF/município,
a categoria sem informação individualizada permanece no total nacional. O detalhamento
por localizador mostra o texto oficial, preservando Nacional quando assim publicado.
Não há rateio nem preenchimento com zero.

## Gold complementar

A Silver já preserva UF, nome do município, código/nome/sigla/descrição do localizador
e código/nome do subtítulo. O fato antigo agrega esse detalhe. A nova tabela Gold
`fact_federal_execution_location` conserva os oito campos e as mesmas dimensões
administrativas e seis medidas do fato antigo, com um grão mais fino.

`location_key` é uma chave técnica SHA-256 integral do JSON ordenado desses oito
campos, não um identificador geográfico oficial. Distingue combinações, inclusive
nulos e textos diferentes. O contrato e a versão de cada entrada ficam registrados.

A preparação parte de um release base explícito e fixa uma versão Silver. Para cada
ano, o complemento deve reproduzir **todas as chaves do fato anterior, as seis medidas
em Decimal e a contagem de linhas**, além de passar schema, nulidade e unicidade.
Diferença de calendário ou de um centavo bloqueia a candidata. Não basta comparar um
total nacional. Os demais fatos, dimensões e agregados são reutilizados nas versões
exatas da base. Gold permanece em Delta; não há cópia em PostgreSQL ou DuckDB.

A escrita gera somente uma candidata `validated`. Não altera o release ativo. Antes
de uma reconstrução geral das contas, executar novamente o complemento sobre a base
correspondente; nunca reutilizar a localização se a reconciliação com essa base falhar.

## API e portal

Os novos detalhamentos só aparecem em `/contas/meta` quando a tabela complementar
está no manifesto fixado: UF do localizador, município do localizador e localizador
original. A execução usa o complemento para manter os cruzamentos existentes. Na base
antiga, essas dimensões são rejeitadas e permanecem ausentes dos metadados.

Os filtros são sobre os campos originais, combináveis com função, programa, ação,
órgão, natureza e autor de emenda. Fases nunca se somam; totais e estornos são preservados.
A lente C continua independente de A/B e sem mapa ou conversão implícita em execução
local. A interface segue o guia do DS e usa rotas próprias para cada painel.

A execução própria dos entes tem [plano separado](../development/plano-execucao-estados-municipios.md).
Disponibilidade de portal ou API não comprova ligação entre um repasse e sua aplicação.

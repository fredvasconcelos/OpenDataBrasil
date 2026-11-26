# Proposta de Excel rastreável e metadados comuns

26/11/2026 · versão documental `0.1.1-proposta` · **aguarda revisão do mantenedor**.
Não implementada no portal/API. Não altera arquitetura, schema Gold, estatística,
releases ou exportadores. Base: [inventário de dicionários](../data_catalog/dicionarios-2026-11-26/README.md).

## Comportamento atual comprovado

Inspeção de `apps/api/src/odb_api/{exports.py,schemas.py,routes/kpi.py,kpis.py}`
e `apps/portal/src/components/{Dashboard.tsx,ExportMenu.tsx}`, público `6b62666`.
Execução em memória de `frame`, `metadata`, `render` e da rota real com dependências
sintéticas: XLSX, ZIP/CSV, JSON e Parquet inspecionados. Não foi download do serviço
local, que não estava acessível a esta execução.

| Item | Existe | Falta ou limite observado |
|---|---|---|
| XLSX | Abas `dados` e `metadados`; metadados em pares campo/valor, objetos como JSON | Dicionário, fontes e métodos tabulares próprios. |
| Dados longos | Território, UF, período, rótulos de dimensões, valor, status e unidade; em seleção ampliada, nível/grão/tipo | Códigos de categorias e fonte por linha não saem no quadro; a categoria é trocada pelo nome. |
| Versão | Release e tabelas/versões em proveniência | Faltam ligação por linha/bloco e versão imutável de metodologia/dicionário. |
| Filtros | Níveis, grãos, recorte, períodos, períodos por grão, dimensões e correção | `categories` é aplicado à consulta mas omitido em `metadata.filtros`. Em marginais separadas, `dimensions` registra apenas o último conjunto. |
| Precisão | Nulos e estados de sigilo/zero sobrevivem ao caso sintético; inteiros são exportados como inteiros quando todos integrais | Decimais passam a `float`. Caso sintético `1234567890123456.789012` vira `1234567890123456.8`; não prometer decimal exato. |
| Citação | Dataset, fonte, licença quando recuperados | Aviso fixo diz que a fonte é IBGE inclusive quando o produtor do exemplo é Sinesp. “Sem alteração” também é insuficiente para derivados. |
| Formatos comuns | JSON com metadata/rows, ZIP com CSV/BOM e metadados JSON, Parquet com `odb_metadata` | O objeto comum atual não resolve dicionário/métodos completos. |
| Limites | Recusa por limite de linhas ou truncamento; 200 mil só para os dois KPIs LSPA, demais usam configuração | Limite configurado não comprova extração integral nem aceitação atual da candidata N4. |

Proveniência e lista de dimensões da rota são obtidas da última iteração do laço
de exportação. É necessário avaliar a união de tabelas/versões e métodos de todas
as partes, principalmente em arquivos com vários níveis/grãos/marginais. Esta é
uma lacuna de rastreabilidade observada no código, sem alegação de que todos os
arquivos existentes tenham valores errados.

O exportador de releases em `packages/modeling/.../export.py` é outro produto:
pacote com Parquet/DuckDB/manifesto para intercâmbio operacional. Seus testes não
comprovam que o Excel da interface tenha as novas abas. Exportações de métricas
e de imagens também têm semânticas próprias; não aplicar este contrato a elas
silenciosamente. O bloco de contas exige adaptação específica, ainda não implementada.

## Seleção da tela e conteúdo efetivamente exportado

`ExportIn` não aceita `isolate`, `accumulate` ou `seasonal_sum`; `extra=forbid`
os recusa. O menu envia seleção própria de níveis, grãos, períodos/categorias e
correção. Tabela/Excel mantêm períodos separados, inclusive quando o gráfico
consulta o operador sazonal. Agregações de calendário e correção de preços podem
estar no arquivo; acumulado do gráfico não está nele (ADRs 0026/0041).

| Operação da tela | Representação obrigatória da proposta |
|---|---|
| Isolar | Guardar seleção dos anos e partes da **visualização**, separada dos períodos escolhidos para **dados exportados**. Isolar é arranjo/comparação, não soma automática. |
| Acumular cronologicamente | Registrar `applied=false`, `scope=view` quando só a tela o usa; indicar que dados continuam separados. |
| Isolar + Acumular | Mesmo registro explícito: o Excel atual não contém a barra sazonal. Não copiar seu valor sobre uma observação anual/trimestral. |
| Grão diferente do nativo | Registrar método efetivamente usado (`sum`, `mean`, `last`, `compound` ou outro já autorizado), entradas, unidade e completude; distinguir de uma observação publicada. |
| Correção de preços | Registrar índice, tabela/variável, referência e base efetiva, mapeamento por grupo, fórmula e versão. É aplicada ao arquivo quando solicitada. |
| Percentual na tabela dinâmica | Distinguir percentual publicado de divisão para exibição, com base/denominador. A exportação longa atual não ganha percentuais só porque a tela os calcula. |
| Seleção de categorias | Preservar todas as chaves e os rótulos, conjuntos marginais e limitações de cruzamento. Total e filhos não compõem a mesma soma. |

A seleção de meses/partes dentro de Isolar e os cruzamentos mensais ainda
pendentes não podem constar como capacidades entregues. O modo padrão proposto
continua com dados separados. Uma opção futura de exportar agregados dependerá
de pedido/aceite próprios e usará uma aba distinta, com contribuintes, sem mudar
o sentido de `dados`.

## Abas e vínculos

### Identificação de quem gerou o arquivo

Pedido do mantenedor em 26/11/2026: registrar que a exportação foi gerada pelo
**Open Data Brasil**, preservando a identificação dos produtores oficiais.

- Cabeçalho de impressão, em todas as abas: **Gerado pelo Open Data Brasil**.
- Rodapé: `https://opendatabrasil.org`, instante de geração com fuso explícito
  e paginação. O instante é o da geração do arquivo; não usar a data dinâmica
  de impressão como se fosse a data de geração. Nos exemplos, identificar também
  que são modelos demonstrativos.
- Aba `metadados`: campos tabulares `generator_name`, `generator_url`,
  `generator_role=geracao_do_arquivo`, `generator_version` e `generated_at`.
  Os mesmos campos pertencem a `artifact` no objeto comum e a `generation` na
  extensão documental de códigos, permitindo leitura sem depender da impressão.
- Propriedades do XLSX: gerador do documento identificado como Open Data Brasil,
  com as mesmas informações em propriedades personalizadas. Isso descreve a autoria
  do arquivo exportado; produtores, licenças e citações dos dados permanecem em
  `fontes`. Não reivindicar autoria dos dados oficiais ou substituir seu crédito.

O cabeçalho/rodapé é uma propriedade da página, **fora das células da tabela**.
Não inserir faixas, logotipos, células mescladas ou linhas institucionais antes
dos nomes das colunas ou depois dos registros. As tabelas continuam iniciando em
A1, com os mesmos nomes, códigos, tipos, valores e chaves. Na visualização normal
do Excel, a identificação fica disponível na aba `metadados` e nas propriedades;
o cabeçalho/rodapé aparece na impressão ou no modo de layout da página.

A separação entre dados tabulares e metadados é compatível com a abordagem de
[anotações do CSVW/W3C](https://www.w3.org/TR/tabular-metadata/#common-properties).
Isso é uma decisão de projeto fundamentada nessa abordagem, não certificação
de conformidade do XLSX com CSVW. O mecanismo de página e propriedades está
documentado pelo XlsxWriter em [cabeçalhos/rodapés](https://xlsxwriter.readthedocs.io/page_setup.html#worksheet-set-header)
e [propriedades do arquivo](https://xlsxwriter.readthedocs.io/workbook.html#workbook-set-properties).
Nos demais formatos, preservar a identidade nos metadados ou no arquivo auxiliar;
não adicionar linhas de marca ao CSV nem campos institucionais como medidas.

### Estrutura tabular

As cinco abas obrigatórias são tabelas sem células mescladas nem conteúdo
semântico apenas em cores/comentários. Cada coluna tem identificador estável;
as legendas são legíveis em pt-BR. Valores literais; fórmulas da planilha não
substituem cálculo versionado e não serão executadas ao abrir texto vindo da fonte.

| Aba | Grão e chave | Conteúdo mínimo |
|---|---|---|
| `dados` | Uma observação publicada/derivada autorizada por linha; `row_id` único | `indicator_id`, `kpi_id`, `dataset_id`, `source_table_id`, `source_variable_id`, `geography_key`, código territorial oficial/tipo/vigência, período e seu significado, dimensões/categorias, valor decimal exato, valor original se disponível, status, unidade/multiplicador, `source_id`, `method_id`, `release_id`, bloco. |
| `metadados` | Um registro por atributo/escopo/bloco | Versão do esquema, título, release e versões Delta/manifesto, versões de método e dicionário, código gerador, datas com fuso, cobertura efetiva, filtros completos, seleção da tela e do arquivo, licença/citação e avisos. |
| `dicionario` | `(sheet_id,column_id,entry_type,code,valid_from,valid_to,source_id)` | Definição conceitual da coluna; tipo, domínio, unidade, nulos; códigos/rótulos oficiais; hierarquia; edição/exercício e referências. `entry_type=column` e `code` separam conceito da coluna de definição por código/ano. |
| `fontes` | `source_id` e uma afirmação/referência por registro | Produtor, sistema, dataset/tabela/variável e identificadores oficiais, edição, seção/página, URL, consulta, publicação/obtenção conhecidas, checksum/artefato quando disponível, licença/termos e afirmação sustentada. |
| `metodos` | `(operation_id,sequence)` com referência a `method_id/version` | Método do produtor e operação do portal separados; fórmula, parâmetros completos, entradas/saídas, nível, período, cobertura, avisos e escopo; aplicado ou apenas exibido. |

Abas opcionais condicionadas à necessidade: `contribuintes` (arestas de linhagem,
uma entrada por linha/resultado) e `agregados` (somente se autorizado/exportado).
Se a lista exceder limites do Excel, recusar ou particionar com manifesto, nunca
truncar silenciosamente nem omitir a trilha. Não exportar folhas individuais
suprimidas para tornar reproduzível um agregado protegido.

Os códigos são **texto**, incluindo zeros à esquerda e sinais significativos;
nomes não são chaves. Campo territorial distingue IBGE/SIAFI/nível especial; tipos
N103/N1103 não se convertem para N1 pelo nome “Total”. Contas guardam lente/fase,
exercício e territorialidade do favorecido/sede separada da aplicação do recurso.

`value_exact` será texto decimal canônico com sinal e ponto, preservando escala
quando conhecida. `valor` numérico pode ser uma coluna auxiliar para análise no
Excel, explicitamente sujeita à precisão do formato e jamais a única cópia exata.
Nulo tem valor vazio e `status`/marcador originais; não usar zero, hífen arbitrário
ou texto “N/A” como substituto universal. `X`, `...`, `..`, zero verdadeiro,
zero arredondado e estados derivados continuam distintos. O hífen do Tesouro,
por exemplo, não herda automaticamente a interpretação SIDRA de zero.

Datas desconhecidas ficam nulas com `missing_reason`; a data de consulta do
dicionário não preenche a data de obtenção ou publicação dos dados. Publicação
do produtor, registro, ocorrência, referência, processamento e geração têm campos
distintos. “Atualizado” sem identificar qual deles é insuficiente.

## Registro reproduzível de métodos e operações

Cada método inclui identificador e versão imutáveis, texto/fonte/seção/edição,
fórmula legível, especificação dos tipos, unidade de entrada/saída, parâmetros,
condições de domínio e motivo de bloqueio. Uma nova regra não é inferida da unidade
ou da palavra “total”. Os 183 pareceres sem soma, 30 fluxos pendentes e quatro
composições contíguas da revisão temporal permanecem válidos em seu escopo; as
24 somas sustentadas ainda exigem comparabilidade e completude de cada célula.

Ordem a registrar como grafo de operações, conforme a execução real: resolver
release e fontes → selecionar território/tempo/categorias e conjuntos admissíveis
→ harmonizações/conversões já materializadas (linhagem Gold) → transformações
de consulta na ordem realmente executada → renderização. Correção, agregação e
acumulação não são declaradas comutativas. Cada aresta identifica entradas e saída.
Não adotar esta ordem genérica como nova regra estatística: a implementação futura
deve descrever o plano executado para o indicador e a versão específicos.

Para qualquer agregado futuro, registrar:

- Intervalo inclusivo `min(anos)…max(anos)` e anos intermediários, partes pedidas e contribuintes realmente usados; períodos sobrepostos não podem duplicar a mesma entrada.
- Calendário e grão nativo; agrupamento por território e combinação de categorias, sem fabricar meses a partir de um anual.
- Contagens `expected`, `present`, `missing`, `blocked`; lista de ausências/bloqueios e entradas já parciais; sigilo não é ausência territorial.
- Fórmula e denominador/pesos quando necessários; taxa/média/estoque/índice não recebem soma por inferência.
- Valor, status e aviso do resultado, inclusive subtotal parcial de fluxos já admissíveis; sigilo/incompatibilidade bloqueiam conforme método vigente.
- Origem das entradas e resultado, release, tabelas/versões, versão de método, parâmetros, unidades e precisão/arredondamento. Uma saída derivada não vira observação oficial.

Exemplo didático: jan/2023=10, jan/2024=0 e jan/2025 ausente. Se a soma estiver
autorizada, o subtotal é 10, cobertura 2/3 e aviso de ausência de jan/2025; não é
30 nem uma soma completa. Trocar a ausência por sigilo deve bloquear o método
correspondente, preservando a proteção. Este exemplo é sintético, sem vínculo
com qualquer estatística publicada.

## Códigos e base legal ligados às linhas

Ampliação de 26/11/2026, incorporada sem alterar exportador. O [inventário por
domínio/exercício](../data_catalog/dicionarios-2026-11-26/cobertura-codigos-contas.csv)
tem lacunas explícitas; a existência do dicionário SIOP não comprova que todos os
verbetes foram obtidos. Nenhum corte de ranking serve como prova de completude.

Além das cinco abas, quando o conteúdo envolver códigos e fundamentos normativos,
o mesmo objeto comum deve admitir as seguintes coleções/tabulações. Arquivos
pequenos podem incorporar verbetes ao dicionário, desde que preservem as mesmas
chaves e relações; listas grandes usam abas próprias e particionamento declarado.

| Coleção / aba | Chave e conteúdo | Relação obrigatória |
|---|---|---|
| `code_entries` / `codigos` | `entry_id`, sistema, domínio, código textual, exercício/vigência, contexto/hierarquia, nome e definição oficiais separados da explicação, versão, fonte, edição, seção e consulta | Chave cadastral completa; ação SIOP precisa de exercício, esfera, UO, função, subfunção, programa e ação. PO/localizador acrescentam o respectivo código. |
| `legal_references` / `normas` | `norm_id`, tipo/número/data da norma, dispositivo, URL oficial, redação/versão, início/fim de efeitos quando conhecidos, alteração/revogação/suspensão e situação da verificação | Dispositivo específico, sem preencher vigência desconhecida; data de consulta não é data de início de efeitos. |
| `code_legal_links` / `codigo_norma` | `entry_id`, `norm_id`, natureza da relação, exercício, evidência e situação | Separar “citado no cadastro” de “aplicável ao lançamento”; a primeira relação não comprova a segunda. |
| `row_code_links` / `linha_codigo` | `sheet_id`, `row_id`, `column_id`, código original, exercício, `entry_id`, regra/versão da correspondência e situação | Cada linha/coluna alcança o verbete exato; código sem correspondência fica explícito, sem associação por nome ou outro exercício. |

O [schema complementar documental](../data_catalog/dicionarios-2026-11-26/codigos-normas.schema.json)
e o [exemplo 0A53](../data_catalog/dicionarios-2026-11-26/exemplo-codigos-normas.json)
demonstram as relações e bloqueiam chaves órfãs, código divergente e exercício
divergente. São uma extensão de proposta `0.1.1-proposta-codigos`; ainda não estão
fundidos ao contrato base `0.1.1-proposta` nem à API. A representação final precisa
fechar os campos de vigência/redação, versões, explicação e correspondências antes
de implementação. Os exemplos não significam que o portal já entregue esses dados.

Na demonstração, `0A53` liga a uma ocorrência oficial de **2016** e às citações
CF art. 20 §1º, Lei 9.478/1997 arts. 48–50 e Lei 7.525/1986 art. 6º. A aplicação
das redações ao recebimento fica pendente. O valor informado sem período está
somente em `unverified_input`, **fora de `data_rows`**, com origem e motivo da
não reconciliação. O exemplo XLSX de nove abas mantém `dados`/`linha_codigo`
vazias; não fabrica uma medida, um release ou uma correspondência financeira.

Textos “Não se aplica”/“Sem informação” conservam significado e origem; não viram
códigos territoriais, taxas legais ou zeros. “Royalties”, ação, mecanismo de
transferência e fonte/destinação contábil permanecem campos diferentes. Uma
norma ou novo verbete não cria parcela adicional somável ao pagamento. Para o
caso concreto e as fontes, ver [ficha 0A53](../data_catalog/dicionarios-2026-11-26/acao-0A53.md).

## Um esquema comum aos formatos

Proposta de objeto canônico `odb-export-metadata/0.1.0-proposta`, documentado em
[metadados.schema.json](../data_catalog/dicionarios-2026-11-26/metadados.schema.json),
com [exemplo verificável](../data_catalog/dicionarios-2026-11-26/exemplo-metadados.json).
É um schema documental de proposta; não é contrato novo da API nem afirmação
de conformidade externa. JSON o inclui no envelope, CSV o acompanha como arquivo,
Parquet o associa ao rodapé e XLSX projeta seus mesmos registros nas abas. A soma
de cada exportador não pode ter explicação independente.

| Padrão oficial e edição | Correspondência útil proposta | Limite |
|---|---|---|
| [SDMX, Information Model 2.1](https://docs.sdmx.org/en/i1-doc/Sections/Section2/SDMX_2_1_SECTION_2_InformationModel.html), seções DataSet/Observation e componentes; consulta 26/11/2026 | Dimensões de território/tempo/categoria; medida; atributos de unidade/status; listas de códigos e estrutura versionadas | Documento de explicação do modelo identificado como não normativo. Não afirmar geração SDMX 3.1 ou DSD validada; esquemas oficiais atuais em [SDMX-ML](https://xml.sdmx.org/). |
| [DDI-Codebook 2.6](https://ddialliance.org/ddi-codebook), descrição do estudo/arquivo/variável, versão de 15/04/2026; consulta 26/11/2026 | Universo, conceitos, amostra, ponderação, variáveis, domínios/categorias, qualidade e fontes | Dicionário de uma série agregada não substitui o desenho amostral e o questionário; validar eventual mapeamento XML em etapa própria. |
| [DCAT 3](https://www.w3.org/TR/vocab-dcat-3/), Recomendação de 22/08/2024, Dataset/Distribution e cobertura; consulta 26/11/2026 | Dataset e release como recurso versionado, cada formato como distribuição; licença, produtor, cobertura e acesso | Ajuda a descobrir a distribuição; não define fórmula estatística nem codelist sozinho. |
| [PROV-O](https://www.w3.org/TR/prov-o/), Recomendação de 30/04/2013, §3.1; consulta 26/11/2026 | Fonte/release/arquivo como Entity, transformação como Activity e produtor/gerador como Agent; `used`, `wasGeneratedBy`, `wasDerivedFrom` | Exige grafo com versões/parâmetros reais; desenhar correspondência não valida todas as restrições PROV. |
| [CSVW Metadata](https://www.w3.org/TR/tabular-metadata/), Recomendação de 17/12/2015, §§5.5/5.6/5.7/5.11; consulta 26/11/2026 | Nome/título/descrição de coluna, datatype, null, required, chave primária/estrangeira e relacionamentos entre tabelas | Útil ao CSV e à validação do dicionário comum; XLSX com nomes de abas não é automaticamente CSVW conforme. |

Fontes normativas e trechos indexados localizam os conceitos acima; PROV-O e CSVW
tiveram leitura direta disponível. A proposta usa correspondências justificadas,
sem afirmar certificação SDMX/DDI/DCAT/PROV/CSVW ou adoção arquitetural aprovada.

## Critérios para uma implementação futura

1. Confirmar escopo com o mantenedor e fechar as lacunas por indicador/edição; versionar schema, métodos e codelists sem alterar estatística por efeito colateral.
2. Validar a mesma instância canônica nos quatro formatos; chaves únicas, códigos textuais, nulos/status, precisão exata, referências e licença por origem.
3. Provar seleção completa: categorias, marginais, grãos/níveis, correção, URL/tela e plano exportado, inclusive diferença explícita de operações apenas visuais.
4. Reproduzir cada derivado admissível por suas entradas e parâmetros; testar faltas, zero, sigilo, partes descontínuas, anos intermediários, hierarquia e não soma de taxas/estoques.
5. Conferir limites de linhas/células/tamanho de célula, fontes múltiplas, fórmulas em textos, arquivos parciais e abertura no Excel/LibreOffice. Os limites devem falhar explicitamente.
6. Revisar acessibilidade e leitura humana das cinco abas e da linhagem. Só então testar integração/portal em candidata própria; sem inferir autorização de publicação ou ativação.

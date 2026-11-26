# Dicionários e exportações — contrato implementado

26/11/2026. Versão `odb-export/1.0.0`. Código em desenvolvimento local;
esta documentação não anuncia implantação na beta.

## Consultar a documentação

`GET /api/v1/dictionaries` lista as 335 fichas e seus estados documentais.
Inclui os 44 apoios sem KPI e a preparação de 50 candidatas: 21 N3, 11 N4 e 18 N5.
O campo `publicavel=false` não é uma avaliação negativa de todos esses dados:
indica que a conferência estática não substitui reconciliação/aceite do release.
A reprovação anterior da N5 permanece explícita.

`GET /api/v1/dictionaries/{entry_id}` entrega a ficha integral preservada, ligações
por tabela/variável, campos, códigos, contexto complementar, referências e métodos.
O identificador dos apoios inclui `apoio--`. A versão documental é um SHA-256 dos
sete arquivos de entrada, também identificados individualmente. Não é o release
Gold nem uma data de publicação. O proxy do portal admite somente leitura desses
documentos em `/odb-api/dictionaries`.

Fontes: `fichas.json`, `metodos.json`, `ligacoes.json`, `campos.csv`, `codigos.csv`,
`contextos-complementares.json` e `candidatas.csv` no acervo de dicionários.
Nenhuma definição ausente foi substituída por um nome, nem síntese parcial recebeu
o estado de método integralmente homologado.

## Preparar a expansão

```bash
python -I infrastructure/scripts/preparar_indicadores.py --output preparacao.json
```

Executar no ambiente instalado do projeto. O script confere vínculo KPI/indicador,
fato, fonte configurada, ficha e identificação de variável oficial. Não consulta
o banco de produção, baixa dados, refaz N3/N4/N5 ou ativa releases. O arquivo de
saída deve ser novo. A [preparação versionada](../data_catalog/dicionarios-2026-11-26/preparacao-expansao.json)
conserva os impedimentos e próximos passos de cada candidata.

## Exportação

`POST /api/v1/exports` mantém a seleção existente. Além das colunas legíveis,
inclui `row_id`, `block_id`, `kpi_id`, `indicator_id`, `release_id`, `value_exact`,
`source_table_id` e, por dimensão, `<classificacao>_code` e
`<classificacao>_category_key`. Códigos são texto; `value_exact` conserva a
representação decimal recebida. Datas e valores não informados não são fabricados.

Os metadados mantêm os campos anteriores e acrescentam:

| Campo | Significado |
|---|---|
| `artifact` | Gerador, site, instante UTC e versão do formato |
| `blocos` | Nível, grão, dimensões, categorias, períodos pedidos/exportados, número de linhas, versões e correção de cada consulta |
| `documentacao` | Ficha, ligações, códigos, fontes, sínteses e lacunas relevantes ao KPI |
| `documentacao_status` | Revisão parcial ou ficha não localizada, sem assumir completude |
| `dicionario`, `fontes`, `metodos` | Registros tabulares projetados nas abas correspondentes |
| `operacoes_visuais` | Acumulados do gráfico não aplicados ao arquivo |

A proveniência geral une as tabelas de todos os blocos. Os filtros gerais mantêm
todas as dimensões e categorias; as marginais separadas têm `block_id` distinto.
O bloco registra a correção escolhida com seu mapeamento e a regra de agregação
temporal já configurada quando se consulta um grão derivado. Não se cria uma
nova autorização de soma.

CSV continua em ZIP, com dados UTF-8/BOM e `metadados.json`. JSON usa
`metadata/rows`; Parquet conserva `odb_metadata` no rodapé. XLSX contém a mesma
seleção em seis abas: capa com logo/navegação e cinco tabelas com filtros,
alternância de linhas e cabeçalhos fixos. As tabelas começam em A1 e não têm
mesclas ou totais automáticos. Cabeçalhos/rodapés e propriedades identificam o
gerador e a data UTC. Textos não são convertidos em fórmulas ou links automáticos.

Em metadados do XLSX, `campo/parte/partes/valor` permite recompor um JSON extenso
concatenando `valor` na ordem de `parte`. Dados de observações não são divididos
ou truncados para caber em uma célula; excedentes são recusados. As lacunas dos
dicionários acompanham a exportação. O template não altera os exportadores das
contas, métricas ou imagens.

## Detalhes nativos e piloto mensal

`categorias_nativas=["c240"]` no catálogo canônico habilita na 2609 o campo
`explorable_categories` dos metadados. São as 35 idades adicionais observadas no
indicador, com pai/profundidade. As dez faixas curadas continuam como padrão.
As rotas e exportações aceitam seleções dessas idades; pai e filho no mesmo filtro
são recusados antes de somar. A configuração global não garante completude em
todos os municípios/períodos/cruzamentos. O seletor visual da árvore ainda está
pendente; o suporte desta rodada é o contrato e a consulta pela API.

O gerador aceita `mes_detalhes` somente com o conjunto de captura correspondente
em `cruzar`. O piloto da 2654 preserva sexo na projeção mensal e prova 48 células
da resposta oficial de Brasil/2024. Não foi habilitado no catálogo corrente:
a carga conjunta e a reconciliação dos demais recortes precisam ocorrer em candidata.
Meses ignorados e totais continuam nos originais, sem redistribuição.

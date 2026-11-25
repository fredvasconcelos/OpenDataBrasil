# Auditoria do detalhamento nativo dos KPIs

O auditor `infrastructure/scripts/revisao_detalhamento_kpis.py` compara as opções
nativas do SIDRA com um snapshot da API do portal e estatísticas da Gold do mesmo
release. Não modifica configurações, dados, serviços nem publicação.

## Entradas e execução

Executar com Python isolado (`-I`). Os caminhos abaixo são parâmetros locais,
nunca conteúdo para incluir no Git:

```bash
python -I infrastructure/scripts/revisao_detalhamento_kpis.py \
  --snapshot /evidencias/portal-navigation.json --output /evidencias

python -I infrastructure/scripts/revisao_detalhamento_kpis.py \
  --snapshot /evidencias/portal-navigation.json --output /evidencias --probe

python -I infrastructure/scripts/revisao_detalhamento_kpis.py \
  --snapshot /evidencias/portal-navigation.json --output /evidencias \
  --compare --coverage /cobertura-anterior
```

O snapshot é a resposta de `/api/v1/portal/navigation`. A comparação recebe também:

- `gold-metadata.json`: release, manifesto `tables`, `lineage` (indicador, dataset,
  tabela, variável, níveis, períodos);
- `gold-cruzamentos.json`: release e `rows`, com indicador, tabela, variável, nível,
  período e lista exata de classificações não totais de cada padrão observado;
- diretório de cobertura: `catalogo-api.json` (release e manifesto `tables`) e
  `detalhes.parquet` (indicador, tabela, classificação e `category_territories`, lista
  de estruturas com `category_key`).

As estatísticas devem ser produzidas em consultas somente leitura à Gold Delta
fixada no manifesto. A consulta precisa verificar `truncated=False`; uma relação
truncada não comprova ausência. Manifestos ou releases diferentes impedem a comparação.

## Saídas e interpretação

`matriz.json` e os CSVs `kpis`, `detalhamentos`, `cruzamentos`, `niveis`, `periodos`,
`variaveis` e `notas-fontes` preservam códigos, categorias, hierarquia e exceções
oficiais. `indice-descritores.json` e `indice-amostras.json` registram URL, data,
status e SHA-256 de cada resposta; cada download usa diretório novo.

Há três provas diferentes:

1. Eixos simultâneos no descritor: candidato a cruzamento, sujeito às notas e
   exceções da variável, categoria, período e nível.
2. Amostra `/values`: resposta apenas para os códigos, data e nível registrados.
   A seleção pequena usa até duas categorias por eixo; não cobre o cubo inteiro.
3. Padrão conjunto observado na Gold: existência de registros com o conjunto exato
   de eixos não totais. Não comprova todas as células, categorias ou territórios.

As categorias observadas são reunidas por indicador/tabela ao longo dos períodos,
níveis e variáveis; os totais acrescentados vêm da configuração. Essa evidência
não deve ser interpretada como cobertura integral de cada recorte. Categorias
derivadas e harmonizadas não são equivalidas às nativas por semelhança de nomes.
Uma variável adicional é uma medida candidata; não se torna um filtro do KPI.

O calendário da tabela não elimina as exceções por variável/categoria/nível.
Séries mensais construídas a partir de uma classificação de meses precisam de
avaliação própria: a diferença para o calendário anual não é, sozinha, defeito.

O coletor acessa apenas os endpoints oficiais documentados, em série, com intervalo
mínimo de dois segundos. Bloqueios 403/405/429 interrompem a coleta e impedem retomada
automática no mesmo índice. Erros e valores especiais são preservados. Os sete KPIs
externos ao SIDRA ficam identificados para avaliação em suas fontes, sem atribuição
de códigos SIDRA.

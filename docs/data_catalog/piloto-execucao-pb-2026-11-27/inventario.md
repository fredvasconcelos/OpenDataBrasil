# Piloto de execução própria — Guarabira e Paraíba

Verificação: 27/11/2026. Seleção expressa do mantenedor: Guarabira/Elmar e Governo
da Paraíba. **Situação: descoberta e amostras conferidas; sem integração aos KPIs.**
Este piloto executa o inventário E0 e parte da prova E2 do
[plano de inserção](../../development/plano-execucao-estados-municipios.md).

## Autoridade, acesso e licença

| Escopo | Autoridade e acesso confirmado | Limite |
|---|---|---|
| Executivo de Guarabira | [Site institucional](https://www.guarabira.pb.gov.br/portal-da-transparencia/portal-da-transparencia-atual) vincula o portal Elmar com `e=201082`; cabeçalho identifica prefeitura/CNPJ `08.785.479/0001-20` | `201082` é contexto do fornecedor, não código IBGE. Fundos e instituto de previdência aparecem como outras entidades no seletor; não estão homologados |
| Reúso municipal | [Página Dados Abertos da prefeitura](https://www.guarabira.pb.gov.br/pagina/dados-abertos) declara acesso gratuito e permissão de reúso e vincula os dados da transparência | Sem identificador de licença padronizado confirmado para a API; revisão de condições ainda pendente. Não atribuir CC BY 4.0 por analogia |
| API municipal | [Dados Abertos Elmar](https://transparencia.elmartecnologia.com.br/DadosAbertos?ctx=201082&e=201082) vincula o [Swagger](https://transparencia-api.elmartecnologia.com.br/swagger); descritor v2 lido | Acesso sem credencial nas amostras; não comprova disponibilidade de todos os módulos/anos ou SLA |
| Estado da Paraíba | [Portal estadual](https://transparencia.pb.gov.br/) vincula [API](https://api.dados.pb.gov.br/swagger/) e catálogo; [conjunto de despesas da CGE](https://dados.pb.gov.br/dataset/despesas) possui recursos JSON | Amostra inclui Executivo e Judiciário. Não restringir a Executivo nem anunciar todos os poderes/órgãos por inferência |
| Licença estadual | Recurso de execução e conjunto indicam CC com compartilhamento pela mesma licença; rodapé do catálogo indica CC BY 4.0 | Divergência explícita: não substituir automaticamente o metadado específico pelo rodapé; revisão antes de republicação |

Os acessos HTTP locais das amostras responderam 200, sem autenticação ou contorno.
A raiz Elmar sem contexto responde texto de entidade inválida apesar do HTTP 200;
isso não é indisponibilidade da API. Algumas tentativas do leitor web falharam por
timeout/acesso da ferramenta, sem evidência de 403/CAPTCHA da fonte.

## Recortes capturados e o que foi conferido

| Fonte e seleção | Resultado | Conferência e alcance |
|---|---|---|
| Elmar, `201082`, `07/2026`, exercício 2026, consolidado falso | 42 registros em `data`, todos na competência e entidade pedidas | Integridade, sequência sem repetição, decimais, zeros e sinais; sem total/paginação que demonstre completude |
| Elmar, mesmos filtros, `11/2026` | 8 registros | Correspondência com as 8 linhas visíveis da consulta oficial em novembro: **72 células monetárias** iguais e **7 totais de rodapé** iguais, em Decimal |
| Paraíba, julho/2026, grupo da despesa, Até o mês, página 1/10 | 10 de 334 registros; 34 páginas | Paginação confere; subtotal recebido não é total estadual |
| Paraíba, mesmos filtros, Até o mês, página 1/1000 | 334 de 334 registros; 1 página | Recorte completo segundo o total informado pela API; primeiros 10 registros idênticos à página de 10. Não comprova completude de órgãos/exercícios |
| Paraíba, mesmos filtros, No mês, página 1/10 | 10 de 334 registros | Modalidade temporal preservada separadamente; não se somou com o acumulado nem se comparou linha a linha por posição |

Todos os montantes foram lidos diretamente do JSON com `Decimal`, sem passar por
float. Somatórios técnicos descrevem apenas as linhas recebidas de cada campo.
Negativos não foram corrigidos nem interpretados automaticamente como estorno.
Não houve recodificação territorial, união entre fontes ou cálculo de aplicação.

A consulta visual Elmar não aplicou julho pelos parâmetros GET tentados e continuou
mostrando novembro/2026. A conferência visual usou **novembro efetivamente mostrado**,
com a API da mesma competência; julho não recebeu aceite visual. Não igualar
parâmetros entre a API e o formulário sem conferir o período retornado.

## Contratos e próxima prova

[Dicionário observado](dicionario.md) e [manifestos de captura](manifestos.json).
Os manifestos registram URL exata, horário UTC, status, bytes e SHA-256; originais
e conferências detalhadas permanecem em evidência local, fora da distribuição pública.
O PDF oficial estadual foi preservado; a leitura textual dele não foi validada nesta
rodada. As descrições abaixo se apoiam no Swagger e na configuração/consulta HTML.

Antes de construir Silver/Gold e KPIs:

1. Resolver condições de reúso e divergência de licença; manter atribuição específica.
2. Documentar correspondência CNPJ/contexto/ente oficial, vigência e órgãos/fundos;
   não associar por nome. Medir cobertura por mês e edição, incluindo períodos vazios.
3. Esclarecer o significado temporal de cada valor municipal, principalmente empenhado,
   dotações e saldos. O endpoint retorna objeto genérico no Swagger, sem schema dos
   registros. Enumerar todos os códigos e preservar os descritores por edição.
4. Conferir meses adjacentes e fronteira de exercício, revisões e anulações; comparar
   exportação oficial e consulta. Sinal negativo confirmado não prova sua causa.
5. Para PB, validar grão/chave com órgão, poder, marcador, orçamento democrático,
   classificação e modalidade temporal; obter totais oficiais independentes e
   dicionários/códigos das 11 classificações documentadas. Não juntar classificações
   diferentes como se fossem parcelas independentes.
6. Propor contrato E3 com amostra reconciliada e atualização idempotente. A reexecução
   do diagnóstico offline é determinística; ingestão incremental ainda não foi implementada.
7. Tratar a ligação repasse → execução como prova própria: fonte `600`, `621` ou
   `660` descreve origem/destinação, mas não identifica isoladamente um repasse.
   Sem percentual de aplicação até o aceite do método e do universo rastreável.

## Reproduzir o diagnóstico

Script independente, somente leitura dos originais, sem rede e sem nova dependência:

```sh
python3 -I infrastructure/scripts/diagnosticar_execucao_entes.py \
  --source elmar --manifest "$CAPTURA/manifesto.json" --output "$RESULTADO"
```

Para a API estadual, usar `--source pb`. O manifesto acompanha um arquivo chamado
`resposta` no mesmo diretório e contém os campos `url`, `url_final`, `status`,
`bytes` e `sha256`. A saída deve ser um arquivo novo. A rotina rejeita alteração
por hash, competência/entidade incompatível, consolidação municipal, monetários
inválidos, arredondamento subcentavo, duplicatas exatas e paginação inconsistente.
Uma coluna monetária ausente falha; `null` permanece ausência, sem virar zero.
O diagnóstico não autoriza publicação e não escreve no catálogo nem no lakehouse.

# ADR-0043 — Dicionários versionados e exportação rastreável

Data: 26/11/2026. Situação: implementação local solicitada pelo mantenedor;
publicação e ativação de dados permanecem pendentes.

## Contexto

O exportador omitia categorias nos filtros, conservava apenas a proveniência da
última parte de uma consulta e atribuía todas as fontes ao IBGE. O Excel tinha
somente dados e metadados. A revisão documental produziu 335 fichas e 50 sínteses
metodológicas, com lacunas que precisam continuar identificadas ao serem distribuídas.

## Decisão

- Distribuir no runtime o acervo documental versionado já existente. O índice
  `/api/v1/dictionaries` inclui as 291 fichas de KPI, 44 apoios e a preparação
  estática das 50 candidatas; `/api/v1/dictionaries/{entry_id}` reúne ficha,
  ligações, métodos, campos, códigos e contexto. Disponibilidade do snapshot e
  documentação parcial não equivalem à publicação ou a um método homologado.
- Manter um objeto de metadados comum aos quatro formatos. Registrar os filtros
  de categorias e dimensões de todas as partes, identificar blocos/linhas e unir
  todas as tabelas/versões consultadas. Recusar releases ou versões contraditórios.
- Acrescentar `value_exact` textual, códigos de categoria e chaves do release,
  preservando as colunas legíveis. A coluna numérica é auxiliar; a exportação não
  recupera precisão perdida anteriormente na Gold ou em um cálculo.
- Adotar o Excel de seis abas: Apresentação, dados, metadados, dicionario, fontes
  e metodos. A marca identifica o gerador; créditos e licenças permanecem por
  produtor. Fórmulas automáticas ficam desabilitadas em textos. Metadados extensos
  são divididos em partes numeradas, recomponíveis; campos tabulares que excedam
  limites são recusados, sem truncamento.
- Expor hierarquias por opt-in da configuração. Na 2609/c240, categorias adicionais
  precisam estar observadas no próprio indicador. A seleção de categorias para soma
  rejeita pai e filho juntos. O Total e a partição curada permanecem como padrão.
- Permitir ao gerador preparar projeção mensal com detalhes explicitamente
  selecionados, exigindo a captura conjunta declarada. A opção não é habilitada
  na configuração corrente da 2654: o piloto de Brasil/2024 não homologa todo o cubo.

## Consequências e limites

Clientes de arquivos devem usar nomes de colunas; foram acrescentadas colunas ao
formato longo. O esquema implementado é `odb-export/1.0.0`; não se declara
conformidade integral com os esquemas demonstrativos anteriores, SDMX ou CSVW.
Acumulados apenas visuais continuam fora dos dados exportados. Correção de preços,
grão, parâmetros e proveniência efetivos ficam registrados por bloco.

O inventário de códigos descreve a fonte; não comprova presença de cada código
em cada recorte da Gold. Metodologia completa por variável/edição, seleção visual
hierárquica e cruzamentos ainda ausentes continuam pendentes. N5 não recebe
correção de precisão ou liberação por esta entrega. Exportadores das contas,
métricas e imagens conservam contratos próprios.

Referências: ADRs 0016, 0020, 0040 e 0041;
[dicionários](../data_catalog/dicionarios-2026-11-26/README.md);
[contrato implementado](../development/exportacao-rastreavel.md).

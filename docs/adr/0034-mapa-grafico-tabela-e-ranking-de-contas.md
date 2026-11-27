# ADR-0034: Mapa, gráfico, tabela e ranking no bloco de contas públicas

- **Estado:** aceito (2026-11-22), pela lógica definida pelo mantenedor para evitar
  sobrecarga no portal. Os tetos numéricos serão ajustados por medição (CP4).
- **Contexto normativo:** CLAUDE.md §5.3.8, §10.7, §11.4, §18.5 e §20.6; ADR-0024
  ("Detalhar por"), ADR-0026 (seleção de períodos), ADR-0032 e o Plano D (desempenho).

## Decisões

1. **Mapa:** só o **montante total por território** (Brasil, região, UF, município), na
   lente, no período e nos filtros escolhidos. O tooltip traz o total e a participação no
   território-pai.
   - **"Detalhar por"** (como no ADR-0024): escolhe uma dimensão e uma ou mais categorias
     dela. O mapa recolore com a soma das categorias marcadas, e o tooltip mostra a
     composição do território (top 10 categorias + "demais").
   - Dimensões da **lente A:** tipo de transferência; função; subfunção; programa; ação
     (com a linguagem cidadã); órgão superior; órgão; grupo de despesa; modalidade de
     aplicação; elemento de despesa; classe do favorecido (ADR-0031).
   - Dimensões da **lente B:** órgão superior; órgão; unidade gestora; classe do
     favorecido; atividade econômica (seção CNAE do cadastro PJ).
   - Dimensões da **lente C:** fase (empenhado, liquidado, pago, restos a pagar); função;
     programa; ação; órgão; grupo e elemento; modalidade; autor de emenda. Sem mapa
     municipal (ADR-0032, decisão 6).
2. **Gráfico:** o mesmo comportamento do mapa. Série mensal ou anual do total, ou do
   "detalhar por" (até 10 séries + "demais"), no território selecionado.
3. **Tabela:** desdobra em todos os níveis (território → dimensões → favorecido), com
   **paginação no servidor, 10 linhas por página**.
   - Ordem padrão: valor decrescente. Também ordena por nome.
   - A consulta busca só a página pedida (`LIMIT 10 OFFSET n` sobre partição podada). Nunca
     se buscam milhares de registros para paginar no navegador.
   - Teto de navegação proposto: 100 páginas (1.000 linhas). Além disso, o portal pede um
     filtro ou oferece a exportação, com os tetos atuais.
   - O total do território e o total da página aparecem no rodapé. A contagem de
     registros vem do agregado ou de um `COUNT` sobre a partição podada, a medir.
4. **Ranking contextual:** todo top N obedece à hierarquia selecionada.
   - "Principais favorecidos" do estado X ordena todos os favorecidos de todos os
     municípios de X, mais os estaduais sem município (ADR-0032, decisão 7).
   - O mesmo vale para região e Brasil.
   - Os filtros e o "detalhar por" ativos também se aplicam (ex.: os maiores favorecidos
     da função Saúde em PE).
   - A classe "lançamentos agregados ou intermediados" fica fora do ranking de
     destinatários e aparece no quadro próprio (ADR-0031, decisão 2).
5. **Onde cada consulta roda** (nada de transformação pesada na requisição, §5.3.8):

   | Visão | Lê | Custo esperado |
   |---|---|---|
   | Mapa e gráfico (total) | agregado oficial território × período × lente | pequeno, com cache por release |
   | Mapa e gráfico com "detalhar por" | agregado território × período × dimensão | pequeno a médio |
   | Tabela e ranking | fato no grão de entidade, particionado por ano e UF, com poda por prefixo IBGE | uma página de 10 linhas |

   - Os agregados são produtos da Gold, calculados pelo Polars e persistidos em Delta
     (§10.7). DuckDB não os grava (§11.6).
   - Rotas novas: `/api/v1/contas/...`, com contrato OpenAPI, teto de linhas, tempo
     limite e chave de cache com o release (§26.2).
6. **Só o nome na apresentação** (pedido do mantenedor, 2026-11-22: "não precisamos
   apresentar junto seu par CPF/CNPJ ou código do órgão, para não contaminar a visão da
   tabela"):
   - na tabela, no tooltip, no ranking e nas fichas, órgãos, unidades gestoras, empresas,
     entidades e pessoas aparecem só pelo nome. CPF mascarado, CNPJ e códigos SIAFI ficam
     fora da tela;
   - internamente, a chave continua sendo código + nome (ADR-0031, decisão 3). Dois
     homônimos continuam em linhas separadas, e o aviso de homônimo (ADR-0031, 5.3) explica
     nomes repetidos;
   - as exportações levam os códigos, para quem reutiliza os dados (padrão proposto, a
     confirmar);
   - filtros melhores por esses campos ficam para depois.
7. **Período:** grão mensal, com soma no tempo, porque é fluxo (ADR-0013). Seleção de
   períodos e acumulado como no ADR-0026. Período parcial como no ADR-0033, decisão 4.
8. **Aceite de desempenho** (CP4): p95 da tabela e do ranking abaixo do p95 atual do
   painel no mesmo cenário k6 (`escada.js`), sem 5xx. O teto de 100 páginas e o tamanho
   dos agregados são revistos pela medição.

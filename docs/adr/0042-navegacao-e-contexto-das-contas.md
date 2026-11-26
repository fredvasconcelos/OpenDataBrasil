# ADR-0042 — Catálogos por bloco e contexto do painel de contas

- **Situação:** escopo solicitado pelo mantenedor em 26/11/2026; implementação local sujeita à revisão visual.
- **Escopo:** frontend, navegação e consumo dos contratos existentes. Sem nova fonte, nova fórmula, ativação de release ou implantação na beta.
- Complementa a ADR-0039, substituindo a composição truncada e o ranking anual fixo na interface por consultas já disponíveis em `/contas/table`.

## Entrada por bloco

O Início mostra apenas as duas portas. “Ver indicadores” abre abaixo o catálogo correspondente, sem navegar ao painel. As Estatísticas mantêm busca, temas e prévia. Contas públicas oferece o indicador de Recursos transferidos, único painel implementado; não anuncia as lentes B/C como novos painéis. A ficha continua apresentando A/B separadas. Ambos os cartões usam o azul primário.

A escolha do catálogo é estado local da página, sem cookie ou seletor de lente global. Os filtros dos painéis continuam nas URLs existentes; o seletor do cabeçalho preserva seus links diretos.

## Contexto dos valores

- Total enviado e tipos: `/contas/table?lens=A&group_by=transfer_type`, com `filter=function:<código>` quando houver área. Total usa `value_total`, sem somar linhas no navegador.
- Todas as áreas: paginação de `/contas/table?lens=A&group_by=function`, sem filtro de área. A lista serve para trocar o filtro, e seu contexto é explícito. Código, rótulo, valor e participação vêm da API. Só a largura das barras é normalizada para desenho.
- Recebedores: mesma rota com `group_by=recipient`, período e área selecionados. Mantém exclusões da API, nomes sem documentos, paginação e retorno da ficha. A interface informa o teto navegável quando `rows_total` supera `pages × page_size`.
- Mapa e evolução continuam nos contratos anteriores. Nenhuma associação territorial é inferida.
- Todas as respostas e páginas devem corresponder ao release dos metadados. Divergência, categoria repetida ou lista incompleta interrompem a apresentação; respostas atrasadas não substituem a seleção atual.

Durante a atualização, os cartões e o mapa permanecem montados com o **contexto anterior**, identificado por uma mensagem de atualização e `aria-busy`. O novo contexto e seus valores entram juntos. Uma falha não apresenta os valores antigos como resposta válida.

## Aplicação pelo recebedor

O mantenedor escolheu medir a execução pelo estado/município, e não uma fase da despesa federal. As fontes atualmente integradas não permitem esse cálculo. Dois cartões permanecem visíveis com o estado “Indisponível” e explicação acessível. Ausência não vira zero, não indica recurso não aplicado e não recebe cor de avaliação de desempenho.

Não há barra de aplicado nem percentual estimado. Para habilitá-los, é necessário um contrato específico que identifique fonte, recorte coberto, vínculo com a transferência, estágios da despesa, exercícios/saldos anteriores, contrapartida e denominador comparável. A integração exige reconciliação antes de qualquer publicação.

## Organização visual e acessibilidade

O painel usa a moldura do Painel das Estatísticas: a mesma barra lateral (indicador atual, filtros e limpeza no pé), a mesma área central com rolagem própria, o mesmo mapa (legenda, dica e trilha do recorte sobrepostas) e a mesma faixa de fonte, com notas, proveniência e dicionários em “Notas e proveniência”. Cinco blocos: cartões; mapa; tipos/áreas; evolução; recebedores. Os cartões são baixos e ocupam toda a faixa superior. A partir de 1600 px, como nas Estatísticas, tudo cabe na altura da janela, em duas colunas iguais: o mapa sobre a evolução e a distribuição sobre a tabela de recebedores (opção escolhida pelo mantenedor entre duas versões testadas em 26/11/2026). Cada bloco e os cartões de aplicação têm o botão i das Estatísticas: notas de origem, recortes e dicas de uso saem do corpo do bloco e ficam nele. Quando há área selecionada, ela aparece no título do mapa, da evolução e dos recebedores. A tabela de recebedores segue a tabela das Estatísticas: “Calcular % por” (sem % ou total do território), unidade, ordenação pelo cabeçalho feita na API (por valor ou por nome, valendo para todas as páginas; em ordem alfabética a posição fica em branco), subtotal da página e total do recorte. O % vem da API (`share` sobre o total do recorte); o total inclui o que fica fora do ranking e por isso supera a soma das linhas. A linha mostra só o nome do favorecido; sede e classe ficam na ficha. Parcelas positivas abaixo de 0,05% aparecem como “<0,1%”, nunca como zero. Abaixo disso, a área central rola; em telas menores, os blocos se empilham sem esconder conteúdo.

Tipos ficam fixos, separados por divisor neutro. Somente a lista de áreas tem rolagem própria, com cerca de cinco itens visíveis, teclado e todas as categorias disponíveis. O mapa reutiliza o componente das Estatísticas e reserva espaço para legenda e instruções no modo compacto. Ambos os painéis oferecem a limpeza junto aos filtros da barra lateral, mantendo o indicador escolhido nas Estatísticas.

## Validação

Tipos/lint/Vitest; navegador no build de produção; consulta real área × tipo; recebedores filtrados; ausência de desmontagem durante resposta atrasada; troca rápida de seleção; limpeza; 503 isolado; identificação do release; teclado, axe e claro/escuro; capturas de 390, 1440, 1920 e 2560 px. Evidências e limites no relatório operacional da revisão.

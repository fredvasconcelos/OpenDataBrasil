# Padrões visuais do portal

O portal preserva a identidade do Open Data Brasil. O Design System GOV.BR é
referência para grade, hierarquia e densidade de controles:
<https://www.gov.br/ds/home>.

## Layout

As páginas de catálogo têm contêiner máximo de 1.600 px, com margens responsivas.
Parágrafos de introdução mantêm largura de leitura independente. A grade de temas
usa quatro colunas em desktop largo, três em desktop intermediário, duas em tablet
e uma no celular. O Painel usa uma grade própria, com rolagem quando a altura é
insuficiente. A altura medida da faixa de aviso participa do cálculo do painel.

A página de Métricas mantém o mapa em cartão e três rankings de igual altura ao
lado, com intervalos de 24 px e bases alinhadas. Listas extensas rolam dentro dos
cartões. Abaixo de 1.051 px, os blocos são empilhados com altura natural.

## Controles e temas

Tokens em `apps/portal/src/styles/tokens.css` definem cores, espaços e controles.
As famílias são compacta (32 px), padrão (40 px) e toque (44 px nas ações
principais). Botões de ícone centralizam o desenho; ações com texto podem quebrar
linha. Pontos do mapa preservam dimensões próprias da visualização geográfica.

Cores de texto, superfície, foco e estados usam tokens semânticos nos modos claro
e escuro. A seleção não depende somente de cor. Preservar rótulos acessíveis,
ordem de foco, fechamento por Escape e retorno ao controle que abriu uma janela.

## Conferência

Os testes de revisão visual cobrem cinco páginas, seis larguras de 320 a 1.920 px,
os dois temas, escalas equivalentes a 125%, 150% e 200%, exportação e recuperação
pontual. As escalas são simuladas por viewport e densidade de pixels no Chromium;
não constituem certificação WCAG ou prova em Safari/aparelhos físicos.

Capturas antes/depois devem usar release e dados estáveis. Dados simulados de
Métricas são respostas locais de teste e não devem ser gravados no banco ativo.

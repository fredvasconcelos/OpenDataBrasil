# Plano D — índice leve, recortes e exportação

Implementação autorizada pelo mantenedor em 19/11/2026. A D0 já está integrada.
Este documento especifica a D6 no design system existente, preservando os cálculos
das ADRs 0024 e 0026 e os metadados completos do indicador aberto.

## Escolha de indicador (D1)

O painel recebe o índice leve e o KPI aberto. Na troca, mostra o carregamento e
oferece nova tentativa se houver erro. Mouse e foco antecipam somente os metadados
da opção apontada. O cache pertence ao release do índice; mudança de release pede
a atualização do painel. URL inválida continua escolhendo o primeiro KPI publicado.

## Recorte municipal (D6)

O mapa mantém a trilha Brasil › região › UF. O clique seleciona o território e
preserva a leitura do seu valor. Quando uma UF selecionada oferece municípios,
aparece o botão “Ver municípios de {estado}”. Um seletor de UF permite a mesma
operação por teclado e toque. A visão nacional por município continua disponível
por ação explícita. Os nomes e códigos vêm da geografia do release, sem listas
inventadas. O recorte fica em `foco=uf:NN`, compartilhado por mapa, tabela e arquivo.

## Detalhes do mapa (D6)

Os tooltips de região/UF são carregados juntos por nível; municípios, somente no
recorte de uma UF. Uma leitura das observações alimenta todos os detalhes e usa o
mesmo montador da rota individual, preservando ausências, sigilo e percentuais.
O ponteiro apenas escolhe o detalhe já recebido. A visão municipal nacional mantém
a rota individual para evitar baixar todos os detalhes do país. Resposta truncada
nunca é apresentada como completa. Mudanças nos filtros invalidam o lote anterior.

## Janela de exportação (D6)

Preserva formato, níveis, grãos e dimensões. Acrescenta UF (ou Brasil inteiro) e
períodos por grão, inicialmente seguindo a seleção do painel quando compatível.
Vários grãos possuem seleções separadas; períodos não são ignorados silenciosamente.
A estimativa usa os territórios do recorte no release e a seleção de períodos.
Como a cobertura do KPI pode ser esparsa, a estimativa não substitui a decisão do
servidor. Acima do limite, a mensagem orienta reduzir o recorte ou solicitar o
extrato completo pelo contato do portal. O teto padrão passa a 10 mil somente após
validar essa janela; os dois LSPA conservam a exceção posterior de 200 mil.

## Verificação

Contrato aditivo, equivalência dos detalhes individuais e em lote, filtros de
períodos em exportações com vários níveis/grãos, ausência de novos pedidos ao mover
o ponteiro, URLs/voltar/avançar, teclado/toque, desktop/celular e capturas. A D1 exige
HTML do painel abaixo de 300 KB sem compressão. Réplicas são condicionais à medição;
nenhuma implantação ou configuração externa decorre desta implementação local.

# Manutenção e indisponibilidade do portal

O Caddy serve as páginas estáticas de `infrastructure/vitrine/maintenance/` sem
carregar Next.js, API, fontes externas ou JavaScript. A imagem fixada no Compose
continua sendo a fonte da versão do proxy.

## Modo manual

No diretório da Vitrine, execute o script local instalado junto ao Compose:

```bash
bash maintenance.sh status
bash maintenance.sh on
bash maintenance.sh off
```

No checkout, o caminho é `infrastructure/vitrine/maintenance.sh`. O script não
acessa a rede, não reinicia serviços e não altera dados. `on` cria atomicamente
`maintenance/enabled`; `off` remove somente esse marcador. A mudança vale na
requisição seguinte. O marcador não é versionado nem distribuído no deploy;
uma implantação preserva uma manutenção já ativa.

Navegações HTML recebem **503**, `Cache-Control: no-store` e a página
“Manutenção em andamento”. API, downloads, arquivos do Next.js e requisições
RSC recebem JSON 503, nunca um arquivo HTML com aparência de download concluído.
O tique interno `/_odb/tick` continua respondendo 204 para preservar a rotação
dos logs. Não se informa `Retry-After` sem uma previsão real de retorno.

## Falhas automáticas e retorno

Falhas de conexão com o portal e respostas 502/503/504 do upstream recebem
“Portal temporariamente indisponível” para navegações HTML. Clientes de dados
recebem JSON 503. Não existe recarregamento automático da página estática:
a tentativa é manual, para não aumentar a carga durante um incidente.

Se apenas uma consulta falhar, o painel mostra a falha naquela área e permite
“Tentar de novo”; a página inteira não é suspensa. O Caddy não toma decisões
por número de visitantes. Após a recuperação do serviço e com o modo manual
desligado, a próxima requisição volta ao portal normal, sem reiniciar o proxy.
Uma navegação RSC que falhe pode exigir recarregar a página no navegador para
mostrar a página estática completa.

A proteção depende do Caddy e da máquina funcionando. Queda total da máquina
ou do proxy demanda uma página na borda; isso não é fornecido por este mecanismo.

## Conferência local

```bash
python3 -I tests/vitrine/check_maintenance.py
bash infrastructure/scripts/caddy_log_check.sh
```

O primeiro comando cria uma rede e dois contêineres descartáveis, com porta HTTP
publicada apenas no loopback. Verifica operação normal, manutenção manual, HTML,
RSC, JSON, download, cache, falha do upstream, queda do portal e recuperação.
Não utiliza banco, dados ou configuração de produção. O segundo confere que o
log mantém a privacidade exigida na ADR-0027. Ambos encerram seus temporários.

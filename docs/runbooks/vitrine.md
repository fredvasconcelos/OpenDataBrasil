# Runbook: operar uma Vitrine

A [ADR-0025](../adr/0025-plataforma-propria-fabrica-e-vitrine.md) separa a Fábrica,
que processa e valida, da Vitrine, que serve releases aprovados. Este guia é genérico:
endereços, rede autorizada, chaves, tokens e credenciais pertencem ao operador.
Não devem ser versionados.

## Provisionamento

Em um servidor Ubuntu 24.04, instale sua chave pública e confira a impressão digital
pelo console. O script de provisionamento exige `LAN_CIDR` com a rede autorizada.
`ODB_USER`, `DATA_ROOT` e `ODB_HOME` podem ajustar usuário e armazenamento. Leia o
script antes de executá-lo com privilégios administrativos. Ele altera SSH,
firewall, atualizações e Docker; confirme seu acesso antes de recarregar serviços.

```bash
sudo env LAN_CIDR='<rede-autorizada>' bash bootstrap-ubuntu.sh
```

## Implantação

Defina `ODB_VITRINE_HOST` com um destino SSH configurado por você e `ODB_VITRINE_IP`
com o endereço da interface do servidor. Use autenticação normal por chave, validando
a identidade do destino. A Fábrica deve ter Docker, SSH e rsync.

```bash
export ODB_VITRINE_HOST='<destino-ssh>'
export ODB_VITRINE_IP='<ip-da-vitrine>'
docker compose --profile web build api portal
bash infrastructure/vitrine/deploy.sh
```

O modo `--sem-dados` envia somente código/configuração. Só o use quando os indicadores
e o contrato do código forem compatíveis com o release já servido. Para nova publicação,
valide a Gold e o manifesto antes de executar uma implantação com dados. A transferência
mantém uma versão anterior da Gold e só troca o diretório depois da conferência.

O diretório `/srv/odb/app` contém Compose, Caddyfile, observabilidade e a configuração
local. Gold e backups ficam em `/srv/odb`. Planeje espaço e cópias externas antes de
implantar. O volume Gold é somente leitura para a API; Bronze e Silver não são enviados.
Confira respostas com o destino informado explicitamente:

```bash
python3 -I tests/vitrine/compare_responses.py --vitrine 'https://vitrine.example'
```

O endereço acima é de documentação: substitua-o por sua instalação.

## Releases e recuperação

A API usa o manifesto de publicação do catálogo. Use `odb release list` e
`odb release rollback <release_id> --motivo '<motivo>'` com o papel de operação
configurado no seu ambiente. O rollback confere as versões Delta antes de ativar.
Consulte os runbooks de [Gold](gold.md), [backup](backup.md) e [atualização](atualizacao.md).
Restaurar catálogo ou trocar diretórios da Gold exige backup e conferência prévia.

## Métricas de acesso

A [ADR-0027](../adr/0027-coleta-de-metricas-de-acesso.md) descreve a coleta sem IP ou
cookie. O banco `odb_metrics` é separado do catálogo: é o dado que nasce na Vitrine,
portanto precisa de backup próprio. `backup-metrics.sh` preserva cópias no servidor
e na Fábrica; exige `ODB_VITRINE_HOST`. O log bruto tem retenção curta e não contém IP.

Os nomes de países de `countries.py` vêm de `Intl.DisplayNames` na imagem Node fixada
no projeto, com ICU/CLDR da matriz de compatibilidade. Não derivam da localização de
um visitante nem de um serviço de geolocalização.

## Proxy, limites e observabilidade

Grafana, Jaeger e Prometheus ficam acessíveis somente pela interface local do servidor;
configure seus próprios túneis SSH. Credenciais dos painéis ficam na configuração local.
Não exponha essas interfaces diretamente na internet.

A API aceita cabeçalhos de cliente apenas dos proxies confiáveis. Ao usar um provedor
na borda, configure as faixas e a remoção de cabeçalhos sensíveis conforme a ADR-0027.
O conector de túnel fixo recebe o token por variável de ambiente. O conector temporário
é opcional e seu endereço vem dos logs; não exponha o token nem registre esses endereços
no código. A marcação de homologação e o bloqueio de indexação não substituem autenticação.

Os limites de requisição e o cache são parâmetros da instalação. Para teste de carga,
informe `BASE` nos cenários k6 e restaure os limites ao terminar. O coletor
`amostrar.sh` exige o destino SSH em `ODB_VITRINE_HOST`; `patamares.py` recebe a URL
do Prometheus por `--prom`. Nunca execute carga em uma fonte oficial de dados.

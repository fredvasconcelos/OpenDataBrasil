#!/usr/bin/env bash
# Provisionamento da Vitrine (Open Data Brasil) em Ubuntu Server 24.04.
#
# Uso, no servidor:  sudo bash bootstrap-ubuntu.sh
#
# Idempotente: pode ser rodado de novo sem estragar nada. Faz:
#   1. atualizações do sistema e atualizações automáticas de segurança;
#   2. SSH só com chave (sem senha e sem root), validado antes de recarregar;
#   3. firewall (ufw): entrada negada, SSH só a partir da rede local;
#   4. fail2ban no SSH;
#   5. notebook sempre ligado (tampa fechada não suspende);
#   6. Docker Engine do repositório oficial, com dados em $DATA_ROOT;
#   7. diretórios do projeto em $ODB_HOME (ligados em /srv/odb).
#
# LAN_CIDR é obrigatória. ODB_USER, DATA_ROOT e ODB_HOME são opcionais.
set -euo pipefail

ODB_USER="${ODB_USER:-${SUDO_USER:-ubuntu}}"
LAN_CIDR="${LAN_CIDR:?defina a rede autorizada em LAN_CIDR}"
DATA_ROOT="${DATA_ROOT:-/home/docker}"   # escolha uma partição com espaço para os volumes
ODB_HOME="${ODB_HOME:-/home/odb}"

passo() { printf '\n==> %s\n' "$*"; }
falha() { printf '\nERRO: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || falha "rode com sudo: sudo bash $0"
. /etc/os-release
[ "${VERSION_ID:-}" = "24.04" ] || falha "feito para Ubuntu 24.04 (encontrado: ${PRETTY_NAME:-?})"
id "$ODB_USER" >/dev/null 2>&1 || falha "usuário $ODB_USER não existe"

# Antes de desligar a senha, garante que há chave instalada (senão o acesso se perde).
AUTH_KEYS="$(getent passwd "$ODB_USER" | cut -d: -f6)/.ssh/authorized_keys"
grep -qE '^(ssh-ed25519|ssh-rsa|ecdsa-sha2)' "$AUTH_KEYS" 2>/dev/null \
  || falha "nenhuma chave em $AUTH_KEYS; instale com ssh-copy-id antes"

passo "1/7 Atualizando o sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get -y -q full-upgrade
apt-get -y -q install ca-certificates curl gnupg ufw fail2ban unattended-upgrades \
  rsync jq htop zstd

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
# Reinício automático só quando uma atualização de segurança exigir, de madrugada (UTC).
cat > /etc/apt/apt.conf.d/52odb-unattended <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:30";
EOF

passo "2/7 SSH só com chave"
# Os arquivos de sshd_config.d são lidos em ordem e o primeiro valor vale: 10-odb vem
# antes do 50-cloud-init (que pode ligar a senha).
cat > /etc/ssh/sshd_config.d/10-odb.conf <<EOF
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
AllowUsers $ODB_USER
MaxAuthTries 3
X11Forwarding no
# Sem MACs com SHA-1 nem UMAC de 64 bits (apontados pelo nuclei na V6).
MACs -hmac-sha1,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-64-etm@openssh.com
EOF
sshd -t || falha "configuração do SSH inválida; nada foi recarregado"
systemctl reload ssh

passo "3/7 Firewall (ufw)"
ufw --force default deny incoming
ufw --force default allow outgoing
ufw allow from "$LAN_CIDR" to any port 22 proto tcp comment 'SSH da rede local'
ufw allow from "$LAN_CIDR" to any port 80 proto tcp comment 'Vitrine na rede local'
ufw --force enable
# Atenção: portas publicadas pelo Docker não passam pelo ufw. O compose da Vitrine só
# publica no IP da rede local (nada é aberto no roteador; a internet chega pelo túnel).

passo "4/7 fail2ban no SSH"
cat > /etc/fail2ban/jail.d/odb-sshd.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban

passo "5/7 Notebook sempre ligado"
mkdir -p /etc/systemd/logind.conf.d
cat > /etc/systemd/logind.conf.d/10-odb.conf <<'EOF'
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
EOF
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null
systemctl restart systemd-logind

passo "6/7 Docker Engine (repositório oficial)"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
fi
mkdir -p /etc/docker "$DATA_ROOT"
cat > /etc/docker/daemon.json <<EOF
{
  "data-root": "$DATA_ROOT",
  "log-driver": "local",
  "log-opts": { "max-size": "20m", "max-file": "5" },
  "live-restore": true
}
EOF
apt-get -y -q install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker >/dev/null
systemctl restart docker
# O grupo docker equivale a root na máquina: só o usuário de operação entra nele.
usermod -aG docker "$ODB_USER"

passo "7/7 Diretórios do projeto"
install -d -o "$ODB_USER" -g "$ODB_USER" -m 0750 \
  "$ODB_HOME" "$ODB_HOME/app" "$ODB_HOME/gold" "$ODB_HOME/backups" "$ODB_HOME/logs" "$ODB_HOME/releases"
ln -sfn "$ODB_HOME" /srv/odb

passo "Resumo"
echo "SSH:      $(sshd -T 2>/dev/null | grep -E '^(passwordauthentication|permitrootlogin) ' | tr '\n' ' ')"
echo "Firewall: $(ufw status | head -1)"
echo "Docker:   $(docker --version) | dados em $(docker info -f '{{.DockerRootDir}}')"
echo "Projeto:  /srv/odb -> $ODB_HOME"
echo "Disco:    $(df -h "$ODB_HOME" | awk 'NR==2{print $4" livres em "$6}')"
echo
echo "Pronto. Saia e entre de novo no SSH para o grupo docker valer para $ODB_USER."

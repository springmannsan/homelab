#!/bin/bash

# Exit on any failure
set -euo pipefail

err() {
    echo "ERROR: $*" >&2; exit 1;
}
#info function
info() {
    echo "INFO: $*"; 
}

#set environmental variables for the root profile
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

#check root user id
if [ "$(id -u)" -ne 0 ]; then
    err "This script must be run as root (sudo)"
fi

#apt update and upgrade
apt-get update && apt-get -y upgrade
# samba install and setup

mkdir -p /srv/data/share
chown $USER /srv/data/share
chmod 750 /srv/data/share

apt-get -y install samba
# echo "[$SHARE_NAME]" >> /etc/samba/smb.conf
# echo "  comment = Samaba on Ubuntu" >> /etc/samba/smb.conf
# echo "  path = /srv/data/share" >> /etc/samba/smb.conf
# echo "  read only = no" >> /etc/samba/smb.conf
# echo "  browsable = yes" >> /etc/samba/smb.conf
share_block="
[$SHARE_NAME]
    comment = Homeshare
    path = /srv/data/share
    read only = no
    browsable = yes
"

if ! grep -q "^\[$SHARE_NAME\]$" /etc/samba/smb.conf; then
    echo "$share_block" >> /etc/samba/smb.conf
fi


service smbd restart
ufw allow samba

echo "Provide SMB password for $SAMBA_USER:" 
smbpasswd -a $SAMBA_USER

# backup script

mkdir -p /srv/data/backups
chown root /srv/data/backups
chmod 750 /srv/data/backups

mkdir -p /etc/backup
chmod 750 /etc/backup

mkdir -p /var/log/backup
chmod 750 /var/log/backup

apt-get -y install python3-pip
pip3 install -r requirements.txt --break-system-packages
chown root ./backup.py
chmod 750 ./backup.py
cp ./backup.directories.conf /etc/backup/backup.directories.conf
echo "0 4 * * * root /usr/bin/python3 /provision/homelab/backup.py >> /var/log/backup/backup.log" >> /etc/crontab

################################ tailscale

curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --auth-key=$TAILSCALE_AUTH_KEY

################################# docker 

# Add Docker's official GPG key:
apt install ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt update

#install
apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl start docker

#start containers
chmod 600 ./cert/acme.json
docker compose up -d


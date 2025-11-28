#!/bin/bash

#setting up basic variables
user=$(tail -n 1 /etc/passwd | cut -d: -f1)
network_share_name="homeshare"
hostname="springmannsan.me"

# basic configurations
mkdir /scripts
chmod 750 /scripts

mkdir /srv/data
chown $user /srv/data
chmod 750 /srv/data

#apt update and upgrade
apt-get update
apt-get -y upgrade

# samba install and setup

apt-get -y install samba
echo "[$network_share_name]" >> /etc/samba/smb.conf
echo "  comment = Samaba on Ubuntu" >> /etc/samba/smb.conf
echo "  path = /srv/data" >> /etc/samba/smb.conf
echo "  read only = no" >> /etc/samba/smb.conf
echo "  browsable = yes" >> /etc/samba/smb.conf

service smbd restart
ufw allow samba

echo "Provide SMB password for user: $user"
smbpasswd -a $user

# backup script

cp ./scripts/backup.py /scripts
chown root /scripts/backup.py
chmod 750 /scripts/backup.py
echo "0 4 * * * root /usr/bin/python3 /scripts/backup.py" >> /etc/crontab

#docker

#setup docker apt repository
#https://docs.docker.com/engine/install/ubuntu/

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

#post installation steps
usermod -aG docker $user

#traefik
mkdir ./traefik/certs
chmod 750 ./traefik/certs

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./traefik/certs/local.key -out ./traefik/certs/local.crt \
  -subj "/CN=*.$hostname"

HOSTNAME=$hostname docker compose -f ./traefik/docker-compose.yaml up -d

#portainer
HOSTNAME=$hostname docker compose -f ./portainer/docker-compose.yaml up -d

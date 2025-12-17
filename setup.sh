#!/bin/bash

source .env

# basic configurations
mkdir /srv/data
chown $USER /srv/data
chmod 750 /srv/data

mkdir /srv/data/share
chown $USER /srv/data/share
chmod 750 /srv/data/share

mkdir /srv/data/backups
chown root /srv/data/backups
chmod 750 /srv/data/backups

#apt update and upgrade
apt-get update
apt-get -y upgrade

# samba install and setup
apt-get -y install samba
echo "[$SHARE_NAME]" >> /etc/samba/smb.conf
echo "  comment = Samaba on Ubuntu" >> /etc/samba/smb.conf
echo "  path = /srv/data/share" >> /etc/samba/smb.conf
echo "  read only = no" >> /etc/samba/smb.conf
echo "  browsable = yes" >> /etc/samba/smb.conf

service smbd restart
ufw allow samba

echo "Provide SMB password for $USER:" 
smbpasswd -a $USER

# backup script
apt-get -y install python3-pip
pip3 install -r requirements.txt --break-system-packages
chown root ./backup.py
chmod 750 ./backup.py
echo "0 4 * * * root cd /provision/homelab && /usr/bin/python3 ./backup.py >> ./backup.log" >> /etc/crontab

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

#post installation steps
usermod -aG docker $USER

#start containers
chmod 600 ./cert/acme.json
docker compose up -d


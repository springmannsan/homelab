#!/bin/bash
echo "Starting setup script....."

#setting up basic variables
user = tail -n 1 /etc/passwd | cut -d: -f1
echo "User $user found. Working with this user"

# basic configurations

echo "Creating folders...."

mkdir /srv/data
chown user /srv/data
chmod 750 /srv/data

mkdir /srv/configs
chown user /srv/configs
chmod 750 /srv/data

mkdir /scripts
chown root /scripts
chmod 750 /scripts

#apt update and upgrade

echo "Updating repositories...."
apt-get update 
echo "Repos updated"
echo "Upgrading..."
apt-get -y upgrade
echo "Upgraded..."

# samba install and setup

echo "Installing samba...."
apt-get -y install samba
echo "Samba installed..."
echo "  [datashare]" >> /etc/samba/smb.conf
echo "  comment = Samaba on Ubuntu" >> /etc/samba/smb.conf
echo "  path = /srv/data" >> /etc/samba/smb.conf
echo "  read only = no" >> /etc/samba/smb.conf
echo "  browsable = yes" >> /etc/samba/smb.conf

service smbd restart
ufw allow samba

echo "Provide SMB password for user: $user"
smbpasswd -a $user
echo "Password set!"

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
apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl start docker

#post installation steps
groupadd docker
usermod -aG docker $user
newgrp docker

#done 
echo "OK"
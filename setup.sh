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

mkdir /scripts
chown root /scripts
chmod 750 /scripts

mkdir ./certs
chown root ./certs
chmod 750 ./certs

echo "Folders created"

#apt update and upgrade

echo "Updating repositories...."
apt-get update >> log.out
echo "Repos updated"
echo "Upgrading..."
apt-get -y upgrade >> log.out
echo "Upgraded"

# samba install and setup

echo "Installing samba...."
apt-get -y install samba >> log.out
echo "Samba installed..."
echo "[datashare]" >> /etc/samba/smb.conf
echo "  comment = Samaba on Ubuntu" >> /etc/samba/smb.conf
echo "  path = /srv/data" >> /etc/samba/smb.conf
echo "  read only = no" >> /etc/samba/smb.conf
echo "  browsable = yes" >> /etc/samba/smb.conf

service smbd restart
ufw allow samba

echo "Provide SMB password for user: $user"
smbpasswd -a $user
echo "Password set!"
echo "Samba installed"

# backup script

echo "Creating backup job...."

cp ./scripts/backup.py /scripts
chown root /scripts/backup.py
chmod 750 /scripts/backup.py
echo "0 4 * * * root /usr/bin/python3 /scripts/backup.py" >> /etc/crontab

echo "Backup job created"

#docker

echo "Installing docker..."

#setup docker apt repository
#https://docs.docker.com/engine/install/ubuntu/

# Add Docker's official GPG key:
apt install ca-certificates curl >> log.out
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

apt update >> log.out

#install
apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >> log.out
systemctl start docker

#post installation steps
echo $user
usermod -aG docker $user

echo "Docker installed"

#portainer
echo "Starting portainer..."
docker volume create portainer_data
docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/srv/data/portainer_data portainer/portainer-ce:lts
echo "Portainer started"

#self signed cert for traefik
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./certs/local.key -out ./certs/local.crt \
  -subj "/CN=*.teszt"

docker compose -f ./traefik/docker-compose.yaml up -d






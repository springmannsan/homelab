#!/bin/bash
echo "Starting setup script....."

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

#get user
user = tail -n 1 /etc/passwd | cut -d: -f1
echo "User $user found. Provide password for this user"

echo "Provide SMB password for user: $user"
smbpasswd -a $user
echo "Password set!"

# backup script
cp ./scripts/backup.py /scripts
chown root /scripts/backup.py
chmod 750 /scripts/backup.py
echo "0 4 * * * root /usr/bin/python3" >> /etc/crontab

#done 
echo "OK"
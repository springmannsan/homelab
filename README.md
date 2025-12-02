mkdir /provision
cd /provision
git clone https://github.com/springmannsan/homelab.git
cd homelab
nano .env
chmod 700 setup.sh
./setup.sh
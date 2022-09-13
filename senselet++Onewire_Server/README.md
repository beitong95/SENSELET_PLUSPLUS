# Senselet++ Server Setup

## install docker
Please follow instructions from the docker website

## setup influxdb with persistent storage
```bash
# ATTENTION that "$PWD" is host directory to store PERSISTED container data (when InfluxDB crashes, data still reside here. In that situation, just run this command again to recover data from old instance), this could be changed to any directory you want.
sudo docker run -d -p 8086:8086 -v $PWD:/var/lib/influxdb influxdb:1.8
```
## setup grafana with persistent storage
```bash
# create a persistent volume for your data in /var/lib/grafana (database and plugins)
docker volume create grafana-storage
# start grafana
docker run -d -p 3000:3000 --name=grafana -v grafana-storage:/var/lib/grafana grafana/grafana-enterprise
```
## install message broker and its python library
```bash
sudo apt-get install mosquitto \
sudo apt-get install mosquitto-clients \
sudo pip3 install paho-mqtt
sudo pip3 install influxdb
```

# Then ports 3000 (Grafana), 1883 (message broker), and 8086 have to be exposed to outside
```bash
sudo ufw allow 3000 \
sudo ufw allow 1883 \
sudo ufw allow 8086
```

# get source code
```bash
cd $HOME
git clone *this repo*
```

# run python script
```bash
# run in the background1
ssh -p 22 username@ip
screen (enter screen, if you don't have screen on your server, install it)
python3 -u writer.py 2>&1 | tee -i log.txt
Ctrl+A Ctrl+D (exit screen)
Ctrl+D
```

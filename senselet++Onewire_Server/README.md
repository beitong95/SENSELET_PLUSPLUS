# Senselet

# ATTENTION that "$PWD" is host directory to store PERSISTED container data (when InfluxDB crashes, data still reside here. In that situation, just run this command again to recover data from old instance), this could be changed to any directory you want.
# setup influxdb
# update 2020-11-01 currently influxdb is automatically upgrade to version 1.8.3
# some libs is not avaliable
# we can also add -d here to run the influxdb in the background
sudo docker run -p 8086:8086 -v $PWD:/var/lib/influxdb influxdb

# setup grafana
# 2020-11-01 work
sudo docker run -d -p 3000:3000 grafana/grafana

# install message broker and its python library
# 2020-11-01 add sudo pip3 install influxdb
sudo apt-get install mosquitto \
sudo apt-get install mosquitto-clients \
sudo pip3 install paho-mqtt
sudo pip3 install influxdb

# Then ports 3000 (Grafana), 1883 (message broker), and 8086 have to be exposed to outside
# eg.
sudo ufw allow 3000 \
sudo ufw allow 1883 \
sudo ufw allow 8086

# run python script
# 2020-11-01
#run in the background
unhop python3 writer > /dev/null 2>&1 &
# or run in the foreground
python3 writer.py

# 2020-11-01
# change writer.py to adapt the new influxdb


#TODO
1. add fail detector 
2. add a database to update the sensorMetaData.py

import paho.mqtt.client as paho
import requests
import time
import sys
import os

def on_publish(client,userdata,result):
    pass

# config mqtt
broker="xxx.xxx.xxx.xxx"
port=1883
virtualSensor_id = 1
client = paho.Client("xxx" + str(virtualSensor_id)) # mqtt client id
client.on_publish = on_publish
client.connect(broker,port)
client.loop_start()

#config virtual sensor
vsensor_id = "xxxxx_sensor_1"

# open weather
openweather_api_key = "xxxxxxx"
mntl_lat = "xxxx"
mntl_lon = "xxxx"

def get_temp_humidity(lat, lon):
	r = requests.get("http://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&appid={}".format(lat,lon,openweather_api_key))		
	if r.status_code == 200:
		current_Data = r.json()
		temp = round(current_Data["main"]["temp"] - 273.15, 2)# convert k to c
		humidity = round(current_Data["main"]["humidity"],2)
		# add rain and snow 04162021
		if "rain" in current_Data.keys():
			rain = round(current_Data["rain"]["1h"], 2)
		else: 
			rain = 0.0
		if "snow" in current_Data.keys():
			snow = round(current_Data["snow"]["1h"], 2)
		else: 
			snow = 0.0
		# add pressure
		pressure = round(current_Data["main"]["pressure"],2)
	try:
		ret = client.publish("senselet/" + vsensor_id, str(time.time()) + '_' + str(temp) + '_' + str(humidity) + '_' + str(rain) + '_' + str(snow) + '_' + str(pressure))
		print("senselet/" + vsensor_id + " " + str(time.time()) + '_' + str(temp) + '_' + str(humidity)+ '_' + str(rain) + '_' + str(snow) + '_' + str(pressure))
	except Exception as e:
		print(str(e))	
def main():
	while True:
		get_temp_humidity(mntl_lat, mntl_lon)
		time.sleep(5)
	

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)



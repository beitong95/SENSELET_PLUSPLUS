import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient
from datetime import datetime
from threading import Timer
from collections import defaultdict
import sys
import pytz
import os
from sensorMetaData import sensorMetaData

# keep track the status of the door
doorStatus = {}
waterLeakageStatus = {}
latency_list = []
batched_points = []

def on_publish(client, userdata, result):
	print("TIMEOUT PUBLISHED!")

def on_connect(client, userdata, flags, rc):
	print("Connected with result code "+str(rc))
	client.subscribe("senselet/#")

def on_message(client, userdata, msg):
	global batched_points
	topic = msg.topic

	message = (msg.payload).decode('ascii')

	# initialize the data point 
	points = []
	point  = {}

	# extract sensor id from the message
	id = topic.split('/')[1]

	# first check if the sensor id is registered
	# if the sensor is not registered, we will print error message and skip this message
	if id not in sensorMetaData and 'control' not in id and 'Wireless' not in id and 'network' not in id:
		print("Register data inconsistent. Please check the metadatafile on the server side")
		return
	
	# store sensor id in tags
	point['tags']   = {'sensor': id}

	# extract and store time info 
	tt =   float(message.split('_')[0])
	print(topic+" "+message) # print the received message to stdout

	# extract and store sensory information
	if 'Wireless' in id:
		# wireless sensor
		information = message.split('_')
		if len(information) == 3:
			if information[1] == '1' or information[1] == '0':
				wirelessDoorStatus = float(information[1])
				battery = float(information[2])
				point['measurement'] = 'wirelessSensor'
				point['fields'] = {'doorStatus': wirelessDoorStatus, 'battery':battery}
				point['time']   = datetime.fromtimestamp(tt, pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
			elif information[1].isdigit():
				magnetic = int(information[1])
				battery = float(information[2])
				point['measurement'] = 'wirelessSensor'
				point['fields'] = {'magnetic': magnetic, 'battery':battery}
				point['time'] = int(tt)
				batched_points.append(point)
				if len(batched_points) >= 50:
					influx.write_points(batched_points, time_precision='u')
					batched_points = []
				return 
			else:
				return
	elif 'network' in id:
		point['time']   = datetime.fromtimestamp(tt, pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
		information = message.split('_')
		if len(information) == 2:
			LINK = float(information[1])
			point['measurement'] = 'wifi_measurement_new'
			point['fields'] = {'LINK': LINK}
		
	elif 'control' in id:
		point['time']   = datetime.fromtimestamp(tt, pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
		information = message.split('_')
		if len(information) == 7:
			APMAC = information[1]
			APTXBW = float(information[2])
			APRXBW = float(information[3])
			APRSSI = int(information[4])
			APTX = float(information[5])
			if information[6] == 'no':
				APRX = float(0)
			else:		
				APRX = float(information[6])
			point['measurement'] = 'wifi_measurement'
			point['fields'] = {'APMAC': APMAC, 'APTXBW': APTXBW, 'APRXBW': APRXBW, 'APRSSI': APRSSI, 'APTX': APTX, 'APRX': APRX}
		else:
			APMAC = information[1]
			APRSSI = int(information[2])
			APTX = float(information[3])
			APRX = float(information[4])
			point['measurement'] = 'wifi_measurement'
			point['fields'] = {'APMAC': APMAC, 'APRSSI': APRSSI, 'APTX': APTX, 'APRX': APRX}
	else: 
		point['time']   = datetime.fromtimestamp(tt, pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
		if sensorMetaData[id]['name'] == "sht85":
			temp = float(message.split('_')[1])
			humi = float(message.split('_')[2])
			point['measurement'] = 'temp_humi_measurement'
			point['fields'] = {'temperature': temp, 'humidity': humi}

		elif sensorMetaData[id]['name'] == "mlx90614":
			surfaceTemp = float(message.split('_')[1])
			point['measurement'] = 'surface_temp_measurement'
			point['fields'] = {'temperature': surfaceTemp}

		# 03112021 optimize door and water leakage sensor
		elif sensorMetaData[id]['name'] == "waterLeakageRope":
			# 1 is leaking; 0 is not leaking 
			isWaterLeaking = float(message.split('_')[1])
			if id in waterLeakageStatus:
				if isWaterLeaking == 1 or isWaterLeaking != waterLeakageStatus[id]:
					waterLeakageStatus[id] = isWaterLeaking
				else:
					print("skip writing for ", id, ",waterleakage = ", isWaterLeaking)
					return
			else:
				waterLeakageStatus[id] = isWaterLeaking
			point['measurement'] = 'waterLeakage_measurement'
			point['fields'] = {'isWaterLeaking': isWaterLeaking}

		elif sensorMetaData[id]['name'] == "waterLeakagePoint":
			# 1 is leaking; 0 is not leaking 
			isWaterLeaking = float(message.split('_')[1])
			if id in waterLeakageStatus:
				if isWaterLeaking == 1 or isWaterLeaking != waterLeakageStatus[id]:
					waterLeakageStatus[id] = isWaterLeaking
				else:
					print("skip writing for ", id, ",waterleakage = ", isWaterLeaking)
					return
			else:
				waterLeakageStatus[id] = isWaterLeaking
			point['measurement'] = 'waterLeakage_measurement'
			point['fields'] = {'isWaterLeaking': isWaterLeaking}

		elif sensorMetaData[id]['name'] == "oilLeakagePoint":
			# 1 is leaking; 0 is not leaking 
			isOilLeaking = float(message.split('_')[1])
			point['measurement'] = 'oilLeakage_measurement'
			point['fields'] = {'isOilLeaking': isOilLeaking}

		# 03112021 optimize door and water leakage sensor
		elif sensorMetaData[id]['name'] == "doorSensorSmall":
			# 1 is open; 0 is not open 
			isDoorOpen = float(message.split('_')[1])
			if id in doorStatus:
				if isDoorOpen == 1 or isDoorOpen != doorStatus[id]:
					doorStatus[id] = isDoorOpen
				else:
					print("skip writing for ", id, ",doorStatus = ", isDoorOpen)
					return
			else:
				doorStatus[id] = isDoorOpen
			# here we can add vacuum pump door measurement 
			point['measurement'] = 'door_measurement'
			point['fields'] = {'isDoorOpen': isDoorOpen}

		elif sensorMetaData[id]['name'] == "doorSensorLarge":
			# 1 is open; 0 is not open 
			isDoorOpen = float(message.split('_')[1])
			if id in doorStatus:
				if isDoorOpen == 1 or isDoorOpen != doorStatus[id]:
					doorStatus[id] = isDoorOpen
				else:
					print("skip writing for ", id, ",doorStatus = ", isDoorOpen)
					return
			else:
				doorStatus[id] = isDoorOpen
			point['measurement'] = 'door_measurement'
			point['fields'] = {'isDoorOpen': isDoorOpen}

		elif sensorMetaData[id]['name'] == "airFlow":
			# 1 is open; 0 is not open 
			airSpeed = float(message.split('_')[1])
			point['measurement'] = 'airFlow_measurement'
			point['fields'] = {'speed': airSpeed}

		elif sensorMetaData[id]['name'] == "openweather_sensor":
			temp = float(message.split('_')[1])
			humi = float(message.split('_')[2])
			rain = float(message.split('_')[3])
			snow = float(message.split('_')[4])
			pressure = float(message.split('_')[5])
			point['measurement'] = 'temp_humi_measurement'
			point['fields'] = {'temperature': temp, 'humidity': humi, 'rain': rain, 'snow': snow, 'pressure': pressure}

	points.append(point)
	# write it to influxdb
	if len(points) > 0:
	    influx.write_points(points)


def main():

    global channel, influx, watchdogs #, client_w
    influx = InfluxDBClient('localhost', 8086, 'root', 'root', 'senselet')
    dbs = influx.get_list_database()
    db_exists = False
	# check and create senselet database if it does not exist
    for db in dbs:
        if db['name'] == 'senselet':
            db_exists = True
            break
    if not db_exists:
        influx.create_database('senselet')

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", 1883, 60)
    client.loop_forever()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

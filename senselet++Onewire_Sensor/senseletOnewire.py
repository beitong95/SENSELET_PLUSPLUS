import paho.mqtt.client as paho
from sensorMetaData import sensorMetaData
from sht85 import SHT85
from mlx90614 import MLX90614
import os
import time 
import threading
from threading import Lock
from datetime import datetime
import subprocess

# lock for thread print
thread_print_lock = Lock()

# publish or debug
mode="publish"
#mode="debug"


# setup watchdog
fd = open("/dev/watchdog", "w")
print(fd)

# setup mqtt client and mqtt function
def on_publish(client,userdata,result):
    pass
broker="xxx.xxx.xxx.xxx"
port=1883
raspberrypi_id = 1
client = paho.Client("control" + str(raspberrypi_id))
client.on_publish = on_publish
client.connect(broker,port)
client.loop_start()

#global var
stationTXByte_old = 0
stationRXByte_old = 0
time_old = 0

# thread safe print 
def thread_print(a, *b):
    global mode
    # if we are sending the data to the server, we mute the output 
    if mode == "publish":
        return
    with thread_print_lock:
        # print format: time + data
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print("%s: " % current_time, end='')
        print (a % b)

# sensor list
currentSensors = {}
ignore = 'w1_bus_master'

# Sensor Reading Class
# Each physical sensor will have a sensorReading obj
# There is no thread stop in python thread package, so we use stop flag to stop threads
class SensorReading(threading.Thread): 
  
    global client
    global fd
  
    def __init__(self, metaData): 
        threading.Thread.__init__(self) 
        self._stopper = threading.Event() 
        self.metaData = metaData
  
    def stop(self): 
        self._stopper.set() 
  
    def stopped(self): 
        return self._stopper.isSet() 

    def getInterval(self):
        return 1.0/self.metaData["frequency"]

    def getCalibration(self):
        return float(self.metaData["calibration"])

    def getID(self):
        return self.metaData["id"]

    def kickDog(self, ret):
        if ret.rc == 0:
            nb = fd.write("u")
            fd.flush()
            if nb > 0:
                pass
            else:
                thread_print("WATCHDOG ERROR")
        else:
            thread_print("Didn't kick the dog. ret value = %s" % str(ret.rc))

    def sht85_read(self):
        # get frequency
        interval = self.getInterval()
        calibration = self.getCalibration()
        # get id
        id = self.getID()

        while True: 
            if self.stopped(): 
                return
            t,h,c = self.metaData["i2cDevice"].single_shot("HIGH")
            h = h + calibration
            if c == 5:
                #read fail don't publish rare
                thread_print("sensor: %s. Read fail." % (id))
            else:
                # read success 
                # send r, h, id to the server
                thread_print("sensor: %s. Temp: %s. Hum: %s. Attempts: %s" % (id,str(t), str(h), str(c)))
                # publish 
                try:
                    ret = client.publish("senselet/" + id, str(time.time()) + '_' + str(t) + '_' + str(h))
                    self.kickDog(ret)
                except Exception as e:
                    thread_print(str(e))

            # adapt sleep time
            # after using ds2482, actually c will always be zero
            time.sleep(max(0.1, interval - (0.3*c + 0.2)))

    def mlx90614_read(self):
        # get frequency
        interval = self.getInterval()
        # get id
        id = self.getID()

        while True: 
            if self.stopped(): 
                return
            t,c = self.metaData["i2cDevice"].get_obj_temp()
            if c == 5:
                #read fail
                thread_print("sensor: %s. Read fail." % (id))
            else:
                # read success 
                # send r, h, id to the server
                thread_print("sensor: %s. Temp: %s.Attempts: %s" % (id,str(t), str(c)))
                try:
                    ret = client.publish("senselet/" + id, str(time.time()) + '_' + str(t))
                    self.kickDog(ret)
                except Exception as e:
                    thread_print(str(e))
            # adapt sleep time
            # after using ds2482, actually c will always be zero
            time.sleep(max(0.1, interval - 0.1*c))

    def waterLeakageRope_read(self):
        # get frequency
        interval = self.getInterval()
        # get id
        id = self.getID()
        while True: 
            if self.stopped(): 
                return

            # read adc
            path = "/sys/bus/w1/devices/" + id + "/vad"

            c = 0

            for i in range(5):
                try:
                    with  open(path, "r") as f:
                        status = f.read().replace("\n","")
                    break
                except IOError:
                    c = c + 1

            if c == 5 :
                #read fail
                thread_print("sensor: %s. Read fail." % (id))
            else:
                # read success 
                # convert adc reading to discrete status
                if int(status) < 300 and int(status) > 15:
                    status = 1
                else:
                    status = 0
                # send status to the server
                thread_print("sensor: %s. Status: %s. Attempts: %s" % (id,status, str(c)))
                try:
                    ret = client.publish("senselet/" + id, str(time.time()) + '_' + str(status))
                    self.kickDog(ret)
                except Exception as e:
                    thread_print(str(e))
            time.sleep(interval)

    def waterLeakagePoint_read(self):
        # get frequency
        interval = self.getInterval()
        # get id
        id = self.getID()

        while True: 
            if self.stopped(): 
                return
            path = "/sys/bus/w1/devices/" + id + "/state"

            c = 0
            for i in range(5):
                try:
                    with  open(path, "r") as f:
                        status = f.read(1)
                    break
                except IOError:
                    c = c + 1
            if c == 5 :
                #read fail
                thread_print("sensor: %s. Read fail." % (id))
            else:
                # read success 
                # send status to the server
                s = '{0:08b}'.format(ord(status))[1]
                thread_print("sensor: %s. Status: %s. Attempts: %s" % (id, s, str(c)))
                try:
                    ret = client.publish("senselet/" + id, str(time.time()) + '_' + s)
                    self.kickDog(ret)
                except Exception as e:
                    thread_print(str(e))

            time.sleep(interval)

    def doorSensor_read(self):
        # get frequency
        interval = self.getInterval()
        # get id
        id = self.getID()

        while True: 
            if self.stopped(): 
                return
            path = "/sys/bus/w1/devices/" + id + "/state"

            c = 0
            for i in range(5):
                try:
                    with  open(path, "r") as f:
                        status = f.read(1)
                    break
                except IOError:
                    c = c + 1
            if c == 5 :
                #read fail
                thread_print("sensor: %s. Read fail." % (id))
            else:
                # read success 
                # send status to the server
                s = '{0:08b}'.format(ord(status))[1]
                # convert: 1 is open 0 is close
                if s == "1":
                    s = "0"
                else:
                    s = "1"
                thread_print("sensor: %s. Status: %s. Attempts: %s" % (id, s, str(c)))
                try:
                    ret = client.publish("senselet/" + id, str(time.time()) + '_' + s)
                    self.kickDog(ret)
                except Exception as e:
                    thread_print(str(e))

            time.sleep(interval)

    def oilLeakagePoint_read(self):
        # get frequency
        interval = self.getInterval()
        # get id
        id = self.getID()

        while True: 
            if self.stopped(): 
                return
            path = "/sys/bus/w1/devices/" + id + "/state"

            c = 0
            for i in range(5):
                try:
                    with  open(path, "r") as f:
                        status = f.read(1)
                    break
                except IOError:
                    c = c + 1
            if c == 5 :
                #read fail
                thread_print("sensor: %s. Read fail." % (id))
            else:
                # read success 
                # send status to the server
                s = '{0:08b}'.format(ord(status))[1]
                thread_print("sensor: %s. Status: %s. Attempts: %s" % (id, s, str(c)))
                try:
                    ret = client.publish("senselet/" + id, str(time.time()) + '_' + s)
                    self.kickDog(ret)
                except Exception as e:
                    thread_print(str(e))

            time.sleep(interval)

    def airFlow_read(self):
        # get frequency
        interval = self.getInterval()
        # get id
        id = self.getID()
        while True: 
            if self.stopped(): 
                return

            # read adc
            path = "/sys/bus/w1/devices/" + id + "/vad"

            c = 0

            for i in range(5):
                try:
                    with  open(path, "r") as f:
                        status = f.read().replace("\n","")
                    break
                except IOError:
                    c = c + 1

            if c == 5 :
                #read fail
                thread_print("sensor: %s. Read fail." % (id))
            else:
                # read success 
                # send status to the server
                thread_print("sensor: %s. Speed: %s. Attempts: %s" % (id,status, str(c)))
                try:
                    ret = client.publish("senselet/" + id, str(time.time()) + '_' + str(status))
                    self.kickDog(ret)
                except Exception as e:
                    thread_print(str(e))
            time.sleep(interval)
  
    def run(self): 

        if self.metaData["name"] == "sht85":
            self.sht85_read()

        elif self.metaData["name"] == "mlx90614":
            self.mlx90614_read()

        elif self.metaData["name"] == "waterLeakageRope":
            self.waterLeakageRope_read()

        elif self.metaData["name"] == "waterLeakagePoint":
            self.waterLeakagePoint_read()

        elif self.metaData["name"] == "doorSensorSmall":
            self.doorSensor_read()

        elif self.metaData["name"] == "doorSensorLarge":
            self.doorSensor_read()

        elif self.metaData["name"] == "oilLeakagePoint":
            self.oilLeakagePoint_read()

        elif self.metaData["name"] == "airFlow":
            self.airFlow_read()
# Sensor Reading Class End

# get available devices in the folder
def getDevices():
    path = "/sys/bus/w1/devices/"
    try:
        files = os.listdir(path)
    except:
        return -1
    return files
    

# get the I2C BUS of a given sensor id
def getI2CBUS(sensor):
    path = "/sys/bus/w1/devices/" + sensor + "/"
    try:
        files = os.listdir(path)
    except:
        # oops fail to list dirs -> we unplug it
        return -1
    sub = "i2c"
    busName = [s for s in files if sub in s]
    if len(busName) == 0:
        #we have the file but no i2c -> we unplug it
        return -1
    return int(busName[0].split('-')[1])

def kickDog():
    thread_print("no sensor connect to the device %s." %(raspberrypi_id))


def checkAndUpdateSensors():
    start = time.time()
    global currentSensors

    if len(currentSensors) == 0:
        kickDog()

    # temp sensor list
    newSensors = {}
    # create a temp sensor list
    sensors = getDevices()
    if sensors == -1:
        return -1

    # if there is no sensor connecting to the edge, we still pat the dog

    # sensors are discovered by the driver
    for sensor in sensors:
        if ignore in sensor:
            continue
        if sensor not in sensorMetaData:
            # if the sensor is not registered, we print&log this error
            thread_print("sensor -  %s not registered" % sensor) 
            continue
        else:
            metaData = sensorMetaData[sensor]
            # if the sensor is registered, check if it is an i2c device(i2c device is a little bit complex)
            if metaData["protocol"] == "I2C":
                newI2cBus = getI2CBUS(sensor)
                if newI2cBus == -1 :
                    continue
                    
                else:
                    if metaData["name"] == "sht85":
                        newSensors[sensor] = {
                                "protocol": "I2C",
                                "i2cBus": newI2cBus,
                                "name": metaData["name"],
                                "frequency": metaData["frequency"],
                                "calibration": metaData["calibration"]
                                }
                    else:
                        newSensors[sensor] = {
                                "protocol": "I2C",
                                "i2cBus": newI2cBus,
                                "name": metaData["name"],
                                "frequency": metaData["frequency"]
                                }
            else:
                newSensors[sensor] = {
                        "protocol": metaData["protocol"],
                        "name": metaData["name"],
                        "frequency": metaData["frequency"]
                        }

    # loop through current sensor list, add new sensor, remove unplugged sensor
    # for i2c sensor, we need to check (1) if it exists in the currentSensors (2) if the i2c bus is the same
    for sensor in list(currentSensors):
        metaData = currentSensors[sensor]

        # unplug
        if sensor not in newSensors:
            # thread_print&log
            thread_print("sensor -  %s - %s unplugged" % (sensor, metaData["name"])) 
            # if this is I2C device, we need to close the I2C file
            if metaData["protocol"] == "I2C":
                metaData["i2cDevice"].bus.close()
            # stop the thread
            metaData["threading"].stop()
            metaData["threading"].join()
            # delete this sensor from the connected sensor list
            del currentSensors[sensor]

        else:
            # we need to do extra checks for I2C, we don't need to check sensors with other types
            if metaData["protocol"] == "I2C":
                # if the bus number does not change, do nothing. else, we close the old device and add the new device
                oldI2cBus = metaData["i2cBus"]
                newI2cBus = newSensors[sensor]["i2cBus"]
                if oldI2cBus != newI2cBus:
                    thread_print("i2c sensor change i2c bus from %s -> %s" % (str(oldI2cBus), str(newI2cBus))) 
                    metaData["i2cDevice"].bus.close()
                    # start new bus
                    if metaData["name"] == "sht85":
                        metaData["i2cDevice"] = SHT85(newI2cBus)
                    elif metaData["name"] == "mlx90614":
                        metaData["i2cDevice"] = MLX90614(newI2cBus)

            # delete this sensor from new Sensors list
            del newSensors[sensor]

            # for threading we dont need to do anything

    # remained sensors in newSensors are new plugged sensors
    for sensor in newSensors:
        metaData = newSensors[sensor]
        thread_print("sensor -  %s - %s plugged in to the system" % (sensor, metaData["name"])) 
        if metaData["protocol"]== "I2C":
            newI2cBus = newSensors[sensor]["i2cBus"]

            if metaData["name"]== "sht85":
                i2cDevice = SHT85(newI2cBus)
            elif metaData["name"]== "mlx90614":
                i2cDevice = MLX90614(0x5a,newI2cBus)

            if metaData["name"] == "sht85":
                currentSensors[sensor] = {
                                "id": sensor,
                                "protocol": "I2C",
                                "i2cBus": newI2cBus,
                                "i2cDevice": i2cDevice,
                                "name": metaData["name"],
                                "frequency": metaData["frequency"],
                                "calibration": metaData["calibration"]
                        }
            else:
                currentSensors[sensor] = {
                                "id": sensor,
                                "protocol": "I2C",
                                "i2cBus": newI2cBus,
                                "i2cDevice": i2cDevice,
                                "name": metaData["name"],
                                "frequency": metaData["frequency"]
                        }

        else:
            currentSensors[sensor] = {
                            "id": sensor,
                            "protocol": metaData["protocol"],
                            "name": metaData["name"],
                            "frequency": metaData["frequency"]
                    }
        # start sensor reading thread
        t  = SensorReading(currentSensors[sensor])
        currentSensors[sensor]["threading"] = t
        t.start()

    end = time.time()

# publish network stats
def publishLink():
    global raspberrypi_id
    id = 'network' + str(raspberrypi_id)
    process = subprocess.run('cat /proc/net/wireless', shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    output = process.stdout
    outputList = output.split("\n")
    level = outputList[2].split()[2].replace('.','')
    thread_print("controller: %s. Link: %s. " % (id, level))
    try:
        ret = client.publish("senselet/" + id, str(time.time()) + '_' + level)
    except Exception as e:
        # we just print out the error
        thread_print(str(e))


def publishWIFIStats():
    global raspberrypi_id, stationTXByte_old, stationRXByte_old, time_old
    id = 'control' + str(raspberrypi_id)  
    process = subprocess.run('iw dev wlan0 station dump', shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    output = process.stdout
    outputList = output.split('\n\t')
    stationMAC = str(outputList[0].split()[1])
    stationSignal = str(outputList[7].split('[')[1].split(']')[0]) 
    stationTXRate = str(outputList[8].split('\t')[1].split()[0])
    stationRXRate = str(outputList[9].split('\t')[1].split()[0])

    if stationTXByte_old == 0:
        time_old = time.time()
        stationTXByte_old = int(outputList[4].split('\t')[1])
        stationRXByte_old = int(outputList[2].split('\t')[1])
        stationTXByteRate = 0
        stationRXByteRate = 0
    else:
        time_new = time.time()
        time_diff = time_new - time_old
        stationTXByte_new = int(outputList[4].split('\t')[1])
        stationRXByte_new = int(outputList[2].split('\t')[1])
        stationTXByteRate = str(round((stationTXByte_new - stationTXByte_old)/time_diff ,3))
        stationRXByteRate = str(round((stationRXByte_new - stationRXByte_old)/time_diff,3))

        stationTXByte_old = stationTXByte_new
        stationRXByte_old = stationRXByte_new
        time_old = time_new
        
        thread_print("controller: %s. APMAC: %s. APTXByteRate: %s. APRXByteRate: %s. APSignal: %s. APTXRate: %s. APRXRate: %s. " % (id,stationMAC, stationTXByteRate, stationRXByteRate, stationSignal, stationTXRate, stationRXRate))
        try:
            ret = client.publish("senselet/" + id, str(time.time()) + '_' + stationMAC + '_' + stationTXByteRate + '_' + stationRXByteRate + '_' + stationSignal + '_' + stationTXRate + '_' + stationRXRate)
        except Exception as e:
            # we just print out the error
            thread_print(str(e))


def main():
    while True:
        try:
            # 04/16/2021 add wifi stats
            publishWIFIStats()
            ret = checkAndUpdateSensors()
            if ret == -1:
                thread_print("something wrong happened, lets try it agagin")
                time.sleep(0.5)
                continue
            # read link every 1 s    
            publishLink()
            time.sleep(1)
            publishLink()
            time.sleep(1)
            publishLink()
            time.sleep(1)
        except KeyboardInterrupt:
        # Ctrl-C handling and send kill to threads
            thread_print ("Sending kill to threads...")
            for sensor in currentSensors:
                currentSensors[sensor]["threading"].stop()
            for sensor in currentSensors:
                currentSensors[sensor]["threading"].join()
            break


    thread_print ("Exited")

if __name__ == '__main__':
   main()
   fd.write("V")
   fd.close()
   print("watch dog stop")

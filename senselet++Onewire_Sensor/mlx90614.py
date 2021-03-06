# Thanks for the drive from: https://github.com/CRImier/python-MLX90614 

"""
MLX90614 driver.
You might need to enter this command on your Raspberry Pi:
echo "Y" > /sys/module/i2c_bcm2708/parameters/combined
(I've put it in my rc.local so it's executed each bootup)
"""

import smbus
from time import sleep

class MLX90614():

    MLX90614_RAWIR1=0x04
    MLX90614_RAWIR2=0x05
    MLX90614_TA=0x06
    MLX90614_TOBJ1=0x07
    MLX90614_TOBJ2=0x08

    MLX90614_TOMAX=0x20
    MLX90614_TOMIN=0x21
    MLX90614_PWMCTRL=0x22
    MLX90614_TARANGE=0x23
    MLX90614_EMISS=0x24
    MLX90614_CONFIG=0x25
    MLX90614_ADDR=0x0E
    MLX90614_ID1=0x3C
    MLX90614_ID2=0x3D
    MLX90614_ID3=0x3E
    MLX90614_ID4=0x3F

    comm_retries = 5
    comm_sleep_amount = 0.1
    # record reading reattempt counts [reattempt once, reattempt twice ... ]
    total_error = [0,0,0,0,0]

    def __init__(self, address=0x5a, bus_num=1):
        self.bus_num = bus_num
        self.address = address
        self.bus = smbus.SMBus(bus=bus_num)

    def get_total_error(self):
        return self.total_error

    def read_reg(self, reg_addr):
        err = None
        # c is the current reading reattempt times
        c = 0

        for i in range(self.comm_retries):
            try:
                return self.bus.read_word_data(self.address, reg_addr), c
            except IOError as e:
                self.total_error[c] += 1
                c = c + 1
                err = e
                #"Rate limiting" - sleeping to prevent problems with sensor
                #when requesting data too quickly
                sleep(self.comm_sleep_amount)
        # read fail
        return -1, c

    def data_to_temp(self, data):
        temp = (data*0.02) - 273.15
        return temp
    
    # ambient temperature: temperature on the die of the sensor
    def get_amb_temp(self):
        data = self.read_reg(self.MLX90614_TA)
        return self.data_to_temp(data)

    # object temperature: non-contact measurement
    def get_obj_temp(self):
        data,c  = self.read_reg(self.MLX90614_TOBJ1)
        if data == -1:
            return -1,c
        return round(self.data_to_temp(data),4),c


if __name__ == "__main__":
    sensor = MLX90614()
    print(sensor.get_amb_temp())
    print(sensor.get_obj_temp())

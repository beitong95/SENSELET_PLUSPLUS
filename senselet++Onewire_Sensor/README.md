# senseletonewire
# Raspberry Pi Zero W (Edge device preparation)
 -  download the latest raspbian
    ds28e17 driver is available after Linux-v4.15-rc1(raspbian buster or above)
 - country: united states; language: american English; timezone: chicago; use English language; use US keyboard; skip software update
 
 - set US keyboard for terminal, otherwise you cannot print "@"
    edit /etc/defaults/keyboard
    ```bash
    XKBLAYOUT="us"
    XKBMODEL="pc105" # XkbModel selects the keyboard model. This has an influence only for some extra keys your keyboard might have.
    ```

- set boot option
    boot to "console autologin text console"

- set interface option
    Please enable following interfaces with the following command or you can change boot/config.txt
    ```bash
     sudo raspi-config
    ```
    - ssh
    - i2c
    - serial
    - camera(if needed)

- set network
    Please connect to your own private network

- set up onewire driver and parameters
    disable w1-gpio in raspi-config [This is a default setting, so you don't need to do it.]

    Set up parameter: in "/etc/modprobe.d", create a file named "w1.conf"
    Then, add the following two lines in w1.conf
    ```bash
    options wire timeout=1 slave_ttl=1 #[search time, detect unplug time]
    options ds28e17 speed=100 #[set up ds28e17 i2c speed and stretch time]
    ```

    create "onewire.sh" in the home dir
    add the following two lines in onewire.sh
    ```bash
    modprobe ds2482 #[activate ds2482 driver]
    echo ds2482 0x18 > /sys/bus/i2c/devices/i2c-1/new_device #[detect ds2482]
    ```
    add "bash /home/pi/onewire.sh" in /etc/rc.local file to automatically run the script after booting
    
    **test if the above works:** 
    1. run lsmod to check active drivers
        sample result: 
        >wire 40960  4 ds2482,w1_ds2413,w1_ds2438,w1_ds28e17 (when you connnect the SenseEdge to the hat and sensors)
    
        or the result might be: 
        >wire 36864 1 ds2482 (when you only use the SenseEdge)
    
    2. check parameters
        go to ds28e17 device folder, run: 
        ```bash
        cat speed
        cat stretch
        ```
        then go to onewire master folder, run:
        ```bash
        cat timeout_second
        ```
    
- run edge data collect daemon
    get latest software on edge side

    ```bash
    cd $HOME
    git clone *this repo*
    ```

    before run senseletOneWire.py, you need to install some modules
    ```bash
    #install mosquitto client:
    sudo pip3 install paho-mqtt
    ```
    
    set mode to publish[remove all print]
    if you want to test, keep the mode as debug
    
    change raspberrypi_id to the right id [you can choose the id by your self]
    
    **[auto run]**
    add a daemon or add a command line in /etc/rc.local # actually, we dont need to add sudo because all commands run in the rc.local are run by sudoer. 
    ```bash
    sleep 30;bash /home/pi/onewire.sh;sudo python3 "your path to senseletOnewire.py" & #[add this line if you dont need log]
    sleep 30;bash /home/pi/onewire.sh;sudo python3 "your path to senseletOnewire.py" 2>&1 "your path to the log file" #[if you want a log]
    sleep 30;bash /home/pi/onewire.sh;sudo python3 -u "your path to senseletOnewire.py" 2>&1 | tee -i /some paths/"$(date '+%F-%T')_log.txt"& #[use this if you don't want to overwrite old log files everytime the raspberry pi reboots]
    ```
    
    **[manully run]**
    ```bash
    ssh to the edge device: ssh -p 22 pi@ip_address_of_the_device
    screen
    python3 -u "your path to senseletOnewire.py" 2>&1 | tee -i log.txt
    ctrl+A; ctrl+D [exit screen]
    ctrl+D[exit ssh session]
    ```

# Server
> please see the Readme file in senselet++Onewire_Server

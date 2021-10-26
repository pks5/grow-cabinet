import gpiozero
import json
import sys
import time
import subprocess
import Adafruit_DHT
import threading

DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 5

#Orange 
RELAY1_PIN = 6
#Gelb   
RELAY2_PIN = 13
#Grün   
RELAY3_PIN = 19
#Blau   
RELAY4_PIN = 26


class GrowCab:
    def __init__(self, notify_url=None):
        self.fan_speed_relay = None
        self.notify_url = notify_url
        self.state = {}
        self.dht_thread_running = False
        
    def send(self, data):
        payload = {
            "headers": {
                "to": self.notify_url
            },
            "body": data
        }
        print("<<" + json.dumps(payload), flush=True)

    def receive(self):
        print("Ready to receive commands from socket ...")
        for line in sys.stdin:
            sMessage = line[:-1]
            
            if(sMessage[0:3] == '>>{'):
                message = json.loads(sMessage[2:])
                try:
                    self.process(message)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(e)

    def process(self, message):
        message_body = message["body"]

        if("action" in message_body):
            action = message_body["action"]
        
            if(action == "STATUS"):
                self.send({'state' : self.state})
                return

            if(action == "SHUTDOWN"):
                print("Shutting down ...", flush=True)
                subprocess.run(["shutdown", "-h", "now"])
                return

            if(action == "REBOOT"):
                print("Rebooting ...", flush=True)
                subprocess.run(["shutdown", "-r", "now"])
                return

            if (action == "INIT"):
                pin_nr = message_body["pin"]
                if(pin_nr < 0 or pin_nr > 53):
                    print("Error: Pin out of range 0..53", flush=True)
                    return

                if(self.fan_speed_relay != None):
                    self.fan_speed_relay.close()
                    print("Closed Relay.", flush=True)
                
                self.fan_speed_relay = gpiozero.OutputDevice(pin_nr, active_high=False, initial_value=False)
                print("Created Relay on pin " + str(pin_nr), flush=True)

                self.state["pin"] = pin_nr
                self.send({'state' : self.state}) 
                    
        if(self.fan_speed_relay == None):
            print("Warning: Relay not initialized!", flush=True)
            return
            
        if("mode" in message_body):
            mode = message_body["mode"]
            
            if(mode == "OFF"):
                self.fan_speed_relay.off()
                print("Set Relay to OFF", flush=True)
            elif(mode == "ON"):
                self.light_relay.on()
                self.fan_relay.on()
                self.fan_speed_relay.on()
                print("Set Relay to ON", flush=True)
            else:
                print("Error: invalid mode!", flush=True)
                return

            self.state["mode"] = mode
            self.send({'state' : self.state}) 
    
    def read_dht(self):
        try:
            
            print("Connected to DHT sensor on pin " + str(DHT_PIN), flush=True)

            while True:
                humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
                if(humidity is not None and temperature is not None):
                    print("Temp={0:0.1f}*C  Humidity={1:0.1f}%".format(temperature, humidity), flush=True)
                else:
                    print("Failed to retrieve data from humidity sensor", flush=True)
                time.sleep(3)
        except IOError as error:
            print("IOError: " + str(error), flush=True)
        finally:
            self.dht_thread_running = False
    
    def start_dht_reader(self):
        if(self.dht_thread_running):
            print("DHT Reader thread already running.", flush=True)
        else:
            self.dht_thread_running = True
            threading.Thread(target=self.read_dht).start()
        
    def init_relays(self):
        self.light_relay = gpiozero.OutputDevice(RELAY1_PIN, active_high=False, initial_value=False)
        self.fan_relay = gpiozero.OutputDevice(RELAY2_PIN, active_high=False, initial_value=False)
        #relay3 = gpiozero.OutputDevice(RELAY3_PIN, active_high=False, initial_value=False)
        #relay4 = gpiozero.OutputDevice(RELAY4_PIN, active_high=False, initial_value=True)

        print("Initialized relays.", flush=True)

growcab = GrowCab()

try:
    growcab.init_relays()
    growcab.start_dht_reader()
    growcab.receive()
except KeyboardInterrupt:
    print('Good Bye!')
finally:
    print("cleanup")

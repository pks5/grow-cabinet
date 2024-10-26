import gpiozero
import json
import sys
import time
import subprocess
import board
import adafruit_dht
import threading

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
        self.light_relay = None
        self.fan_relay = None
        self.fan_speed_relay = None
        self.notify_url = notify_url
        self.state = {}
        self.dht_device = None
        self.dht_thread_running = False
        self.retry_time = 1
        self.update_time = 3
        
    def send(self, data):
        payload = {
            "headers": {
                "to": self.notify_url
            },
            "body": data
        }
        print("<<" + json.dumps(payload), flush=True)

    def upload_state(self):
        self.state["fan_on"] = self.fan_relay.value == 1
        self.state["light_on"] = self.light_relay.value == 1
        self.state["fan_full_speed"] = self.fan_speed_relay.value == 1 
        self.send({"state" : self.state})
    
    def receive(self):
        print("Ready to receive commands from socket ...", flush=True)
        for line in sys.stdin:
            sMessage = line[:-1]
            
            if(sMessage[0:3] == '>>{'):
                message = json.loads(sMessage[2:])
                try:
                    self.process(message)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(e, file=sys.stderr, flush=True)

    def process(self, message):
        message_body = message["body"]

        if("action" in message_body):
            action = message_body["action"]
        
            if(action == "STATUS"):
                self.upload_state()
                return

            if(action == "SHUTDOWN"):
                print("Shutting down ...", flush=True)
                time.sleep(0.25)
                subprocess.run(["sudo", "shutdown", "-h", "now"])
                return

            if(action == "REBOOT"):
                print("Rebooting ...", flush=True)
                time.sleep(0.25)
                subprocess.run(["sudo", "shutdown", "-r", "now"])
                return

        if("mode" in message_body):
            mode = message_body["mode"]
            
            if(mode == "OFF"):
                self.fan_speed_relay.off()
                print("Set Fan Speed Relay to OFF", flush=True)
            elif(mode == "ON"):
                self.fan_speed_relay.on()
                print("Set Fan Speed Relay to ON", flush=True)
            else:
                print("Error: invalid mode!", flush=True)
                return

            self.upload_state()
            return

        if("light_mode" in message_body):
            light_mode = message_body["light_mode"]
            
            if(light_mode == "OFF"):
                self.light_relay.off()
                print("Set Light Relay to OFF", flush=True)
            elif(light_mode == "ON"):
                self.light_relay.on()
                print("Set Light Relay to ON", flush=True)
            else:
                print("Error: invalid light mode!", flush=True)
                return

            self.upload_state()
            return
    
    def read_dht(self):
        self.dht_thread_running = True
        print("Listening to DHT sensor on pin " + str(DHT_PIN), flush=True)

        while self.dht_thread_running:
            try:
                humidity = self.dht_device.humidity
                temperature = self.dht_device.temperature
                if(humidity is not None and temperature is not None):
                    print("Temp={0:0.1f}*C  Humidity={1:0.1f}%".format(temperature, humidity), flush=True)
                    self.state["temperature"] = temperature
                    self.state["humidity"] = humidity
                    self.upload_state()
                else:
                    print("Failed to retrieve data from humidity sensor", flush=True)
                time.sleep(self.update_time)
            #except RuntimeError as e:
            #    print(e, file=sys.stderr, flush=True)
            #    time.sleep(self.retry_time)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(e, file=sys.stderr, flush=True)
                time.sleep(self.retry_time)
        
        print("Listener thread finished.", flush=True)
        
    def start_dht_reader(self):
        if(self.dht_thread_running):
            print("DHT Reader thread already running.", flush=True)
        else:
            threading.Thread(target=self.read_dht).start()
        
    def init_relays(self):
        if(self.light_relay is None):
            self.light_relay = gpiozero.OutputDevice(RELAY1_PIN, active_high=False, initial_value=False)
        if(self.fan_relay is None):
            self.fan_relay = gpiozero.OutputDevice(RELAY2_PIN, active_high=False, initial_value=False)
        if(self.fan_speed_relay is None):
            self.fan_speed_relay = gpiozero.OutputDevice(RELAY3_PIN, active_high=False, initial_value=False)
        
        if(self.dht_device is None):
            self.dht_device = adafruit_dht.DHT22(board.D5)

        self.light_relay.on()
        self.fan_relay.on()
        self.upload_state()

        print("Initialized relays.", flush=True)
    
    def cleanup(self):
        self.dht_thread_running = False
        if(self.dht_device is not None):
            self.dht_device.exit()
            print("Closed DHT device.", flush=True)
        print("cleanup", flush=True)


try:
    growcab = GrowCab()
    growcab.init_relays()
    growcab.start_dht_reader()
    growcab.receive()
    
except KeyboardInterrupt:
    print('Good Bye!', flush=True)
finally:
    growcab.cleanup()

from gpiozero import OutputDevice
import json
import sys
import time
import subprocess

class GrowCabTest:
    def __init__(self, notify_url=None):
        self.fan_speed_relay = None
        self.notify_url = notify_url
        self.state = {}
        
    def send(self, data):
        payload = {
            "headers": {
                "to": self.notify_url
            },
            "body": data
        }
        print("<<" + json.dumps(payload), flush=True)

    def receive(self):
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
                subprocess.run(["shutdown", "-h", "now"])
                return

            if(action == "REBOOT"):
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
                
                self.fan_speed_relay = OutputDevice(pin_nr, active_high=False, initial_value=False)
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
                self.fan_speed_relay.on()
                print("Set Relay to ON", flush=True)
            else:
                print("Error: invalid mode!", flush=True)
                return

            self.state["mode"] = mode
            self.send({'state' : self.state}) 
    
buzzer = GrowCabTest()

try:
    buzzer.receive()
except KeyboardInterrupt:
    print('Good Bye!')
finally:
    print("cleanup")

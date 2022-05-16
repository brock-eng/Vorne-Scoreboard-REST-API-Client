import requests

import webbrowser
import json
import time
from datetime import datetime
import random

sleep = lambda t: time.sleep(t)

# Scoreboard specific methods (displaying text, etc.)
class Scoreboard:
    def __init__(self, workstation) -> None:
        self.ws = workstation
        return
    
    # Normal display message
    def Display(self, line1 = "", line2 = "", line3 = "", time=10) -> None:
        displayObject = self.CreateTextObject(line1, line2, line3, time)
        self.ws.POST("api/v0/scoreboard/overlay", json.dumps(displayObject))
        return

    # Continuously prints some random characters to the screen
    def DisplayNonsense(self, line1 = "", line2 = "", line3 = "", time=10) -> None:
        i = 0
        timestep = 2
        while i < 10:
            letters = ['a', 'b', 'c', 'd', 'e', 'f']
            displayObject = self.CreateTextObject(str(i), "".join([random.choice(letters) for x in range(20)]), line3, time)
            response = self.ws.POST("api/v0/scoreboard/overlay", json.dumps(displayObject))
            print('Display Nonsense: ' + str(i) + '-> ', response)
            sleep(timestep)
            i += 1
        
        return

    # Warning display message
    def PrintImage(self, byteInformation):
        response = self.ws.POST("api/v0/scoreboard/graphic/image?x=0&y=0&w=80&h=32", byteInformation, headersIn={'Content-Type': 'application/octet-stream'})
        if response.status_code != 200:
            print("HTTP ERROR: ", response.status_code)
        return response
    
    # Set the scoreboard display setting
    def SetImageMode(self, status) -> bool:
        if status not in ['none', 'trans', 'over', 'under']:
            return False
        else:
            response = self.ws.POST('api/v0/scoreboard/graphic/mode', json.dumps({'value' : status}))
            if response.status_code == 200:
                return True
            else:
                return False

    # Return the current display mode of the scoreboard
    def GetImageMode(self) -> str:
        response = self.ws.GET('api/v0/scoreboard/graphic/mode', jsonToggle = True)
        return response["data"]["value"]

    # Opens Scoreboard in the web browser
    def Open(self):
        webbrowser.open(self.ws.ip + '#!/view/scoreboard')
        return

    # Creates a text dictionary object that displays on the scoreboard
    def CreateTextObject(self, line1 = "", line2 = "", line3 = "", time=10) -> dict:
        displayObject = {
            "duration": time,
            "text": [
                line1,
                line2,
                line3
            ]
        }
        return displayObject

    # Turns the scoreboard 'off'
    # Note that this doesn't actually turn off the power
    # Instead it displays a blank image overlay using direct screen control
    def TurnOff(self):
        imageMapBytes = bytes(7860)
        self.SetImageMode(imageMapBytes)
        return





# Class that holds all API methods for interacting with a Workstations Vorne scoreboard
# Initialize with an ip address and an optional workstation name
class WorkStation:
    
    # Initialize with an ip address
    def __init__(self, ipAddress, name = "") -> None:
        self.Scoreboard = Scoreboard(self)
        self.name = name
        self.ip = 'http://' + ipAddress + '/'
        self.active = True
        return

    # Open the current scoreboard dashboard
    def Open(self):
        webbrowser.open(self.ip + '#!/view/tpt')
        return
    
    # Returns GET http based on a query
    def GET(self, query, printToggle = False, jsonToggle = False):
        requestIP = self.ip + query
        response = requests.get(requestIP)
        if (response.status_code != requests.codes.ok):
            raise Exception('Error: bad http request made from {' + requestIP + "}  Error code: " + str(response.status_code))

        if jsonToggle:
            if printToggle:
                parsed = json.loads(response.text)
                print(json.dumps(parsed, indent=4, sort_keys=True))
            return response.json()
        else:
            if printToggle:
                print(response.text + '\n')
            return response

    # Posts a value to a destination query in http
    def POST(self, query, setValue, headersIn = ""):
        requestIP = self.ip + query
        if (headersIn != ''):
            return requests.post(requestIP, setValue)
        else:
            return requests.post(requestIP, setValue, headers = headersIn)

    # Set current part run based on part number
    def SetPart(self, PartNo, ideal = 20, takt = 30, \
        downTime = 60, changeOver = True, changeOverTarget = 60) -> bool:
        serialHeaders = {"pkey" : "RIB26OGS3R7VRcaRMbVM90mjza"}
        vorneURL = "api/v0/part_run"

        partRunBase = {
            "part_id": PartNo,
            "ideal_cycle_time": ideal,
            "takt_time": takt,
            "down_threshold": downTime,
            "start_with_changeover": changeOver,
            "changeover_reason": "part_change",
            "changeover_target": changeOverTarget,
            "disable_when" : {
                "type" : "timer"
            }
        }
        
        response = self.POST(vorneURL, json.dumps(partRunBase))
        responseCheck = (response.status_code == 200)
        return responseCheck, PartNo

    # Returns information on the last unrecognized barcode
    # Note that any barcode that is not printed using Vorne's system
    # is considered unrecognized
    def GetScan(self):
        metadata = self.GET("api/v0/device", jsonToggle=True)
        return metadata["data"]["serial_unrecognized_raw"]["value"]

    # Returns the current scan id.
    # Used for determining if a new scan has taken place
    def GetScanID(self) -> int:
        metadata = self.GET("api/v0/device", jsonToggle = True)
        return int(metadata["data"]["serial_unrecognized_count"]["value"])

    # Returns the current team size
    def GetTeam(self) -> int:
        metadata = self.GET("api/v0/team", jsonToggle = True)
        return int(metadata["data"]["team_size"])
        
    # Sets a team size
    def SetTeam(self, size):
        self.POST("api/v0/team", json.dumps({"team_id" : str(size), "team_size" : int(size)}))
        return

    # Pushes a count value to an input pin
    def InputPin(self, pinNumber, count = 1):
        response = self.POST("api/v0/inputs/" + str(pinNumber), json.dumps({"count": int(count)}))
        return

    # Gets the current process state
    def GetProcessState(self) -> str:
        metadata = self.GET("api/v0/process_state/active", jsonToggle=True)
        return str(metadata["data"]["name"]) , str(metadata["data"]["information_source"])

    # Sets the previous downtime reason
    def SetDowntimeReason(self, reason):
        self.POST("api/v0/process_state/reason", json.dumps({"value" : str(reason)}))
        return

    # Starts production state
    def StartProduction(self):
        self.POST("api/v0/process_state/start_production", json.dumps({}))
        return

    def StartDowntime(self):
        self.POST("api/v0/process_state/start_down_event", json.dumps({}))
        return

    # Sets active to true/false
    def SetActiveState(self, state):
        self.active = state
        return

    # Prints an overview of the current workstation, including state/reason/elapsed_time
    def PrintOverview(self):
        response = self.GET("api/v0/process_state/active", printToggle=False, jsonToggle=True)
        print("Workstation: " + self.name)
        print("Running: " + str(str(response['data']['name']) == 'running'))
        print("State  : " + response['data']['name'])
        print("Reason : " + response['data']['process_state_reason'])
        print("Time[s]: " + str(int(response['data']['elapsed'])))
        print("Time[m]: " + str(int(response['data']['elapsed'] / 60)))
        return
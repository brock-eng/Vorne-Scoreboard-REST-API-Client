### End user branch for the vorne scoreboard tool.
# This branch has reduced features and is mostly used
# for polling a scoreboard and activating cuustom barcode commands

version = "1.4 (11/29/2021)"

from tkinter import *
import threading
import webbrowser
from requests.models import stream_decode_response_unicode
import yaml
import time

from keylogger import *
from workstation import *
from bytecanvas import *
from programs import Program

class Application(Frame):
    # Application startup
    def __init__(self) -> None:
        # Create and format widgets
        self.Build()

        # Configure App, set Keybinds, class variables, etc.
        self.Configure()

        # Tracked Running Programs
        self.runningPrograms = dict()
        
        self.runningLoop = True
        self.scanID = -1
        self.pollingDuration = 1

        # App title
        self.root.title('Seats-Vorne Control Server'.format(version=self.version))


        # Startup Message
        self.OutputConsole('Running for workstation: {name} at ip {ip}'.format(name=self.ws.name, ip=self.ws.ip))
        self.OutputConsole('Software Version: {version}'.format(version = self.version))
        
        if self.keyloggerMode:
            self.OutputConsole('Running keylogger SN detection.')
        else: 
            self.OutputConsole('Keylogger disabled. (Enable via config file)')

        if self.debugMode:
            self.OutputConsole('Running in debug mode: Enhanced message reporting.')
        
        # Start main control program
        self.StartPolling()

    # Builds and formats tkinter widgets
    def Build(self):
        # Create root
        self.root = Tk()
        
        # Creating Widgets
        self.connectionStatus = Label()
        self.consoleOutputLabel = Label(text = 'Console Log')
        self.consoleOutput = Text()
        
        # Formatting Widgets
        self.root.iconbitmap('res\img\seats.ico')
        self.connectionStatus.place(x = 0)
        self.consoleOutputLabel.place(x = 0)
        self.connectionStatus.pack(fill = X)
        self.consoleOutputLabel.pack(fill = X)
        self.consoleOutput.pack(fill = BOTH)
        self.consoleOutput.configure(state=DISABLED)
        return
        

    # App configuration settings
    def Configure(self):
        # Opening config file and getting settings
        self.version = version
        stream = open("config.yml", 'r')
        config = yaml.safe_load(stream)
        self.ws = WorkStation(ipAddress = config["ipAddress"], name = config["workstation"])
        self.debugMode = config["debug_mode"]
        self.defaultCycleTime = config["default_cycle_time"]

        print(self.defaultCycleTime)
        
        # Set webbrowser path (set to use chrome)
        browserPath = config["browserPath"]
        webbrowser.register("wb", None, webbrowser.BackgroundBrowser(browserPath))

        # Keybinds / Handlers
        self.root.protocol("WM_DELETE_WINDOW", self.OnClose)

        # Start minimized
        self.root.wm_state('iconic')
        
        # keylogger support
        self.keyloggerMode = config["keylogger_mode"]
        if self.keyloggerMode:
            self.keylogger = KeyLogger()
        return

    # Output a console message
    def OutputConsole(self, message, printMode = True):
        if not printMode: return
        self.consoleOutput.configure(state='normal')
        self.consoleOutput.insert(END, '[' + datetime.now().strftime("%H:%M:%S") + ']')
        self.consoleOutput.insert(END, message)
        self.consoleOutput.insert(END, '\n')
        self.consoleOutput.see(END)
        self.consoleOutput.configure(state='disabled')

    # Alters the current scoreboard display
    def Display(self, *args):
        if str(args[0][0]).upper() == 'MODE':
            result = self.ws.Scoreboard.SetImageMode(args[0][1])
            if not result:
               raise NameError('Invalid display mode -> {none, over, under, trans}')
            else:
                self.OutputConsole('Changed display mode for ' + self.ws.name + ' to ' + str(args[0][2]) + '.')
            return

        if str(args[0][0]).upper() == 'TURNOFF':
            if str(self.ws.name) in self.runningPrograms.keys():
                self.runningPrograms[self.ws.name].Stop()
                self.runningPrograms.pop(self.ws.name)
                self.OutputConsole('Stopped program running at workstation: ' + self.ws.name)

            blankCanvas = ByteCanvas()
            result = self.ws.Scoreboard.PrintImage(blankCanvas.Output())
            resultDisplay = self.ws.Scoreboard.SetImageMode('over')
            if not result:
               raise NameError('Improper arguments called for \'display turnoff\' command')
            if not resultDisplay:
                raise NameError('Error setting display mode to \'over\'')
            else:
                self.OutputConsole('Turned off scoreboard display for ' + self.ws.name)
                self.OutputConsole('Call \'display turnon {ws}\' to return to normal screen.')
            return
        
        if str(args[0][0]).upper() == 'TURNON':
            resultDisplay = self.ws.Scoreboard.SetImageMode('none')
            if not resultDisplay:
               raise NameError('Error posting \'turnon\' to scoreboard.')
            else:
                self.OutputConsole('Turned on scoreboard display for ' + self.ws.name + '.')
            return


        if str(args[0][0]).upper() == 'STOP':
            if self.ws.name not in self.runningPrograms:
                raise RuntimeError('No program running on that workstation.')
            self.runningPrograms[self.ws.name].Stop()
            self.runningPrograms.pop(self.ws.name)
            self.OutputConsole('Stopped program running at workstation: ' + self.ws.name)
            return
            
        # Run a custom program on the screen.
        if str(args[0][0]).upper() == 'RUN':
            wsName = self.ws.name
            programName = str(args[0][2]).upper()
            wsObject = self.ws
            
            # Stop currently runnin program if there is one
            if wsName in self.runningPrograms:
                self.runningPrograms[wsName].Stop()
                self.runningPrograms.pop(wsName)
                self.OutputConsole('Stopped program running at workstation: ' + wsName)

            newProgram = Program(wsName)
            if len(args[0]) > 3: progArgs = (wsObject, args[0][3])
            else: progArgs = (wsObject, )
            programList = {
                'BOUNCE'    : newProgram.BounceProgram,
                'CONTROL'   : newProgram.ControlProgram,
                'COUNT'     : newProgram.CountProgram,
                'BOUNCE2'   : newProgram.Bounce2Program
            }
            if programName not in programList.keys():
                raise NameError('Program name not found.')
            
            # if not set to image display, change to over
            if wsObject.Scoreboard.GetImageMode() != "over":
                if programName != 'COUNT': 
                    self.Display(["TURNOFF", args[0][1]])

            newThread = threading.Thread(target=programList[programName], args=progArgs)
            newThread.start()
            self.runningPrograms[wsName] = newProgram
            self.OutputConsole('Running {program_name} program on {ws}'.format(program_name = programName, ws = self.ws.name))
            return
        
        raise NameError('Display subcommand not found: ' + str(args[0][0]))

    # Opens a workstation in the browser
    def Open(self, *args):
        if (len(args[0]) == 0):
            raise NameError("OPEN cmd requires a workstation name")
        
        try:
            webbrowser.get("wb").open(self.ws.ip)
            self.OutputConsole("Opened workstation {name} in browser.".format(name = args[0]))
        except:
            raise NameError("Could not find path.")
        return

    # Send a one line string message to a display
    def Message(self, *args):
        msg = ' '.join(args[0][1:])
        
        try:
            self.ws.Scoreboard.Display(msg)
            self.OutputConsole('Printed to {' + str(args[0][0]) + '}: \"' + msg + '\"')
        except:
            raise TypeError("Error posting message to display")
        return

    # Starts continuous polling of a workstation
    # Gets the unrecognized scan and triggers actions
    def StartPolling(self, *args):
        newThread = threading.Thread(target=self.PollingLoop)
        newThread.start()
        self.OutputConsole('Started polling at ' + self.ws.ip)
        return

    # Constantly polls the WS and processes its last unrecognized scan
    def PollingLoop(self):
        # Get latest unrecognized scan and store it in dict
        try:
            self.scanID = self.ws.GetScanID()
        except:
            self.OutputConsole("Failed to connect to scoreboard: " + self.ws.ip)
            self.connectionStatus.config(text="Not Connected {date}".format(date = datetime.now().strftime("%H:%M:%S")))

        # Main poll loop
        while self.ws.active == True:
            try:
                # Handle the last unrecognized scan
                self.HandleLastScan()

                # Keylogger support
                if self.keyloggerMode:
                    scannedSerialYesNo, scannedSN = self.keylogger.RetrieveSN()
                    self.OutputConsole(self.keylogger.PrintDebug(), self.debugMode)
                    if scannedSerialYesNo:
                        self.ConvertSerialPartRun(scannedSN, parse=False)

                time.sleep(self.pollingDuration)
                self.connectionStatus.config(text="Connected {date}".format(date = datetime.now().strftime("%H:%M:%S")))
            except:
                self.OutputConsole("Connection Error: " + self.ws.ip)
                self.connectionStatus.config(text="Not Connected {date}".format(date = datetime.now().strftime("%H:%M:%S")))
        
        return

    # Handles the latest unrecognized scan
    def HandleLastScan(self):
        scannedText = self.ws.GetScan()
        scanNumber = self.ws.GetScanID()

        # if returned scan is equal to previous, do nothing
        if scanNumber == self.scanID: return
        else:   self.scanID = scanNumber
        
        # Custom commands
        if scannedText[0:4] == '%CUS': # detect if custom tag
            self.OutputConsole("Detected custom command: " + scannedText[4:])
            CustomCommand = scannedText[4:]
            self.RunScannedCommand(str(CustomCommand).upper())

        # Serial numbers scanned into the Vorne
        elif scannedText[0] == 'S': # SN
            self.OutputConsole("Detected SN: " + str(scannedText))
            self.ConvertSerialPartRun(serialNum = scannedText, parse=True)
        else:
            self.OutputConsole("Unrecognized barcode: " + scannedText)
        return

    # Reads the last unrecognized scan
    # Converts to catalog number and starts a new part run
    def ConvertSerialPartRun(self, serialNum, parse = True):
        if parse:
            serialNum = str(serialNum[1:]).rstrip()   # remove 'S' and '\r' from SN

        # Convert serial to catalog
        partNo = self.ConvertSerial(serialNum)
        if partNo == -1:
            return

        # Check if current part run matches new part run
        # If true then cancel the part run (it's already running the part)
        currentPartNo = self.ws.GET("api/v0/part_run", jsonToggle=True)["data"]["part_id"]

        if str(partNo) == str(currentPartNo):
            self.OutputConsole("Did not set new part run: {" + str(partNo) + "} is already in production.")
            self.IncreaseCount()
            return

        # TODO: Add dynamic std. run factor
        #
        #
        # Submit new part run based on catalog num
        idealTime = self.defaultCycleTime * 60
        result = self.ws.SetPart(partNo, changeOver=False, ideal=idealTime, takt=idealTime * 1.25, downTime=idealTime * 2)

        if result: 
            self.IncreaseCount()
            self.OutputConsole("Converted Serial {SN} to new part run: {PN}".format(SN = serialNum, PN = partNo))
        else: 
            self.OutputConsole("Failed to convert serial to new part run.")

        return

    # Increments the scoreboard count by a certain amount
    def IncreaseCount(self, count = 1):
        self.ws.InputPin(1, count)
        self.OutputConsole("Incremented count by {count}", self.debugMode)

    # Sets a part run (For command line functionality)
    def SetPartNo(self, PartNo):
        # Set display to on if not already on
        if self.ws.Scoreboard.GetImageMode() != "none":
            self.Display(["TURNON"])

        # Check if current part run matches new part run
        # If true then cancel the part run (it's already running the part)
        currentPartNo = self.ws.GET("api/v0/part_run", jsonToggle=True)["data"]["part_id"]

        if str(PartNo) == str(currentPartNo):
            self.OutputConsole("Did not set new part run: {" + str(PartNo) + "} is already in production.")
            return

        # Call set part command
        self.ws.SetPart(PartNo, changeOver=False)
        
        self.OutputConsole("Set {" + self.ws.name + "} part run to " + str(PartNo) + ".")
        return

    # Grab a catalog number using the seats-api endpoint
    def ConvertSerial(self, serial):
        try: 
            response = requests.get("https://seats-api.seatsinc.com/ords/api1/serial/json/?serialno=" + serial + "&pkey=RIB26OGS3R7VRcaRMbVM90mjza")
            partNo = response.json()['catalog_no']
        except: 
            self.OutputConsole("Could not find PartNo for given serial: {" + serial + "}")
            self.ws.Scoreboard.Display("Warning:", "Part not found for","SN: " + str(serial))
            return -1
        return partNo

    # Adds an amount of operators to the current team
    def TeamAdd(self, size):
        currentSize = self.ws.GetTeam()
        newSize = size + currentSize
        self.ws.SetTeam(newSize)
        return

    # Starts a new downtime event
    def DowntimeEvent(self):
        self.ws.POST("api/v0/process_state/start_down_event", json.dumps({}))
        self.OutputConsole("Started new downtime event.")
        return

    # Runs a custom scanned command 
    def RunScannedCommand(self, cmd):
        cmd = str(cmd).rstrip()
        nullArg = "***NULLARGUMENT_THIS_SHOULD_NOT_BE_USED***"
        if cmd == "COUNTPROG":
            self.Display(["run", nullArg,"count"],)
        elif cmd == "SAMPLEPART":
            self.SetPartNo(["Sample"])
        elif cmd == "TURNOFF":
            self.Display(["turnoff"])
        elif cmd == "TURNON":
            self.Display(["turnon"])
        elif cmd == "OPENLINK1":
            webbrowser.get("wb").open(self.ws.ip)
        elif cmd == "FUNTIMES":
            self.Display(["run", nullArg, "bounce2", 10],)
        elif cmd == "OPERATORS++":
            self.TeamAdd(1)
        elif cmd == "OPERATORS--":
            self.TeamAdd(-1)
        elif cmd == "DOWNTIME":
            self.DowntimeEvent()
        else:
            self.OutputConsole("Warning: Custom command not found: " + str(cmd))


    # Run the application
    def Run(self):
        self.root.mainloop()

    # Window close handling
    def OnClose(self, *args):
        for program in self.runningPrograms:
            self.runningPrograms[program].Stop()

        self.ws.SetActiveState(False)
        
        time.sleep(self.pollingDuration * 1.5)

        self.root.destroy()

        
def main():
    ConsoleApp = Application()
    ConsoleApp.Run()


if __name__ == '__main__': main()
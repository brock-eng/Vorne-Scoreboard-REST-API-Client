### End user branch for the vorne scoreboard tool.
# This branch has reduced features and is mostly used
# for polling a scoreboard and activating cuustom barcode commands

version = "1.5 (12/1/2021)"

from tkinter import *
import threading
import webbrowser
import yaml
import time
import csv

from keylogger import *
from workstation import *
from bytecanvas import *
from programs import Program

HOURS_TO_SECONDS = int(3600)
MINUTES_TO_SECONDS = int(60)

class Application(Frame):
    # Application startup
    def __init__(self) -> None:
        # Create and format widgets
        self.Build()

        # Configure App, set Keybinds, class variables, etc.
        self.Configure()

        # Startup Message
        self.OutputConsole('Running for workstation: {name} at ip {ip}'.format(name=self.ws.name, ip=self.ws.ip))
        self.OutputConsole('Software Version: {version}'.format(version = self.version))
        
        if self.keyloggerMode:
            self.OutputConsole('Running keylogger SN detection.')
        else: 
            self.OutputConsole('Keylogger disabled. (Enable via config file)')

        if self.debugMode:
            self.OutputConsole('Running in debug mode: Enhanced message reporting.')
        
        # self.DebugTesting()

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
        self.defaultCycleTime = config["default_cycle_time"] * MINUTES_TO_SECONDS
        self.downtimeMultiplier = config["downtime_multiplier"]
        self.idealTimeFudgeFactor = config["ideal_time_fudge_factor"]
        self.lookupSetting = config["lookup_times"]
        self.taktTimeFactor = config["takt_time_factor"]

        # Class State Variables
        self.runningPrograms = dict()   # Custom programs
        self.scanID = -1                # ScanID of the last unrecognized vorne scan
        self.pollingDuration = 1        # How long between each scoreboard poll (connection)
        self.serialNos = list()         # List of previously scanned serials

        # Set webbrowser path (set to use chrome)
        browserPath = config["browserPath"]
        webbrowser.register("wb", None, webbrowser.BackgroundBrowser(browserPath))

        # Keybinds / Handlers
        self.root.protocol("WM_DELETE_WINDOW", self.OnClose)

        # Start minimized
        self.root.wm_state('iconic')
        
        # Keylogger support
        self.keyloggerMode = config["keylogger_mode"]
        if self.keyloggerMode:
            self.keylogger = KeyLogger()

        # CSV File location (for std lookup times)
        self.dataFilePath = config["time_data_file"]
        try:
            open(self.dataFilePath)
        except:
            self.OutputConsole("Couldn't open data file.  Setting times to default.")
            self.lookupSetting = False

        # App title
        self.root.title('Seats-Vorne Control Server'.format(version=self.version))
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
                self.OutputConsole("Error: " + self.ws.ip)
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

        # Check if serial already scanned, if it has been scanned we ignore this scan
        if serialNum in self.serialNos:
            self.ws.Scoreboard.Display(line1 = "Warning:", line2 = "Duplicate SN", line3 = "scanned.", time = 5)
            self.OutputConsole("Detected a duplicate serialNo: " + serialNum)
            return
        else:
            self.serialNos.append(serialNum)

        # Convert serial to catalog
        partNo = self.ConvertSerial(serialNum)
        if partNo == -1:
            return

        # If not using automatic run detection, start
        null, currentInfoSource = self.ws.GetProcessState()
        if currentInfoSource != "run_detector":
            self.OutputConsole("Starting auto detection.")
            self.ws.StartProduction()

        # Do not set a new part run if currently running same part
        currentPartNo = self.ws.GET("api/v0/part_run", jsonToggle=True)["data"]["part_id"]
        if str(partNo) == str(currentPartNo):
            self.OutputConsole("Did not set new part run: {" + str(partNo) + "} is already in production.")
            self.IncreaseCount()
        
        # New part run
        else:
            try:
                # Dynamic time lookup
                if self.lookupSetting:
                    # Get current team, if < 0 set to a default of 10
                    currentTeamCount = self.ws.GetTeam()
                    if currentTeamCount <= 0: 
                        currentTeamCount = 14
                        self.OutputConsole("Warning: Did not find a correct team size.  Defaulted to 14.")

                    lookupTime = self.LookupTimes(partNo)
                    if lookupTime > 0: # found part time
                        _idealTime = lookupTime / float(currentTeamCount) * self.idealTimeFudgeFactor
                    else: # not found or zero time amount, apply default times
                        _idealTime = self.defaultCycleTime
                
                # Default time settings
                else:
                    _idealTime = self.defaultCycleTime
            except: 
                self.OutputConsole("Program error: Could not lookup times for part {0}".format(partNo))
                _idealTime = self.defaultCycleTime

            _downtime = _idealTime * self.downtimeMultiplier
            _taktTime = _idealTime * self.taktTimeFactor

            result = self.ws.SetPart(partNo, changeOver=False, ideal=_idealTime, takt=_taktTime, downTime=_downtime)

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
    def SetPartNo(self, partNo):
        # Set display to on if not already on
        if self.ws.Scoreboard.GetImageMode() != "none":
            self.Display(["TURNON"])

        # If not using automatic run detection, start
        null, currentInfoSource = self.ws.GetProcessState()
        if currentInfoSource != "run_detector":
            self.OutputConsole("Starting auto detection.")
            self.ws.StartProduction()

        # Do not set a new part run if currently running same part
        currentPartNo = self.ws.GET("api/v0/part_run", jsonToggle=True)["data"]["part_id"]
        if str(partNo) == str(currentPartNo):
            self.OutputConsole("Did not set new part run: {" + str(partNo) + "} is already in production.")
            self.IncreaseCount()

        # New part run
        else:
            try:
                # Dynamic time lookup
                if self.lookupSetting:
                    # Get current team, if < 0 set to a default of 10
                    currentTeamCount = self.ws.GetTeam()
                    if currentTeamCount <= 0: 
                        currentTeamCount = 14
                        self.OutputConsole("Warning: Did not find a correct team size.  Defaulted to 14.")

                    lookupTime = self.LookupTimes(partNo)
                    if lookupTime > 0: # found part time
                        _idealTime = lookupTime / float(currentTeamCount)
                    else: # not found or zero time amount, apply default times
                        _idealTime = self.defaultCycleTime
                
                # Default time settings
                else:
                    _idealTime = self.defaultCycleTime
            except: 
                self.OutputConsole("Program error: Could not lookup times for part {0}".format(partNo))
                _idealTime = self.defaultCycleTime

            _downtime = _idealTime * self.downtimeMultiplier
            _taktTime = _idealTime * self.taktTimeFactor

            result = self.ws.SetPart(partNo, changeOver=False, ideal=_idealTime, takt=_taktTime * 1, downTime=_downtime)

            if result: 
                self.IncreaseCount()
                self.OutputConsole("Set {" + self.ws.name + "} part run to " + str(partNo) + ".")
            else: 
                self.OutputConsole("Failed to set a to new part run.")

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
            self.ws.StartDowntime()
        elif cmd == "REJECT":
            self.ws.InputPin(2, 1)
        elif cmd == "UNKNOWNPART":
            self.OutputConsole("Warning: starting a part run using an unknown part.")
            self.SetPartNo(["Placeholder Part"])
        else:
            self.OutputConsole("Warning: Custom command not found: " + str(cmd))

    # Lookup std run times from a pre-built csv file
    def LookupTimes(self, partNo) -> float:
        with open(self.dataFilePath) as dataFile:
            dataReader = csv.reader(dataFile)
            found = False
            foundTime = 0

            # loop through each row and try to find the matching part
            for row in enumerate(dataReader):
                storedPartNo = str(row[1][0])
                stdRunTime = str(row[1][1])

                if str(partNo).upper() == str(storedPartNo).upper():
                    # found a match
                    foundTime = float(stdRunTime) * HOURS_TO_SECONDS
                    found = True
                    break
            
            if not found:
                self.OutputConsole("Could not find stdRunFactor for part: {0}".format(partNo))
                return float(-1)
            else:
                self.OutputConsole("Found a part run time of {0} for part {1}".format(foundTime, partNo))
                return float(foundTime)

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

    # Testing function
    def DebugTesting(self):
        if self.lookupSetting:
            testPartNos = list()
            testPartNos = ["186586VD478", "Nonsense", "188441VD731", "128596VN06", "131526HN303"]
            for partNo in testPartNos:
                lookupTime = self.LookupTimes(partNo)
                currentTeamCount = self.ws.GetTeam()
                print(partNo)
                print("Lookuptime:", lookupTime)
                print("TeamSize:", currentTeamCount)

                if lookupTime > 0: # found part time
                    _idealTime = lookupTime / float(currentTeamCount) * self.idealTimeFudgeFactor
                    _downtime = _idealTime * self.downtimeMultiplier
                    _taktTime = _idealTime * self.taktTimeFactor
                else: # not found, apply default times
                    _idealTime = self.defaultCycleTime
                    _downtime = _idealTime * self.downtimeMultiplier
                    _taktTime = _idealTime * self.taktTimeFactor
                
                print("Ideal and downtime:",_idealTime, _downtime, _taktTime, "\n")

        
def main():
    ConsoleApp = Application()
    ConsoleApp.Run()


if __name__ == '__main__': main()
import time
import keyboard

# Keylogging class that tracks keys pressed as well as the timestamp of each
class KeyLogger:
    def __init__(self) -> None:
        self.keylog = list()
        self.reading = False
        self.readSN = ""
        self.foundSNYesNo = False
        self.foundSN = ""

        keyboard.on_release(self.KeystrokeCallback)

    # main keystroke event handler
    def KeystrokeCallback(self, event) -> None:
        keyName = str(event.name).upper()   # character name
        
        self.keylog.append(keyName)
        self.DetSerialNum(keyName)

    # determines if a serial number has been entered
    # mostly done through timestamp checking
    def DetSerialNum(self, keyName) -> None:
        if len(self.keylog) < 2: return

        # Start read event
        if (not self.reading) and (self.keylog[-2] + self.keylog[-1] == "SHIFTS"):
            self.reading = True

        # End read event
        elif keyName == "ENTER" and self.reading == True:
            self.reading = False
            self.foundSNYesNo = True
            self.foundSN = self.readSN
            self.keylog.clear()
            self.readSN = ""
            print("Found barcode as: {" + self.foundSN + "}")

        # Add to current read if not special character
        elif self.reading:
            if len(keyName) <= 1:
                self.readSN += keyName


    # Can be called to retrieve a valid SN input if one has been registered
    def RetrieveSN(self):
        if self.foundSNYesNo:
            self.foundSNYesNo = False
            returnSN = self.foundSN
            self.foundSN = ""
                
            return True, returnSN
        else:
            return False, ""

    # Transforms list of keys to readable string
    def ParseList(self, keyList, specialChars = True) -> str:
        value = ""
        for char in keyList:
            if not specialChars:
                if len(char) <= 1:
                    value += char
            else:
                value += char
        return value

    # debug printing utility
    def PrintDebug(self) -> str:
        return self.ParseList(self.keylog, specialChars=True)


def keyloggerTestMain():
    keylogger = KeyLogger()

    while True:
        resultYesNo, resultSN = keylogger.RetrieveSN()
        print(keylogger.PrintDebug())
        time.sleep(1)


if __name__ == "__main__": keyloggerTestMain()
        

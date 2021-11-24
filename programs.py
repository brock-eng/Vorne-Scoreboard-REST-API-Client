import keyboard
import time

from bytecanvas import ByteCanvas
from workstation import *

class Program:
    def __init__(self, name) -> None:
        self.isRunning = True
        self.ws = name

    def Stop(self):
        self.isRunning = False

    def BounceProgram(self, WS):
        newCanvas = ByteCanvas()

        # newCanvas.DrawLine(40, 0, 40, 32, 'G4')
        newCanvas.Fill(0, 0, 80, 31, 'G4')
        newCanvas.Fill(35, 14, 45, 18, 'BLANK')
        
        x = 40
        y = 16
        vX = 1
        vY = 1
        
        while self.isRunning:
            # Clear the previous 'ball' position
            newCanvas.ClearPixel(x, y)

            x += vX
            y += vY
            
            # Collides with x-wall
            if bool(newCanvas.GetPixel(x, y - vY)):
                newCanvas.PaintPixel(x, y - vY, 'BLANK')
                x -= vX
                vX = -vX
                yNotTriggered = False
            # Collides with y-wall
            
            if bool(newCanvas.GetPixel(x-vX, y)):
                newCanvas.PaintPixel(x-vX, y, 'BLANK')
                y -= vY
                vY = -vY
            else: # Collides with corner-wall
                if bool(newCanvas.GetPixel(x, y) and yNotTriggered):
                    newCanvas.PaintPixel(x, y, 'BLANK')
                    x -= vX
                    y -= vY
                    vX = -vX
                    vY = -vY
            yNotTriggered = True  

            # Collision with screen borders
            if (x >= 79): 
                vX = -1
            else:
                if x <= 0: 
                    vX = 1

            if (y >= 31): 
                vY = -1
            else:
                if y <= 0: vY = 1

            # Update the ball position
            newCanvas.PaintPixel(x, y, 'R1')
            WS.Scoreboard.PrintImage(newCanvas.Output())
            
            time.sleep(0.04)

            # Quit if q is pressed
            if keyboard.is_pressed('q'):
                self.isRunning = False


    def Bounce2Program(self, WS, numBalls = 10):
        newCanvas = ByteCanvas()

        newCanvas.Fill(0, 0, 80, 31, 'G4')
        
        class ball:
            def __init__(self) -> None:
                self.x = int(random.randint(0, newCanvas.WIDTH - 2))
                self.y = int(random.randint(0, newCanvas.HEIGHT - 2))
                self.vX = int(-1 + 2 * random.randint(0, 1))
                self.vY = int(-1 + 2 * random.randint(0, 1))
                self.color = int(random.randint(1,3)) * 4


        numBalls = int(numBalls)
        balls = list()
        i = 0
        while i < numBalls:
            balls.append(ball())
            i+=1
        
        while self.isRunning:
            for b in balls:
            # Clear the previous 'ball' position
                newCanvas.ClearPixel(b.x, b.y)

                b.x += b.vX
                b.y += b.vY
                
                # Collides with x-wall
                if bool(newCanvas.GetPixel(b.x, b.y - b.vY)):
                    newCanvas.PaintPixel(b.x, b.y - b.vY, 'BLANK')
                    b.x -= b.vX
                    b.vX = -b.vX
                    yNotTriggered = False
                # Collides with y-wall
                
                if bool(newCanvas.GetPixel(b.x-b.vX, b.y)):
                    newCanvas.PaintPixel(b.x-b.vX, b.y, 'BLANK')
                    b.y -= b.vY
                    b.vY = -b.vY
                else: # Collides with corner-wall
                    if bool(newCanvas.GetPixel(b.x, b.y) and yNotTriggered):
                        newCanvas.PaintPixel(b.x, b.y, 'BLANK')
                        b.x -= b.vX
                        b.y -= b.vY
                        b.vX = -b.vX
                        b.vY = -b.vY

                yNotTriggered = True  

                # Collision with screen borders
                if (b.x >= 79): 
                    b.vX = -1
                else:
                    if b.x <= 0: 
                        b.vX = 1

                if (b.y >= 31): 
                    b.vY = -1
                else:
                    if b.y <= 0: b.vY = 1

                # Update the ball position
                newCanvas.PaintPixel(b.x, b.y, b.color)

            WS.Scoreboard.PrintImage(newCanvas.Output())
            
            time.sleep(0.04)

            # Quit if q is pressed
            if keyboard.is_pressed('q'):
                self.isRunning = False

    def ControlProgram(self, WS):
        newCanvas = ByteCanvas()

        x = 40
        y = 16
        vX = 1
        vY = 1
        
        deleteMode = True
        color = 7
        size = 10
        
        while self.isRunning:

            if deleteMode:
                newCanvas.Fill(x, y, x + size, y + size, 0)

            if keyboard.is_pressed('up'):
                y += -1
            if keyboard.is_pressed('left'):
                x += -1
            if keyboard.is_pressed('right'):
                x += 1
            if keyboard.is_pressed('down'):
                y += 1

            if keyboard.is_pressed('shift'):
                color += 1

            if keyboard.is_pressed('ctrl'):
                color -= 1

            if color < 0:
                color = 0

            newCanvas.Fill(x, y, x + size, y + size, color)
            WS.Scoreboard.PrintImage(newCanvas.Output())
            
            time.sleep(0.1)

            if keyboard.is_pressed('q'):
                isRunning = False
            
            if keyboard.is_pressed('enter'):
                deleteMode = not deleteMode

    def CountProgram(self, WS):

        while self.isRunning:
            if keyboard.is_pressed('up'):
                WS.InputPin(1, 1)
                while keyboard.is_pressed('up') or keyboard.is_pressed('down'):
                    pass
            elif keyboard.is_pressed('down'):
                WS.InputPin(2, 1)
                while keyboard.is_pressed('up') or keyboard.is_pressed('down'):
                    pass

            elif keyboard.is_pressed('0'):
                WS.Scoreboard.Display("this is a", "sample message", time=5)
                while keyboard.is_pressed('up') or keyboard.is_pressed('down'):
                    pass

            elif keyboard.is_pressed('1'):
                WS.Scoreboard.Display("you pressed the", "'1' key", time=5)
                while keyboard.is_pressed('up') or keyboard.is_pressed('down'):
                    pass


                    
            
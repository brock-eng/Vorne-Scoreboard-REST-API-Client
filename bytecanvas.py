# class for creating canvases for directly importing onto a vorne xl scoreboard
class ByteCanvas:

    # Color dictionary
    # Base Colors are Red, Green, Yellow
    # Format is {COLOR}{STRENGTH}
    # Prefix with a 'B' for blinking effect
    # EX: Blinking red of strength 2 -> "BR2"
    COLORS = {
        "BLANK" : 0,
        "R1" : 1,"R2" : 2,"R3" : 3,"R4" : 4,
        "G1" : 5,"G2" : 6,"G3" : 7,"G4" : 8,
        "Y1" : 9,"Y2" : 10,"Y3" : 11,"Y4" : 12,
        "BR1" : 13,"BR2" : 14,"BR3" : 15,"BR4" : 16,
        "BG1" : 17,"BG2" : 18,"BG3" : 19,"BG4" : 20,
        "BY1" : 21,"BY2" : 22,"BY3" : 23,"BY4" : 24
    }

    # canvas constants
    WIDTH = 80
    HEIGHT = 32

    def __init__(self) -> None:
        self.bytecanvas = bytearray(self.WIDTH * self.HEIGHT)

    # paints a single pixel based on the x and y coordinate
    def PaintPixel(self, x, y, value):
        if (x >= self.WIDTH or y >= self.HEIGHT or x < 0 or y < 0):
            # print("Tried to paint an invalid pixel @ (x,y): ", x, " ", y)
            return
        if not(isinstance(value, int)):
            value = self.COLORS[value]

        self.bytecanvas[x + y * self.WIDTH] = value

    # returns the pixel value at a specified location
    # refer to 'COLORS' dictionary for the int return value
    def GetPixel(self, x, y) -> int:
        return int(self.bytecanvas[x + y * self.WIDTH])

    # Sets a specified pixel to no-color
    def ClearPixel(self, x, y):
        self.bytecanvas[x + y * self.WIDTH] = 0

    # Fills a square area between two points
    def Fill(self, x1, y1, x2, y2, value):
        ystart = y1
        while x1 <= x2:
            while y1 <= y2:
                self.PaintPixel(x1, y1, value)
                y1 += 1
            x1 += 1
            y1 = ystart
    
    # Prints current array to console for debugging purposes
    def Print(self):
        print(bytes(self.bytecanvas))

    # Returns outputable array used for sending the byte data
    def Output(self):
        return bytes(self.bytecanvas)

    # Draws a line connecting two sets of x,y points
    def DrawLine(self, x1, y1, x2, y2, value):
        dy = y2 - y1
        dx = x2 - x1

        if (abs(dy) < abs(dx)):
            if (x1 > x2):
                self.DrawLineLow(x2, y2, x1, y1, value)
            else:
                self.DrawLineLow(x1, y1, x2, y2, value)
        else:
            if (y1 > y2):
                self.DrawLineHigh(x2, y2, x1, y1, value)
            else:
                self.DrawLineHigh(x1, y1, x2, y2, value)

    # Should not be called, line subfunction
    def DrawLineLow(self, x1, y1, x2, y2, value):
        dy = y2 - y1
        dx = x2 - x1
        yi = 1
        y = y1

        if (dy < 0):
            yi = -1
            dy *= -1
        D = 2 * dy - dx

        x = x1
        while x <= x2:
            self.PaintPixel(x, y, value)
            if (D > 0):
                y += yi
                D += 2 * (dy - dx)
            else:
                D += 2 * dy
            x += 1

    # Should not be called, line subfunction
    def DrawLineHigh(self, x1, y1, x2, y2, value):
        dy = y2 - y1
        dx = x2 - x1
        xi = 1
        x = x1

        if (dx < 0):
            xi = -1
            dx *= -1
        D = 2 * dx - dy

        y = y1
        while y <= y2:
            self.PaintPixel(x, y, value)
            if (D > 0):
                x += xi
                D += 2 * (dx - dy)
            else:
                D += 2 * dx
            y += 1

    def DrawCircle(self, xc, yc, r, color):
        x = 0
        y = r
        d = 3 - 2 * r
        self.Circle(xc, yc, x, y, color)
        while (y >= x):
            if (d > 0):
                d += 4 * (x - y) + 10
                x+=1
                y-=1
            else:
                 d += 4 * x + 6
                 x+=1
            self.Circle(xc, yc, x, y, color)
  

    def Circle(self, xc, yc, x, y, color):
        self.PaintPixel(xc + y, yc + x, color)
        self.PaintPixel(xc - x, yc - y, color)
        self.PaintPixel(xc - y, yc - x, color)
        self.PaintPixel(xc + y, yc - x, color)
        self.PaintPixel(xc + x, yc - y, color)
        self.PaintPixel(xc - x, yc + y, color)
        self.PaintPixel(xc - y, yc + x, color)
        self.PaintPixel(xc + x, yc + y, color)

def main():
    testCanvas = ByteCanvas()
    testCanvas.PaintPixel(5, 5, "BR1")
    testCanvas.Fill(0, 0, 80, 31, "R1")
    testCanvas.Print()
    print('finished')
    return

if __name__ == '__main__': main()

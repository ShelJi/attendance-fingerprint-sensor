import time


class SSD1309:

    WIDTH = 128
    HEIGHT = 64

    FONT = {
        "A": ["01110","10001","10001","11111","10001","10001","10001"],
        "B": ["11110","10001","10001","11110","10001","10001","11110"],
        "C": ["01111","10000","10000","10000","10000","10000","01111"],
        "D": ["11110","10001","10001","10001","10001","10001","11110"],
        "E": ["11111","10000","10000","11110","10000","10000","11111"],
        "F": ["11111","10000","10000","11110","10000","10000","10000"],
        "G": ["01111","10000","10000","10111","10001","10001","01111"],
        "H": ["10001","10001","10001","11111","10001","10001","10001"],
        "I": ["11111","00100","00100","00100","00100","00100","11111"],
        "J": ["00111","00010","00010","00010","10010","10010","01100"],
        "K": ["10001","10010","10100","11000","10100","10010","10001"],
        "L": ["10000","10000","10000","10000","10000","10000","11111"],
        "M": ["10001","11011","10101","10101","10001","10001","10001"],
        "N": ["10001","11001","10101","10011","10001","10001","10001"],
        "O": ["01110","10001","10001","10001","10001","10001","01110"],
        "P": ["11110","10001","10001","11110","10000","10000","10000"],
        "Q": ["01110","10001","10001","10001","10101","10010","01101"],
        "R": ["11110","10001","10001","11110","10100","10010","10001"],
        "S": ["01111","10000","10000","01110","00001","00001","11110"],
        "T": ["11111","00100","00100","00100","00100","00100","00100"],
        "U": ["10001","10001","10001","10001","10001","10001","01110"],
        "V": ["10001","10001","10001","10001","10001","01010","00100"],
        "W": ["10001","10001","10001","10101","10101","11011","10001"],
        "X": ["10001","10001","01010","00100","01010","10001","10001"],
        "Y": ["10001","10001","01010","00100","00100","00100","00100"],
        "Z": ["11111","00001","00010","00100","01000","10000","11111"],

        "0": ["01110","10001","10011","10101","11001","10001","01110"],
        "1": ["00100","01100","00100","00100","00100","00100","01110"],
        "2": ["01110","10001","00001","00010","00100","01000","11111"],
        "3": ["11110","00001","00001","01110","00001","00001","11110"],
        "4": ["00010","00110","01010","10010","11111","00010","00010"],
        "5": ["11111","10000","10000","11110","00001","00001","11110"],
        "6": ["01110","10000","10000","11110","10001","10001","01110"],
        "7": ["11111","00001","00010","00100","01000","01000","01000"],
        "8": ["01110","10001","10001","01110","10001","10001","01110"],
        "9": ["01110","10001","10001","01111","00001","00001","01110"],

        " ": ["00000"] * 7,
        ".": ["00000","00000","00000","00000","00000","00110","00110"],
        "!": ["00100","00100","00100","00100","00100","00000","00100"],
        "?": ["01110","10001","00001","00010","00100","00000","00100"],
        "-": ["00000","00000","00000","11111","00000","00000","00000"],
        ":": ["00000","00110","00110","00000","00110","00110","00000"],
    }

    def __init__(self, spi, cs, dc, rst):

        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst

        self.buffer = bytearray(1024)

        self._init_display()

    def _command(self, value):

        while not self.spi.try_lock():
            pass

        self.spi.configure(
            baudrate=4000000,
            polarity=0,
            phase=0
        )

        self.dc.value = False
        self.cs.value = False

        self.spi.write(bytes([value]))

        self.cs.value = True
        self.spi.unlock()

    def _data(self, data):

        while not self.spi.try_lock():
            pass

        self.spi.configure(
            baudrate=4000000,
            polarity=0,
            phase=0
        )

        self.dc.value = True
        self.cs.value = False

        self.spi.write(data)

        self.cs.value = True
        self.spi.unlock()

    def _init_display(self):

        self.rst.value = False
        time.sleep(0.1)

        self.rst.value = True
        time.sleep(0.1)

        commands = [
            (0xAE,),
            (0xD5, 0x80),
            (0xA8, 0x3F),
            (0xD3, 0x00),
            (0x40,),
            (0x8D, 0x14),
            (0x20, 0x00),
            (0xA1,),
            (0xC8,),
            (0xDA, 0x12),
            (0x81, 0xCF),
            (0xD9, 0xF1),
            (0xDB, 0x40),
            (0xA4,),
            (0xA6,),
            (0xAF,)
        ]

        for command in commands:

            for value in command:
                self._command(value)

    def clear(self):

        for i in range(1024):
            self.buffer[i] = 0

    def pixel(self, x, y):

        if 0 <= x < 128 and 0 <= y < 64:

            index = x + (y // 8) * 128

            self.buffer[index] |= 1 << (y % 8)

    def text(self, message, x=0, y=0):

        cursor_x = x
        cursor_y = y

        for character in message:

            if character == "\n":

                cursor_x = x
                cursor_y += 8

                continue

            character = character.upper()

            if character not in self.FONT:

                continue

            # Wrap automatically
            if cursor_x + 6 > 128:

                cursor_x = x
                cursor_y += 8

            if cursor_y + 7 > 64:

                break

            bitmap = self.FONT[character]

            for row in range(7):

                for col in range(5):

                    if bitmap[row][col] == "1":

                        self.pixel(
                            cursor_x + col,
                            cursor_y + row
                        )

            cursor_x += 6

    def show(self):

        self._command(0x21)
        self._command(0x00)
        self._command(0x7F)

        self._command(0x22)
        self._command(0x00)
        self._command(0x07)

        self._data(self.buffer)
        
import board
import busio
import digitalio

#from ssd1309 import SSD1309


spi = busio.SPI(
    clock=board.GP10,
    MOSI=board.GP11
)

cs = digitalio.DigitalInOut(board.GP9)
dc = digitalio.DigitalInOut(board.GP8)
rst = digitalio.DigitalInOut(board.GP12)

cs.direction = digitalio.Direction.OUTPUT
dc.direction = digitalio.Direction.OUTPUT
rst.direction = digitalio.Direction.OUTPUT

cs.value = True


oled = SSD1309(
    spi,
    cs,
    dc,
    rst
)


oled.clear()

oled.text(
    "Hello World!"
)

oled.show()

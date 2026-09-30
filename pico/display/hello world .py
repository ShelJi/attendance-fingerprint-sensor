import board
import busio
import digitalio
import time


# =========================================================
# SSD1309 CONFIGURATION
# =========================================================

WIDTH = 128
HEIGHT = 64


# =========================================================
# SPI
# =========================================================

spi = busio.SPI(
    clock=board.GP10,     # OLED CLK
    MOSI=board.GP11      # OLED DIN
)


# =========================================================
# OLED CONTROL PINS
# =========================================================

cs = digitalio.DigitalInOut(board.GP9)
dc = digitalio.DigitalInOut(board.GP8)
rst = digitalio.DigitalInOut(board.GP12)

cs.direction = digitalio.Direction.OUTPUT
dc.direction = digitalio.Direction.OUTPUT
rst.direction = digitalio.Direction.OUTPUT

cs.value = True


# =========================================================
# SPI COMMAND
# =========================================================

def command(cmd):
    while not spi.try_lock():
        pass

    spi.configure(
        baudrate=4000000,
        polarity=0,
        phase=0
    )

    dc.value = False
    cs.value = False

    spi.write(bytes([cmd]))

    cs.value = True
    spi.unlock()


# =========================================================
# SPI DATA
# =========================================================

def data(buffer):
    while not spi.try_lock():
        pass

    spi.configure(
        baudrate=4000000,
        polarity=0,
        phase=0
    )

    dc.value = True
    cs.value = False

    spi.write(buffer)

    cs.value = True
    spi.unlock()


# =========================================================
# OLED RESET
# =========================================================

rst.value = False
time.sleep(0.1)

rst.value = True
time.sleep(0.1)


# =========================================================
# SSD1309 INITIALIZATION
# =========================================================

command(0xAE)       # Display OFF

command(0xD5)       # Display clock
command(0x80)

command(0xA8)       # Multiplex ratio
command(0x3F)

command(0xD3)       # Display offset
command(0x00)

command(0x40)       # Display start line

command(0x8D)       # Charge pump
command(0x14)

command(0x20)       # Memory addressing mode
command(0x00)

command(0xA1)       # Segment remap

command(0xC8)       # COM scan direction

command(0xDA)       # COM pins
command(0x12)

command(0x81)       # Contrast
command(0xCF)

command(0xD9)       # Pre-charge
command(0xF1)

command(0xDB)       # VCOM detect
command(0x40)

command(0xA4)       # Display RAM

command(0xA6)       # Normal display

command(0xAF)       # Display ON


# =========================================================
# FRAMEBUFFER
# =========================================================

buffer = bytearray(WIDTH * HEIGHT // 8)


# =========================================================
# CLEAR SCREEN
# =========================================================

def clear():
    for i in range(len(buffer)):
        buffer[i] = 0


# =========================================================
# SET PIXEL
# =========================================================

def pixel(x, y, value=1):

    if x < 0 or x >= WIDTH:
        return

    if y < 0 or y >= HEIGHT:
        return

    index = x + (y // 8) * WIDTH
    bit = y & 7

    if value:
        buffer[index] |= (1 << bit)
    else:
        buffer[index] &= ~(1 << bit)


# =========================================================
# SEND BUFFER TO OLED
# =========================================================

def show():

    # Column address
    command(0x21)
    command(0x00)
    command(0x7F)

    # Page address
    command(0x22)
    command(0x00)
    command(0x07)

    # Send framebuffer
    data(buffer)


# =========================================================
# 5x7 FONT
# =========================================================

FONT = {

    "H": [
        0b10001,
        0b10001,
        0b10001,
        0b11111,
        0b10001,
        0b10001,
        0b10001
    ],

    "e": [
        0b00000,
        0b01110,
        0b10001,
        0b11111,
        0b10000,
        0b10001,
        0b01110
    ],

    "l": [
        0b01100,
        0b00100,
        0b00100,
        0b00100,
        0b00100,
        0b00100,
        0b01110
    ],

    "o": [
        0b00000,
        0b01110,
        0b10001,
        0b10001,
        0b10001,
        0b10001,
        0b01110
    ],

    "W": [
        0b10001,
        0b10001,
        0b10001,
        0b10101,
        0b10101,
        0b11011,
        0b10001
    ],

    "r": [
        0b00000,
        0b10110,
        0b11001,
        0b10000,
        0b10000,
        0b10000,
        0b10000
    ],

    "d": [
        0b00001,
        0b00001,
        0b01111,
        0b10001,
        0b10001,
        0b10001,
        0b01111
    ],

    "!": [
        0b00100,
        0b00100,
        0b00100,
        0b00100,
        0b00100,
        0b00000,
        0b00100
    ],

    " ": [
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000
    ]
}


# =========================================================
# DRAW CHARACTER
# =========================================================

def draw_char(char, x, y, scale=2):

    if char not in FONT:
        return

    bitmap = FONT[char]

    for row in range(7):

        for col in range(5):

            if bitmap[row] & (1 << (4 - col)):

                for sy in range(scale):

                    for sx in range(scale):

                        pixel(
                            x + col * scale + sx,
                            y + row * scale + sy,
                            1
                        )


# =========================================================
# DRAW TEXT
# =========================================================

def text(message, x, y, scale=2):

    cursor_x = x

    for char in message:

        draw_char(
            char,
            cursor_x,
            y,
            scale
        )

        cursor_x += 6 * scale


# =========================================================
# HELLO WORLD
# =========================================================

clear()

text(
    "Hello World!",
    10,
    20,
    scale=2
)

show()

print("Hello World displayed!")
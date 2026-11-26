import board
import busio
import digitalio
import time

# =========================
# SPI
# =========================

spi = busio.SPI(
    clock=board.GP10,   # CLK
    MOSI=board.GP11     # DIN
)

# =========================
# OLED pins
# =========================

cs = digitalio.DigitalInOut(board.GP9)
dc = digitalio.DigitalInOut(board.GP8)
rst = digitalio.DigitalInOut(board.GP12)

cs.direction = digitalio.Direction.OUTPUT
dc.direction = digitalio.Direction.OUTPUT
rst.direction = digitalio.Direction.OUTPUT

cs.value = True


# =========================
# Send command
# =========================

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


# =========================
# Send data
# =========================

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


# =========================
# RESET
# =========================

rst.value = False
time.sleep(0.1)

rst.value = True
time.sleep(0.1)


# =========================
# SSD1309 INITIALIZATION
# =========================

command(0xAE)       # Display OFF

command(0xD5)       # Display clock
command(0x80)

command(0xA8)       # Multiplex ratio
command(0x3F)

command(0xD3)       # Display offset
command(0x00)

command(0x40)       # Start line

command(0x8D)       # Charge pump
command(0x14)

command(0x20)       # Memory addressing
command(0x00)

command(0xA1)       # Segment remap

command(0xC8)       # COM scan direction

command(0xDA)       # COM pins
command(0x12)

command(0x81)       # Contrast
command(0xCF)

command(0xD9)       # Pre-charge
command(0xF1)

command(0xDB)       # VCOM
command(0x40)

command(0xA4)       # Display RAM

command(0xA6)       # Normal display

command(0xAF)       # Display ON


# =========================
# FULL SCREEN WHITE
# =========================

# 128 x 64 / 8 = 1024 bytes
buffer = bytearray([0xFF] * 1024)


# Column address
command(0x21)
command(0x00)
command(0x7F)

# Page address
command(0x22)
command(0x00)
command(0x07)

# Send pixels
data(buffer)

print("SSD1309 FULL SCREEN TEST")

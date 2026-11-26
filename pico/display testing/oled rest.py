import board
import busio
import digitalio
import time


# SPI
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
dc.value = True

# Hardware reset
rst.value = False
time.sleep(0.1)
rst.value = True
time.sleep(0.1)

print("OLED reset successful")	

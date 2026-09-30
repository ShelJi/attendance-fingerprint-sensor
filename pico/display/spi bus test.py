import board
import busio
import displayio
from fourwire import FourWire

displayio.release_displays()

spi = busio.SPI(
    clock=board.GP10,
    MOSI=board.GP11
)

display_bus = FourWire(
    spi,
    command=board.GP8,
    chip_select=board.GP9,
    reset=board.GP12
)

print("SPI display bus created successfully")

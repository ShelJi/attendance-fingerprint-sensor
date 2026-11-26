import board
import busio

i2c = busio.I2C(board.GP9, board.GP8)

while not i2c.try_lock():
    pass

print("I2C devices:")

print([hex(x) for x in i2c.scan()])

i2c.unlock()
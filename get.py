import time
from machine import I2C,Pin
from vl53l1x import VL53L1X

""" パラメータ """
I2C_SCL_PIN = 22  #自分で指定
I2C_SDA_PIN = 21  #自分で指定
""" パラメータ(終わり) """
i2c = I2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))

distance = VL53L1X(i2c) #20mm~400mm
while True:
    print("range: mm ", distance.read())
    time.sleep_ms(50)

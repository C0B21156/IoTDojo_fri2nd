import peripheral2
import central2
import ubluetooth
import utime
import ubinascii
from micropython import const

ble=ubluetooth.BLE()

def exec():
    #central2.Centr()
    #utime.sleep_ms(2000)
    peripheral2.periph()
    utime.sleep_ms(2000)
    #ble.active(False)


if __name__ == "__main__":
    exec()

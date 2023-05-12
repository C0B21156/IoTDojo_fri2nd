


# This example demonstrates a simple temperature sensor peripheral.
#
# The sensor's local value updates every second, and it will notify
# any connected central every 10 seconds.

import bluetooth
import random
import struct
import time
import binascii
from central2 import BLEDevCentral
from BLE_advertising import advertising_payload

from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_INDICATE_DONE = const(20)

_FLAG_READ = const(0x0002)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)

# デバイス情報サービス
_Dev_Info_UUID = bluetooth.UUID(0x180A)
# デバイスの名前
_Dev_CHAR = (bluetooth.UUID(0x2A00),
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE,) #読、通知、応答要求付き通知
_Dev_SERVICE = (_Dev_Info_UUID,(_Dev_CHAR,),)

class BLE:

    ble = None
    name = None

    def __init__(self, ble, name="esp32-3"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle,),) = self._ble.gatts_register_services((_Dev_SERVICE,))
        self._connections = set()
        self._payload = advertising_payload(
            name=name, services=[_Dev_Info_UUID], appearance= 0)
        self._advertise()

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._advertise()
        elif event == _IRQ_GATTS_INDICATE_DONE:
            conn_handle, value_handle, status = data

    def set_dev_name(self, dev_name, notify=False, indicate=False):
        # Data is sint16 in degrees Celsius with a resolution of 0.01 degrees Celsius.
        # Write the local value, ready for a central to read.
        self._ble.gatts_write(self._handle, struct.pack('12si',dev_name)) #読み込み可能な書き込み
        if notify or indicate:
            for conn_handle in self._connections:
                if notify:
                    # Notify connected centrals.
                    self._ble.gatts_notify(conn_handle, self._handle)
                if indicate:
                    # Indicate connected centrals.
                    self._ble.gatts_indicate(conn_handle, self._handle)

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)


def periph():
    ble = bluetooth.BLE()
    ble.config(gap_name='senser05')
    set_name = ble.config('gap_name')
    #addr = ble.config('mac')
    #print(addr[1])
    print(binascii.hexlify("esp32"))
    b = BLE(ble)
    #val = BLEDevCentral._update_value(self, data):
    #print(val)
    #print(Centr)

    i = 0
    count = 0

    while count < 2: #2回出力
    #while True: #無限ループ
        # Write every second, notify every 10 seconds.
        i = (i + 1) % 10
        b.set_dev_name(set_name, notify=i == 0, indicate=False)
        ##Random walk the temperature.
        print(set_name)
        time.sleep_ms(1000)
        count += 1

if __name__ == "__main__":
    periph()
# This example demonstrates a simple temperature sensor peripheral.
#
# The sensor's local value updates every second, and it will notify
# any connected central every 10 seconds.

import bluetooth
import random
import struct
import utime
import binascii
from BLE_advertising import advertising_payload
import manegment_8

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

    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle,),) = self._ble.gatts_register_services((_Dev_SERVICE,))
        self._connections = set()
        self._check = False

    def _payload_1(self, name):
        self._name = name
        self._payload_1 = advertising_payload(
            name=name, services=[_Dev_Info_UUID], appearance= 0)
        self._advertise()
        
    def _payload_2(self, name):
        self._name = name
        self._payload_2 = advertising_payload(
            name=name, services=[_Dev_Info_UUID], appearance= 0)
        self._stop()


    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            self._check = True
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._check = False
            self._advertise()
        elif event == _IRQ_GATTS_INDICATE_DONE:
            conn_handle, value_handle, status = data

    def set_dev_name(self, name, notify=False, indicate=False):
        # Data is sint16 in degrees Celsius with a resolution of 0.01 degrees Celsius.
        # Write the local value, ready for a central to read.
        fm = '{}si'.format(len(name))
        self._ble.gatts_write(self._handle, struct.pack(fm,name)) #読み込み可能な書き込み
        #self._ble.gatts_write(self._handle, name)
        if notify or indicate:
            for conn_handle in self._connections:
                if notify:
                    # Notify connected centrals.
                    self._ble.gatts_notify(conn_handle, self._handle)
                if indicate:
                    # Indicate connected centrals.
                    self._ble.gatts_indicate(conn_handle, self._handle)

    def _advertise(self, interval_us=100000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload_1)

    def _stop(self, interval_us = None):
        self._ble.gap_advertise(interval_us, adv_data=self._payload_2)


def periph(timeout=10):
    ble = bluetooth.BLE()
    gapname = manegment_8.nameinfo()
    ble.config(gap_name= str(gapname))
    set_name = ble.config('gap_name')
    print(set_name)
    
    print(type(set_name))
    set_name = set_name.decode('utf-8')
    print(type(set_name))
    data = set_name

    b = BLE(ble)

    i = 0
    connect_count = 0

    if b._check is False:
        b._payload_1("com8")
        while timeout > 0:
            i = (i + 1) % 10
            b.set_dev_name(data, notify=i == 0, indicate=False)
            print(".")
            utime.sleep_ms(1000)
            timeout -=1
            
    if timeout is 0:
        b._payload_2("com8")
        b.set_dev_name(data, notify=i == 0, indicate=False)
        print("終了")
        
    


if __name__ == "__main__":
    periph()
import bluetooth
import random
import struct
import utime
import binascii
from BLE_advertising import advertising_payload
# import manegement_s1
import info 
import json

from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTS_INDICATE_DONE = const(20)

_FLAG_READ = const(0x0002)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)

# デバイス情報サービス
_Dev_Info_UUID = bluetooth.UUID(0x180A)
# デバイスの名前
_Dev_CHAR = (bluetooth.UUID(0x2A00),
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE,) # 読み取り，通知，応答要求付き通知
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
        self._connect_count = 0

    def _payload_1(self, name):
        self._name = name
        self._payload_1 = advertising_payload(
            name=name, services=[_Dev_Info_UUID], appearance=0)
        self._advertise()
        
    def _payload_2(self, name):
        self._name = name
        self._payload_1 = advertising_payload(
            name=name, services=[_Dev_Info_UUID], appearance=0)
        self._advertise()
        
    def _payload_3(self, name):
        self._name = name
        self._payload_2 = advertising_payload(
            name=name, services=[_Dev_Info_UUID], appearance=0)
        self._stop()

    def _irq(self, event, data):
        # 接続を追跡して通知を送信できるようにする．
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            self._check = True
            print(self._check)
            self._connect_count += 1
            print(f"connection : {self._connect_count}")
            utime.sleep_ms(3000)
            self._check = False
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            # 新しい接続を許可するために再びアドバタイズを開始する．
            self._check = False
            #self._advertise()

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            # 新しい接続を許可するために再びアドバタイズを開始する．
            self._check = False
            #self._advertise()

        elif event == _IRQ_GATTS_INDICATE_DONE:
            conn_handle, value_handle, status = data
            print(data)

    def set_dev_name(self, name, notify=False, indicate=False):
        fm = '{}si'.format(len(name))
        self._ble.gatts_write(self._handle, struct.pack(fm, name))  # 読み込み可能な書き込み
        if notify or indicate:
            for conn_handle in self._connections:
                if notify:
                    # 接続されたセントラルに通知する．
                    self._ble.gatts_notify(conn_handle, self._handle)
                if indicate:
                    # 接続されたセントラルに示す．
                    self._ble.gatts_indicate(conn_handle, self._handle)

    def _advertise(self, interval_us=100000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload_1)

    def _stop(self, interval_us=None):
        self._ble.gap_advertise(interval_us, adv_data=self._payload_2)

def periph(timeout=10):
    ble = bluetooth.BLE()
    
    # gapname = manegement_s1.nameinfo()
    jf_open = open('info/SN01.json', 'r')
    jf_load = json.load(jf_open)
    gapname = jf_load["device_number"]
    
    ble.config(gap_name=str(gapname))
    set_name = ble.config('gap_name')
    print(set_name)
    
    print(type(set_name))
    set_name = set_name.decode('utf-8')
    print(type(set_name))
    data = set_name

    b = BLE(ble)

    i = 0
    
    b._payload_1(jf_load["packet_routeTS"])
    print(timeout)
    print(b._connect_count)
    while timeout > 1 or b._connect_count is 0:
        if b._check is False:
            i = (i + 1) % 10
            b.set_dev_name(data, notify=i == 0, indicate=False)
            print(".")
            utime.sleep_ms(1000)
            timeout -=1

    if timeout is 0 or b._connect_count is 1:
        b._payload_3(jf_load["packet_routeTS"])
        b.set_dev_name(data, notify=i == 0, indicate=False)
    print("終了")
    return b._connect_count
        
if __name__ == "__main__":
    periph()
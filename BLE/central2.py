import bluetooth
import random
import struct
import utime
import ubinascii
import micropython

from BLE_advertising import decode_services, decode_name

from micropython import const

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_GATTC_INDICATE = const(19)

_ADV_IND = const(0x00)
_ADV_DIRECT_IND = const(0x01)
_ADV_SCAN_IND = const(0x02)
_ADV_NONCONN_IND = const(0x03)

# org.bluetooth.service.environmental_sensing
_Dev_Info_UUID = bluetooth.UUID(0x180A)
# org.bluetooth.characteristic.temperature
_Dev_Name_UUID = bluetooth.UUID(0x2A00)
_Dev_CHAR = (_Dev_Name_UUID,bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,)
_ENV_SENSE_SERVICE = (_Dev_Info_UUID,(_Dev_CHAR,),)


def form_mac_address(addr: bytes) -> str:
    return ":".join('{:02x}'.format(b) for b in addr)

class BLEDevCentral:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)

        self._reset()

    def _reset(self):
        # Cached name and address from a successful scan.
        self._name = None
        self._addr_type = None
        self._addr = None

        # Cached value (if we have one)
        self._value = None

        # Callbacks for completion of various operations.
        # These reset back to None after being invoked.
        self._scan_callback = None
        self._conn_callback = None
        self._read_callback = None

        # Persistent callback for when new data is notified from the device.
        self._notify_callback = None

        # Connected device.
        self._conn_handle = None
        self._start_handle = None
        self._end_handle = None
        self._value_handle = None

    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            adv = ubinascii.hexlify(adv_data)
            adr = ubinascii.hexlify(addr)
            if '6573703332' in adv: #esp32
            #if '65737033322d34' in adv: #esp32-4
                adv = str(ubinascii.unhexlify(adv), 'utf-8')
                print('type:{} addr:{} rssi:{} data:{}'.format(addr_type, adr, rssi, adv))    
                if adv_type in (_ADV_IND, _ADV_DIRECT_IND) and _Dev_Info_UUID in decode_services(adv_data):
                    # Found a potential device, remember it and stop scanning.
                    self._addr_type = addr_type
                    self._addr = bytes(addr)  # Note: addr buffer is owned by caller so need to copy it.
                    self._name = adv or "?"
                    self._ble.gap_scan(None)

        elif event == _IRQ_SCAN_DONE:
            print('Scan compelete')
            if self._scan_callback:
                if self._addr:
                    # Found a device during the scan (and the scan was explicitly stopped).
                    self._scan_callback(self._addr_type, self._addr, self._name)
                    print("callbask is:", self._scan_callback)
                    self._scan_callback = None
                else:
                    # Scan timed out.
                    self._scan_callback(None, None, None)

        elif event == _IRQ_PERIPHERAL_CONNECT: #gap_connect()が成功しました。
            # Connect successful.
            conn_handle, addr_type, addr = data
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
                self._ble.gattc_discover_services(self._conn_handle) #characteristicsについて問い合わせる
                print('peripheral discovered')

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Disconnect (either initiated by us or the remote end).
            conn_handle, _, _ = data
            if conn_handle == self._conn_handle:
                # If it was initiated by us, it'll already be reset.
                self._reset()

        elif event == _IRQ_GATTC_SERVICE_RESULT:#_ble.gattc_discover_servicesy結果より発生する
            # Connected device returned a service.
            conn_handle, start_handle, end_handle, uuid = data
            if conn_handle == self._conn_handle and uuid == _Dev_Info_UUID:
                self._start_handle, self._end_handle = start_handle, end_handle

        elif event == _IRQ_GATTC_SERVICE_DONE: #上のイベントの検索が完了すると発生する
            # Service query complete.
            if self._start_handle and self._end_handle:
                self._ble.gattc_discover_characteristics(
                    self._conn_handle, self._start_handle, self._end_handle
                )
            else:
                print("Failed to find environmental sensing service.")

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Connected device returned a characteristic.
            conn_handle, def_handle, value_handle, properties, uuid = data
            if conn_handle == self._conn_handle and uuid == _Dev_Name_UUID:
                self._value_handle = value_handle

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            # Characteristic query complete.
            if self._value_handle:
                # We've finished connecting and discovering device, fire the connect callback.
                if self._conn_callback:
                    self._conn_callback()
            else:
                print("Failed to find temperature characteristic.")

        elif event == _IRQ_GATTC_READ_RESULT: #読み込みイベント
            # A read completed successfully.
            conn_handle, value_handle, char_data = data
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                self._update_value(char_data)
                if self._read_callback:
                    self._read_callback(self._value)
                    #print("12345")
                    #print(self._value)
                    self._read_callback = self._value
                    return self._read_callback

        elif event == _IRQ_GATTC_READ_DONE:
            # Read completed (no-op).
            conn_handle, value_handle, status = data

        elif event == _IRQ_GATTC_NOTIFY:
            # The ble_temperature.py demo periodically notifies its value.
            conn_handle, value_handle, notify_data = data
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                self._update_value(notify_data)
                if self._notify_callback:
                    self._notify_callback(self._value)

    # Returns true if we've successfully connected and discovered characteristics.
    def is_connected(self):
        return self._conn_handle is not None and self._value_handle is not None

    # Find a device advertising the environmental sensor service.
    def scan(self, callback=None):
        self._addr_type = None
        self._addr = None
        self._scan_callback = callback
        self._ble.gap_scan(7000, 6000, 6000)

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, addr_type=None, addr=None, callback=None): #connect関数
        self._addr_type = addr_type or self._addr_type
        self._addr = addr or self._addr
        self._conn_callback = callback
        if self._addr_type is None or self._addr is None:
            return False
        # if アドバタイズの中身が~だったら
        #print(self._addr)
        self._ble.gap_connect(self._addr_type, self._addr) #接続要求
        return True

    # Disconnect from current device.
    def disconnect(self):
        if not self._conn_handle:
            return
        self._ble.gap_disconnect(self._conn_handle)
        self._reset()

    # Issues an (asynchronous) read, will invoke callback with data.
    def read(self, callback):
        if not self.is_connected():
            return
        self._read_callback = callback
        self._ble.gattc_read(self._conn_handle, self._value_handle) #リモート読み込み

    # Sets a callback to be invoked when the device notifies us.
    def on_notify(self, callback):
        self._notify_callback = callback

    def _update_value(self, data):
        # Data is sint16 in degrees Celsius with a resolution of 0.01 degrees Celsius.
        self._value = ubinascii.hexlify(data)
        self._value = bytes(self._value)
        self._value = str(ubinascii.unhexlify(self._value), 'utf-8')
        return self._value #ここでscan内容出力

    def value(self):
        return self._value


def Centr():
    ble = bluetooth.BLE()
    ble.config(gap_name='senser04')
    set_name = ble.config('gap_name')
    print(set_name)
    central = BLEDevCentral(ble)

    not_found = False

    def on_scan(addr_type, addr, name): #scanのcallback
        if addr_type is not None:
            #もし、nameがsenser01なら
            name = ubinascii.hexlify(name)
            addr = ubinascii.hexlify(addr)
            name = str(ubinascii.unhexlify(name), 'utf-8')
            print("Found sensor:", addr_type, addr, name)
            central.connect()
        else:
            nonlocal not_found
            not_found = True
            print("No sensor found.")

    central.scan(callback=on_scan) #def scan

    # Wait for connection...
    while not central.is_connected():
        utime.sleep_ms(100)
        if not_found:
            return

    print("Connected")

    # Explicitly issue reads, using "print" as the callback.
    count = 0
    while count < 3:
        central.read(callback=print)
        print("#####")
        utime.sleep_ms(2000)
        count += 1
        print(count)
    senser = central._read_callback
    print(senser)
    central.disconnect()
    print("Disconnected")
    return senser

if __name__ == "__main__":
    Centr()
import threading
import serial
import socket
import base64
import json
import time
from glob import glob

from serial.tools import list_ports

DEBUG = True
DEBUG2 = False

def dprint(*data, **kargs):
    if DEBUG2:
        print(*data)

# スレッドを停止するためのイベント
stop_event = threading.Event()

class ESP32Communicator:
    """
    ESP32とのシリアル通信をするクラス
    """
    def __init__(self, front_communicator):
        self.front_communicator = front_communicator
        # シリアルポートを見つけて接続
        self.serial_port = self.find_serial_port()
        self.serial_connection = serial.Serial(self.serial_port, 115200, timeout=1)
        self.received_data = None
        self.udp_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    
    def find_serial_port(self):
        serial_ports = glob('/dev/ttyUSB*')
        return serial_ports[0]
    

    def read_data(self):
        """
        ESP32からシリアルデータを読み取り、デコードしてUDPで送信する
        """
        while not stop_event.is_set():
            if self.serial_connection.in_waiting >= 13:
                raw_data = self.serial_connection.readline().decode('ASCII').rstrip()
                if DEBUG:
                    print(f"Received raw data: {raw_data}")
                decoded_data = int.from_bytes(base64.b64decode(raw_data), 'little')
                #print(f"Decoded data: {bin(decoded_data)}")
                self.received_data = decoded_data
                self.process_data(decoded_data)

    def process_data(self, data):
        """
        受信データを解析し、FRONT側に送信する
        """
        parsed_data = self.parse_data(data)
        #print(f"Parsed Data: {parsed_data}")

        json_data = self.front_communicator.convert_to_json(parsed_data)
        self.front_communicator.send_data(json_data)

    def parse_data(self, data):
        """
        データをフォーマットに基づいて解析する
        """
        format_value = (data >> 58) & 0x3F
        if format_value in [11, 21, 31, 41]:
            print(bin(data))
            parsed_data = {
                'format': format_value,
                'field1': (data >> 50) & 0xFF,  # 8-bit field
                'field2': (data >> 42) & 0xFF,  # 8-bit field
                'field3': (data >> 34) & 0xFF,  # 8-bit field
                'field4': (data >> 22) & 0xFFF,  # 12-bit field
                'field5': (data >> 10) & 0xFFF  # 12-bit field
            }
        else:
            parsed_data = {
                'format': format_value,
                'field1': (data >> 46) & 0xFFF,  # 12-bit field
                'field2': (data >> 34) & 0xFFF,  # 12-bit field
                'field3': (data >> 22) & 0xFFF   # 12-bit field
            }
        return parsed_data
    
    def send_to_esp32(self, data):
        """
        フロントエンドから受け取ったデータをESP32に送る
        """
        byte_len = (data.bit_length() + 7) // 8
        b64_esp32_com = base64.b64encode(data.to_bytes(byte_len, 'big')) + b'\n'

        print('send_data=', b64_esp32_com)

        self.serial_connection.write(b64_esp32_com)

class FrontCommunicator:
    """
    フロントエンドとのUDP通信を行うクラス
    """
    def __init__(self, esp32_communicator, ip="0.0.0.0", port_send=6050, port_receive=6060):
        self.esp32_communicator = esp32_communicator
        self.front_ip = "192.168.11.34"
        self.udp_ip = ip
        self.udp_port_send = port_send
        self.udp_port_receive = port_receive
        self.udp_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.udp_ip, self.udp_port_receive))
        # cylinderを辞書型として初期化
        self.cylinder = {}
        # Fixed Motion
        self.fixed_motion_thread = None
        self.fix_inprocess_flag = False

    def send_data(self, data):
        """
        解析されたデータをUDPでフロントエンドに送信
        """
        json_string = json.dumps(data)  # 辞書をJSON文字列に変換
        if DEBUG:
            print(f"Sending data: {json_string}")  # デバッグ用
        self.udp_send_socket.sendto(json_string.encode('utf-8'), (self.front_ip, self.udp_port_send))
        if DEBUG:
            print(f"Sent data to {self.udp_ip}:{self.udp_port_send} -> {json_string}")

    def convert_to_json(self, data):
        """
        データをフロントエンドが期待するJSON形式に変換
        """
        if data['format'] in [5, 6, 7, 8]:
            sensor_num = data['format'] - 5
            self.cylinder[sensor_num] = {"position": data['field1'], "voltage": data['field2'], "command": data['field3']}
            return {
                "type": "current_sensor_value",
                "sensors": [
                    {"num": sensor_num, "position": data['field1'], "voltage": data['field2'], "command": data['field3']}
                ]
            }
        elif data['format'] in [11, 21, 31, 41]:
            print("[DEBUG] ### CGC Response", data)
            return {
                "type": "response_gain_value",
                "num": (data['format'] - 10) // 10,
                "gains": {
                    "p": data['field1'],
                    "i": data['field2'],
                    "d": data['field3'],
                },
                "capture": {
                    "max": data['field4'],
                    "min": data['field5'],
                }
            }
        else:
            raise ValueError("Unsupported type")

    def receive_data(self):
        """
        フロントエンドからのUDPデータを受信して表示
        """
        field1 = 0 #初期化
        while not stop_event.is_set():
            data, addr = self.udp_socket.recvfrom(1024)
            json_data = data.decode('utf-8')
            print(f"Received data from {addr}: {json_data}")
            trans_data = json.loads(json_data)
            if trans_data['type'] == "set_target_value":
                format_value = 63
                if 'position' in trans_data:
                    bit_input = 0b0000  # positionの場合は0000
                    #TODO trans_data['position'][0]の使い方が意図したものではない。。添え字番号=='num'にしたい
                    if trans_data['position'][0]['num'] == "0":
                        field1 = int(trans_data['position'][0]['value'])
                        field2 = self.cylinder[1]['position']
                        field3 = self.cylinder[2]['position']
                        field4 = self.cylinder[3]['position']
                    elif trans_data['position'][0]['num'] == "1":
                        field1 = self.cylinder[0]['position']
                        field2 = int(trans_data['position'][0]['value'])
                        field3 = self.cylinder[2]['position']
                        field4 = self.cylinder[3]['position']
                    elif trans_data['position'][0]['num'] == "2":
                        field1 = self.cylinder[0]['position']
                        field2 = self.cylinder[1]['position']
                        field3 = int(trans_data['position'][0]['value'])
                        field4 = self.cylinder[3]['position']
                    elif trans_data['position'][0]['num'] == "3":
                        field1 = self.cylinder[0]['position']
                        field2 = self.cylinder[1]['position']
                        field3 = self.cylinder[2]['position']
                        field4 = int(trans_data['position'][0]['value'])
                elif 'command' in trans_data:
                    valve_map = 2.275
                    bit_input = 0b1111  # commandの場合は1111
                    if trans_data['command'][0]['num'] == "0":
                        field1 = int(int(trans_data['command'][0]['value'])/valve_map)
                        field2 = self.cylinder[1]['command']
                        field3 = self.cylinder[2]['command']
                        field4 = self.cylinder[3]['command']
                    elif trans_data['command'][0]['num'] == "1":
                        field1 = self.cylinder[0]['command']
                        field2 = int(int(trans_data['command'][0]['value'])/valve_map)
                        field3 = self.cylinder[2]['command']
                        field4 = self.cylinder[3]['command']
                    elif trans_data['command'][0]['num'] == "2":
                        field1 = self.cylinder[0]['command']
                        field2 = self.cylinder[1]['command']
                        field3 = int(int(trans_data['command'][0]['value'])/valve_map)
                        field4 = self.cylinder[3]['command']
                    elif trans_data['command'][0]['num'] == "3":
                        field1 = self.cylinder[0]['command']
                        field2 = self.cylinder[1]['command']
                        field3 = self.cylinder[2]['command']
                        field4 = int(int(trans_data['command'][0]['value'])/valve_map)
                        
                data = (format_value << 58) | (bit_input << 54) | (field1 << 42) | (field2 << 30) | (field3 << 18) | (field4 << 6)
                self.esp32_communicator.send_to_esp32(data)
          
            elif trans_data['type'] == "request_gain_value":
                format_value = 1
                if trans_data['num'] == "0":
                    field1 = 0b1000
                elif trans_data['num'] == "1":
                    field1 = 0b0100
                elif trans_data['num'] == "2":
                    field1 = 0b0010
                elif trans_data['num'] == "3":
                    field1 = 0b0001
                else:
                    assert False
                data = (format_value << 58) | (field1<< 54)
                self.esp32_communicator.send_to_esp32(data)
                
            elif trans_data['type'] == "request_capture":
                # ID 6bit
                format_value = 50

                # シリンダー番号 4bit
                if trans_data['num'] == "0":
                    field1 = 0b1000
                elif trans_data['num'] == "1":
                    field1 = 0b0100
                elif trans_data['num'] == "2":
                    field1 = 0b0010
                elif trans_data['num'] == "3":
                    field1 = 0b0001
                else:
                    assert False

                # キャプチャ位置 2bit
                if trans_data['capture'] == "offset":
                    field2 = 0b01
                elif trans_data['capture'] == "stroke":
                    field2 = 0b10
                else:
                    assert False

                data = (format_value << 58) | (field1 << 54) | (field2 << 52)
                self.esp32_communicator.send_to_esp32(data)
                
            elif trans_data['type'] == "set_gain_value":
                if 'num' in trans_data == 1:
                    format_value = 10
                    P = float(trans_data['p'])
                    I = float(trans_data['i'])
                    D = float(trans_data['d'])
                    #  各ゲインを10倍する
                    Pbin = (P * 10)
                    Ibin = (I * 10)
                    Dbin = (D * 10)
                    data = (format_value << 58) | (Pbin << 50) | (Ibin << 42) | (Dbin << 34)
                    self.esp32_communicator.send_to_esp32(data) 
                elif 'num' in trans_data == 2:
                    format_value = 21
                    P = float(trans_data['p'])
                    I = float(trans_data['i'])
                    D = float(trans_data['d'])
                    #  各ゲインを10倍する
                    Pbin = (P * 10)
                    Ibin = (I * 10)
                    Dbin = (D * 10)
                    data = (format_value << 58) | (Pbin << 50) | (Ibin << 42) | (Dbin << 34)
                    self.esp32_communicator.send_to_esp32(data) 
                elif 'num' in trans_data == 3:
                    format_value = 31
                    P = float(trans_data['p'])
                    I = float(trans_data['i'])
                    D = float(trans_data['d'])
                    #  各ゲインを10倍する
                    Pbin = (P * 10)
                    Ibin = (I * 10)
                    Dbin = (D * 10)
                    data = (format_value << 58) | (Pbin << 50) | (Ibin << 42) | (Dbin << 34)
                    self.esp32_communicator.send_to_esp32(data) 
                elif 'num' in trans_data == 4:
                    format_value = 41
                    P = float(trans_data['p'])
                    I = float(trans_data['i'])
                    D = float(trans_data['d'])
                    #  各ゲインを10倍する
                    Pbin = (P * 10)
                    Ibin = (I * 10)
                    Dbin = (D * 10)
                    data = (format_value << 58) | (Pbin << 50) | (Ibin << 42) | (Dbin << 34)
                    self.esp32_communicator.send_to_esp32(data) 
                    
            elif trans_data['type'] == "fixed_motion":
                    format_value = 63
                    bit_input = 0b1111
                    if trans_data["motion"] == 'crawl':
                        print('crawl')
                        if not self.fix_inprocess_flag:
                            self.fixed_motion_thread = threading.Thread(target=self.crawl_motion)
                            self.fixed_motion_thread.start()
                        h1 = 0
                        k1 = 0
                        h2 = 0
                        k2 = 0
                        data = (format_value << 58) | (bit_input << 54) | (h1 << 42) | (k1 << 30) | (h2 << 28) | (k2 << 16)
                        self.esp32_communicator.send_to_esp32(data)
                    elif trans_data["motion"] == 'trot':
                        print('trot')
                        h1 = 0
                        k1 = 0
                        h2 = 0
                        k2 = 0
                        data = (format_value << 58) | (bit_input << 54) | (h1 << 42) | (k1 << 30) | (h2 << 28) | (k2 << 16)
                    elif trans_data["motion"] == 'pace':
                        print('pace')
                        h1 = 0
                        k1 = 0
                        h2 = 0
                        k2 = 0
                        data = (format_value << 58) | (bit_input << 54) | (h1 << 42) | (k1 << 30) | (h2 << 28) | (k2 << 16)
                    elif trans_data["motion"] == 'bound':
                        print('bound')

    def crawl_motion(self):
        # 同時に実行されることを防ぐフラグ
        self.fix_inprocess_flag = True

        wait_time = 0.3

        # initialization
        pos_h0 = 0
        pos_h1 = 0
        pos_k0 = 0
        pos_k1 = 0

        # Status
        state = 0

        while True:
            if state == 0:
                # hipを伸ばす
                pos_h0 += 64
                if pos_h0 >= 4095:
                    state = 1
            elif state == 1:
                # kneeを伸ばす
                pos_k0 += 64
                if pos_k0 >= 1536:
                    state = 2
            elif state == 2:
                # hipを縮めてkneeを伸ばす
                pos_h0 -= 128
                pos_k0 += 64
                if (pos_h0 <= 0) or (pos_k0 >= 4095):
                    state = 3
            elif state == 3:
                # kneeを縮める
                pos_k0 -= 128
                if (pos_k0 <= 0):
                    state = 4
                    break
            
            # 動作を送信
            format_value = 63
            bit_input = 0b1111
            data = (format_value << 58) | (bit_input << 54) | (pos_h0 << 42) | (pos_k0 << 30) | (pos_h1 << 18) | (pos_k1 << 6)

            self.esp32_communicator.send_to_esp32(data)
            print(f'id:{format_value}, bit:{bin(bit_input)}, state:{state}, h0:{pos_h0}, k0:{pos_k0}')

            time.sleep(wait_time)

        # Whileから抜けたらthreadを初期化
        self.fix_inprocess_flag = False
    
    def trot_motion(self):
        pass

    def pace_motion(self):
        pass

    def bound_motion(self):
        pass
            

class MainApp:
    """
    メインアプリケーションクラス
    """
    def __init__(self):
        self.front_communicator = FrontCommunicator(None)  # ここで一時的に None を渡す
        self.esp32_communicator = ESP32Communicator(self.front_communicator)
        self.front_communicator.esp32_communicator = self.esp32_communicator

    def run(self):
        """
        ESP32とフロントエンドの通信をスレッドで並行実行
        """
        self.cylinder = [{"position": None, "voltage": None, "command": None} for _ in range(4)]
        esp32_receiver = threading.Thread(target=self.esp32_communicator.read_data)
        front_receiver = threading.Thread(target=self.front_communicator.receive_data)
        esp32_receiver.start()
        front_receiver.start()
        
        
    def stop(self):
        """
        スレッドを停止する
        """
        stop_event.set()

# Main entry point
if __name__ == "__main__":
    try:
        MainApp().run()
    except KeyboardInterrupt:
        stop_event.set()
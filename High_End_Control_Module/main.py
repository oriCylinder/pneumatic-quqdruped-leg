import threading
import serial
import socket
import base64
import json
import glob

from serial.tools import list_ports

# スレッドを停止するためのイベント
stop_event = threading.Event()

class ESP32Communicator:
    """
    ESP32とのシリアル通信をするクラス
    """
    def __init__(self):
        # シリアルポートを見つけて接続
        self.serial_port = self.find_serial_port()
        self.serial_connection = serial.Serial(self.serial_port, 115200, timeout=1)
        self.received_data = None
        self.udp_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    '''
    def find_serial_port(self):
        serial_ports = glob('/dev/ttyUSB*')
        for port in serial_ports:
            try:
                ser = serial.Serial(port, 115200, timeout=1)
                if ser.in_waiting > 0:
                    print(f"Using port: {port}")
                    ser.close()
                    return port
            except:
                continue
        raise Exception("No valid serial ports found")
    '''
    def find_serial_port(self):
        """
        シリアルポートを探索する（Windowsに対応）
        """
        available_ports = list_ports.comports()
        for port in available_ports:
            try:
                ser = serial.Serial(port.device, 115200)
                print(f"Using dummy port: {port.device}")
                ser.close()
                return port.device
            except:
                continue
        raise Exception("No valid serial ports found for dummy ESP32")

    def read_data(self):
        """
        ESP32からシリアルデータを読み取り、デコードしてUDPで送信する
        """
        while not stop_event.is_set():
            if self.serial_connection.in_waiting >= 13:
                raw_data = self.serial_connection.readline().decode('utf-8').rstrip()
                print(f"Raw data length: {len(raw_data)}")  # デバッグ用
                decoded_data = int.from_bytes(base64.b64decode(raw_data), 'little')
                print(f"Received raw data: {raw_data}")
                self.received_data = decoded_data
                self.process_data(decoded_data)

    def process_data(self, data):
        """
        受信データを解析し、UDPで送信する
        """
        parsed_data = self.parse_data(data)
        self.udp_sender.sendto(json.dumps(parsed_data).encode('utf-8'), ("0.0.0.0", 6050))
        print(f"Parsed Data: {parsed_data}")

    def parse_data(self, data):
        """
        データをフォーマットに基づいて解析する
        """
        format_value = (data >> 58) & 0x3F
        if format_value in [11, 21, 31, 41]:
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
                'field1': (data >> 48) & 0xFFF,  # 12-bit field
                'field2': (data >> 36) & 0xFFF,  # 12-bit field
                'field3': (data >> 24) & 0xFFF   # 12-bit field
            }
        return parsed_data

class FrontCommunicator:
    """
    フロントエンドとのUDP通信を行うクラス
    """
    def __init__(self, ip="0.0.0.0", port_send=6050, port_receive=6060):
        self.udp_ip = ip
        self.udp_port_send = port_send
        self.udp_port_receive = port_receive
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.udp_ip, self.udp_port_receive))

    def send_data(self, data):
        """
        解析されたデータをUDPでフロントエンドに送信
        """
        json_data = self.convert_to_json(data)
        json_string = json.dumps(json_data)  # 辞書をJSON文字列に変換
        print(f"Sending data: {json_string}")  # デバッグ用
        self.udp_socket.sendto(json_string.encode('utf-8'), (self.udp_ip, self.udp_port_send))
        print(f"Sent data to {self.udp_ip}:{self.udp_port_send} -> {json_string}")

    def convert_to_json(self, data):
        """
        データをフロントエンドが期待するJSON形式に変換
        """
        if data['format'] in [5, 6, 7, 8]:
            sensor_num = data['format'] - 5
            return {
                "type": "current_sensor_value",
                "sensors": [
                    {"num": sensor_num, "position": data['field1'], "voltage": data['field2'], "command": data['field3']}
                ]
            }
        elif data['format'] in [11, 21, 31, 41]:
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
        while not stop_event.is_set():
            data, addr = self.udp_socket.recvfrom(1024)
            json_data = data.decode('utf-8')
            print(f"Received data from {addr}: {json_data}")
            # ESP32に戻して送信する場合、下記にシリアル書き込み処理を追加可能
            # self.serial_connection.write(json_data.encode('utf-8'))

class MainApp:
    """
    メインアプリケーションクラス
    """
    def __init__(self):
        self.esp32_communicator = ESP32Communicator()
        self.front_communicator = FrontCommunicator()

    def run(self):
        """
        ESP32とフロントエンドの通信をスレッドで並行実行
        """
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
    MainApp().run()
import time
import base64
import serial
import random
from serial.tools import list_ports

class DummyESP32:
    def __init__(self):
        self.serial_port = self.find_serial_port()
        self.serial_connection = serial.Serial(self.serial_port, 115200)

    def find_serial_port(self):
        # Windowsでも動作するように、利用可能なポートを探す
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

    def generate_data(self):
        # ダミーデータ生成: 64ビットデータをシリアル送信するように模擬する
        format_value = random.choice([5, 6, 7, 8, 11, 21, 31, 41])  # ランダムにフォーマット値を選ぶ
        field1 = random.randint(0, 0xFFF)  # 12ビットフィールド
        field2 = random.randint(0, 0xFFF)  # 12ビットフィールド
        field3 = random.randint(0, 0xFFF)  # 12ビットフィールド

        # フォーマット値をビットシフトして、全体の64ビットデータを作成する
        data = (format_value << 58) | (field1 << 48) | (field2 << 36) | (field3 << 24)
        return data

    def encode_and_send_data(self):
        while True:
            # 64ビットのダミーデータを生成
            data = self.generate_data()

            # バイナリデータをBase64にエンコードして送信する
            encoded_data = base64.b64encode(data.to_bytes(8, 'little')).decode('utf-8')

            # シリアルポートにデータを書き込み（送信）
            self.serial_connection.write((encoded_data + '\n').encode('utf-8'))
            print(f"Sent dummy data: {encoded_data}")

            # 1秒待機して次のデータを送信
            time.sleep(1)

if __name__ == "__main__":
    dummy_esp32 = DummyESP32()
    dummy_esp32.encode_and_send_data()
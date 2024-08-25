import socket
import json
import time
import random

# サンプルデータの作成
def generate_data():
    return {
        "sensors": [
            {"num": i, "position": random.randint(0, 4095), "voltage": random.randint(0, 4095), "command": random.randint(0, 1800)} 
            for i in range(5)  # 例として5個のセンサー
        ],
        "targets": [
             {"num": i, "val": random.randint(0, 100)} 
             for i in range(5)  # 例として5個のセンサー
        ]
    }

# UDP送信先のIPアドレスとポート
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# ソケットの作成
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# データの送信
while True:
    data = generate_data()
    json_data = json.dumps(data)
    sock.sendto(json_data.encode('utf-8'), (UDP_IP, UDP_PORT))
    print(f"Sent: {json_data}")
    time.sleep(1)  # 5秒間隔で送信
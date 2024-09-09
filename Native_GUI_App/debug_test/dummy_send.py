import socket
import json
import time
import random
import threading

# サンプルデータの作成
def generate_data(i):
    return {
        "type":"current_sensor_value",
        "sensors": [
            {"num": i, "position": random.randint(0, 4095), "voltage": random.randint(0, 4095), "command": random.randint(0, 4095)} 
        ]
    }

# UDP送信先のIPアドレスとポート
IP = "127.0.0.1"
UDP_PORT = 6050

stop_event = threading.Event()

# UDP サーバー
def udp_server():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #udp_socket.bind((IP, UDP_PORT))
    print("UDPサーバーが待機中...")
    i = 0
    
    while not stop_event.is_set():
        if i == 8:
            i = 0
        data = generate_data(i)
        json_data = json.dumps(data)
        udp_socket.sendto(json_data.encode('utf-8'), (IP, UDP_PORT))
        print(f"UDP送信: {json_data}")
        i+=1
        time.sleep(0.1)
    
    udp_socket.close()
    print("UDPサーバーを終了しました。")

if __name__ == "__main__":
    udp_thread = threading.Thread(target=udp_server)

    udp_thread.start()

    try:
        while  udp_thread.is_alive():
            udp_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\nプログラムを終了します...")
        stop_event.set()  # 終了フラグを立てる
        udp_thread.join()
import socket
import json
import time
import random
import threading

# サンプルデータの作成
def generate_data():
    return {
        "sensors": [
            {"num": i, "position": random.randint(0, 4095), "voltage": random.randint(0, 4095), "command": random.randint(0, 1800)} 
            for i in range(5)  # 例として5個のセンサー
        ],
        "targets": [
            {"num": i, "val": random.randint(0, 100)} 
            for i in range(5)  # 例として5個のターゲット
        ]
    }

# UDP送信先のIPアドレスとポート
IP = "127.0.0.1"
UDP_PORT = 6050
TCP_PORT = 6000

stop_event = threading.Event()

# TCP サーバー
def tcp_server():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.settimeout(10)  # タイムアウトを設定（10秒）
    tcp_socket.bind((IP, TCP_PORT))
    try:
        tcp_socket.listen(1)
        print("TCPサーバーが待機中...")
        conn, addr = tcp_socket.accept()
        print(f"TCPクライアントが接続: {addr}")
        conn.sendall(b'connected')

        while not stop_event.is_set():
            try:
                data = conn.recv(1024)
                if not data:
                    print("クライアントが切断しました。")
                    break
                print(f"TCP受信: {data.decode('utf-8')}")
            except socket.timeout:
                print("タイムアウトしました。接続を切断します。")
                break
    except socket.timeout:
        print("クライアントが接続しませんでした。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()
        tcp_socket.close()
        print("TCPサーバーを終了しました。")

# UDP サーバー
def udp_server():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((IP, UDP_PORT))
    print("UDPサーバーが待機中...")
    
    while not stop_event.is_set():
        data = generate_data()
        json_data = json.dumps(data)
        udp_socket.sendto(json_data.encode('utf-8'), (IP, UDP_PORT))
        print(f"UDP送信: {json_data}")
        time.sleep(1)
    
    udp_socket.close()
    print("UDPサーバーを終了しました。")

if __name__ == "__main__":
    tcp_thread = threading.Thread(target=tcp_server)
    udp_thread = threading.Thread(target=udp_server)

    tcp_thread.start()
    udp_thread.start()

    try:
        while tcp_thread.is_alive() or udp_thread.is_alive():
            tcp_thread.join(timeout=1)
            udp_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\nプログラムを終了します...")
        stop_event.set()  # 終了フラグを立てる
        tcp_thread.join()
        udp_thread.join()
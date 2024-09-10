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

flag = 0

# UDP サーバー
def udp_sender():
    global flag
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #udp_socket.bind((IP, UDP_PORT))
    print("UDPサーバーが待機中...")
    i = 0
    
    while not stop_event.is_set():
        if flag == 1:
            data = {"type": "response_gain_value", "gains": {"p":"10","i":"20","d":"30"}, "capture": {"max":"1000","min":"100"}}
            json_data = json.dumps(data)
            udp_socket.sendto(json_data.encode('utf-8'), (IP, UDP_PORT))
            flag = 0
        else:
            if i == 8:
                i = 0
            data = generate_data(i)
            json_data = json.dumps(data)
            udp_socket.sendto(json_data.encode('utf-8'), (IP, UDP_PORT))
            print(f"UDP送信: {json_data}")
            i+=1
        time.sleep(1/30)
    
    udp_socket.close()
    print("UDPサーバーを終了しました。")

def udp_receiver():
    global flag
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((IP, 6060))
    
    while not stop_event.is_set():              
        data, addr = udp_socket.recvfrom(4096)
        receive_data = data.decode()
        trans_data = json.loads(receive_data)
        if trans_data['type'] == 'request_gain_value' or trans_data['type'] == 'set_gain_value' or trans_data['type'] == 'request_capture' or trans_data['type'] == 'request_gain_save':
            flag = 1
        print(trans_data)
        time.sleep(0.1)
    
    udp_socket.close()



if __name__ == "__main__":
    udp_s_thread = threading.Thread(target=udp_sender)
    udp_r_thread = threading.Thread(target=udp_receiver)

    udp_s_thread.start()
    udp_r_thread.start()

    try:
        while  udp_s_thread.is_alive() and udp_r_thread.is_alive():
            udp_s_thread.join(timeout=1)
            udp_r_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\nプログラムを終了します...")
        stop_event.set()  # 終了フラグを立てる
        udp_s_thread.join()
        udp_r_thread.join()
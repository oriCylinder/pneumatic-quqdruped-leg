import socket
import json
import time
import random
import threading
from pprint import pprint
import serial
import base64
import struct
from bitarray import bitarray

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

# UDP送信先のIPアドレスとポート
IP = "192.168.11.34"
UDP_PORT = 6050

stop_event = threading.Event()

def gen_com_set_target_value(data_json):
        # 最初の6ビットは63（111111）、次の4ビットは識別子0000
    identifier_bits = '111111'  # 63の6ビット表現
    if data_json["type"] == "set_target_value":
        mid_bits = '0000'  # targetの場合の識別子
    else:
        raise ValueError("Unsupported type")

    # target_valuesをcylinder_numの昇順にソート
    sorted_values = sorted(data_json["target_values"], key=lambda x: x["cylinder_num"])

    # 最初の10ビットから始まるビット列
    bit_list = [identifier_bits + mid_bits]

    for target in sorted_values:
        value = target["value"] & 0xFFF  # 12ビット

        # valueを12ビットのバイナリ文字列に変換
        bits = f'{value:012b}'
        bit_list.append(bits)

    # 全てのビットを連結して1つのビット列にする
    return ''.join(bit_list)
    # TODO 3.2 /3.3フォーマット変換実装中
    #return 0b1111110000111111111111000000000000111111111111000000000000000000  # サンプル位置指示
    #return 0b0000010010111111111111000000000000111111111111000000000000000000


def listen_front():
    # udpのソケットをバインドして待ち受け
    src_ip = "0.0.0.0"                             # 受信元IP
    src_port = 6050                                # 受信元ポート番号
    src_addr = (src_ip, src_port)                 # アドレスをtupleに格納

    BUFSIZE = 1024                             # バッファサイズ指定
    udp_serv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # ソケット作成
    udp_serv_sock.bind(src_addr)

    while not stop_event.is_set():                                     # 常に受信待ち

        data, addr = udp_serv_sock.recvfrom(BUFSIZE)# 受信
        data_json = json.loads(data.decode())
        #print(addr)                  # 受信データと送信アドレス表示
        #pprint(data_json)
        
        # 3.データ生成
        #print(data_json["type"], data_json["type"] == "set_target_value")
        if data_json["type"] == "set_target_value":
            esp32_com = gen_com_set_target_value(data_json)

        # 4.シリアルでデータ送信
        esp32_com = esp32_com.ljust(64, '0')
        #print(esp32_com)
        esp32_com_int = int(esp32_com, 2)
        byte_len = (esp32_com_int.bit_length() + 7) // 8
        b64_esp32_com = base64.b64encode(esp32_com_int.to_bytes(byte_len, 'big'))
        ser.write(b64_esp32_com + b'\n')
        #print(f"Sent binary data: {(b64_esp32_com.decode())}")

        #print(ser.read(4096))
    
def listen_esp32():
    global _parsedData
    global _getData

    # serial待ち受け

    # 1.serialでデータを受信
    if ser.in_waiting >= 14:
        #ser.read(10560) #から読み、データバッファをカラにする
        #data = ser.readline()
        data = ser.readline().decode('utf-8').rstrip()
        #bits = bitarray(endian='big')
        #bits.frombytes(data)
        #print(data)
        
        data2 = int.from_bytes(base64.b64decode(data), 'little')
        _getData = data2
        #print(bin(data2))
        data_parse()
        print(_parsedData['format'])
        print(_parsedData['field1'])
        print(_parsedData['field2'])
        print(_parsedData['field3'])
        # 000000000000000010000000 b64decode
        #time.sleep(1)#while (serialでデータが来た)
        #jsonを作る関数をここに
        pvc_data = convert_to_json()
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # udp_socket.((IP, UDP_PORT))

        while True:
            udp_socket.sendto(pvc_data.encode('utf-8'), (IP, 6050))
            #print(f"UDP送信: {pvc_data}")
        udp_socket.close()
        print("UDPサーバーを終了しました。")

        

    # 2.構文解析
                # 3.データ生成
                # 4.udpでデータ受信

# グローバル変数
_getData = 0
_parsedData = {
    'format': 0,
    'field1': 0,
    'field2': 0,
    'field3': 0,
    'field4': 0,
    'field5': 0,
    'field6': 0,
    'field7': 0,
    'field8': 0,
}

def data_parse():
    global _getData, _parsedData

    # フォーマットの抽出
    _parsedData['format'] = (_getData >> 58) & 0x3F # 受信したデータの頭6ビットをフォーマット番号として代入

    format_value = _parsedData['format']#5,6,7,8,11,21,31,41が来るはず
    # PVC1~4とCGC1~4
    if format_value in(5, 6, 7, 8):
         parse_fields(12, 12, 12, 0, 0, 0, 0, 0)
    elif format_value in(11, 21, 31, 41):
         parse_fields(8, 8, 8, 8, 12, 12)
    else:
        _parsedData['field1'] = 5000

def parse_fields(len1, len2, len3, len4, len5, len6, len7, len8): # 
    global _getData, _parsedData

    shift = 58

    def get_field(len_value):
        nonlocal shift
        if len_value > 0:
            shift -= len_value
            field_value = (_getData >> shift) & ((1 << len_value) - 1)
        else:
            field_value = 0
        return field_value

    _parsedData['field1'] = get_field(len1)
    _parsedData['field2'] = get_field(len2)
    _parsedData['field3'] = get_field(len3)
    _parsedData['field4'] = get_field(len4)
    _parsedData['field5'] = get_field(len5)
    _parsedData['field6'] = get_field(len6)
    _parsedData['field7'] = get_field(len7)
    _parsedData['field8'] = get_field(len8)

    # 残りのデータが有効かどうかをチェック
    if (_getData & 0x1F) > 0:
        return False

    return True

def convert_to_json():
    global _parsedData

    if _parsedData['format'] == 5:
        pvc_data = {
            "type":"current_sensor_value",
            "sensors":[
            {"num":0, "position":_parsedData['field1'], "voltage":_parsedData['field2'], "comand":_parsedData['field3']} 
        ]
    }
    elif _parsedData['format'] == 6:
        pvc_data = {
            "type":"current_sensor_value",
            "sensors":[
            {"num":1, "position":_parsedData['field1'], "voltage":_parsedData['field2'], "comand":_parsedData['field3']}
        ]
    }
    elif _parsedData['format'] == 7:
        pvc_data = {
            "type":"current_sensor_value",
            "sensors":[
            {"num":2, "position":_parsedData['field1'], "voltage":_parsedData['field2'], "comand":_parsedData['field3']} 
        ]
    }
    elif _parsedData['format'] == 8:
        pvc_data = {
            "type":"current_sensor_value",
            "sensors":[
            {"num":3, "position":_parsedData['field1'], "voltage":_parsedData['field2'], "comand":_parsedData['field3']}
        ]
    }
    try:
        json_data = json.dumps(pvc_data, ensure_ascii=False, indent=4)
        return json_data
    except (TypeError, ValueError) as e:
            return str(e)


if __name__ == "__main__":
    front_thread = threading.Thread(target=listen_front)
    esp32_thread = threading.Thread(target=listen_esp32)

    front_thread.start()
    esp32_thread.start()

    try:
        while  front_thread.is_alive():
            front_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\nプログラムを終了します...")
        stop_event.set()  # 終了フラグを立てる
        front_thread.join()

from kivymd.app import MDApp
from kivy.properties import StringProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.transition.transition import MDSharedAxisTransition
from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivymd.uix.navigationdrawer import MDNavigationDrawer, MDNavigationDrawerLabel, MDNavigationDrawerItem

from kivy.core.text import LabelBase, DEFAULT_FONT

from kivy.core.window import Window
from kivy.lang import Builder

from kivy.clock import Clock
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
from matplotlib import font_manager

import socket
import json
import threading
import time

# フォントの追加
font_manager.fontManager.addfont("./font/NotoSansJP-Regular.ttf") #matplotlib
plt.rc('font', family="Noto Sans JP")
LabelBase.register(DEFAULT_FONT, './font/NotoSansJP-Regular.ttf') #Kivy

class StartScreen(MDScreen):
    pass

class MainScreen(MDScreen):
    pass

class NonInteractiveCard(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = [20, 20, 20, 20]  # 左、上、右、下の順に余白を設定
    def set_properties_widget(self):
        return False
    def on_touch_down(self,touch):
        return False
    
class UDPClient:
    def __init__(self, ip, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((ip, port))
        except (OSError, socket.error) as e:
            raise ValueError(f"Invalid address: {ip}:{port}. Error: {e}")
        
        self.sock.settimeout(3.0)  # 3秒間通信がないとタイムアウト

    def receive_message(self):
        try:
            data, _ = self.sock.recvfrom(1024)  # データを受信
            return data.decode()
        except socket.timeout:
            return None
        
    def close(self):
        self.sock.close()

class UDPCommunicator:
    def __init__(self, ip, port, fps):
        self.udp_ip = ip
        self.udp_port = port
        self.frame_duration = 1 / fps
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_message(self, data):
        message = json.dumps(data)
        self.sock.sendto(message.encode(), (self.udp_ip, self.udp_port))

    def receive_message(self, buffer_size=1024):
        try:
            self.sock.settimeout(self.frame_duration)
            data, addr = self.sock.recvfrom(buffer_size)
            # 受信データをデシリアライズして返す
            return json.loads(data.decode()), addr
        except socket.timeout:
            return None, None
        except json.JSONDecodeError:
            print("Received data is not valid JSON")
            return None, None

    def run(self,data_to_send):
        try:
            while True:
                start_time = time.time()
                
                # 受信
                received_data, addr = self.receive_message()
                if received_data:
                    print(f"Received message: {received_data} from {addr}")
                else:
                    print("No data received")

                # 送信
                self.send_message(data_to_send)

                # 次のフレームまでの待機
                elapsed_time = time.time() - start_time
                sleep_time = self.frame_duration - elapsed_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            self.sock.close()

class SettingsManager:
    def __init__(self, filename='settings.json'):
        self.filename = filename
        self.settings = self.load_settings()

    def load_settings(self):
        """設定をJSONファイルから読み込みます。ファイルが存在しない場合は空の設定を返します。"""
        try:
            with open(self.filename, 'r') as file:
                settings = json.load(file)
        except FileNotFoundError:
            settings = {}  # デフォルト設定を定義
        return settings

    def save_settings(self):
        """現在の設定をJSONファイルに保存します。"""
        with open(self.filename, 'w') as file:
            json.dump(self.settings, file, indent=4)

    def update_setting(self, key, value):
        """設定を更新します。"""
        self.settings[key] = value

    def get_setting(self, key, default=None):
        """設定を取得します。指定されたキーが存在しない場合はデフォルト値を返します。"""
        return self.settings.get(key, default)
    
class MainApp(MDApp):
    slider_value = StringProperty("0")    
    def __init__(self, **kwargs):
        super(MainApp, self).__init__(**kwargs)
        self.settings_manager = SettingsManager()
        self.theme_cls.theme_style_switch_animation = True
        self.theme_cls.theme_style = self.settings_manager.get_setting('theme')
        self.theme_cls.primary_palette = self.settings_manager.get_setting('color')
        self.client = None
        self.running = False
        
    def build(self):
        # ScreenManagerのインスタンスを作成
        self.screen_manager = MDScreenManager(transition=MDSharedAxisTransition())

        # 各 .kv ファイルを読み込み、画面を追加
        Builder.load_file('start.kv')
        Builder.load_file('main.kv')

        # ScreenManagerに各スクリーンを追加
        self.screen_manager.add_widget(StartScreen())
        self.screen_manager.add_widget(MainScreen())
        
        self.screen_manager.get_screen('start').ids.address_field.text = self.settings_manager.get_setting('address')

        return self.screen_manager
    
    def on_start(self):
        Window.maximize()
        self.screen_manager.get_screen('main').ids.nav_drawer.set_state("open")

    def switch_theme_style(self):
        self.theme_cls.theme_style = (
            "Dark" if self.theme_cls.theme_style == "Light" else "Light"
        )
        self.settings_manager.update_setting('theme', self.theme_cls.theme_style)
        self.settings_manager.save_settings()

    def show_snackbar(self, message):
        snackbar = MDSnackbar(
            MDSnackbarText(
                text=message,
            ),
            pos_hint={"center_x": 0.5, "center_y":0.1},
            size_hint_x=0.5,
        )
        snackbar.open()

    def change_screen(self, screen_name):
        self.root.current = screen_name
        
    def switch_actuator(self):
        slider_value = StringProperty("0")
        
    def connect(self):
        connect_button = self.screen_manager.get_screen('start').ids.connect_button
        address_field = self.screen_manager.get_screen('start').ids.address_field
        progressindicator = self.screen_manager.get_screen('start').ids.progressindicator
        self.settings_manager.update_setting('address', self.screen_manager.get_screen('start').ids.address_field.text)
        self.settings_manager.save_settings()
        connect_button.disabled = True
        address_field.disabled = True
        progressindicator.active = True
        
        try:
            self.client = UDPClient(address_field.text, 5005)
            self.running = True
            self.thread = threading.Thread(target=self.receive_data)
            self.thread.start()
        except ValueError:
            self.disconnect()
            self.show_snackbar("Disconnected")  # エラーメッセージをsnackbarに表示
            self.status_text = "Disconnected"
        
    def receive_data(self):
        while self.running:
            message = self.client.receive_message()
            if message:
                try:
                    data = json.loads(message)  # JSONデータをパース
                    Clock.schedule_once(lambda dt: self.change_screen('main'))
                    #self.process_data(data)  # データの処理
                except json.JSONDecodeError:
                    self.status_text = "Received invalid JSON"
                    Clock.schedule_once(lambda dt: self.show_snackbar("Received invalid JSON"))
            else:
                self.status_text = "Connection Failed"
                # Clockを使ってメインスレッドでスナックバーを表示
                Clock.schedule_once(lambda dt: self.show_snackbar("Connection Failed"))
                Clock.schedule_once(lambda dt: self.disconnect())
                break
            time.sleep(1)
    
    def process_data(self):
        # numリストを表示
        self.nav_drawer_menu.clear_widgets()
        for num in self.num_list:
            label = MDNavigationDrawerLabel(text=f"Sensor {num}")
            label.bind(on_release=lambda x, num=num: self.select_num(num))
            self.nav_drawer_menu.add_widget(label)
        
    def disconnect(self):
        self.change_screen('start')
        connect_button = self.screen_manager.get_screen('start').ids.connect_button
        address_field = self.screen_manager.get_screen('start').ids.address_field
        progressindicator = self.screen_manager.get_screen('start').ids.progressindicator
        connect_button.disabled = False
        address_field.disabled = False
        progressindicator.active = False

        self.running = False
        if self.client:
            self.client.close()
        self.status_text = "Disconnected"

    def on_stop(self):
        self.disconnect()
        
        
if __name__ == '__main__':
    MainApp().run()
# GUIライブラリのインポート
from kivymd.app import MDApp
from kivy.lang import Builder

# GUIコンポーネント関連
from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

# Kivyフォント関連
from kivy.core.text import LabelBase, DEFAULT_FONT
LabelBase.register(DEFAULT_FONT, './font/NotoSansJP-Regular.ttf')

# グラフ描画関連
from kivy.clock import Clock
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont("./font/NotoSansJP-Regular.ttf") #matplotlib
plt.rc('font', family="Noto Sans JP")

# 画面遷移関連
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager

# 通信関連
import json
import socket
import threading

class StartScreen(MDScreen):
    def on_connect_button_press(self):
        """接続ボタンが押されたときに通信を開始します。"""
        app = MDApp.get_running_app()
        app.start_communication()

class MainScreen(MDScreen):
    def update_tcp_label(self, message):
        """TCPからのメッセージを表示します。"""
        self.ids.tcp_label.text = f"TCP受信: {message}"

    def update_udp_label(self, message):
        """UDPからのメッセージを表示します。"""
        self.ids.udp_label.text = f"UDP受信: {message}"

    def on_disconnect_button_press(self):
        """切断ボタンが押されたときに通信を切断します。"""
        app = MDApp.get_running_app()
        app.stop_communication()

class PageManager(MDScreenManager):
    pass
    
class NativeGUIApp(MDApp):
    Builder.load_file('layout.kv')
    
    def build(self):
        self.screen_manager = PageManager()
        self.settings_manager = SettingsManager()
        self.theme_cls.theme_style_switch_animation = True
        self.theme_cls.theme_style = self.settings_manager.get_setting('theme')
        self.theme_cls.primary_palette = self.settings_manager.get_setting('color')
        self.screen_manager.get_screen('start').ids.address_field.text = self.settings_manager.get_setting('address')

        self.connect_button = self.screen_manager.get_screen('start').ids.connect_button
        self.address_field = self.screen_manager.get_screen('start').ids.address_field
        self.progressindicator = self.screen_manager.get_screen('start').ids.progressindicator

        self.tcp_thread = None
        self.udp_thread = None
        
        return self.screen_manager
    
    def start_communication(self):
        """TCPの通信を開始します。"""
        address_field = self.screen_manager.get_screen('start').ids.address_field

        if not self.tcp_thread:
            self.running = True
            self.tcp_thread = threading.Thread(target=self.tcp_client, args=(address_field.text,))
            self.tcp_thread.start()

    def stop_communication(self, error):
        """TCPとUDPの通信を切断します。"""
        self.running = False
        Clock.schedule_once(lambda dt: self.change_screen('start'))
        self.connect_button.disabled = False
        self.address_field.disabled = False
        self.progressindicator.active = False

        Clock.schedule_once(lambda dt: self.show_snackbar(error)) # エラーメッセージをsnackbarに表示

        if self.tcp_thread:
            self.tcp_socket.close()
            self.tcp_thread = None
            #self.screen_manager.get_screen('main').update_tcp_label("TCP切断")
        if self.udp_thread:
            self.udp_socket.close()
            self.udp_thread = None
            #self.screen_manager.get_screen('main').update_udp_label("UDP切断")
        print("切断しました")

    def tcp_client(self,address):
        self.settings_manager.update_setting('address', self.screen_manager.get_screen('start').ids.address_field.text)
        self.settings_manager.save_settings()
        self.connect_button.disabled = True
        self.address_field.disabled = True
        self.progressindicator.active = True

        print("TCPサーバーに接続中")
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((address, 6000))
            print("接続完了")
            
            response = self.tcp_socket.recv(1024)
            print(f"サーバーからのメッセージ: {response.decode()}")
            Clock.schedule_once(lambda dt: self.change_screen('main'))
            #Clock.schedule_once(lambda dt: self.screen_manager.get_screen('main').update_tcp_label(response.decode()))

            # TCP接続が確立されたので、UDP接続を開始
            self.udp_thread = threading.Thread(target=self.udp_client, args=(address,))
            self.udp_thread.start()

            while self.running:
                #TCP通信->Server
                #message = self.screen_manager.get_screen('start').ids.input_field.text
                message = "TCP_SPEAKING"
                if message:
                    self.tcp_socket.sendall(message.encode())
                    if message.lower() == "exit":
                        break

        except Exception as e:
            print(f"TCPクライアントエラー: {e}")
            self.stop_communication("TCPサーバーに接続できません")
        finally:
            if self.tcp_socket:
                self.tcp_socket.close()
                self.tcp_socket = None

    def udp_client(self,address):
        print("UDPサーバーに接続中")
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(("localhost", 6050))
            print("UDPでサーバーからのメッセージを受信中...")

            while True:
                data, addr = self.udp_socket.recvfrom(1024)
                print(f"UDP 受信: {data.decode()}")
                #Clock.schedule_once(lambda dt: self.screen_manager.get_screen('main').update_udp_label(data.decode()))

        except Exception as e:
            print(f"UDPクライアントエラー: {e}")
            self.stop_communication("UDPサーバーに接続できません")
        finally:
            if self.udp_socket:
                self.udp_socket.close()
                self.udp_socket = None
    
    def switch_theme_style(self):
        self.theme_cls.theme_style = (
            "Dark" if self.theme_cls.theme_style == "Light" else "Light"
        )
        self.settings_manager.update_setting('theme', self.theme_cls.theme_style)
        self.settings_manager.save_settings()

    def change_screen(self, screen_name):
        self.root.current = screen_name

    def show_snackbar(self, message):
        snackbar = MDSnackbar(
            MDSnackbarText(
                text=message,
            ),
            pos_hint={"center_x": 0.5, "center_y":0.1},
            size_hint_x=0.5,
        )
        snackbar.open()
    
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
    
class NonInteractiveCard(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = [20, 20, 20, 20]  # 左、上、右、下の順に余白を設定
    def set_properties_widget(self):
        return False
    def on_touch_down(self,touch):
        return False

if __name__ == '__main__':
    NativeGUIApp().run()
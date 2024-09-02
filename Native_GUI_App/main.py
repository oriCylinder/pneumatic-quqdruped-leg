# GUIライブラリのインポート
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.config import Config
Config.set('graphics', 'maxfps', 60)
Config.set('kivy', 'kivy_clock', 'free_all')

# GUIコンポーネント関連
from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivy.uix.boxlayout import BoxLayout

# Kivyフォント関連
from kivy.core.text import LabelBase, DEFAULT_FONT
LabelBase.register(DEFAULT_FONT, './font/NotoSansJP-Regular.ttf')

# グラフ描画関連
import numpy as np
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

stop_event = threading.Event()

class StartScreen(MDScreen):
    def on_connect_button_press(self):
        """接続ボタンが押されたときに通信を開始します。"""
        app = MDApp.get_running_app()
        app.start_communication()

class MainScreen(MDScreen):
    def on_disconnect_button_press(self):
        """切断ボタンが押されたときに通信を切断します。"""
        app = MDApp.get_running_app()
        app.stop_communication("切断されました")

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

        self.udp_thread = None
        
        return self.screen_manager
    
    def on_stop(self):
        stop_event.set()
        return True
    
    def start_communication(self):
        """UDP通信を開始します。"""
        address_field = self.screen_manager.get_screen('start').ids.address_field
        
        self.udp_thread = None
        stop_event.clear()

        if not self.udp_thread:
            self.udp_thread = threading.Thread(target=self.udp_client, args=(address_field.text,))
            self.udp_thread.start()

    def stop_communication(self, message):
        """UDPの通信を切断します。"""
        self.change_screen('start')
        self.connect_button.disabled = False
        self.address_field.disabled = False
        self.progressindicator.active = False
        
        stop_event.set()
        Clock.schedule_once(lambda dt: self.show_snackbar(message)) # エラーメッセージをsnackbarに表示
    
    def udp_client(self,address):
        self.settings_manager.update_setting('address', self.screen_manager.get_screen('start').ids.address_field.text)
        self.settings_manager.save_settings()
        self.connect_button.disabled = True
        self.address_field.disabled = True
        self.progressindicator.active = True
        
        print("UDPサーバーに接続中")
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.settimeout(3)
            self.udp_socket.bind((address, 6050))
            print("UDPでサーバーからのメッセージを受信中...")
            
            #初回のデータを受け取ったときの処理
            data, addr = self.udp_socket.recvfrom(1024)
            print(f"Connected: {addr}")
            Clock.schedule_once(lambda x: self.change_screen('main'))
            
            #グラフ描画
            while not stop_event.is_set():
                data, addr = self.udp_socket.recvfrom(1024)
                print(f"UDP 受信: {data.decode()}")
                
            self.udp_socket.close()
            self.udp_socket = None
            print("切断しました")

        except Exception as e:
            print(f"UDPクライアントエラー: {e}")
            self.stop_communication("UDPサーバーに接続できません")
            
    
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
    
class GraphView(BoxLayout):
    """Matplotlib のグラフを表示するためのウィジェット"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 初期化に用いるデータ
        x = np.linspace(-np.pi, np.pi, 100)
        y = np.sin(x)
        # 描画状態を保存するためのカウンタ
        self.counter = 0

        # Figure, Axis を保存しておく
        self.fig, self.ax = plt.subplots()
        # 最初に描画したときの Line も保存しておく
        self.line, = self.ax.plot(x, y)

        # ウィジェットとしてグラフを追加する
        widget = FigureCanvasKivyAgg(self.fig)
        self.add_widget(widget)

        # 0.033 秒ごとに表示を更新するタイマーを仕掛ける
        Clock.schedule_interval(self.update_view, 0.033)
        
    def update_view(self, *args, **kwargs):
        # データを更新する
        self.counter += np.pi / 100  # 10 分の pi ずらす
        # ずらした値を使ってデータを作る
        x = np.linspace(-np.pi + self.counter,
                        np.pi + self.counter,
                        100)
        y = np.sin(x)
        # Line にデータを設定する
        self.line.set_data(x, y)
        # グラフの見栄えを調整する
        self.ax.relim()
        self.ax.autoscale_view()
        # 再描画する
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        
    
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
# GUIライブラリのインポート
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.config import Config
from kivy.core.window import Window
Config.set('graphics', 'maxfps', 60)

# GUIコンポーネント関連
from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivymd.uix.navigationdrawer import MDNavigationDrawerItem, MDNavigationDrawerItemText, MDNavigationDrawerLabel

# Kivyフォント関連
from kivy.core.text import LabelBase, DEFAULT_FONT
LabelBase.register(DEFAULT_FONT, './font/NotoSansJP-Regular.ttf')

# グラフ描画関連
import numpy as np
from kivy.clock import Clock
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib
matplotlib.use('Agg')   #非アクティブになる現象を抑止
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont("./font/NotoSansJP-Regular.ttf") #matplotlib
plt.rc('font', family="Noto Sans JP")

# 画面遷移関連
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from functools import partial

# 通信関連
import json
import socket
import threading
import time
import datetime
import random

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
    trans_data =  ''
    selected_actuater = 0
    
    def build(self):    #描画が始まる前の処理
        self.screen_manager = PageManager()
        self.settings_manager = SettingsManager()
        self.theme_cls.theme_style_switch_animation = True
        self.theme_cls.theme_style = self.settings_manager.get_setting('theme')
        self.theme_cls.primary_palette = self.settings_manager.get_setting('color')
        self.screen_manager.get_screen('start').ids.address_field.text = self.settings_manager.get_setting('address')

        self.connect_button = self.screen_manager.get_screen('start').ids.connect_button
        self.address_field = self.screen_manager.get_screen('start').ids.address_field
        self.progressindicator = self.screen_manager.get_screen('start').ids.progressindicator

        self.graph_area = self.screen_manager.get_screen('main').ids.graph_area

        self.udp_thread = None
        
        return self.screen_manager
    
    def on_start(self): #描画が始まったときの処理
        Window.maximize()
        self.screen_manager.get_screen('main').ids.nav_drawer.set_state("open")
    
    def on_stop(self):  #描画が止まるときの処理
        stop_event.set()
        return True
    
    def start_communication(self):
        """UDP通信を開始（スレッド）"""
        address_field = self.screen_manager.get_screen('start').ids.address_field
        address = address_field.text
        
        #送り側のソケットを定義
        self.dynamicUdpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.udpClntSock.sendto(data, (address,6050)) 送るとき
        
        self.udp_thread = None
        stop_event.clear()

        if not self.udp_thread:
            self.udp_thread = threading.Thread(target=self.udp_receiver, args=(address,))
            self.udp_thread.start()

    def stop_communication(self, message):
        """UDPの通信を切断します。"""
        self.change_screen('start')
        self.connect_button.disabled = False
        self.address_field.disabled = False
        self.progressindicator.active = False
        
        stop_event.set()
        Clock.schedule_once(lambda dt: self.show_snackbar(message)) # エラーメッセージをsnackbarに表示
    
    def udp_receiver(self,address):
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
            data, addr = self.udp_socket.recvfrom(4096)
            self.receive_data = data.decode()
            print(f"Connected: {addr}")
            Clock.schedule_once(lambda x: self.change_screen('main'))
            
            #データの取得と変数への格納
            while not stop_event.is_set():                
                data, addr = self.udp_socket.recvfrom(4096)
                receive_data = data.decode()
                self.trans_data = json.loads(receive_data)
                
                self.position = next((sensor['position'] for sensor in self.trans_data.get('sensors', []) if sensor.get('num') == int(self.selected_actuater)), None)
                self.voltage = next((sensor['voltage'] for sensor in self.trans_data.get('sensors', []) if sensor.get('num') == int(self.selected_actuater)), None)
                self.command = next((sensor['command'] for sensor in self.trans_data.get('sensors', []) if sensor.get('num') == int(self.selected_actuater)), None)
                
            self.udp_socket.close()
            self.udp_socket = None
            print("切断しました")

        except Exception as e:
            print(f"UDPクライアントエラー: {e}")
            self.stop_communication("UDPサーバーに接続できません")

    def change_screen(self, screen_name):
        if screen_name == 'main':
            Clock.schedule_once(lambda x: self.update_drawer_menu())      
        else:
            self.graph_area.clear_widgets() #グラフを初期化
        self.root.current = screen_name
        
    def switch_actuater(self, num, obj):
        """アクチュエータを変更・選択したとき"""
        if self.selected_actuater != num:
            self.selected_actuater = num
            
            if hasattr(self, 'update_event'):
                Clock.unschedule(self.update_event)
                
            self.graph_area.clear_widgets() #グラフを初期化
            self.fig = plt.figure()
            self.fig, self.ax = plt.subplots()
            self.fig.patch.set_alpha(0)
            self.ax.patch.set_alpha(0)
            
            self.x = list(range(200))
            self.y1 = [0] * 200
            self.y2 = [0] * 200
            self.y3 = [0] * 200
            
            self.pos_line, = self.ax.plot(self.x, self.y1, label="Position")  # 1本目の線
            self.vol_line, = self.ax.plot(self.x, self.y2, label="Voltage")  # 2本目の線
            self.com_line, = self.ax.plot(self.x, self.y3, label="Command")  # 3本目の線
            
            self.ax.get_xaxis().set_visible(False)
            
            self.graph_area.add_widget(FigureCanvasKivyAgg(self.fig))   #新規グラフを追加
            self.update_event = Clock.schedule_interval(self.update_graph, 0.01)
        
    def update_graph(self, *args):
        # 1本目の線のy値の更新
        self.y1.append(self.position)  # y1値の更新
        self.y1.pop(0)  # 古いy1値の削除

        # 2本目の線のy値の更新（例としてself.positionに0.5を足した値）
        self.y2.append(self.voltage)  # y2値の更新
        self.y2.pop(0)  # 古いy2値の削除
        
        self.y3.append(self.command)  # y2値の更新
        self.y3.pop(0)  # 古いy2値の削除

        # 各線のデータを更新
        self.pos_line.set_ydata(self.y1)
        self.vol_line.set_ydata(self.y2)
        self.com_line.set_ydata(self.y3)

        self.ax.relim()  # limitsを再計算
        self.ax.autoscale_view()  # スケールを更新

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
                
    def update_drawer_menu(self):
        navigation_drawer = self.screen_manager.get_screen('main').ids.nav_drawer_menu
        navigation_drawer.children[0].clear_widgets()
        actuater_num = len(self.trans_data['sensors'])

        navigation_drawer.add_widget(MDNavigationDrawerLabel(text="ActuaterList"))

        for actuater in range(actuater_num):
            actuater_list = MDNavigationDrawerItem(
                MDNavigationDrawerItemText(text="アクチュエータ" + str(actuater)))
            actuater_list.bind(on_release=partial(self.switch_actuater, str(actuater)))
            navigation_drawer.add_widget(actuater_list)
            
    def show_snackbar(self, message):
        snackbar = MDSnackbar(
            MDSnackbarText(
                text=message,
            ),
            pos_hint={"center_x": 0.5, "center_y":0.1},
            size_hint_x=0.5,
        )
        snackbar.open()
    
    def switch_theme_style(self):
        self.theme_cls.theme_style = (
            "Dark" if self.theme_cls.theme_style == "Light" else "Light"
        )
        self.settings_manager.update_setting('theme', self.theme_cls.theme_style)
        self.settings_manager.save_settings()
    
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

if __name__ == '__main__':
    NativeGUIApp().run()
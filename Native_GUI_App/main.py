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

class StartScreen(MDScreen):
    pass

class MainScreen(MDScreen):
    pass

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
        
        return self.screen_manager
    
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
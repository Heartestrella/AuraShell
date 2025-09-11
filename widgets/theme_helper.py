# theme_helper.py
from qfluentwidgets import toggleTheme, Theme
from PyQt5.QtGui import QColor, QFont

_current_theme = Theme.DARK
_on_theme_changed = None
_font_settings = {
    'family': 'Courier New',
    'size': 12,
    # 自动颜色：浅色主题用深色字，深色主题用浅色字
    'bg_color_light': "#888888",
    'bg_color_dark': "#252525"
}

def apply_dark_theme():
    global _current_theme
    _current_theme = Theme.DARK
    toggleTheme(Theme.DARK)
    if _on_theme_changed: _on_theme_changed()

def apply_light_theme():
    print("切换背景到亮色")
    global _current_theme
    _current_theme = Theme.LIGHT
    toggleTheme(Theme.LIGHT)
    if _on_theme_changed: _on_theme_changed()

def current_theme():
    return _current_theme

def set_theme_change_callback(cb):
    global _on_theme_changed
    _on_theme_changed = cb

def get_font_settings():
    return _font_settings.copy()

def update_font_settings(settings):
    global _font_settings
    _font_settings.update(settings)
    if _on_theme_changed: _on_theme_changed()

def get_current_font_color():
    """自动根据主题返回字体颜色"""
    if _current_theme == Theme.DARK:
        return '#ffffff'  # 深色主题用白色字
    else:
        return '#000000'  # 浅色主题用黑色字

def get_current_bg_color():
    if _current_theme == Theme.DARK:
        return _font_settings['bg_color_dark']
    else:
        return _font_settings['bg_color_light']

def get_font():
    return QFont(_font_settings['family'], _font_settings['size'])
#!/usr/bin/env python3
"""点点 — 薄荷绿像素桌面宠物"""

import sys
import os
import math
import random
import json
import re
import hashlib
import time
import base64
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QMenu, QPushButton, QHBoxLayout, QInputDialog, QLineEdit,
    QTextBrowser, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QThread, pyqtSignal, QUrl, QPropertyAnimation
from PyQt6.QtGui import (
    QPainter, QColor, QPixmap, QImage, QTransform, QCursor, QRegion, QTextDocument, QPalette
)

# 数据目录：打包后用 ~/Library/Application Support/DianDian，开发时用脚本所在目录
def _data_dir():
    if getattr(sys, 'frozen', False):
        d = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "DianDian")
    else:
        d = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(d, exist_ok=True)
    return d

DATA_DIR = _data_dir()

# ============================================================
# 像素数据 — 水滴形 16x16（左边短尖，圆墩鞋，短腿）
# ============================================================
# 0=透明 1=身体 2=腿 3=黑色(眼) 4=圆鞋子
_BASE = [
    #0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
    [0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0],  # 0  顶
    [0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0],  # 1
    [0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0],  # 2
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 3  宽
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 4
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 5
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 6  眼睛行
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 7
    [0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0],  # 8  左宽右收
    [0,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0],  # 9
    [1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0],  # 10 左小尖
    [0,0,0,0,0,2,0,0,0,2,0,0,0,0,0,0],  # 11 短腿（居中对称）
    [0,0,0,0,4,4,0,0,4,4,0,0,0,0,0,0],  # 12 小鞋 2x1 对称
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],  # 13
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],  # 14
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],  # 15
]

def _make_eye_variant(lcols, rcols, eye_row=6):
    grid = [row[:] for row in _BASE]
    grid[eye_row][lcols[0]] = 3
    grid[eye_row][rcols[0]] = 3
    return grid

def _make_stare():
    grid = [row[:] for row in _BASE]
    for c in (5, 10):
        grid[5][c] = 3
        grid[6][c] = 3
    return grid

# 眼睛 col5 和 col10
CLAWD_NORMAL = _make_eye_variant([5], [10])
CLAWD_LOOK_L = _make_eye_variant([5], [10])
CLAWD_LOOK_R = _make_eye_variant([5], [10])
CLAWD_LOOK_U = _make_eye_variant([5], [10], eye_row=5)
CLAWD_STARE = _make_stare()

CLAWD_BLINK = [row[:] for row in _BASE]

# 走路：鞋交替偏移
CLAWD_WALK1 = [row[:] for row in CLAWD_NORMAL]
CLAWD_WALK1[11] = [0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0]
CLAWD_WALK1[12] = [0,0,4,4,0,0,0,0,0,4,4,0,0,0,0,0]
CLAWD_WALK2 = [row[:] for row in CLAWD_NORMAL]
CLAWD_WALK2[11] = [0,0,0,0,0,0,2,0,2,0,0,0,0,0,0,0]
CLAWD_WALK2[12] = [0,0,0,0,0,4,4,0,4,4,0,0,0,0,0,0]

# 乱蹬：鞋散开
CLAWD_FLAIL1 = [row[:] for row in CLAWD_STARE]
CLAWD_FLAIL1[11] = [0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0]
CLAWD_FLAIL1[12] = [0,4,4,0,0,0,0,0,0,0,4,4,0,0,0,0]
CLAWD_FLAIL2 = [row[:] for row in CLAWD_STARE]
CLAWD_FLAIL2[11] = [0,0,0,0,2,0,0,0,0,2,0,0,0,0,0,0]
CLAWD_FLAIL2[12] = [0,0,0,4,4,0,0,0,4,4,0,0,0,0,0,0]

# 像素硬币
COIN_FRAMES = [
    [[0,0,3,3,3,3,0,0],[0,3,4,4,4,4,3,0],[3,4,4,3,4,4,4,3],
     [3,4,3,3,3,3,4,3],[3,4,4,3,4,4,4,3],[3,4,4,3,4,4,4,3],
     [0,3,4,4,4,4,3,0],[0,0,3,3,3,3,0,0]],
    [[0,0,0,3,3,0,0,0],[0,0,0,4,4,0,0,0],[0,0,0,4,4,0,0,0],
     [0,0,0,3,3,0,0,0],[0,0,0,3,3,0,0,0],[0,0,0,4,4,0,0,0],
     [0,0,0,4,4,0,0,0],[0,0,0,3,3,0,0,0]],
    [[0,0,3,3,3,3,0,0],[0,3,4,4,4,4,3,0],[3,4,4,4,4,4,4,3],
     [3,4,4,3,3,4,4,3],[3,4,4,3,3,4,4,3],[3,4,4,4,4,4,4,3],
     [0,3,4,4,4,4,3,0],[0,0,3,3,3,3,0,0]],
]
COIN_COLORS = {3: QColor(160, 165, 175), 4: QColor(220, 225, 235)}

PX = 7
COLORS = {
    1: QColor(140, 215, 180),   # 薄荷绿身体
    2: QColor(110, 190, 155),   # 腿稍深
    3: QColor(26, 26, 26),      # 眼睛
    4: QColor(100, 180, 150),   # 圆鞋子（深薄荷）
}
SPRITE_W, SPRITE_H = 16 * PX, 16 * PX
SPRITE_MAX = max(SPRITE_W, SPRITE_H)
BUBBLE_ZONE = 55
PANEL_H = 45
WIN_W = SPRITE_MAX + 250  # 气泡最大220+起始偏移，需要足够宽
WIN_H = SPRITE_MAX + BUBBLE_ZONE + PANEL_H

CLICK_LINES = [
    "在呢", "想摸鱼了",
    "要一起玩吗", "要喝咖啡吗", "你也辛苦了",
    "做什么呢", "来了来了", "我在我在",
    "休息一下吧", "需要我吗",
    "你今天状态不错", "做得很好",
]
IDLE_LINES = [
    "要不要休息一下", "我在看你工作...", "嗯...想事情",
    "好无聊", "今天天气怎么样", "心情不错",
    "发呆中", "肚子饿了", "今天周几来着",
    "该喝水了", "伸个懒腰", "有点困",
    "窗外的光线变了",
    "你很厉害", "一直在努力呢",
]
FORTUNE_LIST = [
    "大吉！超级幸运", "中吉，好事要来", "小吉，平安是福",
    "适合搞创作", "适合摸鱼...不，努力", "心情会很好",
    "灵感要来了", "该吃点好的", "贵人运很旺",
    "适合学新东西", "会收到好消息", "桃花运不错哦",
    "财运小有上升", "适合整理房间", "今天宜早睡",
    "会有意外惊喜",
]


# 像素食物 8x8
FOOD_APPLE = [
    [0,0,0,5,5,0,0,0],
    [0,0,0,6,0,0,0,0],
    [0,0,7,7,7,7,0,0],
    [0,7,7,7,7,7,7,0],
    [0,7,7,7,7,7,7,0],
    [0,7,7,7,7,7,7,0],
    [0,0,7,7,7,7,0,0],
    [0,0,0,7,7,0,0,0],
]
FOOD_TEA = [
    [0,0,5,0,5,0,0,0],
    [0,0,0,5,0,0,0,0],
    [0,8,8,8,8,8,0,0],
    [0,8,9,9,9,8,8,0],
    [0,8,9,9,9,8,8,0],
    [0,8,9,9,9,8,0,0],
    [0,8,8,8,8,8,0,0],
    [0,0,8,8,8,0,0,0],
]
FOOD_CAKE = [
    [0,0,0,5,0,0,0,0],
    [0,0,5,10,5,0,0,0],
    [0,11,11,11,11,11,0,0],
    [0,12,12,12,12,12,0,0],
    [0,11,11,11,11,11,0,0],
    [0,12,12,12,12,12,0,0],
    [0,12,12,12,12,12,0,0],
    [0,13,13,13,13,13,0,0],
]

FOOD_COLORS = {
    5: QColor(80, 160, 60),    # 叶子/茎 绿色
    6: QColor(120, 80, 40),    # 茎 棕色
    7: QColor(220, 60, 60),    # 苹果 红色
    8: QColor(230, 230, 220),  # 杯子 白色
    9: QColor(160, 200, 120),  # 茶水 浅绿
    10: QColor(255, 200, 50),  # 火焰 黄色
    11: QColor(255, 180, 200), # 奶油 粉色
    12: QColor(210, 170, 110), # 蛋糕体 棕黄
    13: QColor(180, 140, 90),  # 底座 深棕
}

FOOD_SUSHI = [
    [0,0,0,0,0,0,0,0],
    [0,0,14,14,14,14,0,0],
    [0,14,14,14,14,14,14,0],
    [0,14,14,14,14,14,14,0],
    [0,15,15,15,15,15,15,0],
    [0,15,8,8,8,8,15,0],
    [0,15,15,15,15,15,15,0],
    [0,0,0,0,0,0,0,0],
]

FOOD_BURGER = [
    [0,0,0,0,0,0,0,0],
    [0,0,18,18,18,18,18,0],
    [0,18,18,18,18,18,18,18],
    [0,19,20,20,20,20,19,0],
    [21,21,21,21,21,21,21,21],
    [0,18,18,18,18,18,18,18],
    [0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0],
]

FOOD_LINES = {
    "苹果": ["谢谢", "好甜", "正好饿了"],
    "茶":  ["暖暖的", "好喝", "正需要这个"],
    "蛋糕": ["好幸福", "甜甜的", "最喜欢了"],
    "寿司": ["好新鲜", "最爱三文鱼", "满足"],
    "汉堡": ["好大一个", "肉饼好香", "满足感爆棚"],
}

FOOD_GRIDS = {"苹果": FOOD_APPLE, "茶": FOOD_TEA, "蛋糕": FOOD_CAKE, "寿司": FOOD_SUSHI, "汉堡": FOOD_BURGER}

# 毯子像素 16x6
BLANKET = [
    [0,0,0,16,16,16,16,16,16,16,16,16,16,0,0,0],
    [0,0,16,16,16,16,16,16,16,16,16,16,16,16,0,0],
    [0,16,16,16,16,16,16,16,16,16,16,16,16,16,16,0],
    [0,16,16,16,16,16,16,16,16,16,16,16,16,16,16,0],
    [0,0,16,16,16,16,16,16,16,16,16,16,16,16,0,0],
    [0,0,0,16,16,16,16,16,16,16,16,16,16,0,0,0],
]

# 小植物像素 6x8
PLANT = [
    [0,0,0,5,0,0],
    [0,0,5,5,5,0],
    [0,5,5,5,5,5],
    [0,0,5,5,5,0],
    [0,0,0,6,0,0],
    [0,0,0,6,0,0],
    [0,0,17,17,17,0],
    [0,0,17,17,17,0],
]

EXTRA_COLORS = {
    14: QColor(240, 130, 80),  # 三文鱼 橙色
    15: QColor(245, 245, 235), # 米饭 白色
    16: QColor(180, 160, 220), # 毯子 淡紫
    17: QColor(180, 130, 90),  # 花盆 棕色
    18: QColor(210, 160, 60),  # 汉堡面包 金棕
    19: QColor(90, 180, 70),   # 生菜 绿色
    20: QColor(255, 210, 50),  # 芝士 黄色
    21: QColor(120, 60, 30),   # 肉饼 深棕
    22: QColor(200, 185, 235), # 毯子格纹 浅淡紫
}
FOOD_COLORS.update(EXTRA_COLORS)


def grid_to_pixmap(grid, colors=None):
    if colors is None: colors = COLORS
    w, h = len(grid[0]) * PX, len(grid) * PX
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    p = QPainter(img)
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            if val in colors:
                p.fillRect(c * PX, r * PX, PX, PX, colors[val])
    p.end()
    return QPixmap.fromImage(img)


def coin_pixmap(idx):
    grid = COIN_FRAMES[idx % 3]
    sz = 4
    img = QImage(8*sz, 8*sz, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    p = QPainter(img)
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            if val in COIN_COLORS:
                p.fillRect(c*sz, r*sz, sz, sz, COIN_COLORS[val])
    p.end()
    return QPixmap.fromImage(img)


class State:
    IDLE = "idle"
    WALKING = "walking"
    SLEEPING = "sleeping"
    HAPPY = "happy"
    DRAGGING = "dragging"


# ============================================================
# 像素风 UI 组件
# ============================================================
PX_BORDER = QColor(70, 70, 70)         # 像素边框色
PX_BG = QColor(245, 240, 230, 230)     # 像素气泡底色（微黄白，像旧纸）
PX_TEXT = QColor(50, 50, 50)           # 文字色
PX_BTN = QColor(110, 190, 155)        # 按钮底色（和点点协调）
PX_BTN_HOVER = QColor(90, 170, 135)

class SpeechBubble(QWidget):
    """像素风气泡：方块边框 + 直角"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._text = ""
        self.setFixedSize(160, 50)
        self.hide()

    def set_text(self, text):
        self._text = text
        fm = self.fontMetrics()
        inset = 12  # 左右各12（含2px边框）
        max_w = 220
        text_w = max_w - inset * 2
        br = fm.boundingRect(QRect(0, 0, text_w, 0),
                             Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, text)
        tw = min(br.width() + inset * 2, max_w)
        tw = max(tw, 50)
        th = br.height() + 14
        self.setFixedSize(tw, th)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        bw = 1  # 边框粗细
        inset = 12  # 和set_text一致
        # 填充背景
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(PX_BG)
        p.drawRect(bw, bw, w - bw*2, h - bw*2)
        # 像素边框（四条线，不圆角）
        p.setBrush(PX_BORDER)
        p.drawRect(bw, 0, w - bw*2, bw)      # 上
        p.drawRect(bw, h - bw, w - bw*2, bw)  # 下
        p.drawRect(0, bw, bw, h - bw*2)       # 左
        p.drawRect(w - bw, bw, bw, h - bw*2)  # 右
        # 文字：左右padding = inset
        p.setPen(PX_TEXT)
        p.drawText(inset, 5, w - inset * 2, h - 10,
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, self._text)
        p.end()


class ImageViewer(QWidget):
    """点击图片后的全屏放大查看器，支持左右切换同组图片"""
    _ARROW_CSS = "color: rgba(255,255,255,200); font-size: 28px; background: transparent;"

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setGeometry(screen)
        # 页码指示器
        self._indicator = QLabel(self)
        self._indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._indicator.setStyleSheet("color: rgba(255,255,255,200); font-size: 13px; background: transparent;")
        self._indicator.setFixedWidth(screen.width())
        self._indicator.move(0, screen.height() - 40)
        # 左右箭头（默认隐藏，hover时淡入，位置跟着图片走）
        self._arrow_l = QLabel("◂", self)
        self._arrow_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow_l.setFixedSize(32, 44)
        self._arrow_l.setStyleSheet(self._ARROW_CSS)
        self._arrow_r = QLabel("▸", self)
        self._arrow_r.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow_r.setFixedSize(32, 44)
        self._arrow_r.setStyleSheet(self._ARROW_CSS)
        # 箭头透明度动画
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation
        self._opacity_l = QGraphicsOpacityEffect(self._arrow_l)
        self._opacity_l.setOpacity(0.0)
        self._arrow_l.setGraphicsEffect(self._opacity_l)
        self._anim_l = QPropertyAnimation(self._opacity_l, b"opacity")
        self._anim_l.setDuration(200)
        self._opacity_r = QGraphicsOpacityEffect(self._arrow_r)
        self._opacity_r.setOpacity(0.0)
        self._arrow_r.setGraphicsEffect(self._opacity_r)
        self._anim_r = QPropertyAnimation(self._opacity_r, b"opacity")
        self._anim_r.setDuration(200)
        self._arrow_l_visible = False
        self._arrow_r_visible = False
        self.setMouseTracking(True)
        self._label.setMouseTracking(True)
        self._images_list = []
        self._idx = 0
        self._pix_rect = None  # 当前图片在屏幕上的区域

    def show_image(self, img_data, all_images=None, clicked_url=None):
        if all_images and len(all_images) > 1:
            self._images_list = list(all_images.items())
            self._idx = 0
            if clicked_url:
                for i, (u, _) in enumerate(self._images_list):
                    if u == clicked_url:
                        self._idx = i
                        break
        else:
            self._images_list = [("", img_data)]
            self._idx = 0
        self._fade_arrow(self._anim_l, self._opacity_l, 0.0); self._arrow_l_visible = False
        self._fade_arrow(self._anim_r, self._opacity_r, 0.0); self._arrow_r_visible = False
        self._swipe_acc = 0
        self._display_current()
        self.show()
        self.raise_()

    def _display_current(self):
        _, data = self._images_list[self._idx]
        qimg = QImage()
        qimg.loadFromData(data)
        screen = QApplication.primaryScreen().geometry()
        max_w = int(screen.width() * 0.8)
        max_h = int(screen.height() * 0.8)
        pix = QPixmap.fromImage(qimg)
        if pix.width() > max_w or pix.height() > max_h:
            pix = pix.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._label.setPixmap(pix)
        # 计算图片实际显示区域
        cx, cy = screen.width() // 2, screen.height() // 2
        pw, ph = pix.width(), pix.height()
        self._pix_rect = (cx - pw // 2, cy - ph // 2, pw, ph)
        # 箭头在图片内部边缘
        self._arrow_l.move(self._pix_rect[0] + 6, cy - 22)
        self._arrow_r.move(self._pix_rect[0] + pw - 38, cy - 22)
        n = len(self._images_list)
        self._indicator.setText(f"{self._idx + 1} / {n}" if n > 1 else "")

    def mouseMoveEvent(self, event):
        if len(self._images_list) <= 1 or not self._pix_rect:
            return
        x = int(event.position().x())
        y = int(event.position().y())
        px, py, pw, ph = self._pix_rect
        in_img = px <= x <= px + pw and py <= y <= py + ph
        # 左箭头：图片内左侧60px区域
        want_l = in_img and x <= px + 60 and self._idx > 0
        if want_l and not self._arrow_l_visible:
            self._fade_arrow(self._anim_l, self._opacity_l, 1.0); self._arrow_l_visible = True
        elif not want_l and self._arrow_l_visible:
            self._fade_arrow(self._anim_l, self._opacity_l, 0.0); self._arrow_l_visible = False
        # 右箭头：图片内右侧60px区域
        want_r = in_img and x >= px + pw - 60 and self._idx < len(self._images_list) - 1
        if want_r and not self._arrow_r_visible:
            self._fade_arrow(self._anim_r, self._opacity_r, 1.0); self._arrow_r_visible = True
        elif not want_r and self._arrow_r_visible:
            self._fade_arrow(self._anim_r, self._opacity_r, 0.0); self._arrow_r_visible = False

    def _fade_arrow(self, anim, effect, target):
        anim.stop()
        anim.setStartValue(effect.opacity())
        anim.setEndValue(target)
        anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))
        p.end()

    def mousePressEvent(self, event):
        if not self._pix_rect:
            self.hide()
            return
        x = int(event.position().x())
        y = int(event.position().y())
        px, py, pw, ph = self._pix_rect
        in_img = px <= x <= px + pw and py <= y <= py + ph
        if not in_img:
            # 点击图片外面 = 关闭
            self.hide()
            return
        if len(self._images_list) <= 1:
            self.hide()
            return
        # 点击图片内左侧 = 上一张，右侧 = 下一张
        if x <= px + pw // 2:
            if self._idx > 0:
                self._idx -= 1
                self._display_current()
            else:
                self.hide()
        else:
            if self._idx < len(self._images_list) - 1:
                self._idx += 1
                self._display_current()
            else:
                self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key.Key_Left and self._idx > 0:
            self._idx -= 1
            self._display_current()
        elif event.key() == Qt.Key.Key_Right and self._idx < len(self._images_list) - 1:
            self._idx += 1
            self._display_current()


class RichPanel(QWidget):
    """像素风展开卡片：用QTextBrowser显示rich content，支持图片"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self._max_h = 420
        self._panel_w = 380
        self.setFixedSize(self._panel_w, self._max_h)
        self._browser = QTextBrowser(self)
        self._browser.setOpenExternalLinks(False)
        self._browser.move(2, 2)
        self._browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._browser.setStyleSheet(f"""
            QTextBrowser {{
                background: rgba(245, 240, 230, 245);
                border: 1.8px solid {PX_BORDER.name()};
                border-radius: 0px;
                font-family: "PingFang SC", -apple-system, sans-serif;
                font-size: 12px;
                line-height: 1.3;
                color: {PX_TEXT.name()};
                padding: 10px 16px 10px 16px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(160, 155, 145, 140);
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self._images = {}
        self._image_viewer = ImageViewer()
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._on_link_click)
        # 滚动条淡入淡出
        sb = self._browser.verticalScrollBar()
        sb_eff = QGraphicsOpacityEffect(sb)
        sb_eff.setOpacity(0.0)
        sb.setGraphicsEffect(sb_eff)
        self._sb_eff = sb_eff
        self._sb_anim = QPropertyAnimation(sb_eff, b"opacity", self)
        self._sb_anim.setDuration(300)
        self._sb_hide_timer = QTimer(self)
        self._sb_hide_timer.setSingleShot(True)
        self._sb_hide_timer.timeout.connect(self._fade_scrollbar_out)
        sb.valueChanged.connect(self._on_scroll)
        # 关闭按钮
        self._close_btn = QLabel("×", self)
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.move(356, 4)
        self._close_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._close_btn.setStyleSheet("""
            QLabel {
                color: rgba(140, 140, 130, 200);
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            }
            QLabel:hover {
                color: rgba(80, 80, 75, 255);
            }
        """)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.mousePressEvent = lambda e: self._do_close()
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self.hide)
        self.hide()

    def show_rich(self, html, images, anchor_global_pos, auto_hide=True):
        self._images = images
        # 解析html中的图片分组: img:GROUP_ID:URL
        self._image_groups = {}
        for m in re.finditer(r'href="img:(\d+):([^"]+)"', html):
            gid = int(m.group(1))
            url = m.group(2)
            self._image_groups.setdefault(gid, []).append(url)
        doc = self._browser.document()
        doc.clear()
        for url_str, img_data in images.items():
            qimg = QImage()
            qimg.loadFromData(img_data)
            if qimg.width() > 260:
                qimg = qimg.scaledToWidth(260, Qt.TransformationMode.SmoothTransformation)
            doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(url_str), qimg)
        self._browser.setHtml(html)
        self._browser.verticalScrollBar().setValue(0)
        # 根据内容自适应宽高
        doc.setTextWidth(self._panel_w - 30)
        content_h = int(doc.size().height()) + 28
        ideal_w = min(int(doc.idealWidth()) + 40, self._panel_w)
        # 有图片或表格时保证足够宽度
        has_img = bool(images)
        has_table = "<table " in html
        min_w = self._panel_w if has_table else (self._panel_w if has_img else 300)
        w = max(min_w, ideal_w)
        h = max(50, min(content_h, self._max_h))
        self.setFixedSize(w, h)
        self._browser.setFixedSize(w - 4, h - 4)
        self._close_btn.move(w - 24, 4)
        self.move(anchor_global_pos.x(), anchor_global_pos.y() - h // 2)
        self.show()
        self.raise_()
        self._dismiss_on_leave = not auto_hide  # 历史模式：鼠标移走关闭
        if auto_hide:
            self._auto_timer.start(20000)
        else:
            self._auto_timer.stop()

    def set_close_callback(self, cb):
        self._close_cb = cb

    def hide(self):
        super().hide()

    def _do_close(self):
        self._auto_timer.stop()
        self._dismiss_on_leave = False
        super().hide()
        if hasattr(self, '_close_cb') and self._close_cb:
            self._close_cb()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._do_close()

    def leaveEvent(self, event):
        pass  # 不自动关闭，只能点X

    def _on_link_click(self, url):
        url_str = url.toString()
        if url_str.startswith("img:"):
            # 格式: img:GROUP_ID:URL
            parts = url_str[4:].split(":", 1)
            if len(parts) == 2:
                gid, real_url = int(parts[0]), parts[1]
                group_urls = self._image_groups.get(gid, [real_url])
                group_images = {u: self._images[u] for u in group_urls if u in self._images}
                if real_url in self._images:
                    self._image_viewer.show_image(self._images[real_url], group_images, real_url)

    def _on_scroll(self):
        self._sb_anim.stop()
        self._sb_eff.setOpacity(1.0)
        self._sb_hide_timer.start(1000)

    def _fade_scrollbar_out(self):
        self._sb_anim.stop()
        self._sb_anim.setStartValue(self._sb_eff.opacity())
        self._sb_anim.setEndValue(0.0)
        self._sb_anim.start()

    @staticmethod
    def md_to_html(md):
        # cite标签：提取引用文字，转为评论样式
        def _cite_to_review(m):
            text = re.sub(r"</?cite[^>]*>", "", m.group(0)).strip()
            text = text.lstrip("> ").strip()
            # 去掉外层各种引号（ASCII和Unicode）
            text = re.sub(r'^[\s""\u201c\u201d\u2018\u2019\u300c\u300d\']+', '', text)
            text = re.sub(r'[\s""\u201c\u201d\u2018\u2019\u300c\u300d\']+$', '', text)
            if not text:
                return ""
            return f'\n__cite__{text}\n'
        md = re.sub(r">\s*<cite[^>]*>.*?</cite>", _cite_to_review, md, flags=re.DOTALL)
        md = re.sub(r"<cite[^>]*>(.*?)</cite>", lambda m: _cite_to_review(m), md, flags=re.DOTALL)
        # mark高亮块：提取内容，加标记前缀
        def _mark_block(m):
            inner = m.group(1).strip()
            return f'\n__mark_start__\n{inner}\n__mark_end__\n'
        md = re.sub(r"<mark>(.*?)</mark>", _mark_block, md, flags=re.DOTALL)
        # 清理空的引用行（只剩 > 和空白）
        md = re.sub(r"^>\s*$", "", md, flags=re.MULTILINE)
        md = re.sub(r"\n{3,}", "\n\n", md)
        # 先处理代码块
        lines = md.split("\n")
        processed = []
        in_code = False
        code_buf = []
        for line in lines:
            if line.strip().startswith("```"):
                if in_code:
                    code = "\n".join(code_buf)
                    import html as html_mod
                    code = html_mod.escape(code)
                    processed.append(f'<pre style="background:#eae6dc;border:1.8px solid {PX_BORDER.name()};padding:6px 8px;font-size:11px;font-family:monospace;margin:4px 0;white-space:pre-wrap">{code}</pre>')
                    code_buf = []
                    in_code = False
                else:
                    in_code = True
                continue
            if in_code:
                code_buf.append(line)
            else:
                processed.append(line)
        if code_buf:
            import html as html_mod
            code = html_mod.escape("\n".join(code_buf))
            processed.append(f'<pre style="background:#eae6dc;border:1.8px solid {PX_BORDER.name()};padding:6px 8px;font-size:11px;font-family:monospace;margin:4px 0;white-space:pre-wrap">{code}</pre>')
        # 预处理：收集markdown表格，转为信息行
        final_lines = []
        i = 0
        while i < len(processed):
            s = processed[i].strip()
            if s.startswith("|") and s.endswith("|"):
                # 收集整个表格
                table_rows = []
                while i < len(processed) and processed[i].strip().startswith("|") and processed[i].strip().endswith("|"):
                    row = processed[i].strip()
                    cells = [c.strip() for c in row.strip("|").split("|")]
                    # 跳过分隔行 | --- | :--- | ---: | :---: |
                    if not all(re.match(r'^:?-+:?$', c) for c in cells):
                        table_rows.append(cells)
                    i += 1
                if not table_rows:
                    continue
                ncols = max(len(r) for r in table_rows)
                if ncols <= 2:
                    # 两列表格：转为标签行
                    for cells in table_rows:
                        if len(cells) >= 2:
                            final_lines.append(f"__label__{cells[0]}：{cells[1]}")
                        else:
                            final_lines.append(cells[0] if cells else "")
                else:
                    # 多列表格：渲染为HTML table
                    cell_css = "padding:3px 6px;font-size:11px;border-bottom:1px solid rgba(180,172,155,0.3);line-height:1.3;vertical-align:top"
                    header_css = f"{cell_css};font-weight:bold;background:rgba(232,226,214,0.5)"
                    tbl = f'<table cellspacing="0" style="margin:6px 0;border-collapse:collapse;width:100%">'
                    for ri, cells in enumerate(table_rows):
                        tbl += "<tr>"
                        for ci, c in enumerate(cells):
                            c = re.sub(r'\*\*', '', c)
                            css = header_css if (ri == 0 or ci == 0) else cell_css
                            tbl += f"<td style='{css}'>{c}</td>"
                        tbl += "</tr>"
                    tbl += "</table>"
                    final_lines.append(tbl)
            else:
                final_lines.append(processed[i])
                i += 1
        lines = final_lines
        html_parts = []
        in_ul = False
        in_mark = False
        mark_buf = []
        for line in lines:
            s = line.strip()
            # mark高亮块的开始/结束
            if s == "__mark_start__":
                if in_ul:
                    html_parts.append("</ul>")
                    in_ul = False
                in_mark = True
                mark_buf = []
                continue
            if s == "__mark_end__":
                in_mark = False
                # 高亮块：内容用正文样式显示，不做标签/列表特殊处理
                mark_lines = []
                for ml in mark_buf:
                    ms = ml.strip()
                    if not ms:
                        continue
                    # 标题
                    mh = re.match(r"^(#{1,4})\s+(.*)", ms)
                    if mh:
                        n = len(mh.group(1))
                        sizes = {1: 14, 2: 13.5, 3: 12.5, 4: 12}
                        mark_lines.append(f"<p style='margin:4px 0 2px 0;font-size:{sizes.get(n,12)}px;font-weight:bold'>{mh.group(2)}</p>")
                        continue
                    # 列表项：去掉**，统一用正文样式
                    if ms.startswith("- ") or ms.startswith("· ") or ms.startswith("• "):
                        item = re.sub(r'\*\*', '', ms[2:])
                        mark_lines.append(f"<p style='margin:1px 0;line-height:1.4'>· {item}</p>")
                        continue
                    mark_lines.append(f"<p style='margin:1px 0;line-height:1.4'>{ms}</p>")
                mark_inner = "\n".join(mark_lines)
                html_parts.append(f"<div style='margin:8px 0;padding:8px 12px;background:rgba(235,232,225,0.8);border-left:2.5px solid rgba(170,165,155,0.6);border-radius:0px'>{mark_inner}</div>")
                continue
            if in_mark:
                mark_buf.append(line)
                continue
            if not s:
                if in_ul:
                    html_parts.append("</ul>")
                    in_ul = False
                continue
            # cite评论行
            if s.startswith("__cite__"):
                if in_ul:
                    html_parts.append("</ul>")
                    in_ul = False
                cite_text = s[8:]
                html_parts.append(f"<p style='margin:2px 0;padding:3px 8px;font-size:10.5px;color:#888;line-height:1.3'>「{cite_text}」</p>")
                continue
            # 已处理的HTML块（如<pre>）直接通过
            if s.startswith("<pre ") or s.startswith("<table "):
                if in_ul:
                    html_parts.append("</ul>")
                    in_ul = False
                html_parts.append(line)
                continue
            hm = re.match(r"^(#{1,4})\s+(.*)", s)
            if hm:
                if in_ul:
                    html_parts.append("</ul>")
                    in_ul = False
                n = len(hm.group(1))
                sizes = {1: 14, 2: 13.5, 3: 12.5, 4: 12}
                top_m = {1: 14, 2: 12, 3: 10, 4: 8}
                sz = sizes.get(n, 12)
                tm = top_m.get(n, 8)
                extra = "border-bottom:1px solid rgba(70,70,70,0.15);padding-bottom:3px" if n <= 2 else ""
                lvl = min(n + 1, 4)
                html_parts.append(f"<h{lvl} style='margin:{tm}px 0 4px 0;font-size:{sz}px;font-weight:bold;{extra}'>{hm.group(2)}</h{lvl}>")
                continue
            if s.startswith("- ") or s.startswith("· ") or s.startswith("• "):
                li_content = s[2:]
                # 列表项里的标签行：**label**：value 或 短标签：value
                clean_li = re.sub(r'\*\*', '', li_content)
                # 通用模式：短标签（纯中文/英文/数字，无标点）+ 中/英冒号 + 内容
                li_label = re.match(r'^([\u4e00-\u9fff\w\s·]{1,10}?)([：:])(.+)', clean_li)
                if li_label:
                    if in_ul:
                        html_parts.append("</ul>")
                        in_ul = False
                    html_parts.append(f"<p style='margin:-1px 0;line-height:1.3;font-size:11px;color:#555'>· <b>{li_label.group(1)}{li_label.group(2)}</b>{li_label.group(3)}</p>")
                    continue
                if not in_ul:
                    html_parts.append("<ul style='margin:2px 0;padding-left:18px'>")
                    in_ul = True
                html_parts.append(f"<li style='margin:1px 0;line-height:1.4'>{li_content}</li>")
                continue
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if s.startswith("> "):
                html_parts.append(f"<blockquote style='margin:3px 0;padding:2px 8px;border-left:3px solid #bbb;color:#666;font-size:11.5px'>{s[2:]}</blockquote>")
                continue
            # 标签行（表格转换的 或 原生"地址：xxx"格式）
            label_s = s[9:] if s.startswith("__label__") else s
            is_from_table = s.startswith("__label__")
            label_m = re.match(r'^([\u4e00-\u9fff\w\s·]{1,10}?)([：:])(.+)', label_s)
            if label_m and (is_from_table or re.match(r'^[\u4e00-\u9fff\w\s·]{1,10}[：:]', label_s)):
                html_parts.append(f"<p style='margin:-1px 0;line-height:1.3;font-size:11px;color:#555'>· <b>{label_m.group(1)}{label_m.group(2)}</b>{label_m.group(3)}</p>")
                continue
            if is_from_table:
                html_parts.append(f"<p style='margin:-1px 0;line-height:1.3;font-size:11px;color:#555'>{label_s}</p>")
                continue
            # 水平线
            if re.match(r'^---+$', s):
                continue  # 跳过分隔线，section间距由标题margin控制
            html_parts.append(f"<p style='margin:1px 0;line-height:1.4'>{s}</p>")
        if in_ul:
            html_parts.append("</ul>")
        html = "\n".join(html_parts)
        html = re.sub(r"\*\*(.+?)\*\*", r"\1", html)
        html = re.sub(r"\*(.+?)\*", r"<i>\1</i>", html)
        html = re.sub(r"`([^`]+)`", rf'<code style="background:#eae6dc;padding:1px 4px;font-size:11px;border:1.8px solid {PX_BORDER.name()}">\1</code>', html)
        # markdown链接 [text](url)（非图片）
        html = re.sub(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)', r'<a style="font-size:10px;color:#5577aa;word-break:break-all" href="\2">\1</a>', html)
        # 裸URL单独成行的，缩小显示
        html = re.sub(r'<p style=\'[^\']*\'>(https?://[^\s<]+)</p>', r'<p style="margin:1px 0;line-height:1.3;font-size:10px;color:#5577aa;word-break:break-all">\1</p>', html)
        # 把连续图片并排：先标记，再分组
        def _group_images(html):
            IMG_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
            lines = html.split("\n")
            result = []
            img_buf = []
            grp_id = [0]
            for line in lines:
                stripped = line.strip()
                clean = re.sub(r"</?p[^>]*>|<br>", "", stripped).strip()
                if IMG_RE.fullmatch(clean):
                    img_buf.append(IMG_RE.search(clean).group(2))
                else:
                    if img_buf:
                        result.append(RichPanel._imgs_to_row(img_buf, grp_id[0]))
                        grp_id[0] += 1
                        img_buf = []
                    result.append(line)
            if img_buf:
                result.append(RichPanel._imgs_to_row(img_buf, grp_id[0]))
            return "\n".join(result)
        html = _group_images(html)
        return f'<div style="text-align:left">{html}</div>'

    @staticmethod
    def _imgs_to_row(urls, group_id=0):
        n = len(urls)
        w = 140 if n == 1 else (220 // n - 4)
        cells = "".join(f'<td style="vertical-align:middle;text-align:center"><a href="img:{group_id}:{u}"><img src="{u}" width="{w}"></a></td>' for u in urls)
        return f'<table cellspacing="2" style="margin:4px 0"><tr>{cells}</tr></table>'

    @staticmethod
    def extract_image_urls(md):
        return re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)


class BubbleDots(QWidget):
    """像素风小方块泡泡"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(8, 8)
        self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(PX_BG)
        p.drawRect(0, 0, 8, 8)
        p.setBrush(PX_BORDER)
        p.drawRect(0, 0, 8, 1)
        p.drawRect(0, 7, 8, 1)
        p.drawRect(0, 0, 1, 8)
        p.drawRect(7, 0, 1, 8)
        p.end()


class RPSPanel(QWidget):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.callback = callback
        self.setFixedSize(max(SPRITE_W, 160), 32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        btn_style = f"""
            QPushButton {{
                background: {PX_BTN.name()}; color: white; border: 1.8px solid {PX_BORDER.name()};
                border-radius: 0px; font-size: 11px; padding: 4px 8px;
            }}
            QPushButton:hover {{ background: {PX_BTN_HOVER.name()}; }}
        """
        for name in ["石头", "剪刀", "布"]:
            btn = QPushButton(name, self)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked, n=name: self._pick(n))
            layout.addWidget(btn)
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._auto_hide)
        self.hide()

    def showPanel(self):
        self.show(); self._timeout.start(5000)

    def _auto_hide(self):
        if self.isVisible(): self.hide(); self.callback(None)

    def _pick(self, c):
        self._timeout.stop(); self.hide(); self.callback(c)


class CoinWidget(QWidget):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(24, 60)
        self.callback = callback
        self.coin_frames = [coin_pixmap(i) for i in range(3)]
        self.coin_frames = [f.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation) for f in self.coin_frames]
        self.label = QLabel(self)
        self.label.setFixedSize(20, 20)
        self.frame_idx = self.tick = 0
        self.total_ticks = 24
        self.result = 0
        self.base_y = 38
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.hide()

    def flip(self):
        self.result = random.choice([0, 2])
        self.frame_idx = self.tick = 0
        self.label.move(3, self.base_y)
        self.show(); self.timer.start(50)

    def _animate(self):
        self.tick += 1
        t, total = self.tick, self.total_ticks
        y = self.base_y - int(45 * math.sin(math.pi * t / total))
        if t < total * 0.7: self.frame_idx += 1
        elif t % 2 == 0: self.frame_idx += 1
        self.label.setPixmap(self.coin_frames[self.frame_idx % 3])
        self.label.move(3, y)
        if t >= total:
            self.label.setPixmap(self.coin_frames[self.result])
            self.label.move(3, self.base_y)
            self.timer.stop()
            r = "正面" if self.result == 0 else "反面"
            self.callback(r)
            QTimer.singleShot(2500, self.hide)


# ============================================================
# 聊天线程 — 流式调用自研模型 API
# ============================================================
_API_URL = "http://agi-arkaiagent-offline.devops.xiaohongshu.com/agent/v3/xproject/chat_stream_v2"

class ChatThread(QThread):
    chunk_received = pyqtSignal(str)        # 累积文本实时推送
    finished_signal = pyqtSignal(list, dict) # (有序bubble列表[(type,text)], {url:bytes}图片)
    visible_think = pyqtSignal(str)          # <think><visible>思考词</visible></think>

    def __init__(self, text, conversation_id, location="", messages=None, parent=None):
        super().__init__(parent)
        self._text = text
        self._conv_id = conversation_id
        self._location = location
        self._messages = messages or []

    def run(self):
        msg_id = str(random.randint(10**18, 10**19 - 1))
        trace_id = f"diandian_{int(time.time()*1000)}"
        # 多轮：把历史拼进content，位置拼进当前query
        user_text = self._text
        if self._location and self._query_needs_location(self._text):
            user_text = f"[我在{self._location}] {self._text}"
        if self._messages:
            parts = []
            for m in self._messages:
                role = "用户" if m["role"] == "user" else "点点"
                parts.append(f"{role}：{m['content']}")
            parts.append(f"用户：{user_text}")
            full_content = "\n".join(parts)
        else:
            full_content = user_text
        body = json.dumps({
            "pipelineNumberId": 30,
            "userId": "194184245103718400",
            "conversationId": self._conv_id,
            "queryMessageId": msg_id,
            "userLocation": self._location,
            "content": full_content,
            "sensitiveDetail": {},
            "hideInnerThoughts": True,
            "returnObservation": True,
            "doSample": True,
            "enableMemory": True,
            "source": "xhs",
            "createTime": int(time.time() * 1000),
            "userInput": self._text,
            "xhsUserid": "6400a8d2000000001002421e",
            "extraData": {}
        }).encode("utf-8")

        req = urllib.request.Request(
            _API_URL,
            data=body,
            headers={"Content-Type": "application/json", "traceId": trace_id},
        )
        full_text = ""
        selected_images = {}  # {img-id: url}
        _visible_emitted = False
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        line = line[5:]
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("type") == "reply":
                        delta = obj.get("delta", "")
                        full_text += delta
                        # 提取<visible>思考词
                        if not _visible_emitted:
                            vm = re.search(r"<visible>(.*?)</visible>", full_text, re.DOTALL)
                            if vm:
                                vt = vm.group(1).strip()
                                # 清理末尾的 ｜收集 等标记
                                vt = re.sub(r'[｜|]\S+$', '', vt).strip()
                                if vt:
                                    self.visible_think.emit(vt)
                                    _visible_emitted = True
                        clean = ChatThread._clean_response(full_text)
                        self.chunk_received.emit(clean)
                    elif obj.get("type") == "selected_image":
                        selected_images.update(obj.get("selected_image", {}))
        except urllib.error.HTTPError as e:
            if e.code == 502:
                full_text = "连不上服务器，可能没连公司网络/VPN哦"
            else:
                full_text = f"服务器返回了错误（{e.code}），稍后再试试"
        except urllib.error.URLError:
            full_text = "网络不通，检查一下WiFi或VPN连接吧"
        except Exception as e:
            full_text = f"出了点问题：{e}"

        # 保存raw data日志
        try:
            log_dir = os.path.join(DATA_DIR, "chat_logs")
            os.makedirs(log_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            with open(os.path.join(log_dir, f"{ts}.md"), "w", encoding="utf-8") as f:
                f.write(f"# Query: {self._text}\n\n---\n\n{full_text}\n")
        except Exception:
            pass

        bubbles = self._parse_response(full_text, selected_images)
        if not bubbles:
            bubbles = [("short", "...没想出来")]
        # 收集rich bubble里的markdown图片URL并下载
        img_data = {}
        for btype, content in bubbles:
            if btype == "rich":
                for url in RichPanel.extract_image_urls(content):
                    if url not in img_data:
                        try:
                            with urllib.request.urlopen(url, timeout=8) as r:
                                img_data[url] = r.read()
                        except Exception:
                            pass
        self.finished_signal.emit(bubbles, img_data)

    _LOC_KEYWORDS = re.compile(
        r"推荐|附近|哪里|好吃|好玩|去哪|周边|门店|餐厅|咖啡|酒店|酒吧|"
        r"景点|打卡|探店|逛|吃什么|喝什么|玩什么|去处|商场|书店|"
        r"火锅|奶茶|甜品|烧烤|夜宵|早餐|brunch|下午茶"
    )

    @staticmethod
    def _query_needs_location(text):
        return bool(ChatThread._LOC_KEYWORDS.search(text))

    @staticmethod
    def _strip_tags(text):
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
        text = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL)
        text = re.sub(r"<tool_call>.*", "", text, flags=re.DOTALL)
        text = re.sub(r"<visible>.*?</visible>", "", text, flags=re.DOTALL)
        return text

    @staticmethod
    def _parse_response(text, selected_images=None):
        """返回有序bubble列表[(type, content)]"""
        if selected_images is None:
            selected_images = {}
        text = ChatThread._strip_tags(text)
        bubbles = []
        for part in re.split(r"</bubble>", text):
            part = part.strip()
            if not part or "<bubble>" not in part:
                continue
            if "<long_rich_text>" in part:
                # rich bubble — 提取CDATA里的markdown
                cdata = re.search(r"<!\[CDATA\[(.*?)\]\]>", part, flags=re.DOTALL)
                if cdata:
                    md = cdata.group(1).strip()
                    # 把 <image id=img-xxx ...></image> 替换成markdown图片
                    def _replace_image(m):
                        img_id = m.group(1)
                        url = selected_images.get(img_id, "")
                        if url:
                            return f"![{img_id}]({url})"
                        return ""
                    md = re.sub(r"<image\s+id=([^\s>]+)[^>]*>\s*</image>", _replace_image, md)
                    bubbles.append(("rich", md))
            else:
                # 短bubble
                m = re.search(r"<content>(.*?)</content>", part, flags=re.DOTALL)
                if m:
                    t = m.group(1).strip()
                    t = re.sub(r"<cite[^>]*>.*?</cite>", "", t, flags=re.DOTALL)
                    t = t.strip()
                    if t:
                        bubbles.append(("short", t))
        # fallback
        if not bubbles:
            cleaned = re.sub(r"<[^>]+>", "", text)
            cleaned = re.sub(r"<!\[CDATA\[.*?\]\]>", "", cleaned, flags=re.DOTALL)
            cleaned = cleaned.strip()
            if cleaned:
                bubbles = [("short", cleaned)]
        return bubbles

    @staticmethod
    def _clean_response(text):
        bubbles = ChatThread._parse_response(text)
        for btype, content in bubbles:
            if btype == "short":
                return content
        return ""


# ============================================================
# 主窗口
# ============================================================
class ClawdPet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WIN_W, WIN_H)
        self.setMouseTracking(True)  # 追踪鼠标用于眼睛跟踪

        self.sprite = QLabel(self)
        self.sprite.setFixedSize(SPRITE_MAX, SPRITE_MAX)
        self.sprite.move(0, BUBBLE_ZONE)

        self.bubble = SpeechBubble(self)
        # 圆泡泡固定在精灵右上角，永远同一个位置
        self.bubble_dots = BubbleDots(self)
        # 固定：精灵右上角
        self._dot_x = SPRITE_W - 2
        self._dot_y = BUBBLE_ZONE - 14
        self.bubble_dots.move(self._dot_x, self._dot_y)
        self.rps_panel = RPSPanel(self, self._rps_result)
        self.coin = CoinWidget(self, self._coin_result)

        # 食物显示
        self.food_label = QLabel(self)
        self.food_label.setFixedSize(40, 40)
        self.food_label.hide()

        # 番茄钟：倒计时数字
        self.pomo_dot = QLabel(self)
        self.pomo_dot.setFixedSize(45, 16)
        self.pomo_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomo_dot.setFixedSize(55, 20)
        self.pomo_dot.setStyleSheet(f"color: {PX_BTN_HOVER.name()}; font-size: 14px; font-weight: bold; background: transparent;")
        self.pomo_dot.move(SPRITE_W - 10, BUBBLE_ZONE - 4)
        self.pomo_dot.hide()
        self._pomo_tick_timer = QTimer(self)
        self._pomo_tick_timer.timeout.connect(self._update_pomo_display)
        self._pomodoro_active = False

        # 喝水提醒
        self._water_active = False
        self._water_interval = 30 * 60 * 1000  # 默认30分钟
        self._water_timer = QTimer(self)
        self._water_timer.timeout.connect(self._water_remind)

        # 位置：手动 > IP定位 > 上次缓存
        self._user_location = ""
        self._load_location()

        # 聊天
        self._chat_data_path = os.path.join(DATA_DIR, ".chat_data.json")
        self._conv_id = "CHAT_" + hashlib.sha256(f"diandian_{time.time()}".encode()).hexdigest()
        self._chat_thread = None
        self._chatting = False
        self._chat_history = []  # [(question, bubble_list, images), ...]
        self._chat_messages = []  # 多轮对话上下文 [{"role":"user","content":...}, {"role":"assistant","content":...}]
        self._last_chat_time = 0   # 上次对话时间戳，超3分钟自动清上下文
        self._load_chat_data()
        self._rich_panel_next_pending = False
        self._chat_is_last_bubble = False
        self._chat_advance_timer = QTimer(self)
        self._chat_advance_timer.setSingleShot(True)
        self._chat_advance_timer.timeout.connect(self._on_advance_timeout)
        self._rich_panel = RichPanel()
        self._rich_panel.set_close_callback(self._on_rich_panel_closed)
        self.chat_input = QLineEdit(self)
        self.chat_input.setPlaceholderText("和点点说点什么...")
        self._chat_input_min_w = 100
        self._chat_input_max_w = 200
        self.chat_input.setFixedSize(self._chat_input_min_w, 26)
        self.chat_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(245, 240, 230, 160);
                border: 1.8px solid {PX_BORDER.name()};
                border-radius: 0px;
                font-size: 12px;
                color: {PX_TEXT.name()};
                padding: 2px 6px;
            }}
        """)
        pal = self.chat_input.palette()
        pal.setColor(pal.ColorRole.PlaceholderText, QColor(160, 155, 140, 180))
        self.chat_input.setPalette(pal)
        self.chat_input.move(max(0, SPRITE_W // 2 - self._chat_input_min_w // 2), BUBBLE_ZONE - 38)
        self.chat_input.returnPressed.connect(self._send_chat)
        self.chat_input.textChanged.connect(self._on_chat_input_changed)
        self.chat_input.hide()
        # 输入框空闲自动收起
        self._chat_input_timer = QTimer(self)
        self._chat_input_timer.setSingleShot(True)
        self._chat_input_timer.timeout.connect(self._auto_hide_chat_input)
        self._chat_input_idle = 8000  # 8秒无操作自动收

        # 毯子（睡觉时显示）
        self.blanket_label = QLabel(self)
        blanket_img = QImage(16*PX, 6*PX, QImage.Format.Format_ARGB32)
        blanket_img.fill(QColor(0, 0, 0, 0))
        bp = QPainter(blanket_img)
        for r, row in enumerate(BLANKET):
            for c, val in enumerate(row):
                if val in FOOD_COLORS:
                    bp.fillRect(c*PX, r*PX, PX, PX, FOOD_COLORS[val])
        bp.end()
        self.blanket_label.setPixmap(QPixmap.fromImage(blanket_img))
        self.blanket_label.setFixedSize(16*PX, 6*PX)
        self.blanket_label.hide()


        # 季节粒子
        self._particles = []
        self._particle_timer = QTimer(self)
        self._particle_timer.timeout.connect(self._animate_particles)
        self._particle_timer.start(100)
        # 根据月份决定粒子类型
        month = date.today().month
        if month in (12, 1, 2):
            self._particle_type = "snow"
        elif month in (3, 4, 5):
            self._particle_type = "petal"
        elif month in (6, 7, 8):
            self._particle_type = "sun"
        else:
            self._particle_type = "leaf"

        # zzz 标签
        self.zzz_labels = []
        for i in range(3):
            z = QLabel(self)
            z.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            z.setStyleSheet(f"color: rgba(140,215,180,{180-i*50}); font-size: {14-i*2}px; font-weight: bold; background: transparent;")
            z.setText("z"); z.setFixedSize(16, 16); z.hide()
            self.zzz_labels.append(z)
        self._zzz_timer = QTimer(self)
        self._zzz_timer.timeout.connect(self._animate_zzz)
        self._zzz_tick = 0

        # 预渲染所有帧
        self.frames = {
            "normal": grid_to_pixmap(CLAWD_NORMAL),
            "look_l": grid_to_pixmap(CLAWD_LOOK_L),
            "look_r": grid_to_pixmap(CLAWD_LOOK_R),
            "look_u": grid_to_pixmap(CLAWD_LOOK_U),
            "stare": grid_to_pixmap(CLAWD_STARE),
            "blink": grid_to_pixmap(CLAWD_BLINK),
            "sleep": grid_to_pixmap(CLAWD_BLINK),
            "walk1": grid_to_pixmap(CLAWD_WALK1),
            "walk2": grid_to_pixmap(CLAWD_WALK2),
            "flail1": grid_to_pixmap(CLAWD_FLAIL1),
            "flail2": grid_to_pixmap(CLAWD_FLAIL2),
        }

        # 状态
        self.state = State.IDLE
        self.walk_dir = 1
        self._walk_axis = 'h'
        self.walk_toggle = False
        self._cur_eye = "normal"  # 当前眼睛方向
        self._show_frame("normal")

        self._drag_start = None
        self._win_start = None
        self._flail_toggle = False
        self._pending_click = False
        self._dbl_click_guard = False

        # 无交互计时（自动入睡用）
        self._idle_since = 0
        self._quiet = True  # 默认自己玩，不跟随鼠标
        self._hiding = False  # 藏猫猫

        # 边缘躲藏
        self._hidden_edge = None  # None / "left" / "right"
        self._peek_amount = 0
        self._is_peeking = False

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() // 2 - WIN_W // 2, screen.height() - WIN_H - 60)
        self.base_y = self.pos().y()
        self.jump_phase = self.jumps_left = self.tick = 0
        self._rps_ai = ""

        # 定时器
        t = QTimer(self); t.timeout.connect(self._on_tick); t.start(60)
        bt = QTimer(self); bt.timeout.connect(self._blink); bt.start(3000)
        self.rand_timer = QTimer(self)
        self.rand_timer.timeout.connect(self._random)
        self.rand_timer.start(random.randint(30000, 70000))
        self.end_timer = QTimer(self)
        self.end_timer.setSingleShot(True)
        self.end_timer.timeout.connect(lambda: self._go(State.IDLE))
        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.timeout.connect(self._hide_bubble)

        # 眼睛追踪定时器
        self._eye_timer = QTimer(self)
        self._eye_timer.timeout.connect(self._track_eyes)
        self._eye_timer.start(200)

        _greetings = [
            ("嗨，我是点点", "双击我可以聊天哦"),
            ("嗨，我是点点", "无聊了就来找我说话吧"),
            ("嗨，我是点点", "右键菜单有很多好玩的"),
            ("来啦来啦", "双击我，什么都可以问哦"),
        ]
        g1, g2 = random.choice(_greetings)
        QTimer.singleShot(500, lambda: self._say(g1, 3000) if not self.chat_input.isVisible() else None)
        QTimer.singleShot(4000, lambda: self._say(g2, 3500) if not self.chat_input.isVisible() else None)
        # 首次启动且无任何位置信息，3秒后引导设置
        if not self._user_location:
            QTimer.singleShot(3000, self._first_time_location)
        self.show(); self.raise_()

        # macOS 全屏置顶
        try:
            import ctypes, ctypes.util
            objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
            objc.objc_getClass.restype = ctypes.c_void_p
            objc.sel_registerName.restype = ctypes.c_void_p
            objc.objc_msgSend.restype = ctypes.c_void_p
            objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            NSApp = objc.objc_msgSend(objc.objc_getClass(b'NSApplication'), objc.sel_registerName(b'sharedApplication'))
            windows = objc.objc_msgSend(NSApp, objc.sel_registerName(b'windows'))
            objc.objc_msgSend.restype = ctypes.c_uint64
            count = objc.objc_msgSend(windows, objc.sel_registerName(b'count'))
            if count > 0:
                objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64]
                objc.objc_msgSend.restype = ctypes.c_void_p
                win = objc.objc_msgSend(windows, objc.sel_registerName(b'objectAtIndex:'), 0)
                objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64]
                objc.objc_msgSend.restype = None
                objc.objc_msgSend(win, objc.sel_registerName(b'setLevel:'), 3)
        except Exception:
            pass

    def paintEvent(self, event):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(self.rect(), QColor(0, 0, 0, 0))
        p.end()

    # -------- 眼睛追踪鼠标 --------
    def _track_eyes(self):
        if self.state not in (State.IDLE, State.HAPPY):
            return
        cursor = QCursor.pos()
        center = self.mapToGlobal(QPoint(SPRITE_W // 2, BUBBLE_ZONE + SPRITE_H // 2))
        dy = cursor.y() - center.y()
        # 只在鼠标在上方很远时抬头看，其余时间正常
        new_eye = "look_u" if dy < -100 else "normal"
        if new_eye != self._cur_eye:
            self._cur_eye = new_eye
            self._show_frame(new_eye)

    # -------- 显示帧 --------
    def _show_frame(self, name):
        self.cur_frame = name
        pm = self.frames.get(name, self.frames["normal"])
        if self.state == State.WALKING:
            axis = self._walk_axis
            if axis == 'h':
                pass  # 水滴形不翻转，鞋子动画方向才对
            elif axis == 'v':
                pm = pm.transformed(QTransform().rotate(90 if self.walk_dir == -1 else -90))
            elif axis == 'hang':
                pm = pm.transformed(QTransform().rotate(180))
        elif self.state == State.DRAGGING:
            # 拖拽时不翻转
            pass
        self.sprite.setPixmap(pm)

    def _say(self, text, duration=2500):
        self.bubble.set_text(text)
        bw, bh = self.bubble.width(), self.bubble.height()
        # 气泡左下角贴着圆泡泡右上角
        bx = self._dot_x + 12  # 圆泡泡右边
        by = self._dot_y - bh  # 气泡底部对齐圆泡泡顶部
        if by < 0: by = 0
        self.bubble.move(bx, by)
        self.bubble.show()
        self.bubble_dots.show()
        self.bubble_dots.show()
        self.bubble_timer.start(duration)

    def _hide_bubble(self):
        self.bubble.hide()
        self.bubble_dots.hide()

    def _touch(self):
        """记录交互时间，重置自动入睡"""
        self._idle_since = self.tick

    # -------- 动画主循环 --------
    def _on_tick(self):
        self.tick += 1
        pos = self.pos()

        if self.state == State.IDLE:
            if self._chatting:
                pass  # 聊天模式下不做任何自动行为
            elif not self._quiet:
                # 检查鼠标距离，远了就走过去
                cursor = QCursor.pos()
                cx = pos.x() + SPRITE_W // 2
                dx = cursor.x() - cx
                if abs(dx) > 150:
                    self._go(State.WALKING)
                    self._walk_axis = 'follow'
                    self.walk_dir = 1 if dx > 0 else -1
                # 自动入睡：60秒无交互
                if self.tick - self._idle_since > 1000:
                    self._say("有点有点累了", 2500)
                    QTimer.singleShot(3000, self._auto_sleep)
                    self._idle_since = self.tick

        elif self.state == State.DRAGGING:
            # 拖拽时腿乱蹬
            if self.tick % 4 == 0:
                self._flail_toggle = not self._flail_toggle
                self._show_frame("flail1" if self._flail_toggle else "flail2")

        elif self.state == State.WALKING:
            if self._drag_start is not None:
                return
            scr = QApplication.primaryScreen().virtualGeometry()
            for s in QApplication.screens():
                scr = scr.united(s.virtualGeometry())
            speed = 2
            nx, ny = pos.x(), pos.y()
            axis = self._walk_axis

            if axis == 'follow':
                cursor = QCursor.pos()
                tx = cursor.x() - SPRITE_W // 2
                ty = cursor.y() - BUBBLE_ZONE - SPRITE_H // 2
                dx = tx - nx
                dy = ty - ny
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 30:
                    self._go(State.IDLE)
                else:
                    self.walk_dir = 1 if dx > 0 else -1
                    nx += int(speed * dx / dist)
                    ny += int(speed * dy / dist)
            elif axis == 'h':
                nx += speed * self.walk_dir
                if nx >= scr.right() - self.width():
                    nx = scr.right() - self.width()
                    self._walk_axis = 'v'; self.walk_dir = -1
                elif nx <= scr.left():
                    nx = scr.left()
                    self._walk_axis = 'v'; self.walk_dir = -1
            elif axis == 'v':
                ny += speed * self.walk_dir
                if ny <= 0:
                    ny = 0
                    self._walk_axis = 'hang'; self._hang_tick = 0
                    self.walk_dir = random.choice([-1, 1])
                elif ny >= scr.bottom() - self.height():
                    ny = scr.bottom() - self.height()
                    self._walk_axis = 'h'
                    self.walk_dir = -1 if nx > scr.left() + scr.width() // 2 else 1
            elif axis == 'hang':
                ny = 0
                nx += speed * self.walk_dir
                self._hang_tick = getattr(self, '_hang_tick', 0) + 1
                if nx >= scr.right() - self.width():
                    nx = scr.right() - self.width(); self.walk_dir = -1
                elif nx <= scr.left():
                    nx = scr.left(); self.walk_dir = 1
                if self._hang_tick > 150:
                    self._walk_axis = 'fall'; self._fall_speed = 0
                    self._fall_ground = QApplication.primaryScreen().availableGeometry().bottom() - self.height()
            elif axis == 'fall':
                self._fall_speed = getattr(self, '_fall_speed', 0) + 1.2
                ny += int(self._fall_speed)
                ground = getattr(self, '_fall_ground', 800)
                if ny >= ground:
                    ny = ground
                    self.base_y = ny
                    self._say("...好疼", 2500)
                    self._show_frame("stare")
                    self._walk_axis = 'stunned'
                    self._stun_tick = 0
            elif axis == 'stunned':
                self._stun_tick = getattr(self, '_stun_tick', 0) + 1
                if self._stun_tick > 50:
                    self._go(State.IDLE)
            # 限制在虚拟桌面范围内
            nx = max(scr.left(), min(nx, scr.right() - self.width()))
            ny = max(0, min(ny, scr.bottom() - self.height()))
            self.move(nx, ny)
            if axis not in ('fall', 'stunned') and self.tick % 8 == 0:
                self.walk_toggle = not self.walk_toggle
                self._show_frame("walk1" if self.walk_toggle else "walk2")

        elif self.state == State.HAPPY:
            if self.jump_phase < 6: dy = -4
            elif self.jump_phase < 12: dy = 4
            else:
                self.jumps_left -= 1; self.jump_phase = -1
                if self.jumps_left <= 0: self._go(State.IDLE); return
                dy = 0
            self.jump_phase += 1
            self.move(pos.x(), pos.y() + dy)

        elif self.state == State.SLEEPING:
            self.move(pos.x(), self.base_y + int(2 * math.sin(self.tick * 0.05)))

        self.update()
        self._update_mask()

    def _auto_sleep(self):
        if self.state == State.IDLE and not self.chat_input.isVisible() and not self._rich_panel.isVisible():
            self._go(State.SLEEPING)

    def _blink(self):
        if self.state not in (State.IDLE, State.HAPPY): return
        self._show_frame("blink")
        QTimer.singleShot(150, lambda: self._show_frame(self._cur_eye) if self.state in (State.IDLE, State.HAPPY) else None)

    def _random(self):
        if self.state != State.IDLE or self._chatting or self.chat_input.isVisible() or self._rich_panel.isVisible():
            self.rand_timer.start(random.randint(30000, 70000)); return

        # 偶尔触发工作提醒（20%概率），剩下的走正常随机
        if random.random() < 0.2:
            hint = self._get_work_hint()
            if hint:
                self._say(hint, 4000)
                self.rand_timer.start(random.randint(30000, 70000))
                return

        act = random.choice(["walk", "happy", "talk", "talk", "talk", "sleep", "eat"])
        if act == "walk":
            self._go(State.WALKING); self._say("出去走走", 2000)
        elif act == "happy":
            self._go(State.HAPPY); self._say("心情不错", 2000)
        elif act == "sleep":
            self._go(State.SLEEPING); self._say("有点累了", 2000)
            self.end_timer.start(random.randint(6000, 12000))
        elif act == "eat":
            food = random.choice(list(FOOD_GRIDS.keys()))
            self._say(f"吃个{food}", 2000)
            QTimer.singleShot(500, lambda: self._feed(food))
        elif act == "talk":
            self._say(random.choice(IDLE_LINES), 3000)
        self.rand_timer.start(random.randint(30000, 70000))

    def _get_work_hint(self):
        """根据时间和日志状态生成工作提醒，没有就返回 None"""
        from datetime import datetime
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=周一, 4=周五

        today = date.today()
        log_path = Path.home() / "projects" / "work_log" / "daily_log" / today.strftime("%Y-%m") / today.strftime("%m-%d.md")
        has_log = log_path.exists() and log_path.stat().st_size > 10

        # 周五下午提醒周报
        if weekday == 4 and hour >= 14:
            return random.choice(["周五了，周报写了吗", "该出周报了"])

        # 下午6点后提醒记录
        if hour >= 18 and not has_log:
            return random.choice(["今天还没写记录", "该记录一下今天做了什么"])

        # 上午提醒开工
        if hour >= 9 and hour < 10 and not has_log:
            return "新的一天，加油"

        return None

    def _go(self, state):
        old = self.state
        pos = self.pos()
        self.base_y = pos.y()
        self.state = state
        # 状态变化时收起输入框
        if self.chat_input.isVisible():
            self.chat_input.hide()
            self._chat_input_timer.stop()
        if old == State.SLEEPING and state != State.SLEEPING:
            self._stop_zzz()
            self.blanket_label.hide()
        if state == State.IDLE:
            self.walk_edge = "bottom"
            self.base_y = self.pos().y()
            self._show_frame("normal")
            self._idle_since = self.tick
        elif state == State.WALKING:
            self.walk_dir = random.choice([-1, 1])
            self._walk_axis = 'h'
            self._show_frame("walk1")
        elif state == State.SLEEPING:
            self._show_frame("sleep"); self._start_zzz()
            # 盖毯子
            self.blanket_label.move(0, BUBBLE_ZONE + SPRITE_H - 30)
            self.blanket_label.show()
        elif state == State.HAPPY:
            self.jumps_left = 3; self.jump_phase = 0; self._show_frame("normal")

    # -------- zzz --------
    def _start_zzz(self):
        self._zzz_tick = 0; self._zzz_timer.start(400)

    def _stop_zzz(self):
        self._zzz_timer.stop()
        for z in self.zzz_labels: z.hide()

    def _animate_zzz(self):
        self._zzz_tick += 1
        bx, by = SPRITE_W - 15, BUBBLE_ZONE - 5
        for i, z in enumerate(self.zzz_labels):
            phase = (self._zzz_tick + i * 3) % 12
            if phase < 9:
                z.move(bx + i * 10 + phase * 2, by - phase * 4); z.show()
            else:
                z.hide()

    # -------- 季节粒子 --------
    def _animate_particles(self):
        # 偶尔生成新粒子
        if random.random() < 0.3 and len(self._particles) < 5:
            p = QLabel(self)
            p.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            p.setFixedSize(6, 6)
            t = self._particle_type
            if t == "snow":
                p.setStyleSheet("background: rgba(255,255,255,180); border-radius: 3px;")
            elif t == "petal":
                p.setStyleSheet("background: rgba(255,180,200,180); border-radius: 3px;")
            elif t == "leaf":
                p.setStyleSheet("background: rgba(200,170,50,180); border-radius: 2px;")
            else:  # sun - 小光点
                p.setStyleSheet("background: rgba(255,230,100,150); border-radius: 3px;")
            x = random.randint(0, SPRITE_W + 30)
            p.move(x, BUBBLE_ZONE - 10)
            p.show()
            self._particles.append({"label": p, "x": x, "y": BUBBLE_ZONE - 10, "dx": random.uniform(-0.5, 0.5), "dy": random.uniform(0.5, 1.5)})

        # 移动粒子
        to_remove = []
        for pt in self._particles:
            pt["x"] += pt["dx"]
            pt["y"] += pt["dy"]
            pt["label"].move(int(pt["x"]), int(pt["y"]))
            if pt["y"] > BUBBLE_ZONE + SPRITE_H + 20:
                pt["label"].hide()
                pt["label"].deleteLater()
                to_remove.append(pt)
        for pt in to_remove:
            self._particles.remove(pt)

    # -------- 窗口 mask（让透明区域点击穿透）--------
    def _update_mask(self):
        region = QRegion(self.sprite.geometry())
        for child in self.findChildren(QWidget):
            if child.isVisible() and child.parent() == self:
                region = region.united(QRegion(child.geometry()))
        self.setMask(region)

    # -------- 鼠标 --------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._touch()
            self._drag_start = e.globalPosition().toPoint()
            self._win_start = self.pos()
            self._pre_drag_state = self.state
            self._pre_drag_dir = self.walk_dir
            self._pre_drag_axis = self._walk_axis
            # 记录拖拽位置历史（算甩飞速度用）
            self._drag_history = [(e.globalPosition().toPoint(), self.tick)]
            if not self._chatting and not self._rich_panel.isVisible():
                if self.chat_input.isVisible():
                    self.chat_input.hide()
                    self._chat_input_timer.stop()
                self._hide_bubble()
            # 记录面板相对位置，拖拽时同步移动
            if self._rich_panel.isVisible():
                self._drag_panel_offset = self._rich_panel.pos() - self.pos()
            else:
                self._drag_panel_offset = None
            if self.state == State.SLEEPING:
                self._stop_zzz()
                self.blanket_label.hide()
            self.state = State.DRAGGING

    def mouseMoveEvent(self, e):
        if self._drag_start is not None:
            d = e.globalPosition().toPoint() - self._drag_start
            p = self._win_start + d
            scr = QApplication.primaryScreen().virtualGeometry()
            for s in QApplication.screens():
                scr = scr.united(s.virtualGeometry())
            x = max(scr.left(), min(p.x(), scr.right() - self.width()))
            y = max(scr.top(), min(p.y(), scr.bottom() - self.height()))
            self.move(x, y)
            self.base_y = y
            # 面板跟着走
            if self._drag_panel_offset is not None and self._rich_panel.isVisible():
                self._rich_panel.move(QPoint(x, y) + self._drag_panel_offset)
            # 记录最近 5 个位置
            self._drag_history.append((e.globalPosition().toPoint(), self.tick))
            if len(self._drag_history) > 5:
                self._drag_history.pop(0)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            was_drag = False
            if self._drag_start:
                d = e.globalPosition().toPoint() - self._drag_start
                was_drag = abs(d.x()) > 5 or abs(d.y()) > 5
            self._drag_start = None

            if self.state == State.DRAGGING:
                self.base_y = self.pos().y()
                prev = self._pre_drag_state
                if prev == State.WALKING:
                    self.state = State.WALKING
                    self.walk_dir = self._pre_drag_dir
                    self._walk_axis = self._pre_drag_axis
                    self._show_frame("walk1")
                elif prev == State.SLEEPING:
                    self._go(State.SLEEPING)
                else:
                    self._go(State.IDLE)

            if not was_drag:
                self._on_click()

    def _on_click(self):
        if self._dbl_click_guard:
            return
        self._touch()
        if self._hiding:
            self._found()
            return
        # 面板可见时忽略点击（聊天中 or 历史浏览）
        if self._rich_panel.isVisible():
            return
        # 聊天中点击 → 提前切换到下一个bubble
        if self._chatting and self._chat_advance_timer.isActive():
            self._chat_advance_timer.stop()
            self._on_advance_timeout()
            return
        # 延迟执行，让双击有机会取消
        self._pending_click = True
        QTimer.singleShot(250, self._do_click)

    def _do_click(self):
        if not self._pending_click:
            return
        self._pending_click = False
        if self.chat_input.isVisible():
            return
        if self.state == State.SLEEPING:
            self._go(State.IDLE); self._say("嗯...醒了", 2000)
        else:
            self._show_frame("stare")
            self._say(random.choice(CLICK_LINES), 2500)
            QTimer.singleShot(800, lambda: self._show_frame(self._cur_eye) if self.state == State.IDLE else None)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._touch()
            self._pending_click = False
            self._dbl_click_guard = True
            if self._rich_panel.isVisible():
                # 面板开着时只跳跳，不关面板不出输入框
                pass
            else:
                self._hide_bubble()
                self._toggle_chat()
            QTimer.singleShot(300, lambda: setattr(self, '_dbl_click_guard', False))

    def contextMenuEvent(self, event):
        self._touch()
        self._hide_bubble()
        self._rich_panel.hide()
        self.chat_input.hide()
        self._chat_input_timer.stop()
        menu = QMenu(self)
        _menu_base = f"""
            QMenu {{
                background: {PX_BG.name()};
                border: 1.8px solid {PX_BORDER.name()};
                border-radius: 0px;
                padding: 3px 0;
                font-size: 12px;
                color: {PX_TEXT.name()};
            }}
            QMenu::item {{ padding: 6px 16px; }}
            QMenu::separator {{ height: 1.8px; background: {PX_BORDER.name()}; margin: 2px 4px; }}
        """
        _menu_css = _menu_base + f"QMenu::item:selected {{ background: {PX_BTN.name()}; color: white; }}"
        menu.setStyleSheet(_menu_css)
        chat_menu = menu.addMenu("聊天")
        chat_menu.setStyleSheet(_menu_css)
        a_chat = chat_menu.addAction("新对话")
        _hist_actions = []
        _hist_refs = list(self._chat_history)
        if _hist_refs:
            chat_menu.addSeparator()
            for entry in reversed(_hist_refs):
                q = entry[0]
                label = q[:12] + "..." if len(q) > 12 else q
                a = chat_menu.addAction(label)
                _hist_actions.append((a, entry))
        menu.addSeparator()
        a_quiet = menu.addAction("点点跟着我" if self._quiet else "点点自己玩")
        menu.addSeparator()
        a_fortune = menu.addAction("今日运势")
        if not getattr(self, '_pomodoro_active', False):
            a_pomo = menu.addAction("番茄钟")
        else:
            a_pomo = menu.addAction(f"番茄钟进行中... {self._pomo_remaining()}")
        if not self._water_active:
            a_water = menu.addAction("喝水提醒")
        else:
            a_water = menu.addAction("关闭喝水提醒")
        menu.addSeparator()
        feed_menu = menu.addMenu("喂点点")
        feed_menu.setStyleSheet(_menu_css)
        a_apple = feed_menu.addAction("苹果")
        a_tea = feed_menu.addAction("茶")
        a_cake = feed_menu.addAction("蛋糕")
        a_sushi = feed_menu.addAction("寿司")
        a_burger = feed_menu.addAction("汉堡")
        a_rps = menu.addAction("猜拳")
        a_hide = menu.addAction("藏猫猫")
        menu.addSeparator()
        a_stop = a_wake = a_walk = a_sleep = None
        if self.state == State.WALKING:
            a_stop = menu.addAction("停下来")
        elif self.state == State.SLEEPING:
            a_wake = menu.addAction("叫醒")
        if self.state != State.WALKING:
            a_walk = menu.addAction("散步")
        if self.state != State.SLEEPING:
            a_sleep = menu.addAction("睡觉")
        menu.addSeparator()
        a_loc = menu.addAction("设置位置")
        menu.addSeparator()
        a_quit = menu.addAction("退出")

        a = menu.exec(event.globalPos())
        if not a: return
        # 先停下当前状态
        if self.state == State.WALKING: self.end_timer.stop()
        if a == a_chat:
            # 新对话：重置上下文
            self._conv_id = "CHAT_" + hashlib.sha256(f"diandian_{time.time()}".encode()).hexdigest()
            self._chat_messages = []
            self._save_chat_data()
            self._toggle_chat(); return
        # 检查是否点了历史记录
        for ha, entry in _hist_actions:
            if a == ha:
                try:
                    idx = self._chat_history.index(entry)
                    self._replay_chat(idx); return
                except ValueError:
                    return
        if a_stop and a == a_stop: self._go(State.IDLE); self._say("好，停下来了", 2000)
        elif a_wake and a == a_wake: self._go(State.IDLE); self._say("嗯...醒了", 2000)
        elif a_walk and a == a_walk:
            if self.state != State.IDLE: self._go(State.IDLE)
            self._go(State.WALKING); self._say("出去走走", 2000)
        elif a_sleep and a == a_sleep:
            self._go(State.SLEEPING); self._say("先休息一会", 2000); self.end_timer.start(10000)
        elif a == a_rps:
            if self.state != State.IDLE: self._go(State.IDLE)
            self._play_rps()
        elif a == a_hide:
            if self.state != State.IDLE: self._go(State.IDLE)
            self._play_hide()
        elif a == a_fortune:
            if self.state != State.IDLE: self._go(State.IDLE)
            self._fortune()
        elif a == a_pomo: self._start_pomodoro()
        elif a == a_water: self._toggle_water()
        elif a == a_apple: self._feed("苹果")
        elif a == a_tea: self._feed("茶")
        elif a == a_cake: self._feed("蛋糕")
        elif a == a_sushi: self._feed("寿司")
        elif a == a_burger: self._feed("汉堡")
        elif a == a_quiet:
            self._quiet = not self._quiet
            if self._quiet:
                self._go(State.IDLE)
                self._say("好，我自己玩", 2000)
            else:
                if self.state == State.WALKING:
                    self._walk_axis = 'follow'
                elif self.state != State.IDLE:
                    self._go(State.IDLE)
                self._say("好，跟着你", 2000)
        elif a == a_loc: self._set_location()
        elif a == a_quit: QApplication.quit()

    # -------- 游戏 --------

    # 猜拳：单局
    def _play_rps(self):
        self._rps_ai = random.choice(["石头", "剪刀", "布"])
        self._hide_bubble()
        panel_w = self.rps_panel.width()
        px = SPRITE_W // 2 - panel_w // 2
        if px < 0: px = 0
        self.rps_panel.move(px, BUBBLE_ZONE - 38)
        self.rps_panel.showPanel()

    def _rps_result(self, player):
        if player is None:
            self._say("算了", 2500)
            return
        ai = self._rps_ai
        wins = {"石头": "剪刀", "剪刀": "布", "布": "石头"}
        self._say(f"我出...{ai}！", 2000)
        if player == ai:
            QTimer.singleShot(1500, lambda: self._say(f"你{player} vs 我{ai}，平局", 3000))
        elif wins[player] == ai:
            QTimer.singleShot(1500, lambda: self._say(f"你{player} vs 我{ai}...你赢了", 3000))
        else:
            QTimer.singleShot(1500, lambda: (self._say(f"你{player} vs 我{ai}，我赢了", 3000), self._go(State.HAPPY)))

    # 抛硬币
    def _play_coin(self):
        self._say("抛！", 2000)
        self.coin.move(SPRITE_W + 10, BUBBLE_ZONE - 10)
        self.coin.flip()

    def _coin_result(self, result):
        self._say(f"...{result}！", 3000)

    # 运势
    def _fortune(self):
        self._say(random.choice(FORTUNE_LIST), 4000)
        self._go(State.HAPPY)

    # 藏猫猫
    # -------- 喂食 --------
    def _feed(self, food_name):
        if self.state != State.IDLE: self._go(State.IDLE)
        grid = FOOD_GRIDS[food_name]
        sz = 4
        img = QImage(8*sz, 8*sz, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        p = QPainter(img)
        for r, row in enumerate(grid):
            for c, val in enumerate(row):
                if val in FOOD_COLORS:
                    p.fillRect(c*sz, r*sz, sz, sz, FOOD_COLORS[val])
        p.end()
        self.food_label.setPixmap(QPixmap.fromImage(img))
        # 食物从右边出现
        self._food_start_x = SPRITE_W + 15
        self._food_end_x = SPRITE_W // 2 + 5  # 嘴巴位置
        self._food_y = BUBBLE_ZONE + SPRITE_H // 2 - 10
        self.food_label.move(self._food_start_x, self._food_y)
        self.food_label.show()
        self._say(random.choice(FOOD_LINES[food_name]), 2500)
        # 动画：食物移向嘴巴
        self._food_tick = 0
        self._food_timer = QTimer(self)
        self._food_timer.timeout.connect(self._animate_eat)
        self._food_timer.start(50)

    def _animate_eat(self):
        self._food_tick += 1
        total = 20  # 约1秒移到嘴边
        progress = min(self._food_tick / total, 1.0)
        x = self._food_start_x + int((self._food_end_x - self._food_start_x) * progress)
        self.food_label.move(x, self._food_y)

        self.update()
        if self._food_tick == total:
            self._show_frame("blink")
        elif self._food_tick == total + 5:
            self.food_label.resize(20, 20)
        elif self._food_tick == total + 10:
            self.food_label.hide()
            self.food_label.setFixedSize(40, 40)
            self._show_frame("normal")
            self._go(State.HAPPY)
            self._food_timer.stop()
            self.update()

    # -------- 番茄钟 --------
    def _start_pomodoro(self, task=None):
        if self._pomodoro_active:
            return
        if task is None:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout as QHL, QSpinBox
            dlg = QDialog()
            dlg.setWindowTitle("番茄钟")
            dlg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
            dlg.setFixedWidth(200)
            dlg.setStyleSheet(f"""
                QDialog {{
                    background: {PX_BG.name()};
                    border: 1.8px solid {PX_BORDER.name()};
                }}
            """)
            lay = QVBoxLayout(dlg)
            lay.setContentsMargins(14, 12, 14, 12)
            lay.setSpacing(8)
            # 时间行：标签 + 数字框 + 分钟
            time_row = QWidget(dlg)
            tl = QHL(time_row)
            tl.setContentsMargins(0, 0, 0, 0)
            tl.setSpacing(6)
            t1 = QLabel("专注")
            t1.setStyleSheet(f"font-size: 12px; color: {PX_TEXT.name()}; background: transparent;")
            spin = QSpinBox(dlg)
            spin.setRange(1, 120)
            spin.setValue(25)
            spin.setFixedSize(52, 24)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.setStyleSheet(f"""
                QSpinBox {{
                    font-size: 12px; color: {PX_TEXT.name()};
                    background: rgba(255,255,255,120);
                    border: 1.8px solid {PX_BORDER.name()};
                    padding: 0 4px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{ width: 0; }}
            """)
            t2 = QLabel("分钟")
            t2.setStyleSheet(f"font-size: 12px; color: {PX_TEXT.name()}; background: transparent;")
            tl.addWidget(t1)
            tl.addWidget(spin)
            tl.addWidget(t2)
            tl.addStretch()
            lay.addWidget(time_row)
            # 任务输入
            task_input = QLineEdit(dlg)
            task_input.setPlaceholderText("要做什么...")
            task_input.setFixedHeight(26)
            task_input.setStyleSheet(f"""
                QLineEdit {{
                    font-size: 12px; color: {PX_TEXT.name()};
                    background: rgba(255,255,255,120);
                    border: 1.8px solid {PX_BORDER.name()};
                    padding: 2px 8px;
                }}
            """)
            pal = task_input.palette()
            pal.setColor(pal.ColorRole.PlaceholderText, QColor(160, 155, 140, 180))
            task_input.setPalette(pal)
            lay.addWidget(task_input)
            # 按钮行
            btn_row = QWidget(dlg)
            bl = QHL(btn_row)
            bl.setContentsMargins(0, 2, 0, 0)
            bl.setSpacing(8)
            bl.addStretch()
            _btn_css = f"""
                QPushButton {{
                    background: {PX_BTN.name()}; color: white;
                    border: 1.8px solid {PX_BORDER.name()};
                    font-size: 11px; padding: 4px 14px;
                }}
                QPushButton:hover {{ background: {PX_BTN_HOVER.name()}; }}
            """
            _btn_cancel_css = f"""
                QPushButton {{
                    background: transparent; color: {PX_TEXT.name()};
                    border: 1.8px solid {PX_BORDER.name()};
                    font-size: 11px; padding: 4px 10px;
                }}
                QPushButton:hover {{ background: rgba(0,0,0,15); }}
            """
            cancel = QPushButton("取消")
            cancel.setStyleSheet(_btn_cancel_css)
            cancel.clicked.connect(dlg.reject)
            ok = QPushButton("开始")
            ok.setStyleSheet(_btn_css)
            ok.clicked.connect(dlg.accept)
            bl.addWidget(cancel)
            bl.addWidget(ok)
            lay.addWidget(btn_row)
            task_input.setFocus()
            # 居中到点点旁边
            pet_pos = self.mapToGlobal(QPoint(SPRITE_W + 10, 0))
            dlg.move(pet_pos.x(), pet_pos.y())
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            task = task_input.text().strip() or "专注"
            self._pomo_mins = spin.value()
        self._pomo_task = task
        self._pomodoro_active = True
        self._pomo_duration = getattr(self, '_pomo_mins', 25) * 60 * 1000
        self._say(f"开始：{self._pomo_task}", 3000)
        self.pomo_dot.show()
        self._pomo_tick_timer.start(1000)  # 每秒刷新
        # 25分钟后结束
        self._pomo_timer = QTimer(self)
        self._pomo_timer.setSingleShot(True)
        self._pomo_timer.timeout.connect(self._pomo_done)
        self._pomo_timer.start(self._pomo_duration)

    def _update_pomo_display(self):
        if not self._pomodoro_active:
            return
        self.pomo_dot.setText(self._pomo_remaining())

    def _pomo_remaining(self):
        if not getattr(self, '_pomo_timer', None):
            return ""
        remain = self._pomo_timer.remainingTime() // 1000
        m, s = divmod(max(remain, 0), 60)
        return f"{m}:{s:02d}"

    def _pomo_done(self):
        self._pomodoro_active = False
        self._pomo_tick_timer.stop()
        self.pomo_dot.hide()
        # 跳到鼠标旁边
        cursor = QCursor.pos()
        self.move(cursor.x() - SPRITE_W // 2, cursor.y() - self.height() // 2)
        self.base_y = self.pos().y()
        self._go(State.HAPPY)
        self._say(f"「{self._pomo_task}」时间到，休息一下", 5000)
        # 10分钟后弹任务输入框
        self._pomo_rest_timer = QTimer(self)
        self._pomo_rest_timer.setSingleShot(True)
        self._pomo_rest_timer.timeout.connect(self._pomo_ask_continue)
        self._pomo_rest_timer.start(10 * 60 * 1000)

    def _pomo_ask_continue(self):
        self._say("休息够了", 2000)
        QTimer.singleShot(2000, lambda: self._start_pomodoro())

    # -------- 喝水提醒 --------
    def _toggle_water(self):
        if self._water_active:
            self._water_active = False
            self._water_timer.stop()
            self._say("好，不提醒了", 2000)
        else:
            self._water_active = True
            self._water_timer.start(self._water_interval)
            self._say("每30分钟提醒你喝水", 3000)

    def _water_remind(self):
        if self.state == State.SLEEPING:
            self._stop_zzz()
            self.blanket_label.hide()
        # 跑到鼠标旁边，让用户注意到
        cursor = QCursor.pos()
        self.move(cursor.x() - SPRITE_W // 2, cursor.y() - self.height() // 2)
        self.base_y = self.pos().y()
        line = random.choice(["该喝水了！", "喝口水吧！", "记得喝水哦！", "补充水分！", "咕噜咕噜，喝水时间！"])
        self._go(State.HAPPY)
        self._say(line, 5000)

    def event(self, ev):
        """切输入法时焦点会短暂离开，WindowActivate时抢回焦点"""
        from PyQt6.QtCore import QEvent
        if ev.type() == QEvent.Type.WindowActivate and self.chat_input.isVisible():
            self.chat_input.setFocus()
        return super().event(ev)

    def _on_chat_input_changed(self, text):
        """输入框随文字长度动态变宽"""
        if self.chat_input.isVisible():
            self._chat_input_timer.start(self._chat_input_idle)
        fm = self.chat_input.fontMetrics()
        text_w = fm.horizontalAdvance(text) + 24  # padding
        w = max(self._chat_input_min_w, min(text_w, self._chat_input_max_w))
        self.chat_input.setFixedWidth(w)
        self.chat_input.move(max(0, SPRITE_W // 2 - w // 2), self.chat_input.y())

    def _auto_hide_chat_input(self):
        """空闲自动收起，但有文字时不收"""
        if self.chat_input.text().strip():
            self._chat_input_timer.start(self._chat_input_idle)  # 有内容，续期
        else:
            self.chat_input.hide()

    def _load_location(self):
        """加载位置：config > 后台IP定位"""
        cfg_path = os.path.join(DATA_DIR, ".pet_config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r") as f:
                    cfg = json.load(f)
                self._user_location = cfg.get("location", "")
            except Exception:
                pass
        # 后台IP定位，成功则覆盖（除非用户手动设过）
        import threading
        threading.Thread(target=self._ip_locate, daemon=True).start()

    def _ip_locate(self):
        """IP自动定位（后台线程），成功后更新位置并缓存"""
        try:
            with urllib.request.urlopen("http://ip-api.com/json/?lang=zh-CN&fields=city", timeout=5) as r:
                data = json.loads(r.read().decode("utf-8"))
                city = data.get("city", "")
                if city:
                    self._user_location = city
                    self._save_location(city)
        except Exception:
            pass

    def _save_location(self, loc):
        """持久化位置到config"""
        try:
            cfg_path = os.path.join(DATA_DIR, ".pet_config.json")
            cfg = {}
            if os.path.exists(cfg_path):
                with open(cfg_path, "r") as f:
                    cfg = json.load(f)
            cfg["location"] = loc
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, ensure_ascii=False)
        except Exception:
            pass

    def _load_chat_data(self):
        """启动时恢复聊天历史"""
        try:
            if not os.path.exists(self._chat_data_path):
                return
            with open(self._chat_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._chat_messages = data.get("messages", [])
            self._conv_id = data.get("conv_id", self._conv_id)
            for item in data.get("history", []):
                q = item["question"]
                bubbles = [(b["type"], b["content"]) for b in item["bubbles"]]
                images = {u: base64.b64decode(b64) for u, b64 in item.get("images", {}).items()}
                self._chat_history.append((q, bubbles, images))
        except Exception:
            pass

    def _save_chat_data(self):
        """保存聊天历史到文件"""
        try:
            history = []
            for q, bubbles, images in self._chat_history:
                history.append({
                    "question": q,
                    "bubbles": [{"type": t, "content": c} for t, c in bubbles],
                    "images": {u: base64.b64encode(d).decode() for u, d in images.items()}
                })
            data = {
                "conv_id": self._conv_id,
                "messages": self._chat_messages,
                "history": history
            }
            with open(self._chat_data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def _first_time_location(self):
        """首次启动且无位置信息时，等IP定位结果，若还是空则引导设置"""
        if self._user_location:
            return  # IP定位成功了，不用引导
        self._say("告诉我你在哪个城市吧~", 3000)
        QTimer.singleShot(3500, self._set_location)

    def _set_location(self):
        """右键菜单设置位置"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout as QHL
        dlg = QDialog()
        dlg.setWindowTitle("设置位置")
        dlg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        dlg.setFixedWidth(200)
        dlg.setStyleSheet(f"""
            QDialog {{
                background: {PX_BG.name()};
                border: 1.8px solid {PX_BORDER.name()};
            }}
        """)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        t1 = QLabel("你的城市")
        t1.setStyleSheet(f"font-size: 12px; color: {PX_TEXT.name()}; background: transparent;")
        lay.addWidget(t1)
        loc_input = QLineEdit(dlg)
        loc_input.setText(self._user_location)
        loc_input.setPlaceholderText("留空则自动定位")
        loc_input.setFixedHeight(26)
        loc_input.setStyleSheet(f"""
            QLineEdit {{
                font-size: 12px; color: {PX_TEXT.name()};
                background: rgba(255,255,255,120);
                border: 1.8px solid {PX_BORDER.name()};
                padding: 2px 8px;
            }}
        """)
        pal = loc_input.palette()
        pal.setColor(pal.ColorRole.PlaceholderText, QColor(160, 155, 140, 180))
        loc_input.setPalette(pal)
        lay.addWidget(loc_input)
        # 按钮行
        btn_row = QWidget(dlg)
        bl = QHL(btn_row)
        bl.setContentsMargins(0, 2, 0, 0)
        bl.setSpacing(8)
        bl.addStretch()
        cancel = QPushButton("取消")
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {PX_TEXT.name()};
                border: 1.8px solid {PX_BORDER.name()};
                font-size: 11px; padding: 4px 10px;
            }}
            QPushButton:hover {{ background: rgba(0,0,0,15); }}
        """)
        cancel.clicked.connect(dlg.reject)
        ok = QPushButton("确定")
        ok.setStyleSheet(f"""
            QPushButton {{
                background: {PX_BTN.name()}; color: white;
                border: 1.8px solid {PX_BORDER.name()};
                font-size: 11px; padding: 4px 14px;
            }}
            QPushButton:hover {{ background: {PX_BTN_HOVER.name()}; }}
        """)
        ok.clicked.connect(dlg.accept)
        bl.addWidget(cancel)
        bl.addWidget(ok)
        lay.addWidget(btn_row)
        loc_input.setFocus()
        pet_pos = self.mapToGlobal(QPoint(SPRITE_W + 10, 0))
        dlg.move(pet_pos.x(), pet_pos.y())
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_loc = loc_input.text().strip()
        if new_loc:
            self._user_location = new_loc
            self._save_location(new_loc)
            self._say(f"知道啦，在{new_loc}~", 3000)
        else:
            # 留空：重新自动定位
            self._user_location = ""
            self._save_location("")
            self._say("好的，重新定位中~", 2000)
            import threading
            threading.Thread(target=self._ip_locate, daemon=True).start()

    # -------- 聊天 --------
    def _show_chat_input(self):
        """显示对话框，同时清除其他所有UI元素"""
        self._hide_bubble()
        self._rich_panel.hide()
        self._rich_panel_next_pending = False
        self.chat_input.setFixedWidth(self._chat_input_min_w)
        self.chat_input.move(max(0, SPRITE_W // 2 - self._chat_input_min_w // 2), self.chat_input.y())
        self.chat_input.show()
        self.chat_input.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self.activateWindow()
        self.chat_input.setFocus()
        self.chat_input.raise_()
        self._chat_input_timer.start(self._chat_input_idle)

    def _toggle_chat(self):
        if self.chat_input.isVisible():
            self.chat_input.hide()
            self._chat_input_timer.stop()
        else:
            if self.state != State.IDLE:
                self._go(State.IDLE)
            self._show_chat_input()

    def _send_chat(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()
        self.chat_input.hide()
        self._chat_input_timer.stop()
        self._chatting = True
        self._last_chat_question = text
        self._chat_thinking_shown = False
        self._chat_think_idx = 0
        if self.state != State.IDLE:
            self._go(State.IDLE)
        self._show_frame("stare")
        # 延迟1秒才显示思考提示，快回复就不显示
        self._think_timer = QTimer(self)
        self._think_timer.setSingleShot(True)
        self._think_timer.timeout.connect(self._show_thinking)
        # 长等待时每4秒换一个思考提示
        self._think_rotate_timer = QTimer(self)
        self._think_rotate_timer.timeout.connect(self._rotate_thinking)
        # 超过3分钟没聊天，自动清上下文
        now = time.time()
        if self._chat_messages and (now - self._last_chat_time > 180):
            self._chat_messages = []
            self._conv_id = "CHAT_" + hashlib.sha256(f"diandian_{now}".encode()).hexdigest()
        self._last_chat_time = now
        self._chat_messages.append({"role": "user", "content": text})
        self._chat_thread = ChatThread(text, self._conv_id, self._user_location, self._chat_messages[:-1], self)
        self._chat_thread.chunk_received.connect(self._on_chat_chunk)
        self._chat_thread.finished_signal.connect(self._on_chat_done)
        self._chat_thread.visible_think.connect(self._on_visible_think)
        self._chat_thread.start()

    _THINK_LINES = ["让我想想...", "思考中..."]
    _THINK_LAST = "找到了！"

    def _show_thinking(self):
        if self._chatting and not self._chat_thinking_shown:
            self._chat_thinking_shown = True
            self._think_pool = [random.choice(self._THINK_LINES)]
            self._think_pool_idx = 0
            self._say(self._think_pool[0], 30000)
            self._think_rotate_timer.start(18000)

    def _rotate_thinking(self):
        if not self._chatting:
            self._think_rotate_timer.stop()
            return
        self._think_pool_idx += 1
        if self._think_pool_idx >= len(self._think_pool):
            # 普通提示词用完了，之后一直显示"快好了"
            self._say(self._THINK_LAST, 30000)
            self._think_rotate_timer.stop()
            return
        line = self._think_pool[self._think_pool_idx]
        self._say(line, 30000)

    def _on_visible_think(self, text):
        """API返回的<visible>思考词，替代硬编码思考词"""
        if not self._chatting:
            return
        # 停掉硬编码思考词的定时器
        self._think_timer.stop()
        self._think_rotate_timer.stop()
        self._chat_thinking_shown = True
        self._say(text, 30000)

    def _on_chat_chunk(self, text):
        pass

    def _on_chat_done(self, bubble_list, images):
        self._think_timer.stop()
        self._think_rotate_timer.stop()
        self._show_frame("normal")
        self._chat_bubble_list = bubble_list  # [(type, content), ...]
        self._chat_images = images            # {url: bytes}
        self._chat_bubble_idx = 0
        # 拼完整回复存入上下文
        full_reply = "\n".join(c for _, c in bubble_list)
        self._chat_messages.append({"role": "assistant", "content": full_reply})
        self._last_chat_time = time.time()
        # 上下文最多保留20条（10轮），防太长
        if len(self._chat_messages) > 20:
            self._chat_messages = self._chat_messages[-20:]
        # 存入历史
        q = getattr(self, '_last_chat_question', '')
        if q:
            self._chat_history.append((q, bubble_list, images))
            if len(self._chat_history) > 15:
                self._chat_history.pop(0)
            self._save_chat_data()
        self._play_next_bubble()

    def _play_next_bubble(self):
        idx = self._chat_bubble_idx
        bubbles = self._chat_bubble_list
        if idx >= len(bubbles):
            # 所有bubble播完，延迟3秒恢复自由
            QTimer.singleShot(3000, self._end_chat)
            return
        btype, content = bubbles[idx]
        self._chat_bubble_idx += 1
        has_next = self._chat_bubble_idx < len(bubbles)
        if btype == "short":
            display = content[:80] if len(content) > 80 else content
            self._chat_is_last_bubble = not has_next
            duration = 3500 if self._chat_is_last_bubble else 3000
            self._say(display, duration + 500)  # 后备比timer稍长
            self._chat_advance_timer.stop()
            self._chat_advance_timer.start(duration)
        elif btype == "rich":
            # 先隐藏短气泡
            self._hide_bubble()
            html = RichPanel.md_to_html(content)
            anchor = self.mapToGlobal(QPoint(SPRITE_W + 10, BUBBLE_ZONE))
            self._rich_panel.show_rich(html, self._chat_images, anchor, auto_hide=False)
            if has_next:
                self._rich_panel_next_pending = True
            else:
                self._rich_panel_next_pending = False

    def _on_rich_panel_closed(self):
        """面板关闭后的回调"""
        if getattr(self, '_rich_panel_next_pending', False):
            self._rich_panel_next_pending = False
            QTimer.singleShot(300, self._play_next_bubble)
        elif self._chatting:
            self._end_chat()

    def _on_advance_timeout(self):
        if self._chat_is_last_bubble:
            self._hide_bubble()
            self._end_chat()
        else:
            self._play_next_bubble()



    def _replay_chat(self, idx):
        """重播历史：短bubble+rich+短bubble 三块合并显示在面板里"""
        if idx < 0 or idx >= len(self._chat_history):
            return
        _, bubble_list, images = self._chat_history[idx]
        # 清理所有UI状态
        if self.state != State.IDLE:
            self._go(State.IDLE)
        self._hide_bubble()
        self.chat_input.hide()
        self._chat_input_timer.stop()
        self._chatting = False
        self._rich_panel_next_pending = False  # 不触发后续播放
        # 按原始顺序构建HTML，短bubble用像素风气泡样式
        parts = []
        for btype, content in bubble_list:
            if btype == "short":
                parts.append(
                    f'<div style="background:rgba(245,240,230,255);border:1.8px solid {PX_BORDER.name()};'
                    f'padding:6px 10px;margin:4px 0;font-size:12px;color:{PX_TEXT.name()}">'
                    f'{content}</div>'
                )
            elif btype == "rich":
                parts.append(RichPanel.md_to_html(content))
        html = "\n".join(parts)
        anchor = self.mapToGlobal(QPoint(SPRITE_W + 10, BUBBLE_ZONE + 20))
        self._rich_panel.show_rich(html, images, anchor, auto_hide=False)

    def _end_chat(self):
        self._chatting = False
        self._show_chat_input()

    def _play_hide(self):
        self._say("我藏好了", 1500)
        self._pre_hide_pos = self.pos()
        QTimer.singleShot(1500, self._do_hide)

    def _do_hide(self):
        self._hide_bubble()
        # 直接消失，随机出现在屏幕边缘
        scr = QApplication.primaryScreen().availableGeometry()
        edge = random.choice(["right", "top"])
        peek = 20
        if edge == "right":
            hx = scr.right() - peek
            hy = random.randint(scr.top() + 100, scr.bottom() - self.height() - 100)
        else:
            hx = random.randint(scr.left() + 100, scr.right() - self.width() - 100)
            hy = scr.top() - self.height() + peek

        self.move(hx, hy)
        self.base_y = hy
        self._hiding = True
        self._show_frame("blink")
        self._hide_timeout = QTimer(self)
        self._hide_timeout.setSingleShot(True)
        self._hide_timeout.timeout.connect(self._hide_give_up)
        self._hide_timeout.start(10000)


    def _found(self):
        """藏猫猫被找到了"""
        self._hiding = False
        self._hide_timeout.stop()
        self._show_frame("stare")
        self._say("...被发现了", 2500)
        # 回到之前的位置
        QTimer.singleShot(1500, lambda: (
            self.move(self._pre_hide_pos),
            setattr(self, 'base_y', self._pre_hide_pos.y()),
            self._go(State.IDLE)
        ))

    def _hide_give_up(self):
        """藏猫猫超时，自己出来"""
        self._hiding = False
        self._say("你不来找我啊", 2500)
        QTimer.singleShot(1500, lambda: (
            self.move(self._pre_hide_pos),
            setattr(self, 'base_y', self._pre_hide_pos.y()),
            self._go(State.IDLE)
        ))


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ClawdPet()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

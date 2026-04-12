#!/usr/bin/env python3
"""Clawd Desktop Pet — with eye tracking, drag flailing, auto sleep, edge hiding"""

import sys
import math
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QMenu, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPixmap, QImage, QTransform, QCursor

# ============================================================
# 像素数据 — 眼睛在 row 6, col 5-6 和 13-14
# ============================================================
# 0=透明 1=身体 2=腿暗色 3=黑色(眼/牙)
_BASE = [
    [0,0,0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,0,0],  # 0 耳
    [0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0],  # 1
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 2
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 3
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 4
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 5
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 6 眼睛行
    [0,1,1,1,1,1,1,1,1,3,3,1,1,1,1,1,1,1,1,0],  # 7 小獠牙（紧凑）
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 8
    [0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0],  # 9
    [0,0,0,0,2,2,0,2,2,0,0,2,2,0,2,2,0,0,0,0],  # 10 腿
]

# 眼睛位置: 左眼(row6, col), 右眼(row6, col)
# 正常: 5,6 和 13,14
# 看左: 4,5 和 12,13
# 看右: 6,7 和 14,15
# 看上: row5 的 5,6 和 13,14
# 看下: row7 的 5,6 和 13,14 (替换獠牙行)
# 瞪眼: 3x2 大眼 row5-6

def _make_eye_variant(lcols, rcols, eye_row=6):
    grid = [row[:] for row in _BASE]
    grid[eye_row][lcols[0]] = 3
    grid[eye_row][lcols[1]] = 3
    grid[eye_row][rcols[0]] = 3
    grid[eye_row][rcols[1]] = 3
    return grid

def _make_stare():
    """被戳：眼睛多 1px 高，微微变大"""
    grid = [row[:] for row in _BASE]
    # 正常眼 + 上面多 1 行
    for c in (5, 6): grid[5][c] = 3; grid[6][c] = 3
    for c in (13, 14): grid[5][c] = 3; grid[6][c] = 3
    return grid

CLAWD_NORMAL = _make_eye_variant([5, 6], [13, 14])
# 看左/右只偏移 1 像素，很微妙
CLAWD_LOOK_L = _make_eye_variant([5, 6], [13, 14])  # 不移了，太近会撞獠牙
CLAWD_LOOK_R = _make_eye_variant([5, 6], [13, 14])  # 同上
CLAWD_LOOK_U = _make_eye_variant([5, 6], [13, 14], eye_row=5)  # 只有看上保留
CLAWD_STARE = _make_stare()

CLAWD_BLINK = [row[:] for row in _BASE]  # 无眼睛 = 闭眼

CLAWD_WALK1 = [row[:] for row in CLAWD_NORMAL]
CLAWD_WALK1[10] = [0,0,0,0,0,0,0,2,2,0,0,2,2,0,0,0,0,0,0,0]
CLAWD_WALK2 = [row[:] for row in CLAWD_NORMAL]
CLAWD_WALK2[10] = [0,0,0,0,2,2,0,0,0,0,0,0,0,0,2,2,0,0,0,0]

# 乱蹬帧（腿更夸张）
CLAWD_FLAIL1 = [row[:] for row in CLAWD_STARE]
CLAWD_FLAIL1[10] = [0,0,0,2,2,0,0,0,2,2,0,0,0,0,0,2,2,0,0,0]
CLAWD_FLAIL2 = [row[:] for row in CLAWD_STARE]
CLAWD_FLAIL2[10] = [0,0,0,0,0,2,2,0,0,0,0,2,2,0,2,0,0,0,0,0]

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
COLORS = {1: QColor(215, 119, 87), 2: QColor(180, 90, 65), 3: QColor(26, 26, 26)}
SPRITE_W, SPRITE_H = 20 * PX, 11 * PX
SPRITE_MAX = max(SPRITE_W, SPRITE_H)
BUBBLE_ZONE = 55
PANEL_H = 45
WIN_W = SPRITE_MAX + 200
WIN_H = SPRITE_MAX + BUBBLE_ZONE + PANEL_H

CLICK_LINES = [
    "在呢", "干嘛戳我", "想摸鱼了", "要一起玩吗", "要喝咖啡吗",
    "你也辛苦了", "做什么呢", "嗯？", "来了来了", "戳够了没",
    "我在我在", "你好忙啊", "休息一下吧", "怎么了",
]
IDLE_LINES = [
    "加油", "要不要休息一下", "我在看你工作...", "嗯...想事情",
    "好无聊", "今天天气怎么样", "突然好开心", "打个哈欠...",
    "发呆中", "肚子饿了", "今天周几来着", "窗外什么声音",
    "该喝水了", "伸个懒腰", "有点困",
]
FORTUNE_LIST = [
    "大吉！超级幸运", "中吉，好事要来！", "小吉，平安是福",
    "适合搞创作", "适合...摸鱼。不，努力", "心情会很好！",
    "灵感要来了", "该吃点好的", "贵人运很旺",
    "适合学新东西", "会收到好消息", "桃花运不错哦",
    "财运小有上升", "适合整理房间", "今天宜早睡", "会有意外惊喜",
]


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
# 气泡 / 猜拳 / 硬币 （和之前一样）
# ============================================================
class SpeechBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._text = ""
        self.setFixedSize(160, 50)
        self.hide()

    def set_text(self, text):
        self._text = text
        fm = self.fontMetrics()
        pad_x, pad_y = 20, 12
        max_w = 220
        br = fm.boundingRect(QRect(0, 0, max_w - pad_x, 0),
                             Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, text)
        tw = min(br.width() + pad_x, max_w)
        tw = max(tw, 50)
        th = br.height() + pad_y
        self.setFixedSize(tw, th)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 190))
        p.drawRoundedRect(0, 0, w, h, 12, 12)
        p.setPen(QColor(60, 60, 60))
        p.drawText(10, 2, w - 20, h - 4,
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._text)
        p.end()


class BubbleDots(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(12, 12)
        self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 150))
        p.drawEllipse(1, 1, 10, 10)
        p.end()


class RPSPanel(QWidget):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.callback = callback
        self.setFixedSize(SPRITE_W, 36)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        btn_style = """
            QPushButton { background: rgba(255,255,255,0.85); color: #444; border: none;
                border-radius: 6px; font-size: 12px; padding: 6px 8px; }
            QPushButton:hover { background: rgba(255,255,255,1.0); }
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
        self.setFixedSize(36, 80)
        self.callback = callback
        self.coin_frames = [coin_pixmap(i) for i in range(3)]
        self.coin_frames = [f.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation) for f in self.coin_frames]
        self.label = QLabel(self)
        self.label.setFixedSize(30, 30)
        self.frame_idx = self.tick = 0
        self.total_ticks = 24
        self.result = 0
        self.base_y = 50
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
        self.bubble_dots = BubbleDots(self)
        self._dot_x = SPRITE_W - 2
        self._dot_y = BUBBLE_ZONE - 14
        self.bubble_dots.move(self._dot_x, self._dot_y)
        self.rps_panel = RPSPanel(self, self._rps_result)
        self.coin = CoinWidget(self, self._coin_result)

        # zzz 标签
        self.zzz_labels = []
        for i in range(3):
            z = QLabel(self)
            z.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            z.setStyleSheet(f"color: rgba(215,119,87,{180-i*50}); font-size: {14-i*2}px; font-weight: bold; background: transparent;")
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

        # 无交互计时（自动入睡用）
        self._idle_since = 0

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

        QTimer.singleShot(500, lambda: self._say("嗨，我是 Clawd", 2500))
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
                if self.walk_dir == -1:
                    pm = QPixmap.fromImage(pm.toImage().mirrored(True, False))
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
        bx = self._dot_x + 12
        by = self._dot_y - bh
        if by < 0: by = 0
        self.bubble.move(bx, by)
        self.bubble.show()
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
            self.move(pos.x(), self.base_y + int(4 * math.sin(self.tick * 0.08)))
            # 自动入睡：60秒无交互
            if self.tick - self._idle_since > 1000:  # ~60s
                self._say("打个哈欠...", 2500)
                QTimer.singleShot(3000, self._auto_sleep)
                self._idle_since = self.tick  # 防止重复触发

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

            if axis == 'h':
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
                    self._say("哎呀好痛", 2500)
                    self._show_frame("stare")
                    self._walk_axis = 'stunned'
                    self._stun_tick = 0
            elif axis == 'stunned':
                self._stun_tick = getattr(self, '_stun_tick', 0) + 1
                if self._stun_tick > 50:
                    self._go(State.IDLE)

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

    def _auto_sleep(self):
        if self.state == State.IDLE:
            self._go(State.SLEEPING)

    def _blink(self):
        if self.state not in (State.IDLE, State.HAPPY): return
        self._show_frame("blink")
        QTimer.singleShot(150, lambda: self._show_frame(self._cur_eye) if self.state in (State.IDLE, State.HAPPY) else None)

    def _random(self):
        if self.state != State.IDLE:
            self.rand_timer.start(random.randint(30000, 70000)); return
        act = random.choice(["walk", "happy", "talk", "talk", "talk", "sleep"])
        if act == "walk":
            self._go(State.WALKING); self._say("散步去！", 2000)
        elif act == "happy":
            self._go(State.HAPPY); self._say("突然好开心", 2000)
        elif act == "sleep":
            self._go(State.SLEEPING); self._say("困了...", 2000)
            self.end_timer.start(random.randint(6000, 12000))
        elif act == "talk":
            self._say(random.choice(IDLE_LINES), 3000)
        self.rand_timer.start(random.randint(30000, 70000))

    def _go(self, state):
        old = self.state
        pos = self.pos()
        self.move(pos.x(), self.base_y)
        self.state = state
        if old == State.SLEEPING and state != State.SLEEPING:
            self._stop_zzz()
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

    # -------- 鼠标 --------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._touch()
            self._drag_start = e.globalPosition().toPoint()
            self._win_start = self.pos()
            # 进入拖拽状态（乱蹬）
            self._pre_drag_state = self.state
            if self.state == State.SLEEPING:
                self._stop_zzz()
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

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            was_drag = False
            if self._drag_start:
                d = e.globalPosition().toPoint() - self._drag_start
                was_drag = abs(d.x()) > 5 or abs(d.y()) > 5
            self._drag_start = None

            if self.state == State.DRAGGING:
                self.base_y = self.pos().y()
                self._go(State.IDLE)

            if not was_drag:
                self._on_click()

    def _on_click(self):
        self._touch()
        if self.state == State.SLEEPING:
            self._go(State.IDLE); self._say("嗯...醒了", 2000)
        else:
            # 瞪眼 + 说话
            self._show_frame("stare")
            self._say(random.choice(CLICK_LINES), 2500)
            QTimer.singleShot(800, lambda: self._show_frame(self._cur_eye) if self.state == State.IDLE else None)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._touch()
            self._go(State.HAPPY); self._say("好开心", 2000)

    def contextMenuEvent(self, event):
        self._touch()
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 4px 0; font-size: 14px; }
            QMenu::item { padding: 8px 20px; }
            QMenu::item:selected { background: rgba(215,119,87,0.15); }
        """)
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
        a_rps = menu.addAction("猜拳")
        a_flip = menu.addAction("抛硬币")
        a_fortune = menu.addAction("今日运势")
        menu.addSeparator()
        a_quit = menu.addAction("退出")

        a = menu.exec(event.globalPos())
        if not a: return
        # 先停下当前状态
        if self.state == State.WALKING: self.end_timer.stop()
        if a_stop and a == a_stop: self._go(State.IDLE); self._say("好吧，停下了", 2000)
        elif a_wake and a == a_wake: self._go(State.IDLE); self._say("嗯...醒了", 2000)
        elif a_walk and a == a_walk:
            if self.state != State.IDLE: self._go(State.IDLE)
            self._go(State.WALKING); self._say("散步去！", 2000)
        elif a_sleep and a == a_sleep:
            self._go(State.SLEEPING); self._say("晚安！", 2000); self.end_timer.start(10000)
        elif a == a_rps:
            if self.state != State.IDLE: self._go(State.IDLE)
            self._play_rps()
        elif a == a_flip:
            if self.state != State.IDLE: self._go(State.IDLE)
            self._play_coin()
        elif a == a_fortune:
            if self.state != State.IDLE: self._go(State.IDLE)
            self._fortune()
        elif a == a_quit: QApplication.quit()

    # -------- 游戏 --------
    def _play_rps(self):
        self._rps_ai = random.choice(["石头", "剪刀", "布"])
        self._hide_bubble()  # 藏掉气泡，让面板独占上方
        self.rps_panel.move(0, BUBBLE_ZONE - 38)
        self.rps_panel.showPanel()

    def _rps_result(self, player):
        if player is None: self._say("不出啊...算了", 2500); return
        ai = self._rps_ai
        wins = {"石头": "剪刀", "剪刀": "布", "布": "石头"}
        self._say(f"我出...{ai}！", 2000)
        if player == ai:
            QTimer.singleShot(1500, lambda: self._say(f"你{player} vs 我{ai}，平局！再来", 3000))
        elif wins[player] == ai:
            QTimer.singleShot(1500, lambda: self._say(f"你{player} vs 我{ai}...你赢了，哼", 3000))
        else:
            QTimer.singleShot(1500, lambda: (self._say(f"你{player} vs 我{ai}，我赢啦！", 3000), self._go(State.HAPPY)))

    def _play_coin(self):
        self._say("抛！", 2000)
        self.coin.move(SPRITE_W + 10, BUBBLE_ZONE - 30)
        self.coin.flip()

    def _coin_result(self, result):
        self._say(f"...{result}！", 3000)

    def _fortune(self):
        self._say(random.choice(FORTUNE_LIST), 4000)
        self._go(State.HAPPY)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ClawdPet()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

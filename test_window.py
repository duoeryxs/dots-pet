import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(300, 200)
        self.setStyleSheet("background-color: rgba(215, 119, 87, 200); border-radius: 20px;")
        
        label = QLabel("🦀 Clawd 在这里！", self)
        label.setFont(QFont(".AppleSystemUIFont", 24))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setGeometry(0, 0, 300, 200)
        label.setStyleSheet("color: white;")
        
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() // 2 - 150, screen.height() // 2 - 100)
        self.show()
        print(f"Window at: {self.pos().x()}, {self.pos().y()}, size: {self.size()}")
        print(f"Screen: {screen.width()}x{screen.height()}")

    def mousePressEvent(self, e):
        self._drag_start = e.globalPosition().toPoint()
        self._win_start = self.pos()
    def mouseMoveEvent(self, e):
        if hasattr(self, '_drag_start'):
            delta = e.globalPosition().toPoint() - self._drag_start
            self.move(self._win_start + delta)

app = QApplication(sys.argv)
w = TestWindow()
sys.exit(app.exec())

"""
Widget Gráfico Sparkline Vetorial dos Últimos 30 Segundos
Desenha curvas suaves em tempo real com QPainter sem sobrecarga de bibliotecas pesadas.
Totalmente configurável para CPU, Memória RAM e Placa de Vídeo (GPU).
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QPointF
from collections import deque

class SparklineWidget(QWidget):
    def __init__(
        self,
        parent=None,
        title_1: str = "CPU",
        color_1: str = "#38BDF8",
        title_2: str = "TEMP",
        color_2: str = "#10B981",
        min_2: float = 30.0,
        max_2: float = 90.0,
        height: int = 54,
        max_points: int = 30
    ):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.max_points = max_points
        self.title_1 = title_1
        self.color_1 = QColor(color_1)
        self.title_2 = title_2
        self.color_2 = QColor(color_2)
        self.min_2 = min_2
        self.max_2 = max_2

        self.history_1 = deque([15.0] * max_points, maxlen=max_points)
        self.history_2 = deque([min_2 + (max_2 - min_2) * 0.3] * max_points, maxlen=max_points)

    def add_point(self, val_1: float, val_2: float):
        self.history_1.append(float(val_1))
        self.history_2.append(float(val_2))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Fundo do Card
        painter.setBrush(QColor("#0B0F19"))
        painter.setPen(QColor("#161F30"))
        painter.drawRoundedRect(0, 0, w, h, 6, 6)

        # Grade sutil
        painter.setPen(QPen(QColor("#162032"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(8, int(h / 2), w - 8, int(h / 2))

        # Legenda e Escala
        font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Label 1
        painter.setPen(self.color_1)
        painter.drawText(8, 12, self.title_1)
        
        # Label 2
        painter.setPen(self.color_2)
        painter.drawText(50, 12, self.title_2)

        # Escala de tempo à direita
        painter.setPen(QColor("#475569"))
        painter.drawText(w - 65, 12, "HISTORICO 30s")

        # Margens internas da área de plotagem
        plot_left = 8
        plot_right = w - 8
        plot_top = 16
        plot_bottom = h - 6
        plot_w = plot_right - plot_left
        plot_h = plot_bottom - plot_top

        n = len(self.history_1)
        if plot_w <= 10 or plot_h <= 10 or n < 2:
            painter.end()
            return

        step_x = plot_w / (self.max_points - 1)

        # 1. Curva 1 (0 a 100%)
        path_1 = QPainterPath()
        for i, val in enumerate(self.history_1):
            clamped = max(0.0, min(100.0, val))
            x = plot_left + i * step_x
            y = plot_bottom - (clamped / 100.0) * plot_h
            if i == 0:
                path_1.moveTo(x, y)
            else:
                path_1.lineTo(x, y)

        # Gradiente translúcido
        fill_path = QPainterPath(path_1)
        fill_path.lineTo(plot_left + (n - 1) * step_x, plot_bottom)
        fill_path.lineTo(plot_left, plot_bottom)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, plot_top, 0, plot_bottom)
        c_fill = QColor(self.color_1.red(), self.color_1.green(), self.color_1.blue(), 30)
        grad.setColorAt(0, c_fill)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(fill_path, grad)

        # Desenha a linha 1 com nitidez
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self.color_1, 1.5))
        painter.drawPath(path_1)

        # 2. Curva 2
        path_2 = QPainterPath()
        for i, val in enumerate(self.history_2):
            clamped = max(self.min_2, min(self.max_2, val))
            x = plot_left + i * step_x
            ratio = (clamped - self.min_2) / (self.max_2 - self.min_2) if self.max_2 > self.min_2 else 0.5
            y = plot_bottom - ratio * plot_h
            if i == 0:
                path_2.moveTo(x, y)
            else:
                path_2.lineTo(x, y)

        painter.setPen(QPen(self.color_2, 1.5))
        painter.drawPath(path_2)

        painter.end()

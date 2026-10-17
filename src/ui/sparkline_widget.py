"""
Widget Gráfico Sparkline Vetorial dos Últimos 30 Segundos
Desenha curvas suaves em tempo real com QPainter sem sobrecarga de bibliotecas pesadas.
Cores:
- CPU: Accent Azure (#38BDF8)
- Temperatura: Emerald Semantic (#10B981)
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QPointF
from collections import deque

class SparklineWidget(QWidget):
    def __init__(self, parent=None, max_points: int = 30):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.max_points = max_points
        self.cpu_history = deque([10.0] * max_points, maxlen=max_points)
        self.temp_history = deque([50.0] * max_points, maxlen=max_points)

    def add_point(self, cpu_val: float, temp_val: float):
        self.cpu_history.append(float(cpu_val))
        self.temp_history.append(float(temp_val))
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

        # Grade e Linhas sutis
        painter.setPen(QPen(QColor("#162032"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(8, int(h / 2), w - 8, int(h / 2))

        # Legenda e Escala
        font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        painter.setFont(font)
        
        # CPU Label
        painter.setPen(QColor("#38BDF8"))
        painter.drawText(8, 12, "CPU")
        
        # Temp Label
        painter.setPen(QColor("#10B981"))
        painter.drawText(36, 12, "TEMP")

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

        n = len(self.cpu_history)
        if n < 2:
            painter.end()
            return

        step_x = plot_w / (self.max_points - 1)

        # 1. Caminho da CPU (0 a 100%)
        cpu_path = QPainterPath()
        for i, val in enumerate(self.cpu_history):
            clamped = max(0.0, min(100.0, val))
            x = plot_left + i * step_x
            y = plot_bottom - (clamped / 100.0) * plot_h
            if i == 0:
                cpu_path.moveTo(x, y)
            else:
                cpu_path.lineTo(x, y)

        # Gradiente translúcido abaixo da curva de CPU
        fill_path = QPainterPath(cpu_path)
        fill_path.lineTo(plot_left + (n - 1) * step_x, plot_bottom)
        fill_path.lineTo(plot_left, plot_bottom)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, plot_top, 0, plot_bottom)
        grad.setColorAt(0, QColor(56, 189, 248, 35))
        grad.setColorAt(1, QColor(56, 189, 248, 0))
        painter.fillPath(fill_path, grad)

        # Remove preenchimento para desenhar apenas as linhas com nitidez
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(QPen(QColor("#38BDF8"), 1.5))
        painter.drawPath(cpu_path)

        # 2. Caminho da Temperatura (30°C a 90°C)
        temp_path = QPainterPath()
        temp_min = 30.0
        temp_max = 90.0
        for i, val in enumerate(self.temp_history):
            clamped = max(temp_min, min(temp_max, val))
            x = plot_left + i * step_x
            ratio = (clamped - temp_min) / (temp_max - temp_min)
            y = plot_bottom - ratio * plot_h
            if i == 0:
                temp_path.moveTo(x, y)
            else:
                temp_path.lineTo(x, y)

        painter.setPen(QPen(QColor("#10B981"), 1.5))
        painter.drawPath(temp_path)

        painter.end()

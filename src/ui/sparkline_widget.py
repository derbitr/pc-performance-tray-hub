from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QPointF
from collections import deque

from typing import Optional

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
        max_points: int = 30,
        title_3: Optional[str] = None,
        color_3: Optional[str] = None,
        min_3: float = 0.0,
        max_3: float = 100.0,
        initial_1: Optional[float] = None,
        initial_2: Optional[float] = None,
        initial_3: Optional[float] = None
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

        self.title_3 = title_3
        self.color_3 = QColor(color_3) if color_3 else None
        self.min_3 = min_3
        self.max_3 = max_3

        init_1 = float(initial_1) if initial_1 is not None else 15.0
        init_2 = float(initial_2) if initial_2 is not None else (min_2 + (max_2 - min_2) * 0.3)
        self.history_1 = deque([init_1] * max_points, maxlen=max_points)
        self.history_2 = deque([init_2] * max_points, maxlen=max_points)
        if title_3:
            init_3 = float(initial_3) if initial_3 is not None else (min_3 + (max_3 - min_3) * 0.5)
            self.history_3 = deque([init_3] * max_points, maxlen=max_points)
        else:
            self.history_3 = None

    def add_point(self, val_1: float, val_2: float, val_3: Optional[float] = None):
        import math
        try:
            v1 = float(val_1) if val_1 is not None else 0.0
            if math.isnan(v1) or math.isinf(v1):
                v1 = 0.0
        except (ValueError, TypeError):
            v1 = 0.0
        try:
            v2 = float(val_2) if val_2 is not None else self.min_2
            if math.isnan(v2) or math.isinf(v2):
                v2 = self.min_2
        except (ValueError, TypeError):
            v2 = self.min_2

        self.history_1.append(v1)
        self.history_2.append(v2)

        if self.history_3 is not None:
            v3 = self.min_3
            if val_3 is not None:
                try:
                    vf = float(val_3)
                    if not (math.isnan(vf) or math.isinf(vf)):
                        v3 = vf
                except (ValueError, TypeError):
                    pass
            self.history_3.append(v3)

        if self.isVisible():
            self.update()

    def update_latest_third(self, val_3: float):
        if self.history_3 is not None and len(self.history_3) > 0:
            import math
            try:
                vf = float(val_3)
                if not (math.isnan(vf) or math.isinf(vf)):
                    self.history_3[-1] = vf
                    if self.isVisible():
                        self.update()
            except (ValueError, TypeError):
                pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.setBrush(QColor("#0B0F19"))
        painter.setPen(QColor("#161F30"))
        painter.drawRoundedRect(0, 0, w, h, 6, 6)

        painter.setPen(QPen(QColor("#162032"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(8, int(h / 2), w - 8, int(h / 2))

        font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        painter.setFont(font)

        v1 = self.history_1[-1] if self.history_1 else 0.0
        v2 = self.history_2[-1] if self.history_2 else 0.0

        if "RAM" in self.title_1:
            t1_display = f"RAM {v1:.1f}%"
            t2_display = f"LIVRE {v2:.1f} GB"
        elif "CPU" in self.title_1:
            t1_display = f"CPU {int(round(v1))}%"
            t2_display = f"TEMP {int(round(v2))}°C"
        elif "GPU" in self.title_1:
            t1_display = f"GPU {int(round(v1))}%"
            t2_display = f"VRAM {int(round(v2))}%"
        else:
            t1_display = self.title_1
            t2_display = self.title_2

        t3_display = None
        if self.title_3 and self.color_3:
            v3 = self.history_3[-1] if self.history_3 else 0.0
            if "FAN" in self.title_3:
                t3_display = f"FAN {int(round(v3))}%"
            else:
                t3_display = self.title_3

        painter.setPen(self.color_1)
        painter.drawText(8, 12, t1_display)

        t1_w = painter.fontMetrics().horizontalAdvance(t1_display)
        pos_2 = max(55, 8 + t1_w + 10)
        painter.setPen(self.color_2)
        painter.drawText(pos_2, 12, t2_display)

        if t3_display and self.color_3:
            t2_w = painter.fontMetrics().horizontalAdvance(t2_display)
            pos_3 = pos_2 + t2_w + 10
            painter.setPen(self.color_3)
            painter.drawText(pos_3, 12, t3_display)

        painter.setPen(QColor("#475569"))
        th_w = painter.fontMetrics().horizontalAdvance("HISTORICO 30s")
        painter.drawText(w - th_w - 8, 12, "HISTORICO 30s")

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

        path_1 = QPainterPath()
        for i, val in enumerate(self.history_1):
            clamped = max(0.0, min(100.0, val))
            x = plot_left + i * step_x
            y = plot_bottom - (clamped / 100.0) * plot_h
            if i == 0:
                path_1.moveTo(x, y)
            else:
                path_1.lineTo(x, y)

        fill_path = QPainterPath(path_1)
        fill_path.lineTo(plot_left + (n - 1) * step_x, plot_bottom)
        fill_path.lineTo(plot_left, plot_bottom)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, plot_top, 0, plot_bottom)
        c_fill = QColor(self.color_1.red(), self.color_1.green(), self.color_1.blue(), 30)
        grad.setColorAt(0, c_fill)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(fill_path, grad)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self.color_1, 1.5))
        painter.drawPath(path_1)

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

        fill_path_2 = QPainterPath(path_2)
        fill_path_2.lineTo(plot_left + (n - 1) * step_x, plot_bottom)
        fill_path_2.lineTo(plot_left, plot_bottom)
        fill_path_2.closeSubpath()

        grad_2 = QLinearGradient(0, plot_top, 0, plot_bottom)
        c_fill_2 = QColor(self.color_2.red(), self.color_2.green(), self.color_2.blue(), 18)
        grad_2.setColorAt(0, c_fill_2)
        grad_2.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(fill_path_2, grad_2)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self.color_2, 1.5))
        painter.drawPath(path_2)

        if self.history_3 is not None and self.color_3 is not None:
            path_3 = QPainterPath()
            for i, val in enumerate(self.history_3):
                clamped = max(self.min_3, min(self.max_3, val))
                x = plot_left + i * step_x
                ratio = (clamped - self.min_3) / (self.max_3 - self.min_3) if self.max_3 > self.min_3 else 0.5
                y = plot_bottom - ratio * plot_h
                if i == 0:
                    path_3.moveTo(x, y)
                else:
                    path_3.lineTo(x, y)

            fill_path_3 = QPainterPath(path_3)
            fill_path_3.lineTo(plot_left + (n - 1) * step_x, plot_bottom)
            fill_path_3.lineTo(plot_left, plot_bottom)
            fill_path_3.closeSubpath()

            grad_3 = QLinearGradient(0, plot_top, 0, plot_bottom)
            c_fill_3 = QColor(self.color_3.red(), self.color_3.green(), self.color_3.blue(), 18)
            grad_3.setColorAt(0, c_fill_3)
            grad_3.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillPath(fill_path_3, grad_3)

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self.color_3, 1.5))
            painter.drawPath(path_3)

        painter.end()

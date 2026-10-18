from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSlider, QFrame, QProgressBar, QApplication
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPoint, QVariantAnimation, QEasingCurve, QAbstractAnimation
)
from PyQt6.QtGui import QColor, QFont, QCursor, QIcon, QPixmap
from PyQt6.QtSvg import QSvgRenderer

import sys
import os
import json
import psutil
from typing import Dict, Any, Optional

from src.core.power_manager import PowerManager, SCHEMES
from src.core.memory_manager import MemoryManager
from src.core.process_suspender import ProcessSuspender
from src.core.network_optimizer import NetworkOptimizer
from src.core.health_checker import HealthChecker
from src.core.hardware_monitor import HardwareMonitor
from src.core.timer_resolution import TimerResolutionManager
from src.core.disk_cleaner import DiskCleaner
from src.core.game_focus import GameFocusManager
from src.core.gpu_monitor import GPUMonitor
from src.core.fps_sync import FPSSyncManager
from src.core.update_checker import (
    CURRENT_VERSION, UpdateCheckWorker, UpdateDownloadWorker,
    apply_in_place_update, open_releases_page
)
from src.ui.sparkline_widget import SparklineWidget
from src.assets.icons import (
    get_svg, ICON_BOLT, ICON_CPU, ICON_THERMOMETER, ICON_FAN,
    ICON_MEMORY, ICON_PAUSE, ICON_PLAY, ICON_SHIELD, ICON_NETWORK,
    ICON_PIN, ICON_PIN_ACTIVE, ICON_DRAG,
    ICON_TIMER, ICON_CLEAN_DISK, ICON_GAME, ICON_EYE,
    ICON_GPU, ICON_EXPAND, ICON_COLLAPSE, ICON_UPDATE, ICON_DOWNLOAD
)

DARK_STYLESHEET = """
QWidget#FlyoutRoot {
    background-color: #07090E;
    border: 1px solid #1E293B;
    border-radius: 14px;
}
QLabel {
    color: #F1F5F9;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', system-ui, sans-serif;
}
QFrame.GadgetCard {
    background-color: #0B0F19;
    border: 1px solid #161F30;
    border-radius: 9px;
    padding: 7px;
}
QPushButton {
    background-color: #0E1626;
    border: 1px solid #1E293B;
    border-radius: 6px;
    color: #94A3B8;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 10px;
}
QPushButton:hover {
    background-color: #162238;
    border-color: #38BDF8;
    color: #F8FAFC;
}
QPushButton:pressed {
    background-color: #0F172A;
}
QPushButton.ActivePill {
    background-color: #1E3A8A;
    border: 1px solid #38BDF8;
    color: #FFFFFF;
    font-weight: 700;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #161F30;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #38BDF8;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #F8FAFC;
    border: 1px solid #38BDF8;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
"""

def create_svg_pixmap(svg_xml: str, size: int = 16) -> QPixmap:
    renderer = QSvgRenderer(svg_xml.encode('utf-8'))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    from PyQt6.QtGui import QPainter
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap

class SafeSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def keyPressEvent(self, event):
        event.ignore()

    def keyReleaseEvent(self, event):
        event.ignore()

    def wheelEvent(self, event):
        event.ignore()

class DiskHealthWorker(QThread):
    finished = pyqtSignal(str, str)

    def run(self):
        try:
            score = HealthChecker.get_system_health_score()
            disks = score.get("disks", [])
            count = len(disks)
            all_ok = score.get("all_healthy", True)
            if all_ok:
                txt = f"{count} Discos 100% OK" if count > 1 else "Disco 100% OK"
                style = "font-size: 10px; font-weight: 700; color: #10B981; font-family: 'Consolas', monospace;"
            else:
                txt = "Atenção SMART"
                style = "font-size: 10px; font-weight: 700; color: #F59E0B; font-family: 'Consolas', monospace;"
            self.finished.emit(txt, style)
        except Exception:
            self.finished.emit("Discos OK", "font-size: 10px; font-weight: 700; color: #10B981; font-family: 'Consolas', monospace;")

class FlyoutWindow(QWidget):
    scheme_changed = pyqtSignal(str)
    update_available = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setObjectName("FlyoutRoot")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(DARK_STYLESHEET)

        self.power_mgr = PowerManager()
        self.mem_mgr = MemoryManager()
        self.proc_suspender = ProcessSuspender()
        self.net_opt = NetworkOptimizer()
        self.health_checker = HealthChecker()
        self.hw_monitor = HardwareMonitor()
        self.timer_mgr = TimerResolutionManager()
        self.disk_cleaner = DiskCleaner()
        self.game_focus = GameFocusManager()
        self.gpu_monitor = GPUMonitor()
        self.fps_sync = FPSSyncManager()

        self.total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)

        self.config_path = os.path.join(os.path.expanduser("~"), ".pctrayhub_config.json")
        self.is_pinned = False
        self.custom_pos = None
        self.opacity = 100
        self.wing_expanded = False
        self.graph_location = "hub"
        self.fan_location = "hub"
        self.show_cpu_graph = True
        self.show_ram_graph = False
        self.show_gpu_graph = False

        self._load_config()

        self._build_ui()

        self._apply_fan_location(self.fan_location)
        self._apply_graph_location(self.graph_location)
        self._apply_wing_state(reposition=False)
        self._update_graph_visibility()

        self.setWindowOpacity(self.opacity / 100.0)

        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._update_telemetry)
        self.telemetry_timer.start(1500)

        self.update_worker: Optional[UpdateCheckWorker] = None
        self.download_worker: Optional[UpdateDownloadWorker] = None
        self.disk_worker: Optional[DiskHealthWorker] = None
        self.last_update_info: Dict[str, Any] = {}

        self._update_telemetry(force=True)
        self._update_power_pills()
        QTimer.singleShot(250, self._refresh_disk_health)
        QTimer.singleShot(2500, self._check_for_updates)

    def _build_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        self.main_pane = QWidget()
        self.main_pane.setFixedWidth(380)
        self.main_pane_layout = QVBoxLayout(self.main_pane)
        self.main_pane_layout.setContentsMargins(0, 0, 0, 0)
        self.main_pane_layout.setSpacing(6)

        header_card = QFrame()
        header_card.setProperty("class", "GadgetCard")
        header = QHBoxLayout(header_card)
        header.setContentsMargins(8, 7, 8, 7)
        header.setSpacing(6)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(create_svg_pixmap(get_svg(ICON_BOLT, "#38BDF8"), 18))
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("PERFORMANCE TRAY HUB")
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 800; color: #F8FAFC; letter-spacing: 0.04em;")
        hw_info = HardwareMonitor.get_hardware_info()
        sub_lbl = QLabel(f" {hw_info['cpu']} • {hw_info['ram']} ")
        sub_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8; background: #101B2E; border: 1px solid #1E3A8A; border-radius: 4px; padding: 1px 4px; font-family: 'Consolas', monospace;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)
        header.addStretch()

        drag_lbl = QLabel()
        drag_lbl.setPixmap(create_svg_pixmap(get_svg(ICON_DRAG, "#64748B"), 14))
        drag_lbl.setToolTip("Arraste a janela por qualquer área livre")
        drag_lbl.setCursor(Qt.CursorShape.SizeAllCursor)
        header.addWidget(drag_lbl)

        self.btn_wing_toggle = QPushButton(" GADGETS »")
        self.btn_wing_toggle.setToolTip("Expande painel lateral com Placa de Vídeo e Monitor de Jogos")
        self.btn_wing_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_wing_toggle.clicked.connect(self._toggle_side_wing)
        header.addWidget(self.btn_wing_toggle)

        self.btn_pin = QPushButton()
        self.btn_pin.setFixedSize(28, 28)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.clicked.connect(self._toggle_pin)
        header.addWidget(self.btn_pin)
        self._update_pin_button()

        idle_badge = QLabel("IDLE")
        idle_badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #38BDF8; background: #0C121D; border: 1px solid #1E293B; padding: 2px 7px; border-radius: 10px;")
        header.addWidget(idle_badge)
        self.main_pane_layout.addWidget(header_card)

        self.main_pane_layout.addWidget(self._build_power_gadget())

        self.main_pane_layout.addWidget(self._build_telemetry_gadget())

        self.hub_graph_slot = QVBoxLayout()
        self.hub_graph_slot.setContentsMargins(0, 0, 0, 0)
        self.hub_graph_slot.setSpacing(4)
        self.main_pane_layout.addLayout(self.hub_graph_slot)

        self.hub_fan_slot = QVBoxLayout()
        self.hub_fan_slot.setContentsMargins(0, 0, 0, 0)
        self.hub_fan_slot.setSpacing(4)
        self.main_pane_layout.addLayout(self.hub_fan_slot)

        self.main_pane_layout.addLayout(self._build_quick_actions())

        self.main_pane_layout.addLayout(self._build_optimizations_grid())

        self.main_pane_layout.addWidget(self._build_hud_controls())

        footer = QHBoxLayout()
        footer_lbl = QLabel("Atalho: <span style='color:#38BDF8; font-family:Consolas;'>Ctrl+Shift+F12</span>")
        footer_lbl.setTextFormat(Qt.TextFormat.RichText)
        footer_lbl.setStyleSheet("font-size: 10px; color: #475569;")
        footer.addWidget(footer_lbl)
        footer.addStretch()

        self.btn_diag = QPushButton("Diagnóstico")
        self.btn_diag.setToolTip("Copia relatório completo do sistema para a Área de Transferência")
        self.btn_diag.setStyleSheet("font-size: 10px; padding: 2px 6px; color: #38BDF8; border: none; background: transparent;")
        self.btn_diag.clicked.connect(self._copy_diagnostic_report)
        footer.addWidget(self.btn_diag)

        reset_btn = QPushButton("Resetar Canto")
        reset_btn.setToolTip("Restaura a posição original sobre a bandeja")
        reset_btn.setStyleSheet("font-size: 10px; padding: 2px 6px; color: #64748B; border: none; background: transparent;")
        reset_btn.clicked.connect(self.reset_to_tray_position)
        footer.addWidget(reset_btn)

        close_btn = QPushButton("Fechar")
        close_btn.setStyleSheet("font-size: 10px; padding: 2px 8px; color: #64748B; border: none; background: transparent;")
        close_btn.clicked.connect(self.hide)
        footer.addWidget(close_btn)
        self.main_pane_layout.addLayout(footer)

        root_layout.addWidget(self.main_pane)

        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.VLine)
        self.divider.setStyleSheet("color: #161F30; background-color: #161F30; width: 1px;")
        root_layout.addWidget(self.divider)

        self.side_wing = QWidget()
        self.side_wing.setFixedWidth(375)
        self.side_wing_layout = QVBoxLayout(self.side_wing)
        self.side_wing_layout.setContentsMargins(0, 0, 0, 0)
        self.side_wing_layout.setSpacing(6)

        wing_header_card = QFrame()
        wing_header_card.setProperty("class", "GadgetCard")
        wing_header = QHBoxLayout(wing_header_card)
        wing_header.setContentsMargins(8, 7, 8, 7)
        wing_header.setSpacing(6)

        gpu_hdr_icon = QLabel()
        gpu_hdr_icon.setPixmap(create_svg_pixmap(get_svg(ICON_GPU, "#38BDF8"), 16))
        wing_header.addWidget(gpu_hdr_icon)

        w_title_box = QVBoxLayout()
        w_title_box.setSpacing(1)
        w_title_lbl = QLabel("TELEMETRIA & GADGETS")
        w_title_lbl.setStyleSheet("font-size: 11px; font-weight: 800; color: #F8FAFC; letter-spacing: 0.04em;")
        w_sub_lbl = QLabel("PAINEL LATERAL EXPANDIDO (IDLE HUD)")
        w_sub_lbl.setStyleSheet("font-size: 9px; color: #64748B; font-weight: 600;")
        w_title_box.addWidget(w_title_lbl)
        w_title_box.addWidget(w_sub_lbl)
        wing_header.addLayout(w_title_box)
        wing_header.addStretch()

        self.btn_wing_collapse = QPushButton("« RECOLHER")
        self.btn_wing_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_wing_collapse.setStyleSheet("font-size: 10px; padding: 4px 8px; color: #94A3B8; background: #0E1626; border: 1px solid #1E293B;")
        self.btn_wing_collapse.clicked.connect(self._toggle_side_wing)
        wing_header.addWidget(self.btn_wing_collapse)
        self.side_wing_layout.addWidget(wing_header_card)

        self.side_wing_layout.addWidget(self._build_gpu_card())

        self.wing_fan_slot = QVBoxLayout()
        self.wing_fan_slot.setContentsMargins(0, 0, 0, 0)
        self.wing_fan_slot.setSpacing(4)
        self.side_wing_layout.addLayout(self.wing_fan_slot)

        self.side_wing_layout.addWidget(self._build_game_sync_card())
        self.side_wing_layout.addWidget(self._build_top_processes_card())
        self.side_wing_layout.addWidget(self._build_update_card())

        self.wing_graph_slot = QVBoxLayout()
        self.wing_graph_slot.setContentsMargins(0, 0, 0, 0)
        self.wing_graph_slot.setSpacing(4)
        self.side_wing_layout.addLayout(self.wing_graph_slot)

        self.side_wing_layout.addStretch()
        root_layout.addWidget(self.side_wing)

        self.fan_card = self._build_fan_gadget()
        self._build_graph_dashboard()

    def _build_graph_dashboard(self):
        self.graph_card = QFrame()
        self.graph_card.setProperty("class", "GadgetCard")
        lay = QVBoxLayout(self.graph_card)
        lay.setContentsMargins(8, 7, 8, 7)
        lay.setSpacing(5)

        top_row = QHBoxLayout()
        lbl = QLabel("GRÁFICOS EM TEMPO REAL (30s)")
        lbl.setStyleSheet("font-size: 9px; font-weight: 700; color: #64748B; letter-spacing: 0.05em;")
        top_row.addWidget(lbl)
        top_row.addStretch()

        lbl_pos = QLabel("Local:")
        lbl_pos.setStyleSheet("font-size: 9px; color: #475569;")
        top_row.addWidget(lbl_pos)

        self.btn_loc_hub = QPushButton("Hub")
        self.btn_loc_hub.setToolTip("Fixa os gráficos na primeira janela principal")
        self.btn_loc_hub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_loc_hub.clicked.connect(lambda: self._set_graph_location("hub"))
        top_row.addWidget(self.btn_loc_hub)

        self.btn_loc_wing = QPushButton("Lateral")
        self.btn_loc_wing.setToolTip("Move os gráficos para a gaveta lateral expansível")
        self.btn_loc_wing.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_loc_wing.clicked.connect(lambda: self._set_graph_location("wing"))
        top_row.addWidget(self.btn_loc_wing)
        lay.addLayout(top_row)

        pills = QHBoxLayout()
        pills.setSpacing(4)

        self.btn_pill_cpu = QPushButton("CPU && Temp")
        self.btn_pill_cpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pill_cpu.clicked.connect(lambda: self._toggle_graph("cpu"))
        pills.addWidget(self.btn_pill_cpu)

        self.btn_pill_ram = QPushButton("RAM")
        self.btn_pill_ram.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pill_ram.clicked.connect(lambda: self._toggle_graph("ram"))
        pills.addWidget(self.btn_pill_ram)

        self.btn_pill_gpu = QPushButton("GPU • Fan")
        self.btn_pill_gpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pill_gpu.clicked.connect(lambda: self._toggle_graph("gpu"))
        pills.addWidget(self.btn_pill_gpu)
        lay.addLayout(pills)

        self.sparkline_cpu = SparklineWidget(
            self.graph_card,
            title_1="CPU %",
            color_1="#38BDF8",
            title_2="TEMP °C",
            color_2="#10B981",
            min_2=25.0,
            max_2=85.0,
            height=50
        )
        lay.addWidget(self.sparkline_cpu)

        self.sparkline_ram = SparklineWidget(
            self.graph_card,
            title_1="RAM %",
            color_1="#A855F7",
            title_2="LIVRE GB",
            color_2="#38BDF8",
            min_2=0.0,
            max_2=max(4.0, round(self.total_ram_gb, 1)),
            height=50
        )
        lay.addWidget(self.sparkline_ram)

        self.sparkline_gpu = SparklineWidget(
            self.graph_card,
            title_1="GPU %",
            color_1="#F59E0B",
            title_2="VRAM %",
            color_2="#F43F5E",
            min_2=0.0,
            max_2=100.0,
            height=50,
            title_3="FAN %",
            color_3="#38BDF8",
            min_3=0.0,
            max_3=100.0
        )
        lay.addWidget(self.sparkline_gpu)

        self.lbl_no_graphs = QLabel("Nenhum gráfico ativo. Selecione acima.")
        self.lbl_no_graphs.setStyleSheet("font-size: 10px; color: #475569; padding: 10px; text-align: center;")
        self.lbl_no_graphs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_no_graphs)

    def _set_graph_location(self, loc: str):
        if loc not in ("hub", "wing"):
            return
        self.graph_location = loc
        self._apply_graph_location(loc)
        self._save_config()

    def _apply_graph_location(self, loc: str):
        if loc == "hub":
            self.wing_graph_slot.removeWidget(self.graph_card)
            self.hub_graph_slot.addWidget(self.graph_card)
            self.graph_card.setParent(self.main_pane)
            self.graph_card.show()
        else:
            self.hub_graph_slot.removeWidget(self.graph_card)
            self.wing_graph_slot.addWidget(self.graph_card)
            self.graph_card.setParent(self.side_wing)
            self.graph_card.show()
            if not self.wing_expanded:
                self._toggle_side_wing()

        if self.graph_location == "hub":
            self.btn_loc_hub.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700; font-size: 9px; padding: 2px 6px;")
            self.btn_loc_wing.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #64748B; font-weight: 600; font-size: 9px; padding: 2px 6px;")
        else:
            self.btn_loc_wing.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700; font-size: 9px; padding: 2px 6px;")
            self.btn_loc_hub.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #64748B; font-weight: 600; font-size: 9px; padding: 2px 6px;")

        self.adjustSize()
        if self.custom_pos is None and self.isVisible():
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                y = geo.bottom() - self.height() - 12
                self.move(self.x(), y)

    def _set_fan_location(self, loc: str):
        if loc not in ("hub", "wing"):
            return
        self.fan_location = loc
        self._apply_fan_location(loc)
        self._save_config()

    def _apply_fan_location(self, loc: str):
        if not hasattr(self, 'fan_card') or not hasattr(self, 'hub_fan_slot') or not hasattr(self, 'wing_fan_slot'):
            return
        if loc == "hub":
            self.wing_fan_slot.removeWidget(self.fan_card)
            self.hub_fan_slot.addWidget(self.fan_card)
            self.fan_card.setParent(self.main_pane)
            self.fan_card.show()
            if hasattr(self, 'btn_fan_loc_hub') and hasattr(self, 'btn_fan_loc_wing'):
                self.btn_fan_loc_hub.setStyleSheet("background-color: #78350F; border: 1px solid #F59E0B; color: #FFFFFF; font-weight: 700; font-size: 8px; padding: 2px 6px;")
                self.btn_fan_loc_wing.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #64748B; font-weight: 600; font-size: 8px; padding: 2px 6px;")
        else:
            self.hub_fan_slot.removeWidget(self.fan_card)
            self.wing_fan_slot.addWidget(self.fan_card)
            self.fan_card.setParent(self.side_wing)
            self.fan_card.show()
            if hasattr(self, 'btn_fan_loc_hub') and hasattr(self, 'btn_fan_loc_wing'):
                self.btn_fan_loc_wing.setStyleSheet("background-color: #78350F; border: 1px solid #F59E0B; color: #FFFFFF; font-weight: 700; font-size: 8px; padding: 2px 6px;")
                self.btn_fan_loc_hub.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #64748B; font-weight: 600; font-size: 8px; padding: 2px 6px;")
            if not getattr(self, "wing_expanded", False):
                self._toggle_side_wing()

        self.adjustSize()
        if self.custom_pos is None and self.isVisible():
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                y = geo.bottom() - self.height() - 12
                self.move(self.x(), y)

    def _build_power_gadget(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "GadgetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(5)

        hdr = QHBoxLayout()
        lbl = QLabel("PERFIL DE ENERGIA")
        lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.05em;")
        self.lbl_active_scheme = QLabel("Turbo Max")
        self.lbl_active_scheme.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(self.lbl_active_scheme)
        layout.addLayout(hdr)

        pills = QHBoxLayout()
        pills.setSpacing(4)
        self.btn_turbo = QPushButton("Turbo Max")
        self.btn_turbo.clicked.connect(lambda: self._set_scheme("turbo"))
        self.btn_balanced = QPushButton("Equilibrado")
        self.btn_balanced.clicked.connect(lambda: self._set_scheme("balanced"))
        self.btn_silent = QPushButton("Silencioso")
        self.btn_silent.clicked.connect(lambda: self._set_scheme("silent"))

        pills.addWidget(self.btn_turbo)
        pills.addWidget(self.btn_balanced)
        pills.addWidget(self.btn_silent)
        layout.addLayout(pills)
        return card

    def _build_telemetry_gadget(self) -> QWidget:
        box = QHBoxLayout()
        box.setSpacing(8)

        c_card = QFrame()
        c_card.setProperty("class", "GadgetCard")
        c_lay = QVBoxLayout(c_card)
        c_lay.setContentsMargins(8, 7, 8, 7)
        c_lay.setSpacing(2)

        c_top = QHBoxLayout()
        c_lbl = QLabel("CLOCK CPU")
        c_lbl.setStyleSheet("font-size: 9px; font-weight: 700; color: #64748B;")
        c_icon = QLabel()
        c_icon.setPixmap(create_svg_pixmap(get_svg(ICON_CPU, "#64748B"), 13))
        c_top.addWidget(c_lbl)
        c_top.addStretch()
        c_top.addWidget(c_icon)
        c_lay.addLayout(c_top)

        self.lbl_clock = QLabel(f"{self.hw_monitor._base_mhz / 1000.0:.2f} GHz")
        self.lbl_clock.setStyleSheet("font-size: 16px; font-weight: 800; color: #F8FAFC; font-family: 'Consolas', monospace;")
        c_lay.addWidget(self.lbl_clock)

        self.bar_cpu = QProgressBar()
        self.bar_cpu.setTextVisible(False)
        self.bar_cpu.setFixedHeight(3)
        self.bar_cpu.setStyleSheet("QProgressBar { background: #161F30; border: none; border-radius: 1px; } QProgressBar::chunk { background: #38BDF8; }")
        c_lay.addWidget(self.bar_cpu)
        box.addWidget(c_card)

        t_card = QFrame()
        t_card.setProperty("class", "GadgetCard")
        t_lay = QVBoxLayout(t_card)
        t_lay.setContentsMargins(8, 7, 8, 7)
        t_lay.setSpacing(2)

        t_top = QHBoxLayout()
        t_lbl = QLabel("TEMPERATURA")
        t_lbl.setStyleSheet("font-size: 9px; font-weight: 700; color: #64748B;")
        t_icon = QLabel()
        t_icon.setPixmap(create_svg_pixmap(get_svg(ICON_THERMOMETER, "#10B981"), 13))
        t_top.addWidget(t_lbl)
        t_top.addStretch()
        t_top.addWidget(t_icon)
        t_lay.addLayout(t_top)

        self.lbl_temp = QLabel("--°C")
        self.lbl_temp.setStyleSheet("font-size: 16px; font-weight: 800; color: #F8FAFC; font-family: 'Consolas', monospace;")
        t_lay.addWidget(self.lbl_temp)

        self.bar_temp = QProgressBar()
        self.bar_temp.setTextVisible(False)
        self.bar_temp.setFixedHeight(3)
        self.bar_temp.setStyleSheet("QProgressBar { background: #161F30; border: none; border-radius: 1px; } QProgressBar::chunk { background: #10B981; }")
        t_lay.addWidget(self.bar_temp)
        box.addWidget(t_card)

        container = QWidget()
        container.setLayout(box)
        return container

    def _build_fan_gadget(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "GadgetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(5)

        hdr = QHBoxLayout()
        fan_icon = QLabel()
        fan_icon.setPixmap(create_svg_pixmap(get_svg(ICON_FAN, "#F59E0B"), 14))
        hdr.addWidget(fan_icon)
        gpu_name = self.gpu_monitor.primary_gpu.get("name", "GPU")
        lbl = QLabel("Ventoinha da GPU")
        lbl.setToolTip(f"Controle de rotação e perfis térmicos da {gpu_name}")
        lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #94A3B8;")
        hdr.addWidget(lbl)
        hdr.addStretch()

        lbl_pos = QLabel("Local:")
        lbl_pos.setStyleSheet("font-size: 9px; color: #475569;")
        hdr.addWidget(lbl_pos)

        self.btn_fan_loc_hub = QPushButton("Hub")
        self.btn_fan_loc_hub.setToolTip("Fixa a ventoinha no painel principal")
        self.btn_fan_loc_hub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fan_loc_hub.clicked.connect(lambda: self._set_fan_location("hub"))
        hdr.addWidget(self.btn_fan_loc_hub)

        self.btn_fan_loc_wing = QPushButton("Lateral")
        self.btn_fan_loc_wing.setToolTip("Move a ventoinha para o painel lateral de gadgets")
        self.btn_fan_loc_wing.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fan_loc_wing.clicked.connect(lambda: self._set_fan_location("wing"))
        hdr.addWidget(self.btn_fan_loc_wing)
        layout.addLayout(hdr)

        info_row = QHBoxLayout()
        self.lbl_fan_info = QLabel("Auto • 1.650 RPM")
        self.lbl_fan_info.setStyleSheet("font-size: 10px; font-weight: 700; color: #F59E0B; font-family: 'Consolas', monospace;")
        info_row.addWidget(self.lbl_fan_info)
        info_row.addStretch()
        layout.addLayout(info_row)

        pills = QHBoxLayout()
        pills.setSpacing(4)
        self.btn_fan_auto = QPushButton("Auto")
        self.btn_fan_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fan_auto.clicked.connect(lambda: self._set_gpu_fan_preset("auto"))
        pills.addWidget(self.btn_fan_auto)

        self.btn_fan_silent = QPushButton("Silêncio")
        self.btn_fan_silent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fan_silent.clicked.connect(lambda: self._set_gpu_fan_preset("silent"))
        pills.addWidget(self.btn_fan_silent)

        self.btn_fan_gaming = QPushButton("Jogos (85%)")
        self.btn_fan_gaming.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fan_gaming.clicked.connect(lambda: self._set_gpu_fan_preset("gaming"))
        pills.addWidget(self.btn_fan_gaming)

        self.btn_fan_max = QPushButton("MAX")
        self.btn_fan_max.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fan_max.clicked.connect(lambda: self._set_gpu_fan_preset("max"))
        pills.addWidget(self.btn_fan_max)
        layout.addLayout(pills)

        slider_box = QHBoxLayout()
        self.slider_fan = SafeSlider(Qt.Orientation.Horizontal)
        self.slider_fan.setRange(30, 100)
        self.slider_fan.setValue(getattr(self.gpu_monitor, "fan_speed", 50))
        self.slider_fan.valueChanged.connect(self._on_fan_slider_changed)
        slider_box.addWidget(self.slider_fan)
        layout.addLayout(slider_box)

        self._update_gpu_fan_pills()
        return card

    def _build_quick_actions(self) -> QHBoxLayout:
        box = QHBoxLayout()
        box.setSpacing(8)

        self.btn_ram = QPushButton(" Limpar RAM")
        self.btn_ram.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_MEMORY, "#38BDF8"), 14)))
        self.btn_ram.setStyleSheet("background: #0C1626; border: 1px solid #1E3A8A; color: #F8FAFC; padding: 7px;")
        self.btn_ram.clicked.connect(self._on_clean_ram)
        box.addWidget(self.btn_ram)

        self.btn_suspend = QPushButton(" Pausar Launchers")
        self.btn_suspend.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_PAUSE, "#94A3B8"), 14)))
        self.btn_suspend.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #CBD5E1; padding: 7px;")
        self.btn_suspend.clicked.connect(self._on_toggle_suspend)
        box.addWidget(self.btn_suspend)

        return box

    def _build_optimizations_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(6)

        self.btn_timer = QPushButton(" Timer 0.5ms")
        self.btn_timer.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_TIMER, "#38BDF8"), 13)))
        self.btn_timer.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
        self.btn_timer.setToolTip("Reduz a latência de eventos do Windows de 15.6ms para 0.5ms (menos input lag)")
        self.btn_timer.clicked.connect(self._on_toggle_timer)
        grid.addWidget(self.btn_timer, 0, 0)

        self.btn_game = QPushButton(" Game Focus")
        self.btn_game.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_GAME, "#38BDF8"), 13)))
        self.btn_game.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
        self.btn_game.setToolTip("Prioriza o jogo ativo em foco com prioridade máxima nos núcleos da CPU")
        self.btn_game.clicked.connect(self._on_toggle_game_focus)
        grid.addWidget(self.btn_game, 0, 1)

        self.btn_disk = QPushButton(" Limpar SSD")
        self.btn_disk.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_CLEAN_DISK, "#38BDF8"), 13)))
        self.btn_disk.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
        self.btn_disk.setToolTip("Purga arquivos temporários residuais sem tocar em dados úteis")
        self.btn_disk.clicked.connect(self._on_clean_disk)
        grid.addWidget(self.btn_disk, 1, 0)

        self.btn_dns = QPushButton(" Flush DNS")
        self.btn_dns.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_NETWORK, "#38BDF8"), 13)))
        self.btn_dns.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
        self.btn_dns.setToolTip("Limpa o cache DNS do Windows e afere a latência de resposta sem desconectar a internet")
        self.btn_dns.clicked.connect(self._on_flush_dns)
        grid.addWidget(self.btn_dns, 1, 1)

        return grid

    def _build_hud_controls(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "GadgetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        row1 = QHBoxLayout()
        eye_icon = QLabel()
        eye_icon.setPixmap(create_svg_pixmap(get_svg(ICON_EYE, "#64748B"), 13))
        row1.addWidget(eye_icon)
        lbl_op = QLabel("Opacidade HUD:")
        lbl_op.setStyleSheet("font-size: 10px; color: #94A3B8;")
        row1.addWidget(lbl_op)

        self.slider_opacity = SafeSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(60, 100)
        self.slider_opacity.setValue(self.opacity)
        self.slider_opacity.valueChanged.connect(self._on_opacity_slider_changed)
        row1.addWidget(self.slider_opacity)

        self.lbl_opacity_val = QLabel(f"{self.opacity}%")
        self.lbl_opacity_val.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8; font-family: Consolas;")
        self.lbl_opacity_val.setFixedWidth(32)
        row1.addWidget(self.lbl_opacity_val)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        shield_icon = QLabel()
        shield_icon.setPixmap(create_svg_pixmap(get_svg(ICON_SHIELD, "#10B981"), 13))
        row2.addWidget(shield_icon)
        lbl_smart = QLabel("S.M.A.R.T. Discos:")
        lbl_smart.setStyleSheet("font-size: 10px; color: #94A3B8;")
        row2.addWidget(lbl_smart)
        row2.addStretch()

        self.lbl_health_score = QLabel("Verificando...")
        self.lbl_health_score.setStyleSheet("font-size: 10px; font-weight: 700; color: #10B981; font-family: 'Consolas', monospace;")
        row2.addWidget(self.lbl_health_score)
        layout.addLayout(row2)

        return card

    def _refresh_disk_health(self):
        if self.disk_worker is not None and self.disk_worker.isRunning():
            return
        self.disk_worker = DiskHealthWorker(self)
        self.disk_worker.finished.connect(self._apply_disk_health)
        self.disk_worker.start()

    def _apply_disk_health(self, text: str, style: str):
        if hasattr(self, 'lbl_health_score'):
            self.lbl_health_score.setText(text)
            self.lbl_health_score.setStyleSheet(style)

    def _build_gpu_card(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "GadgetCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(5)

        hdr = QHBoxLayout()
        gpu_icon = QLabel()
        gpu_icon.setPixmap(create_svg_pixmap(get_svg(ICON_GPU, "#F59E0B"), 15))
        hdr.addWidget(gpu_icon)

        t_box = QVBoxLayout()
        t_box.setSpacing(1)
        title = QLabel("PLACA DE VÍDEO")
        title.setStyleSheet("font-size: 9px; font-weight: 700; color: #64748B; letter-spacing: 0.05em;")
        self.lbl_gpu_name = QLabel(self.gpu_monitor.primary_gpu.get("name", "GPU"))
        self.lbl_gpu_name.setStyleSheet("font-size: 11px; font-weight: 700; color: #F8FAFC;")
        t_box.addWidget(title)
        t_box.addWidget(self.lbl_gpu_name)
        hdr.addLayout(t_box)
        hdr.addStretch()

        badge_text = "DEDICADA" if self.gpu_monitor.primary_gpu.get("is_discrete") else "INTEGRADA"
        badge = QLabel(badge_text)
        badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #F59E0B; background: #1C150A; border: 1px solid #78350F; padding: 2px 6px; border-radius: 4px;")
        hdr.addWidget(badge)
        lay.addLayout(hdr)

        row1 = QHBoxLayout()
        lbl_l = QLabel("Carga da GPU:")
        lbl_l.setStyleSheet("font-size: 10px; color: #94A3B8;")
        self.lbl_gpu_load_val = QLabel("0% • 40°C")
        self.lbl_gpu_load_val.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8; font-family: Consolas;")
        row1.addWidget(lbl_l)
        row1.addStretch()
        row1.addWidget(self.lbl_gpu_load_val)
        lay.addLayout(row1)

        self.bar_gpu_load = QProgressBar()
        self.bar_gpu_load.setTextVisible(False)
        self.bar_gpu_load.setFixedHeight(3)
        self.bar_gpu_load.setStyleSheet("QProgressBar { background: #161F30; border: none; border-radius: 1px; } QProgressBar::chunk { background: #38BDF8; }")
        lay.addWidget(self.bar_gpu_load)

        row2 = QHBoxLayout()
        lbl_v = QLabel("Memória de Vídeo (VRAM):")
        lbl_v.setStyleSheet("font-size: 10px; color: #94A3B8;")
        self.lbl_gpu_vram = QLabel("0 / 1024 MB (0%)")
        self.lbl_gpu_vram.setStyleSheet("font-size: 10px; font-weight: 700; color: #10B981; font-family: Consolas;")
        row2.addWidget(lbl_v)
        row2.addStretch()
        row2.addWidget(self.lbl_gpu_vram)
        lay.addLayout(row2)

        self.bar_gpu_vram = QProgressBar()
        self.bar_gpu_vram.setTextVisible(False)
        self.bar_gpu_vram.setFixedHeight(3)
        self.bar_gpu_vram.setStyleSheet("QProgressBar { background: #161F30; border: none; border-radius: 1px; } QProgressBar::chunk { background: #10B981; }")
        lay.addWidget(self.bar_gpu_vram)

        row3 = QHBoxLayout()
        lbl_fan = QLabel("Ventoinha:")
        lbl_fan.setStyleSheet("font-size: 10px; color: #94A3B8;")
        self.lbl_card_gpu_fan = QLabel("Auto • 1.650 RPM")
        self.lbl_card_gpu_fan.setStyleSheet("font-size: 10px; font-weight: 700; color: #F59E0B; font-family: Consolas;")
        row3.addWidget(lbl_fan)
        row3.addStretch()
        row3.addWidget(self.lbl_card_gpu_fan)
        lay.addLayout(row3)

        if len(self.gpu_monitor.gpus) > 1:
            sec = self.gpu_monitor.gpus[1]
            sec_lbl = QLabel(f"Secundária: {sec['name']}")
            sec_lbl.setStyleSheet("font-size: 9px; color: #475569; font-family: Consolas;")
            lay.addWidget(sec_lbl)

        return card

    def _build_game_sync_card(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "GadgetCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(5)

        hdr = QHBoxLayout()
        game_icon = QLabel()
        game_icon.setPixmap(create_svg_pixmap(get_svg(ICON_GAME, "#38BDF8"), 15))
        hdr.addWidget(game_icon)

        t_box = QVBoxLayout()
        t_box.setSpacing(1)
        title = QLabel("SINCRONIZAÇÃO DE JOGOS & FPS")
        title.setStyleSheet("font-size: 9px; font-weight: 700; color: #64748B; letter-spacing: 0.05em;")
        self.lbl_game_name = QLabel("Aguardando jogo...")
        self.lbl_game_name.setStyleSheet("font-size: 11px; font-weight: 700; color: #F8FAFC;")
        t_box.addWidget(title)
        t_box.addWidget(self.lbl_game_name)
        hdr.addLayout(t_box)
        hdr.addStretch()

        self.lbl_fps_badge = QLabel("ANTI-CHEAT SEGURO")
        self.lbl_fps_badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #10B981; background: #062419; border: 1px solid #059669; padding: 2px 6px; border-radius: 4px;")
        hdr.addWidget(self.lbl_fps_badge)
        lay.addLayout(hdr)

        row1 = QHBoxLayout()
        lbl_f = QLabel("Taxa de Quadros (FPS):")
        lbl_f.setStyleSheet("font-size: 10px; color: #94A3B8;")
        self.lbl_fps_val = QLabel("Steam / RTSS Sync")
        self.lbl_fps_val.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8; font-family: Consolas;")
        row1.addWidget(lbl_f)
        row1.addStretch()
        row1.addWidget(self.lbl_fps_val)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        lbl_s = QLabel("Status do Game Focus:")
        lbl_s.setStyleSheet("font-size: 10px; color: #94A3B8;")
        self.lbl_game_status = QLabel("Pronto para otimizar")
        self.lbl_game_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #10B981; font-family: Consolas;")
        row2.addWidget(lbl_s)
        row2.addStretch()
        row2.addWidget(self.lbl_game_status)
        lay.addLayout(row2)

        return card

    def _build_top_processes_card(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "GadgetCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 7, 8, 7)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        proc_icon = QLabel()
        proc_icon.setPixmap(create_svg_pixmap(get_svg(ICON_CPU, "#38BDF8"), 14))
        hdr.addWidget(proc_icon)

        title = QLabel("PROCESSOS TOP CONSUMO")
        title.setStyleSheet("font-size: 9px; font-weight: 700; color: #64748B; letter-spacing: 0.05em;")
        hdr.addWidget(title)
        hdr.addStretch()

        btn_refresh = QPushButton("Atualizar")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet("font-size: 8px; color: #38BDF8; background: transparent; border: none; padding: 0px 4px;")
        btn_refresh.clicked.connect(self._update_top_processes)
        hdr.addWidget(btn_refresh)
        lay.addLayout(hdr)

        self.proc_rows_layout = QVBoxLayout()
        self.proc_rows_layout.setSpacing(3)
        lay.addLayout(self.proc_rows_layout)

        return card

    def _update_top_processes(self):
        if not hasattr(self, 'proc_rows_layout'):
            return

        procs = []
        for p in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                info = p.info
                mem_info = info.get('memory_info')
                if not mem_info:
                    continue
                name = (info.get('name') or "").strip()
                if not name:
                    continue
                pid = info.get('pid', 0)
                if pid > 4 and pid != os.getpid() and name.lower() not in ('system', 'idle', 'registry', 'pctrayhub.exe', 'python.exe', 'pythonw.exe'):
                    mem_mb = int(mem_info.rss / (1024 * 1024))
                    procs.append((name, pid, mem_mb))
            except Exception:
                pass

        procs.sort(key=lambda x: x[2], reverse=True)
        top = procs[:3]

        cached = getattr(self, "_cached_proc_rows", [])
        if len(top) == len(cached) and len(top) > 0 and all(top[i][1] == cached[i]["pid"] for i in range(len(top))):
            for i, (name, pid, mem) in enumerate(top):
                cached[i]["mem_lbl"].setText(f"{mem} MB")
                cached[i]["name_lbl"].setText(name)
            return

        while self.proc_rows_layout.count() > 0:
            item = self.proc_rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        self._cached_proc_rows = []

        if not top:
            empty_lbl = QLabel("Nenhum processo pesado ativo.")
            empty_lbl.setStyleSheet("font-size: 9px; color: #64748B;")
            self.proc_rows_layout.addWidget(empty_lbl)
            return

        for name, pid, mem in top:
            row = QHBoxLayout()
            row.setContentsMargins(2, 1, 2, 1)

            p_lbl = QLabel(f"{name}")
            p_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #E2E8F0;")
            row.addWidget(p_lbl)
            row.addStretch()

            mem_lbl = QLabel(f"{mem} MB")
            mem_lbl.setStyleSheet("font-size: 9px; font-weight: 700; color: #38BDF8; font-family: Consolas;")
            row.addWidget(mem_lbl)

            btn_kill = QPushButton("X")
            btn_kill.setFixedSize(16, 16)
            btn_kill.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_kill.setToolTip(f"Encerrar processo {name} (PID {pid})")
            btn_kill.setStyleSheet("font-size: 8px; font-weight: 800; color: #F43F5E; background: #1C0F14; border: 1px solid #4C1D24; border-radius: 3px; padding: 0px;")
            btn_kill.clicked.connect(lambda checked, p=pid: self._kill_process(p))
            row.addWidget(btn_kill)

            row_widget = QWidget()
            row_widget.setLayout(row)
            self.proc_rows_layout.addWidget(row_widget)

            self._cached_proc_rows.append({
                "pid": pid,
                "name_lbl": p_lbl,
                "mem_lbl": mem_lbl,
                "widget": row_widget
            })

    def _kill_process(self, pid: int):
        self._cached_proc_rows = []
        try:
            p = psutil.Process(pid)
            p.terminate()
            QTimer.singleShot(300, self._update_top_processes)
        except Exception:
            try:
                import subprocess
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                subprocess.run(
                    ["taskkill", "/f", "/pid", str(pid)],
                    timeout=2.0,
                    creationflags=flags
                )
                QTimer.singleShot(300, self._update_top_processes)
            except Exception:
                pass

    def _copy_diagnostic_report(self):
        try:
            hw = self.hw_monitor.get_metrics()
            hw_spec = HardwareMonitor.get_hardware_info()
            vm = psutil.virtual_memory()
            gpu = self.gpu_monitor.get_gpu_info()
            timer_info = self.timer_mgr.get_resolution()
            health = self.health_checker.get_system_health_score()
            disks_str = ", ".join([f"{d.get('name')} ({d.get('health')})" for d in health.get("disks", [])])
            cores = psutil.cpu_count(logical=True) or 4

            report = (
                f"PC PERFORMANCE TRAY HUB - RELATORIO DE DIAGNOSTICO\n"
                f"--------------------------------------------------\n"
                f"Processador: {hw_spec.get('cpu', 'N/A')} ({cores} threads / nucleos)\n"
                f"Clock Atual: {hw.get('clock_ghz', 0.0):.2f} GHz | Uso: {hw.get('cpu_percent', 0)}% | Temp: {hw.get('temp_c', 0)} C\n"
                f"Placa de Video: {gpu.get('name', 'N/A')} (Driver: {gpu.get('driver', 'N/A')})\n"
                f"VRAM: {gpu.get('vram_used_mb', 0)} MB / {gpu.get('vram_total_mb', 0)} MB ({gpu.get('vram_percent', 0)}%)\n"
                f"Memoria RAM: {vm.used / (1024**3):.2f} GB / {vm.total / (1024**3):.2f} GB ({vm.percent}% em uso)\n"
                f"Armazenamento SMART: {disks_str}\n"
                f"Resolucao de Timer: {timer_info.get('current_ms', 15.6):.1f} ms ({'Baixa Latencia' if timer_info.get('is_low_latency') else 'Padrao'})\n"
                f"Status Geral: Sistema Estavel ({health.get('score', 100)}% de integridade)\n"
            )

            cb = QApplication.clipboard()
            if cb:
                try:
                    cb.setText(report)
                except Exception:
                    pass

            if hasattr(self, 'btn_diag'):
                self.btn_diag.setText("Copiado!")
                QTimer.singleShot(1800, lambda: self.btn_diag.setText("Diagnóstico"))
        except Exception:
            pass

    def _build_update_card(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "GadgetCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(5)

        hdr = QHBoxLayout()
        up_icon = QLabel()
        up_icon.setPixmap(create_svg_pixmap(get_svg(ICON_UPDATE, "#38BDF8"), 14))
        hdr.addWidget(up_icon)

        title = QLabel("ATUALIZAÇÕES")
        title.setStyleSheet("font-size: 9px; font-weight: 700; color: #64748B; letter-spacing: 0.05em;")
        hdr.addWidget(title)
        hdr.addStretch()

        self.lbl_ver_badge = QLabel(f"v{CURRENT_VERSION}")
        self.lbl_ver_badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #94A3B8; background: #161F30; border: 1px solid #1E293B; border-radius: 3px; padding: 1px 5px; font-family: Consolas;")
        hdr.addWidget(self.lbl_ver_badge)

        self.btn_check_update = QPushButton("Verificar")
        self.btn_check_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_update.setStyleSheet("font-size: 8px; color: #38BDF8; background: transparent; border: none; padding: 0px 4px;")
        self.btn_check_update.clicked.connect(self._check_for_updates)
        hdr.addWidget(self.btn_check_update)
        lay.addLayout(hdr)

        row_status = QHBoxLayout()
        self.lbl_update_status = QLabel(f"Versão v{CURRENT_VERSION} instalada")
        self.lbl_update_status.setStyleSheet("font-size: 10px; font-weight: 600; color: #10B981;")
        row_status.addWidget(self.lbl_update_status)
        row_status.addStretch()
        lay.addLayout(row_status)

        self.lbl_update_detail = QLabel("Repositório oficial no GitHub")
        self.lbl_update_detail.setStyleSheet("font-size: 9px; color: #64748B;")
        lay.addWidget(self.lbl_update_detail)

        self.bar_update_progress = QProgressBar()
        self.bar_update_progress.setRange(0, 100)
        self.bar_update_progress.setValue(0)
        self.bar_update_progress.setFixedHeight(12)
        self.bar_update_progress.setStyleSheet("QProgressBar { background: #0B0F19; border: 1px solid #161F30; border-radius: 3px; text-align: center; color: #94A3B8; font-size: 8px; font-weight: 700; } QProgressBar::chunk { background: #38BDF8; border-radius: 2px; }")
        self.bar_update_progress.setVisible(False)
        lay.addWidget(self.bar_update_progress)

        update_actions = QHBoxLayout()
        update_actions.setSpacing(6)

        self.btn_direct_update = QPushButton(" Atualizar Agora")
        self.btn_direct_update.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_BOLT, "#FFFFFF"), 12)))
        self.btn_direct_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_direct_update.setStyleSheet("font-size: 10px; font-weight: 700; color: #FFFFFF; background-color: #1E3A8A; border: 1px solid #38BDF8; border-radius: 4px; padding: 5px;")
        self.btn_direct_update.setVisible(False)
        self.btn_direct_update.clicked.connect(self._on_start_direct_update)
        update_actions.addWidget(self.btn_direct_update, stretch=2)

        self.btn_download_update = QPushButton(" Notas")
        self.btn_download_update.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_DOWNLOAD, "#94A3B8"), 10)))
        self.btn_download_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download_update.setStyleSheet("font-size: 10px; font-weight: 600; color: #94A3B8; background-color: #0E1626; border: 1px solid #1E293B; border-radius: 4px; padding: 5px;")
        self.btn_download_update.setVisible(False)
        self.btn_download_update.clicked.connect(self._on_download_update)
        update_actions.addWidget(self.btn_download_update, stretch=1)

        lay.addLayout(update_actions)

        return card

    def _check_for_updates(self):
        if self.update_worker and self.update_worker.isRunning():
            return
        if hasattr(self, 'lbl_update_status'):
            self.lbl_update_status.setText("Verificando atualizações...")
            self.lbl_update_status.setStyleSheet("font-size: 10px; font-weight: 600; color: #38BDF8;")
        if hasattr(self, 'btn_check_update'):
            self.btn_check_update.setEnabled(False)

        self.update_worker = UpdateCheckWorker()
        self.update_worker.check_finished.connect(self._on_update_check_finished)
        self.update_worker.start()

    def _on_update_check_finished(self, result: Dict[str, Any]):
        self.last_update_info = result
        if hasattr(self, 'btn_check_update'):
            self.btn_check_update.setEnabled(True)

        if not hasattr(self, 'lbl_update_status'):
            return

        has_update = result.get("has_update", False)
        latest = result.get("latest_version", CURRENT_VERSION)
        msg = result.get("message", "")

        if has_update:
            self.lbl_update_status.setText(f"Nova versão v{latest} disponível!")
            self.lbl_update_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8;")
            pub = result.get("published_at", "")
            detail_txt = f"Lançada em {pub} no GitHub" if pub else "Disponível no GitHub Releases"
            self.lbl_update_detail.setText(detail_txt)
            self.btn_direct_update.setText(f" Atualizar para v{latest}")
            self.btn_direct_update.setVisible(True)
            self.btn_direct_update.setEnabled(True)
            self.btn_download_update.setVisible(True)
            self.btn_download_update.setEnabled(True)
            self.bar_update_progress.setVisible(False)
            self.lbl_ver_badge.setText(f"v{CURRENT_VERSION} -> v{latest}")
            self.lbl_ver_badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #38BDF8; background: #0C1E36; border: 1px solid #38BDF8; border-radius: 3px; padding: 1px 5px; font-family: Consolas;")
            self.update_available.emit(result)
        else:
            self.lbl_update_status.setText(msg)
            color = "#10B981" if result.get("success") else "#94A3B8"
            self.lbl_update_status.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {color};")
            self.lbl_update_detail.setText("O aplicativo está na versão estável mais recente.")
            self.btn_direct_update.setVisible(False)
            self.btn_download_update.setVisible(False)
            self.bar_update_progress.setVisible(False)
            self.lbl_ver_badge.setText(f"v{CURRENT_VERSION}")
            self.lbl_ver_badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #94A3B8; background: #161F30; border: 1px solid #1E293B; border-radius: 3px; padding: 1px 5px; font-family: Consolas;")

    def _on_start_direct_update(self):
        if self.download_worker and self.download_worker.isRunning():
            return
        download_url = self.last_update_info.get("exe_download_url")
        if not download_url:
            self._on_download_update()
            return

        if getattr(sys, "frozen", False):
            target_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            target_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "dist")
        os.makedirs(target_dir, exist_ok=True)
        temp_dest = os.path.join(target_dir, "PCTrayHub_new.exe")

        self.btn_direct_update.setEnabled(False)
        self.btn_download_update.setEnabled(False)
        self.bar_update_progress.setValue(0)
        self.bar_update_progress.setVisible(True)
        self.lbl_update_status.setText("Iniciando download...")
        self.lbl_update_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8;")

        self.download_worker = UpdateDownloadWorker(download_url, temp_dest)
        self.download_worker.download_progress.connect(self._on_download_progress)
        self.download_worker.download_finished.connect(self._on_download_finished)
        self.download_worker.start()

    def _on_download_progress(self, pct: int, downloaded: int, total: int):
        self.bar_update_progress.setValue(pct)
        d_mb = downloaded / (1024 * 1024)
        t_mb = total / (1024 * 1024) if total > 0 else 0.0
        if t_mb > 0:
            self.lbl_update_status.setText(f"Baixando: {d_mb:.1f} MB / {t_mb:.1f} MB ({pct}%)")
        else:
            self.lbl_update_status.setText(f"Baixando: {d_mb:.1f} MB...")

    def _on_download_finished(self, success: bool, path_or_err: str):
        self.btn_direct_update.setEnabled(True)
        self.btn_download_update.setEnabled(True)
        if success:
            self.bar_update_progress.setValue(100)
            self.lbl_update_status.setText("Atualização concluída! Reiniciando...")
            self.lbl_update_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #10B981;")
            self.lbl_update_detail.setText("O aplicativo iniciará a nova versão automaticamente.")
            QTimer.singleShot(600, lambda: self._apply_update_and_restart(path_or_err))
        else:
            self.bar_update_progress.setVisible(False)
            self.lbl_update_status.setText("Falha no download da atualização.")
            self.lbl_update_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #F43F5E;")
            self.lbl_update_detail.setText(f"Erro: {path_or_err[:40]}")

    def _apply_update_and_restart(self, file_path: str):
        if hasattr(self, 'tray_app') and self.tray_app:
            try:
                if hasattr(self.tray_app, 'ipc_server'):
                    self.tray_app.ipc_server.close()
                    self.tray_app.ipc_server.removeServer("PCPerformanceTrayHub_IpcServer")
            except Exception:
                pass
        res = apply_in_place_update(file_path)
        if not res:
            self.bar_update_progress.setVisible(False)
            self.lbl_update_status.setText("Falha ao aplicar atualização.")
            self.lbl_update_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #F43F5E;")
            self.lbl_update_detail.setText("Execute a atualização manualmente através do GitHub.")
            self.btn_direct_update.setText("Tentar Novamente")
            self.btn_download_update.setVisible(True)

    def _on_download_update(self):
        url = self.last_update_info.get("release_url")
        open_releases_page(url)

    def _toggle_side_wing(self):
        self.wing_expanded = not self.wing_expanded
        self._animate_wing(self.wing_expanded)
        self._save_config()

    def _animate_wing(self, expanding: bool):
        if hasattr(self, '_wing_anim') and self._wing_anim.state() == QAbstractAnimation.State.Running:
            self._wing_anim.stop()

        screen = None
        for s in QApplication.screens():
            if s.geometry().contains(self.pos()):
                screen = s
                break
        if not screen:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None

        start_w = self.width()
        end_w = 770 if expanding else 385
        start_x = self.x()

        if expanding:
            self.side_wing.setVisible(True)
            self.divider.setVisible(True)
            self.btn_wing_toggle.setText(" GADGETS «")
            self.btn_wing_toggle.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700; padding: 4px 8px; font-size: 10px;")
            self._update_top_processes()
        else:
            self.btn_wing_toggle.setText(" GADGETS »")
            self.btn_wing_toggle.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #94A3B8; font-weight: 600; padding: 4px 8px; font-size: 10px;")

        self._wing_anim = QVariantAnimation(self)
        self._wing_anim.setDuration(160)
        self._wing_anim.setStartValue(start_w)
        self._wing_anim.setEndValue(end_w)
        self._wing_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def on_step(val):
            w = int(val)
            self.setFixedWidth(w)
            if geo and start_x + 770 > geo.right():
                shift = w - 385
                new_x = max(geo.left() + 10, start_x - shift)
                self.move(new_x, self.y())

        def on_finish():
            if not expanding:
                self.side_wing.setVisible(False)
                self.divider.setVisible(False)
                self.setFixedWidth(385)
            self.adjustSize()
            if self.custom_pos is None and self.isVisible() and geo:
                y = geo.bottom() - self.height() - 12
                self.move(self.x(), y)

        self._wing_anim.valueChanged.connect(on_step)
        self._wing_anim.finished.connect(on_finish)
        self._wing_anim.start()

    def _apply_wing_state(self, reposition: bool = False):
        screen = None
        for s in QApplication.screens():
            if s.geometry().contains(self.pos()):
                screen = s
                break
        if not screen:
            screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None

        if self.wing_expanded:
            self.side_wing.setVisible(True)
            self.divider.setVisible(True)
            self.setFixedWidth(770)
            self.btn_wing_toggle.setText(" GADGETS «")
            self.btn_wing_toggle.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700; padding: 4px 8px; font-size: 10px;")
            self._update_top_processes()
            if reposition and geo:
                if self.x() + 770 > geo.right():
                    shift = (self.x() + 770) - geo.right() + 12
                    new_x = max(geo.left() + 10, self.x() - shift)
                    self.move(new_x, self.y())
        else:
            self.side_wing.setVisible(False)
            self.divider.setVisible(False)
            self.setFixedWidth(385)
            self.btn_wing_toggle.setText(" GADGETS »")
            self.btn_wing_toggle.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #94A3B8; font-weight: 600; padding: 4px 8px; font-size: 10px;")
            if reposition and geo:
                if self.x() + 770 >= geo.right() - 30:
                    new_x = min(geo.right() - 385 - 12, self.x() + (770 - 385))
                    self.move(new_x, self.y())

        self.adjustSize()
        if self.custom_pos is None and self.isVisible() and geo:
            y = geo.bottom() - self.height() - 12
            self.move(self.x(), y)

    def _toggle_graph(self, graph_key: str):
        if graph_key == "cpu":
            self.show_cpu_graph = not self.show_cpu_graph
        elif graph_key == "ram":
            self.show_ram_graph = not self.show_ram_graph
        elif graph_key == "gpu":
            self.show_gpu_graph = not self.show_gpu_graph

        self._update_graph_visibility()
        self._save_config()

    def _update_graph_visibility(self):
        self.sparkline_cpu.setVisible(self.show_cpu_graph)
        self.sparkline_ram.setVisible(self.show_ram_graph)
        self.sparkline_gpu.setVisible(self.show_gpu_graph)

        any_visible = self.show_cpu_graph or self.show_ram_graph or self.show_gpu_graph
        self.lbl_no_graphs.setVisible(not any_visible)

        self._apply_pill_style(self.btn_pill_cpu, self.show_cpu_graph, "#38BDF8", "#0C1E36")
        self._apply_pill_style(self.btn_pill_ram, self.show_ram_graph, "#A855F7", "#1F1033")
        self._apply_pill_style(self.btn_pill_gpu, self.show_gpu_graph, "#F59E0B", "#2D1A05")

        self.adjustSize()
        if self.custom_pos is None and self.isVisible():
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                y = geo.bottom() - self.height() - 12
                self.move(self.x(), y)

    def _apply_pill_style(self, btn: QPushButton, is_active: bool, border_color: str, bg_active: str):
        if is_active:
            btn.setStyleSheet(f"background-color: {bg_active}; border: 1px solid {border_color}; color: {border_color}; font-size: 10px; font-weight: 700; padding: 5px;")
        else:
            btn.setStyleSheet("background-color: #0B0F19; border: 1px solid #161F30; color: #64748B; font-size: 10px; font-weight: 600; padding: 5px;")

    def _update_telemetry(self, force: bool = False):
        metrics = self.hw_monitor.get_metrics()
        gpu_info = self.gpu_monitor.get_gpu_info(cpu_percent=metrics.get('cpu_percent'))

        if hasattr(self, 'sparkline_cpu'):
            self.sparkline_cpu.add_point(metrics['cpu_percent'], metrics['temp_c'])

        mem = psutil.virtual_memory()
        ram_used_pct = mem.percent
        ram_free_gb = mem.available / (1024 ** 3)
        if hasattr(self, 'sparkline_ram'):
            self.sparkline_ram.add_point(ram_used_pct, ram_free_gb)

        if hasattr(self, 'sparkline_gpu'):
            self.sparkline_gpu.add_point(gpu_info['gpu_percent'], gpu_info['vram_percent'], gpu_info['fan_speed_percent'])

        if not self.isVisible() and not force:
            if hasattr(self, 'game_focus') and self.game_focus.is_active:
                self.game_focus.check_and_boost_active()
            return

        self.lbl_clock.setText(f"{metrics['clock_ghz']:.2f} GHz")
        self.bar_cpu.setValue(metrics['cpu_percent'])

        self.lbl_temp.setText(f"{metrics['temp_c']}°C")
        self.lbl_temp.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {metrics['temp_color']}; font-family: 'Consolas', monospace;")
        self.bar_temp.setValue(metrics['temp_c'])
        self.bar_temp.setStyleSheet(f"QProgressBar {{ background: #161F30; border: none; border-radius: 1px; }} QProgressBar::chunk {{ background: {metrics['temp_color']}; }}")

        self._update_fan_ui(gpu_info)

        if hasattr(self, 'lbl_gpu_name'):
            self.lbl_gpu_name.setText(gpu_info['name'])
            gpu_pct = gpu_info['gpu_percent']
            temp_c = gpu_info['temp_c']
            vram_pct = gpu_info['vram_percent']

            load_color = "#38BDF8" if gpu_pct < 70 else ("#F59E0B" if gpu_pct < 85 else "#F43F5E")
            vram_color = "#10B981" if vram_pct < 70 else ("#F59E0B" if vram_pct < 85 else "#F43F5E")

            self.lbl_gpu_load_val.setText(f"{gpu_pct}% • {temp_c}°C")
            self.lbl_gpu_load_val.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {load_color}; font-family: Consolas;")
            self.bar_gpu_load.setValue(gpu_pct)
            self.bar_gpu_load.setStyleSheet(f"QProgressBar {{ background: #161F30; border: none; border-radius: 1px; }} QProgressBar::chunk {{ background: {load_color}; }}")

            self.lbl_gpu_vram.setText(f"{gpu_info['vram_used_mb']} / {gpu_info['vram_total_mb']} MB ({vram_pct}%)")
            self.lbl_gpu_vram.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {vram_color}; font-family: Consolas;")
            self.bar_gpu_vram.setValue(vram_pct)
            self.bar_gpu_vram.setStyleSheet(f"QProgressBar {{ background: #161F30; border: none; border-radius: 1px; }} QProgressBar::chunk {{ background: {vram_color}; }}")

        fg = self.game_focus.get_foreground_process()
        game_tel = self.fps_sync.get_game_telemetry(fg)
        if hasattr(self, 'lbl_game_name'):
            if game_tel["active"]:
                self.lbl_game_name.setText(game_tel["name"])
                if game_tel["has_rtss"]:
                    self.lbl_fps_val.setText(f"{game_tel['fps']} FPS")
                    self.lbl_fps_val.setStyleSheet("font-size: 11px; font-weight: 800; color: #10B981; font-family: Consolas;")
                    self.lbl_fps_badge.setText("RTSS ATIVO")
                else:
                    self.lbl_fps_val.setText("Anti-Cheat Safe")
                    self.lbl_fps_val.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8; font-family: Consolas;")
                    self.lbl_fps_badge.setText("ANTI-CHEAT SEGURO")
                self.lbl_game_status.setText(f"CPU {game_tel['cpu_percent']:.0f}% • RAM {game_tel['ram_mb']}MB")
            else:
                self.lbl_game_name.setText("Aguardando jogo em foco...")
                self.lbl_fps_val.setText("Standby")
                self.lbl_game_status.setText("Pronto para otimizar")

        if hasattr(self, 'game_focus') and self.game_focus.is_active:
            boosted = self.game_focus.check_and_boost_active()
            if boosted:
                name = boosted.get("name", "Jogo")
                self.btn_game.setText(f" Focus: {name[:7]}")

        if getattr(self, "wing_expanded", False) and hasattr(self, "proc_rows_layout"):
            self._proc_tick = getattr(self, "_proc_tick", 0) + 1
            if self._proc_tick % 2 == 0:
                self._update_top_processes()

    def _update_power_pills(self):
        active = self.power_mgr.get_active_scheme()
        self.lbl_active_scheme.setText(active["name"])
        for btn, k in [(self.btn_turbo, "turbo"), (self.btn_balanced, "balanced"), (self.btn_silent, "silent")]:
            if active.get("id") == k:
                btn.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700;")
            else:
                btn.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #94A3B8; font-weight: 600;")

    def _set_scheme(self, key: str):
        if self.power_mgr.set_scheme(key):
            self._update_power_pills()
            self.scheme_changed.emit(key)

    def _set_gpu_fan_preset(self, mode: str):
        self.gpu_monitor.set_fan_mode(mode)
        self._update_gpu_fan_pills()
        self._update_fan_ui()
        if hasattr(self, 'sparkline_gpu'):
            self.sparkline_gpu.update_latest_third(self.gpu_monitor.fan_speed)
        self._save_config()

    def _update_fan_ui(self, gpu_info: Optional[Dict[str, Any]] = None):
        if gpu_info is None:
            gpu_info = self.gpu_monitor.get_gpu_info()
        fan_speed = gpu_info["fan_speed_percent"]
        fan_rpm = gpu_info["fan_rpm"]
        fan_mode = gpu_info["fan_mode"]

        if hasattr(self, 'lbl_fan_info'):
            if fan_mode == "auto":
                self.lbl_fan_info.setText(f"Auto ({fan_speed}%) • {fan_rpm:,} RPM".replace(",", "."))
            else:
                self.lbl_fan_info.setText(f"{fan_speed}% • {fan_rpm:,} RPM".replace(",", "."))

        if hasattr(self, 'lbl_card_gpu_fan'):
            self.lbl_card_gpu_fan.setText(f"{fan_speed}% • {fan_rpm:,} RPM".replace(",", "."))

        if hasattr(self, 'slider_fan'):
            if fan_mode in ("auto", "silent", "gaming", "max"):
                self.slider_fan.blockSignals(True)
                self.slider_fan.setValue(fan_speed)
                self.slider_fan.blockSignals(False)

    def _update_gpu_fan_pills(self):
        if not hasattr(self, 'btn_fan_auto'):
            return
        mode = self.gpu_monitor.fan_mode
        presets = [
            (self.btn_fan_auto, "auto"),
            (self.btn_fan_silent, "silent"),
            (self.btn_fan_gaming, "gaming"),
            (self.btn_fan_max, "max")
        ]
        for btn, k in presets:
            if mode == k:
                btn.setStyleSheet("background-color: #78350F; border: 1px solid #F59E0B; color: #FFFFFF; font-weight: 700; font-size: 9px; padding: 3px 6px;")
            else:
                btn.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #94A3B8; font-weight: 600; font-size: 9px; padding: 3px 6px;")

    def _on_fan_slider_changed(self, val: int):
        self.gpu_monitor.set_fan_speed(val)
        self._update_gpu_fan_pills()
        self._update_fan_ui()
        if hasattr(self, 'sparkline_gpu'):
            self.sparkline_gpu.update_latest_third(val)
        self._save_config()

    def _on_clean_ram(self):
        res = self.mem_mgr.clean_ram()
        freed = res.get("freed_mb", 0)
        if freed > 0:
            self.btn_ram.setText(f" +{freed} MB!")
        else:
            self.btn_ram.setText(" Otimizado!")
        QTimer.singleShot(2000, lambda: self.btn_ram.setText(" Limpar RAM"))

    def _on_toggle_suspend(self):
        res = self.proc_suspender.toggle()
        if res["is_suspended"]:
            count = res.get("count", 0)
            self.btn_suspend.setText(f" Retomar ({count})")
            self.btn_suspend.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_PLAY, "#38BDF8"), 14)))
            self.btn_suspend.setStyleSheet("background: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700; padding: 7px;")
        else:
            self.btn_suspend.setText(" Pausar Launchers")
            self.btn_suspend.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_PAUSE, "#94A3B8"), 14)))
            self.btn_suspend.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #CBD5E1; padding: 7px;")

    def _on_toggle_timer(self):
        res = self.timer_mgr.toggle()
        if self.timer_mgr.is_active:
            self.btn_timer.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700; padding: 6px;")
            self.btn_timer.setText(" 0.5ms Ativo")
        else:
            self.btn_timer.setStyleSheet("background-color: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
            self.btn_timer.setText(" Timer 0.5ms")

    def _on_toggle_game_focus(self):
        res = self.game_focus.toggle()
        if self.game_focus.is_active:
            name = res.get("name", "Jogo")
            self.btn_game.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700; padding: 6px;")
            self.btn_game.setText(f" Focus: {name[:7]}")
        else:
            self.btn_game.setStyleSheet("background-color: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
            self.btn_game.setText(" Game Focus")

    def _on_clean_disk(self):
        res = self.disk_cleaner.clean_temp_files()
        freed = res.get("freed_mb", 0)
        if freed > 0:
            self.btn_disk.setText(f" -{freed} MB!")
        else:
            self.btn_disk.setText(" Limpo!")
        QTimer.singleShot(2500, lambda: self.btn_disk.setText(" Limpar SSD"))

    def _on_flush_dns(self):
        self.btn_dns.setEnabled(False)
        self.btn_dns.setText(" Limpando...")
        QApplication.processEvents()
        res = self.net_opt.flush_dns()
        lat = res.get("latency_ms", 0)
        if lat > 0:
            self.btn_dns.setText(f" DNS OK ({lat:.0f}ms)")
        else:
            self.btn_dns.setText(" DNS Limpo!")
        self.btn_dns.setEnabled(True)
        QTimer.singleShot(2500, lambda: self.btn_dns.setText(" Flush DNS"))

    def _on_opacity_slider_changed(self, val: int):
        self.opacity = val
        self.setWindowOpacity(val / 100.0)
        self.lbl_opacity_val.setText(f"{val}%")
        self._save_config()

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self._update_pin_button()
        self._save_config()

    def _update_pin_button(self):
        if self.is_pinned:
            self.btn_pin.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_PIN_ACTIVE, "#38BDF8"), 14)))
            self.btn_pin.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; border-radius: 6px; padding: 3px;")
            self.btn_pin.setToolTip("Fixado na Tela (Modo HUD flutuante). Clique para desafixar.")
        else:
            self.btn_pin.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_PIN, "#64748B"), 14)))
            self.btn_pin.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; border-radius: 6px; padding: 3px;")
            self.btn_pin.setToolTip("Fixar na Tela (Não fecha ao clicar fora).")

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.is_pinned = bool(cfg.get("pinned", False))
                    op = cfg.get("opacity", 100)
                    try:
                        self.opacity = max(60, min(100, int(op)))
                    except Exception:
                        self.opacity = 100
                    self.wing_expanded = bool(cfg.get("wing_expanded", False))
                    g_loc = str(cfg.get("graph_location", "hub")).lower()
                    self.graph_location = g_loc if g_loc in ("hub", "wing") else "hub"
                    f_loc = str(cfg.get("fan_location", "hub")).lower()
                    self.fan_location = f_loc if f_loc in ("hub", "wing") else "hub"
                    self.show_cpu_graph = bool(cfg.get("show_cpu_graph", True))
                    self.show_ram_graph = bool(cfg.get("show_ram_graph", False))
                    self.show_gpu_graph = bool(cfg.get("show_gpu_graph", False))
                    f_mode = str(cfg.get("fan_mode", "auto")).lower()
                    fan_mode = f_mode if f_mode in ("auto", "silent", "gaming", "max", "manual") else "auto"
                    try:
                        fan_speed = max(30, min(100, int(cfg.get("fan_speed", 50))))
                    except Exception:
                        fan_speed = 50
                    if hasattr(self, 'gpu_monitor'):
                        self.gpu_monitor.set_fan_mode(fan_mode)
                        if fan_mode == "manual":
                            self.gpu_monitor.set_fan_speed(fan_speed)
                    if "x" in cfg and "y" in cfg:
                        try:
                            self.custom_pos = QPoint(int(cfg["x"]), int(cfg["y"]))
                        except Exception:
                            self.custom_pos = None
            except Exception:
                pass

    def _save_config(self):
        try:
            cfg = {
                "pinned": self.is_pinned,
                "opacity": self.opacity,
                "x": self.pos().x(),
                "y": self.pos().y(),
                "wing_expanded": self.wing_expanded,
                "graph_location": self.graph_location,
                "fan_location": getattr(self, "fan_location", "hub"),
                "fan_mode": self.gpu_monitor.fan_mode if hasattr(self, 'gpu_monitor') else "auto",
                "fan_speed": self.gpu_monitor.fan_speed if hasattr(self, 'gpu_monitor') else 50,
                "show_cpu_graph": self.show_cpu_graph,
                "show_ram_graph": self.show_ram_graph,
                "show_gpu_graph": self.show_gpu_graph
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            self.custom_pos = new_pos
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self, "_drag_pos"):
                del self._drag_pos
            screen = None
            for s in QApplication.screens():
                if s.geometry().contains(self.pos()):
                    screen = s
                    break
            if not screen:
                screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                curr_w = self.width()
                curr_h = self.height()
                clamped_x = max(geo.left() + 8, min(self.x(), geo.right() - curr_w - 8))
                clamped_y = max(geo.top() + 8, min(self.y(), geo.bottom() - curr_h - 8))
                if clamped_x != self.x() or clamped_y != self.y():
                    self.move(clamped_x, clamped_y)
                self.custom_pos = self.pos()
            self._save_config()
            event.accept()

    def _is_pos_visible(self, pos: QPoint) -> bool:
        for screen in QApplication.screens():
            if screen.geometry().contains(pos):
                return True
        return False

    def position_above_tray(self):
        if self.custom_pos and self._is_pos_visible(self.custom_pos):
            screen = None
            for s in QApplication.screens():
                if s.geometry().contains(self.custom_pos):
                    screen = s
                    break
            if screen:
                geo = screen.availableGeometry()
                curr_w = self.width()
                curr_h = self.height()
                clamped_x = max(geo.left() + 8, min(self.custom_pos.x(), geo.right() - curr_w - 8))
                clamped_y = max(geo.top() + 8, min(self.custom_pos.y(), geo.bottom() - curr_h - 8))
                self.move(clamped_x, clamped_y)
                return
        self.reset_to_tray_position()

    def reset_to_tray_position(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        curr_width = 770 if getattr(self, "wing_expanded", False) else 385
        x = max(geo.left() + 8, geo.right() - curr_width - 12)
        y = max(geo.top() + 8, geo.bottom() - self.height() - 12)
        self.move(x, y)
        self.custom_pos = None
        self._save_config()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow() and not self.is_pinned:
                import time
                self._last_hide_time = time.time()
                self.hide()
        super().changeEvent(event)

    def show_or_toggle(self):
        import time
        if self.isVisible():
            self.hide()
        elif time.time() - getattr(self, "_last_hide_time", 0) > 0.25:
            self.position_above_tray()
            self.show()
            self.raise_()
            self.activateWindow()
            self._update_telemetry(force=True)
            self._refresh_disk_health()

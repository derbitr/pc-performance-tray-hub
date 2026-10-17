"""
Interface Gráfica do Flyout Flutuante (Full Night Mode)
Totalmente sem emojis. Utiliza ícones vetoriais SVG, tipografia tabular e paleta True Dark.
Permite exibir gráficos em tempo real tanto na primeira janela quanto na gaveta lateral expansível estilo jogos IDLE.
Inclui monitoramento de GPU dedicado e sincronização de jogos/FPS segura contra Anti-Cheats.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSlider, QFrame, QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
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
from src.ui.sparkline_widget import SparklineWidget
from src.assets.icons import (
    get_svg, ICON_BOLT, ICON_CPU, ICON_THERMOMETER, ICON_FAN,
    ICON_MEMORY, ICON_PAUSE, ICON_PLAY, ICON_SHIELD, ICON_NETWORK,
    ICON_PIN, ICON_PIN_ACTIVE, ICON_DRAG,
    ICON_TIMER, ICON_CLEAN_DISK, ICON_GAME, ICON_EYE,
    ICON_GPU, ICON_EXPAND, ICON_COLLAPSE
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

class FlyoutWindow(QWidget):
    scheme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("FlyoutRoot")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(DARK_STYLESHEET)

        # Core Engines
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

        # Telemetria Global
        self.total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)

        # Configurações Persistentes
        self.config_path = os.path.join(os.path.expanduser("~"), ".pctrayhub_config.json")
        self.is_pinned = False
        self.custom_pos = None
        self.opacity = 100
        self.wing_expanded = False
        self.graph_location = "hub"  # "hub" (Primeira Janela) ou "wing" (Gaveta Lateral)
        self.show_cpu_graph = True
        self.show_ram_graph = False
        self.show_gpu_graph = False

        self._load_config()

        # Monta Interface Gráfica
        self._build_ui()

        # Aplica Localização dos Gráficos e Estado Inicial
        self._apply_graph_location(self.graph_location)
        self._apply_wing_state(reposition=False)
        self._update_graph_visibility()

        # Aplica opacidade carregada
        self.setWindowOpacity(self.opacity / 100.0)

        # Timer de Telemetria (1.5s)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._update_telemetry)
        self.telemetry_timer.start(1500)

        self._update_telemetry()
        self._update_power_pills()

    def _build_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # ==========================================
        # 1. PAINEL PRINCIPAL (PRIMEIRA JANELA - 380px)
        # ==========================================
        self.main_pane = QWidget()
        self.main_pane.setFixedWidth(380)
        self.main_pane_layout = QVBoxLayout(self.main_pane)
        self.main_pane_layout.setContentsMargins(0, 0, 0, 0)
        self.main_pane_layout.setSpacing(6)

        # Topo
        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(create_svg_pixmap(get_svg(ICON_BOLT, "#38BDF8"), 18))
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_lbl = QLabel("PERFORMANCE TRAY HUB")
        title_lbl.setStyleSheet("font-size: 12px; font-weight: 800; color: #F8FAFC; letter-spacing: 0.04em;")
        hw_info = HardwareMonitor.get_hardware_info()
        sub_lbl = QLabel(hw_info["full_spec"])
        sub_lbl.setStyleSheet("font-size: 10px; color: #64748B; font-family: 'Consolas', monospace;")
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
        self.main_pane_layout.addLayout(header)

        # GADGET 1: SELETOR DE PERFIS
        self.main_pane_layout.addWidget(self._build_power_gadget())

        # GADGET 2: TELEMETRIA (CLOCK & TEMPERATURA)
        self.main_pane_layout.addWidget(self._build_telemetry_gadget())

        # SLOT DE GRÁFICOS NO HUB PRINCIPAL
        self.hub_graph_slot = QVBoxLayout()
        self.hub_graph_slot.setContentsMargins(0, 0, 0, 0)
        self.hub_graph_slot.setSpacing(4)
        self.main_pane_layout.addLayout(self.hub_graph_slot)

        # GADGET 3: CONTROLE DE VENTOINHA
        self.main_pane_layout.addWidget(self._build_fan_gadget())

        # GADGET 4: BOTÕES RÁPIDOS (LIMPAR RAM & PAUSAR LAUNCHERS)
        self.main_pane_layout.addLayout(self._build_quick_actions())

        # GADGET 5: GRID DE OTIMIZAÇÕES AVANÇADAS (TIMER, GAME FOCUS, DISCO, DNS)
        self.main_pane_layout.addLayout(self._build_optimizations_grid())

        # GADGET 6: CONTROLES DO HUD (OPACIDADE & SAÚDE S.M.A.R.T.)
        self.main_pane_layout.addWidget(self._build_hud_controls())

        # RODAPÉ
        footer = QHBoxLayout()
        footer_lbl = QLabel("Atalho: <span style='color:#38BDF8; font-family:Consolas;'>Ctrl+Shift+F12</span>")
        footer_lbl.setTextFormat(Qt.TextFormat.RichText)
        footer_lbl.setStyleSheet("font-size: 10px; color: #475569;")
        footer.addWidget(footer_lbl)
        footer.addStretch()

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

        # ==========================================
        # 2. DIVISOR VERTICAL LATERAL (1px)
        # ==========================================
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.VLine)
        self.divider.setStyleSheet("color: #161F30; background-color: #161F30; width: 1px;")
        root_layout.addWidget(self.divider)

        # ==========================================
        # 3. GAVETA LATERAL (SEGUNDA JANELA - 375px)
        # ==========================================
        self.side_wing = QWidget()
        self.side_wing.setFixedWidth(375)
        self.side_wing_layout = QVBoxLayout(self.side_wing)
        self.side_wing_layout.setContentsMargins(0, 0, 0, 0)
        self.side_wing_layout.setSpacing(6)

        # Topo da Gaveta
        wing_header = QHBoxLayout()
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
        self.side_wing_layout.addLayout(wing_header)

        # Card de Placa de Vídeo (GPU)
        self.side_wing_layout.addWidget(self._build_gpu_card())

        # Card de Sincronização de Jogos e FPS
        self.side_wing_layout.addWidget(self._build_game_sync_card())

        # SLOT DE GRÁFICOS NA GAVETA LATERAL
        self.wing_graph_slot = QVBoxLayout()
        self.wing_graph_slot.setContentsMargins(0, 0, 0, 0)
        self.wing_graph_slot.setSpacing(4)
        self.side_wing_layout.addLayout(self.wing_graph_slot)

        self.side_wing_layout.addStretch()
        root_layout.addWidget(self.side_wing)

        # ==========================================
        # 4. CONSTRUÇÃO DO PAINEL DE GRÁFICOS COMPARTILHADO
        # ==========================================
        self._build_graph_dashboard()

    def _build_graph_dashboard(self):
        """Constrói o container de gráficos com seletor de localização (No Hub vs Na Lateral) e filtros."""
        self.graph_card = QFrame()
        self.graph_card.setProperty("class", "GadgetCard")
        lay = QVBoxLayout(self.graph_card)
        lay.setContentsMargins(8, 7, 8, 7)
        lay.setSpacing(5)

        # Linha 1: Título e Seletor de Onde Mostrar
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

        # Linha 2: Filtros Individuais dos Gráficos
        pills = QHBoxLayout()
        pills.setSpacing(4)

        self.btn_pill_cpu = QPushButton("CPU & Temp")
        self.btn_pill_cpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pill_cpu.clicked.connect(lambda: self._toggle_graph("cpu"))
        pills.addWidget(self.btn_pill_cpu)

        self.btn_pill_ram = QPushButton("RAM")
        self.btn_pill_ram.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pill_ram.clicked.connect(lambda: self._toggle_graph("ram"))
        pills.addWidget(self.btn_pill_ram)

        self.btn_pill_gpu = QPushButton("GPU & VRAM")
        self.btn_pill_gpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pill_gpu.clicked.connect(lambda: self._toggle_graph("gpu"))
        pills.addWidget(self.btn_pill_gpu)
        lay.addLayout(pills)

        # Gráfico 1: CPU & Temperatura
        self.sparkline_cpu = SparklineWidget(
            self.graph_card,
            title_1="CPU %",
            color_1="#38BDF8",
            title_2="TEMP °C",
            color_2="#10B981",
            min_2=30.0,
            max_2=95.0,
            height=50
        )
        lay.addWidget(self.sparkline_cpu)

        # Gráfico 2: Memória RAM
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

        # Gráfico 3: GPU & VRAM
        self.sparkline_gpu = SparklineWidget(
            self.graph_card,
            title_1="GPU %",
            color_1="#F59E0B",
            title_2="VRAM %",
            color_2="#F43F5E",
            min_2=0.0,
            max_2=100.0,
            height=50
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

        # Estilo dos botões de localização
        if self.graph_location == "hub":
            self.btn_loc_hub.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700; font-size: 9px; padding: 2px 6px;")
            self.btn_loc_wing.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #64748B; font-weight: 600; font-size: 9px; padding: 2px 6px;")
        else:
            self.btn_loc_wing.setStyleSheet("background-color: #1E3A8A; border: 1px solid #38BDF8; color: #FFFFFF; font-weight: 700; font-size: 9px; padding: 2px 6px;")
            self.btn_loc_hub.setStyleSheet("background-color: #0E1626; border: 1px solid #1E293B; color: #64748B; font-weight: 600; font-size: 9px; padding: 2px 6px;")

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

        # Card Clock
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

        self.lbl_clock = QLabel("3.60 GHz")
        self.lbl_clock.setStyleSheet("font-size: 16px; font-weight: 800; color: #F8FAFC; font-family: 'Consolas', monospace;")
        c_lay.addWidget(self.lbl_clock)

        self.bar_cpu = QProgressBar()
        self.bar_cpu.setTextVisible(False)
        self.bar_cpu.setFixedHeight(3)
        self.bar_cpu.setStyleSheet("QProgressBar { background: #161F30; border: none; border-radius: 1px; } QProgressBar::chunk { background: #38BDF8; }")
        c_lay.addWidget(self.bar_cpu)
        box.addWidget(c_card)

        # Card Temperatura
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

        self.lbl_temp = QLabel("54°C")
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
        fan_icon.setPixmap(create_svg_pixmap(get_svg(ICON_FAN, "#38BDF8"), 14))
        hdr.addWidget(fan_icon)
        lbl = QLabel("Cooler da CPU (Super I/O)")
        lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #94A3B8;")
        hdr.addWidget(lbl)
        hdr.addStretch()

        self.lbl_fan_info = QLabel("100% • 2.500 RPM")
        self.lbl_fan_info.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8; font-family: 'Consolas', monospace;")
        hdr.addWidget(self.lbl_fan_info)
        layout.addLayout(hdr)

        slider_box = QHBoxLayout()
        self.slider_fan = QSlider(Qt.Orientation.Horizontal)
        self.slider_fan.setRange(30, 100)
        self.slider_fan.setValue(100)
        self.slider_fan.valueChanged.connect(self._on_fan_slider_changed)
        slider_box.addWidget(self.slider_fan)

        btn_max = QPushButton("MAX")
        btn_max.setFixedWidth(40)
        btn_max.setStyleSheet("font-size: 9px; font-weight: 800; color: #38BDF8; background: #0C1626; border: 1px solid #1E3A8A;")
        btn_max.clicked.connect(lambda: self.slider_fan.setValue(100))
        slider_box.addWidget(btn_max)
        layout.addLayout(slider_box)

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

        # 1. Timer Resolution (0.5ms)
        self.btn_timer = QPushButton(" Timer 0.5ms")
        self.btn_timer.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_TIMER, "#38BDF8"), 13)))
        self.btn_timer.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
        self.btn_timer.setToolTip("Reduz a latência de eventos do Windows de 15.6ms para 0.5ms (menos input lag)")
        self.btn_timer.clicked.connect(self._on_toggle_timer)
        grid.addWidget(self.btn_timer, 0, 0)

        # 2. Game Focus (Prioridade Alta)
        self.btn_game = QPushButton(" Game Focus")
        self.btn_game.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_GAME, "#38BDF8"), 13)))
        self.btn_game.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
        self.btn_game.setToolTip("Prioriza o jogo ativo em foco na CPU do Core i7")
        self.btn_game.clicked.connect(self._on_toggle_game_focus)
        grid.addWidget(self.btn_game, 0, 1)

        # 3. Limpeza SSD
        self.btn_disk = QPushButton(" Limpar SSD")
        self.btn_disk.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_CLEAN_DISK, "#38BDF8"), 13)))
        self.btn_disk.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
        self.btn_disk.setToolTip("Purga arquivos temporários residuais sem tocar em dados úteis")
        self.btn_disk.clicked.connect(self._on_clean_disk)
        grid.addWidget(self.btn_disk, 1, 0)

        # 4. Flush DNS
        self.btn_dns = QPushButton(" Flush DNS")
        self.btn_dns.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_NETWORK, "#38BDF8"), 13)))
        self.btn_dns.setStyleSheet("background: #0B0F19; border: 1px solid #1E293B; color: #94A3B8; padding: 6px;")
        self.btn_dns.setToolTip("Renova cache de rotas DNS e reduz latência de rede")
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

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
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

        self.lbl_health_score = QLabel("SSD + HDD 100% OK")
        self.lbl_health_score.setStyleSheet("font-size: 10px; font-weight: 700; color: #10B981; font-family: 'Consolas', monospace;")
        row2.addWidget(self.lbl_health_score)
        layout.addLayout(row2)

        return card

    # ==========================================
    # GADGETS DA GAVETA LATERAL
    # ==========================================
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

        # Carga GPU
        row1 = QHBoxLayout()
        lbl_l = QLabel("Carga da GPU:")
        lbl_l.setStyleSheet("font-size: 10px; color: #94A3B8;")
        self.lbl_gpu_load_val = QLabel("0% • 45°C")
        self.lbl_gpu_load_val.setStyleSheet("font-size: 10px; font-weight: 700; color: #F59E0B; font-family: Consolas;")
        row1.addWidget(lbl_l)
        row1.addStretch()
        row1.addWidget(self.lbl_gpu_load_val)
        lay.addLayout(row1)

        self.bar_gpu_load = QProgressBar()
        self.bar_gpu_load.setTextVisible(False)
        self.bar_gpu_load.setFixedHeight(3)
        self.bar_gpu_load.setStyleSheet("QProgressBar { background: #161F30; border: none; border-radius: 1px; } QProgressBar::chunk { background: #F59E0B; }")
        lay.addWidget(self.bar_gpu_load)

        # VRAM
        row2 = QHBoxLayout()
        lbl_v = QLabel("Memória de Vídeo (VRAM):")
        lbl_v.setStyleSheet("font-size: 10px; color: #94A3B8;")
        self.lbl_gpu_vram = QLabel("0 / 1024 MB")
        self.lbl_gpu_vram.setStyleSheet("font-size: 10px; font-weight: 700; color: #F43F5E; font-family: Consolas;")
        row2.addWidget(lbl_v)
        row2.addStretch()
        row2.addWidget(self.lbl_gpu_vram)
        lay.addLayout(row2)

        self.bar_gpu_vram = QProgressBar()
        self.bar_gpu_vram.setTextVisible(False)
        self.bar_gpu_vram.setFixedHeight(3)
        self.bar_gpu_vram.setStyleSheet("QProgressBar { background: #161F30; border: none; border-radius: 1px; } QProgressBar::chunk { background: #F43F5E; }")
        lay.addWidget(self.bar_gpu_vram)

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

    def _toggle_side_wing(self):
        self.wing_expanded = not self.wing_expanded
        self._apply_wing_state(reposition=True)
        self._save_config()

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

    def _update_telemetry(self):
        # 1. CPU & Temperatura
        metrics = self.hw_monitor.get_metrics()
        self.lbl_clock.setText(f"{metrics['clock_ghz']:.2f} GHz")
        self.bar_cpu.setValue(metrics['cpu_percent'])

        self.lbl_temp.setText(f"{metrics['temp_c']}°C")
        self.lbl_temp.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {metrics['temp_color']}; font-family: 'Consolas', monospace;")
        self.bar_temp.setValue(metrics['temp_c'])
        self.bar_temp.setStyleSheet(f"QProgressBar {{ background: #161F30; border: none; border-radius: 1px; }} QProgressBar::chunk {{ background: {metrics['temp_color']}; }}")

        self.lbl_fan_info.setText(f"{metrics['fan_speed_percent']}% • {metrics['fan_rpm']:,} RPM".replace(",", "."))

        if hasattr(self, 'sparkline_cpu'):
            self.sparkline_cpu.add_point(metrics['cpu_percent'], metrics['temp_c'])

        # 2. Memória RAM
        mem = psutil.virtual_memory()
        ram_used_pct = mem.percent
        ram_free_gb = mem.available / (1024 ** 3)
        if hasattr(self, 'sparkline_ram'):
            self.sparkline_ram.add_point(ram_used_pct, ram_free_gb)

        # 3. Placa de Vídeo (GPU)
        gpu_info = self.gpu_monitor.get_gpu_info()
        if hasattr(self, 'sparkline_gpu'):
            self.sparkline_gpu.add_point(gpu_info['gpu_percent'], gpu_info['vram_percent'])

        if hasattr(self, 'lbl_gpu_name'):
            self.lbl_gpu_name.setText(gpu_info['name'])
            self.lbl_gpu_load_val.setText(f"{gpu_info['gpu_percent']}% • {gpu_info['temp_c']}°C")
            self.bar_gpu_load.setValue(gpu_info['gpu_percent'])
            self.lbl_gpu_vram.setText(f"{gpu_info['vram_used_mb']} / {gpu_info['vram_total_mb']} MB ({gpu_info['vram_percent']}%)")
            self.bar_gpu_vram.setValue(gpu_info['vram_percent'])

        # 4. Sincronização de Jogos e FPS (Anti-Cheat Safe)
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

        # 5. Monitoramento dinâmico do Game Focus
        if hasattr(self, 'game_focus') and self.game_focus.is_active:
            boosted = self.game_focus.check_and_boost_active()
            if boosted:
                name = boosted.get("name", "Jogo")
                self.btn_game.setText(f" Focus: {name[:7]}")

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

    def _on_fan_slider_changed(self, val: int):
        self.hw_monitor.set_fan_speed(val)
        self._update_telemetry()

    def _on_clean_ram(self):
        res = self.mem_mgr.clean_ram()
        freed = res.get("freed_mb", 0)
        self.btn_ram.setText(f" +{freed} MB!")
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
        self.btn_disk.setText(f" -{freed} MB!")
        QTimer.singleShot(2500, lambda: self.btn_disk.setText(" Limpar SSD"))

    def _on_flush_dns(self):
        res = self.net_opt.flush_dns()
        lat = res.get("latency_ms", 0)
        self.btn_dns.setText(f" {lat}ms OK")
        QTimer.singleShot(2000, lambda: self.btn_dns.setText(" Flush DNS"))

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
                    self.is_pinned = cfg.get("pinned", False)
                    self.opacity = cfg.get("opacity", 100)
                    self.wing_expanded = cfg.get("wing_expanded", False)
                    self.graph_location = cfg.get("graph_location", "hub")
                    self.show_cpu_graph = cfg.get("show_cpu_graph", True)
                    self.show_ram_graph = cfg.get("show_ram_graph", False)
                    self.show_gpu_graph = cfg.get("show_gpu_graph", False)
                    if "x" in cfg and "y" in cfg:
                        self.custom_pos = QPoint(cfg["x"], cfg["y"])
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
                clamped_x = max(geo.left(), min(self.custom_pos.x(), geo.right() - curr_w))
                clamped_y = max(geo.top(), min(self.custom_pos.y(), geo.bottom() - curr_h))
                self.move(clamped_x, clamped_y)
                return
        self.reset_to_tray_position()

    def reset_to_tray_position(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        curr_width = 770 if getattr(self, "wing_expanded", False) else 385
        x = geo.right() - curr_width - 12
        y = geo.bottom() - self.height() - 12
        self.move(x, y)
        self.custom_pos = None
        self._save_config()

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

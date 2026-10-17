"""
Interface Gráfica do Flyout Flutuante (Full Night Mode)
Totalmente sem emojis. Utiliza ícones vetoriais SVG, tipografia tabular e paleta True Dark.
Posiciona-se com precisão na bandeja do sistema ou em qualquer canto livremente arrastável pelo usuário.
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
from typing import Dict, Any

from src.core.power_manager import PowerManager, SCHEMES
from src.core.memory_manager import MemoryManager
from src.core.process_suspender import ProcessSuspender
from src.core.network_optimizer import NetworkOptimizer
from src.core.health_checker import HealthChecker
from src.core.hardware_monitor import HardwareMonitor
from src.core.timer_resolution import TimerResolutionManager
from src.core.disk_cleaner import DiskCleaner
from src.core.game_focus import GameFocusManager
from src.ui.sparkline_widget import SparklineWidget
from src.assets.icons import (
    get_svg, ICON_BOLT, ICON_CPU, ICON_THERMOMETER, ICON_FAN,
    ICON_MEMORY, ICON_PAUSE, ICON_PLAY, ICON_SHIELD, ICON_NETWORK,
    ICON_PIN, ICON_PIN_ACTIVE, ICON_DRAG,
    ICON_TIMER, ICON_CLEAN_DISK, ICON_GAME, ICON_EYE
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
        self.setFixedWidth(385)

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

        # Config e Persistência de Posição
        self.config_path = os.path.join(os.path.expanduser("~"), ".pctrayhub_config.json")
        self.is_pinned = False
        self.custom_pos = None
        self.opacity = 100
        self._load_config()

        self._build_ui()

        # Aplica opacidade carregada
        self.setWindowOpacity(self.opacity / 100.0)

        # Timer de Telemetria (atualiza a cada 1.5s suavemente)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._update_telemetry)
        self.telemetry_timer.start(1500)

        self._update_telemetry()
        self._update_power_pills()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # TOPO: Cabeçalho com Ícone SVG de Raio, Arrasto e Fixar
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

        # Indicador visual de arrasto
        drag_lbl = QLabel()
        drag_lbl.setPixmap(create_svg_pixmap(get_svg(ICON_DRAG, "#64748B"), 14))
        drag_lbl.setToolTip("Arraste a janela por qualquer área para qualquer canto da tela")
        drag_lbl.setCursor(Qt.CursorShape.SizeAllCursor)
        header.addWidget(drag_lbl)

        # Botão de Fixar na Tela (Alfinete / Modo HUD)
        self.btn_pin = QPushButton()
        self.btn_pin.setFixedSize(28, 28)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.clicked.connect(self._toggle_pin)
        header.addWidget(self.btn_pin)
        self._update_pin_button()

        idle_badge = QLabel("IDLE")
        idle_badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #38BDF8; background: #0C121D; border: 1px solid #1E293B; padding: 2px 7px; border-radius: 10px;")
        header.addWidget(idle_badge)
        main_layout.addLayout(header)

        # GADGET 1: SELETOR DE PERFIS
        main_layout.addWidget(self._build_power_gadget())

        # GADGET 2: TELEMETRIA (CLOCK & TEMPERATURA)
        main_layout.addWidget(self._build_telemetry_gadget())

        # GADGET 3: GRÁFICO SPARKLINE VETORIAL (ÚLTIMOS 30s)
        self.sparkline = SparklineWidget(self)
        main_layout.addWidget(self.sparkline)

        # GADGET 4: CONTROLE DE VENTOINHA
        main_layout.addWidget(self._build_fan_gadget())

        # GADGET 5: BOTÕES RÁPIDOS (LIMPAR RAM & PAUSAR LAUNCHERS)
        main_layout.addLayout(self._build_quick_actions())

        # GADGET 6: GRID DE OTIMIZAÇÕES AVANÇADAS (TIMER, GAME FOCUS, DISCO, DNS)
        main_layout.addLayout(self._build_optimizations_grid())

        # GADGET 7: CONTROLES DO HUD (OPACIDADE & SAÚDE S.M.A.R.T.)
        main_layout.addWidget(self._build_hud_controls())

        # RODAPÉ: ATALHOS GLOBAIS E CONTROLES DE JANELA
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
        main_layout.addLayout(footer)

    def _build_power_gadget(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "GadgetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

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
        c_lay.setContentsMargins(8, 8, 8, 8)
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
        t_lay.setContentsMargins(8, 8, 8, 8)
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
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

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

        # Botão Limpar RAM
        self.btn_ram = QPushButton(" Limpar RAM")
        self.btn_ram.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_MEMORY, "#38BDF8"), 14)))
        self.btn_ram.setStyleSheet("background: #0C1626; border: 1px solid #1E3A8A; color: #F8FAFC; padding: 7px;")
        self.btn_ram.clicked.connect(self._on_clean_ram)
        box.addWidget(self.btn_ram)

        # Botão Pausar Launchers
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

        # Linha de Opacidade
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

        # Linha de Saúde SMART
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

    def _update_telemetry(self):
        metrics = self.hw_monitor.get_metrics()
        self.lbl_clock.setText(f"{metrics['clock_ghz']:.2f} GHz")
        self.bar_cpu.setValue(metrics['cpu_percent'])

        self.lbl_temp.setText(f"{metrics['temp_c']}°C")
        self.lbl_temp.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {metrics['temp_color']}; font-family: 'Consolas', monospace;")
        self.bar_temp.setValue(metrics['temp_c'])
        self.bar_temp.setStyleSheet(f"QProgressBar {{ background: #161F30; border: none; border-radius: 1px; }} QProgressBar::chunk {{ background: {metrics['temp_color']}; }}")

        self.lbl_fan_info.setText(f"{metrics['fan_speed_percent']}% • {metrics['fan_rpm']:,} RPM".replace(",", "."))

        # Alimenta o gráfico Sparkline vetorial
        if hasattr(self, 'sparkline'):
            self.sparkline.add_point(metrics['cpu_percent'], metrics['temp_c'])

        # Monitoramento dinâmico em segundo plano do Game Focus
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
                "y": self.pos().y()
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)
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
            self._save_config()
            event.accept()

    def _is_pos_visible(self, pos: QPoint) -> bool:
        """Verifica se a posição salva ainda está dentro de alguma tela conectada."""
        for screen in QApplication.screens():
            if screen.geometry().contains(pos):
                return True
        return False

    def position_above_tray(self):
        """Se o usuário moveu a janela e ela ainda está visível, restaura; senão alinha no canto inferior direito."""
        if self.custom_pos and self._is_pos_visible(self.custom_pos):
            self.move(self.custom_pos)
            return
        self.reset_to_tray_position()

    def reset_to_tray_position(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.right() - self.width() - 12
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

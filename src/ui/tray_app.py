"""
Aplicação Principal da Bandeja do Sistema (TrayApp)
Gerencia o ícone dinâmico na System Tray ao lado do relógio,
o menu de contexto rápido no botão direito, o flyout flutuante no clique esquerdo
e os atalhos globais de teclado em segundo plano.
"""

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

import sys
import os

from src.ui.flyout_window import FlyoutWindow
from src.ui.hotkey_worker import HotkeyWorker
from src.core.power_manager import PowerManager
from src.core.memory_manager import MemoryManager
from src.core.hardware_monitor import HardwareMonitor

class PerformanceTrayApp:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Componentes
        self.power_mgr = PowerManager()
        self.mem_mgr = MemoryManager()
        self.hw_monitor = HardwareMonitor()

        # Janela Flyout
        self.flyout = FlyoutWindow()

        # Informações de Hardware Dinâmicas
        self.hw_info = HardwareMonitor.get_hardware_info()

        # Ícone da Bandeja
        self.tray = QSystemTrayIcon()
        self.tray.setToolTip(f"Performance Tray Hub • {self.hw_info['cpu']}")
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.messageClicked.connect(self.flyout.show_or_toggle)

        # Menu de Contexto do Botão Direito
        self._build_context_menu()

        # Atalhos Globais
        self.hotkey_worker = HotkeyWorker()
        self.hotkey_worker.hotkey_ram_triggered.connect(self._on_hotkey_ram)
        self.hotkey_worker.hotkey_turbo_triggered.connect(self._on_hotkey_turbo)
        self.hotkey_worker.start()

        # Atualização Periódica do Ícone da Bandeja (a cada 2.5s)
        self.icon_timer = QTimer()
        self.icon_timer.timeout.connect(self._update_tray_icon)
        self.icon_timer.start(2500)

        self._update_tray_icon()
        self.tray.show()

        # Notificação de boas-vindas para evidenciar o ícone na bandeja
        cpu_name = self.hw_info['cpu']
        QTimer.singleShot(800, lambda: self.tray.showMessage(
            "PC Performance Hub Ativo",
            f"Monitorando {cpu_name}. Clique aqui para abrir o painel ou use Ctrl+Shift+F12.",
            QSystemTrayIcon.MessageIcon.Information,
            3500
        ))

    def _generate_tray_pixmap(self, temp_c: int) -> QPixmap:
        """Desenha dinamicamente um ícone vetorial de 32x32 com o raio e os graus."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fundo arredondado escuro
        painter.setBrush(QColor("#080C14"))
        painter.setPen(QColor("#1E3A8A"))
        painter.drawRoundedRect(1, 1, 30, 30, 6, 6)

        # Raiozinho em ciano à esquerda
        painter.setBrush(QColor("#38BDF8"))
        painter.setPen(Qt.PenStyle.NoPen)
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint, QRect
        bolt_points = QPolygon([
            QPoint(10, 5), QPoint(4, 16), QPoint(9, 16),
            QPoint(8, 27), QPoint(15, 13), QPoint(10, 13)
        ])
        painter.drawPolygon(bolt_points)

        # Texto da temperatura
        painter.setPen(QColor("#F8FAFC"))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(13, 0, 18, 32), Qt.AlignmentFlag.AlignCenter, f"{temp_c}")

        painter.end()
        return pixmap

    def _update_tray_icon(self):
        metrics = self.hw_monitor.get_metrics()
        temp = metrics["temp_c"]
        pixmap = self._generate_tray_pixmap(temp)
        self.tray.setIcon(QIcon(pixmap))
        self.tray.setToolTip(f"Performance Hub: {metrics['clock_ghz']:.2f} GHz • {temp}°C • {metrics['temp_status']}")

    def _build_context_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #080C14;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 6px;
                color: #CBD5E1;
                font-family: 'Segoe UI', system-ui;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #162238;
                color: #38BDF8;
            }
            QMenu::separator {
                height: 1px;
                background: #1E293B;
                margin: 4px 0px;
            }
        """)

        act_turbo = menu.addAction("Turbo Max (Desempenho)")
        act_turbo.triggered.connect(lambda: self.flyout._set_scheme("turbo"))

        act_balanced = menu.addAction("Equilibrado")
        act_balanced.triggered.connect(lambda: self.flyout._set_scheme("balanced"))

        act_silent = menu.addAction("Silencioso (Eco)")
        act_silent.triggered.connect(lambda: self.flyout._set_scheme("silent"))

        menu.addSeparator()

        act_ram = menu.addAction("Limpar Memoria RAM")
        act_ram.triggered.connect(self._on_hotkey_ram)

        act_launchers = menu.addAction("Pausar / Retomar Launchers")
        act_launchers.triggered.connect(self.flyout._on_toggle_suspend)

        act_timer = menu.addAction("Alternar Timer 0.5ms (Baixa Latência)")
        act_timer.triggered.connect(self.flyout._on_toggle_timer)

        act_disk = menu.addAction("Limpeza Rápida de SSD")
        act_disk.triggered.connect(self.flyout._on_clean_disk)

        menu.addSeparator()

        act_open = menu.addAction("Abrir Painel")
        act_open.triggered.connect(self.flyout.show_or_toggle)

        act_quit = menu.addAction("Sair")
        act_quit.triggered.connect(self._quit)

        self.tray.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        # Clique com botão esquerdo ou duplo clique abre o flyout
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.flyout.show_or_toggle()

    def _on_hotkey_ram(self):
        res = self.mem_mgr.clean_ram()
        freed = res.get("freed_mb", 0)
        self.tray.showMessage(
            "Memória Otimizada",
            f"Foram liberados {freed} MB de memória RAM.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        self.flyout._update_telemetry()

    def _on_hotkey_turbo(self):
        self.flyout._set_scheme("turbo")
        self.tray.showMessage(
            "Modo Turbo Ativado",
            "Clock e energia configurados para Desempenho Máximo.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _quit(self):
        # 1. Retoma launchers suspensos se houver algum congelado
        try:
            if hasattr(self.flyout, 'proc_suspender') and self.flyout.proc_suspender.is_any_suspended:
                self.flyout.proc_suspender.resume_all()
        except Exception:
            pass

        # 2. Restaura resolução padrão do timer do Windows
        try:
            if hasattr(self.flyout, 'timer_mgr') and self.flyout.timer_mgr.is_active:
                self.flyout.timer_mgr.set_low_latency(False)
        except Exception:
            pass

        # 3. Restaura prioridade do processo se Game Focus estava ativo
        try:
            if hasattr(self.flyout, 'game_focus') and self.flyout.game_focus.is_active:
                self.flyout.game_focus.toggle()
        except Exception:
            pass

        self.hotkey_worker.stop()
        self.tray.hide()
        self.app.quit()

    def run(self):
        return self.app.exec()

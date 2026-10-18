from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtNetwork import QLocalServer

import sys
import os

from src.ui.flyout_window import FlyoutWindow, create_svg_pixmap
from src.assets.icons import (
    get_svg, ICON_BOLT, ICON_MEMORY, ICON_PAUSE, ICON_TIMER,
    ICON_CLEAN_DISK, ICON_SETTINGS, ICON_SHIELD, ICON_UPDATE
)
from src.ui.hotkey_worker import HotkeyWorker
from src.core.power_manager import PowerManager
from src.core.memory_manager import MemoryManager
from src.core.hardware_monitor import HardwareMonitor

class PerformanceTrayApp:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.aboutToQuit.connect(self._quit)

        self.power_mgr = PowerManager()
        self.mem_mgr = MemoryManager()
        self.hw_monitor = HardwareMonitor()

        self.flyout = FlyoutWindow()
        self.flyout.tray_app = self

        self.hw_info = HardwareMonitor.get_hardware_info()

        self.tray = QSystemTrayIcon()
        self.tray.setToolTip(f"Performance Tray Hub • {self.hw_info['cpu']}")
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.messageClicked.connect(self.flyout.show_or_toggle)
        self.flyout.update_available.connect(self._on_update_available)

        self._build_context_menu()

        self.ipc_server = QLocalServer()
        self.ipc_server.removeServer("PCPerformanceTrayHub_IpcServer")
        self.ipc_server.listen("PCPerformanceTrayHub_IpcServer")
        self.ipc_server.newConnection.connect(self._handle_ipc_connection)

        self.hotkey_worker = HotkeyWorker()
        self.hotkey_worker.hotkey_ram_triggered.connect(self._on_hotkey_ram)
        self.hotkey_worker.hotkey_turbo_triggered.connect(self._on_hotkey_turbo)
        self.hotkey_worker.start()

        self.icon_timer = QTimer()
        self.icon_timer.timeout.connect(self._update_tray_icon)
        self.icon_timer.start(2500)

        self._update_tray_icon()
        self.tray.show()

        cpu_name = self.hw_info['cpu']
        if "--updated" in sys.argv:
            msg_title = "PC Performance Hub Atualizado"
            msg_body = f"Aplicativo atualizado com sucesso! Monitorando {cpu_name}."
        else:
            msg_title = "PC Performance Hub Ativo"
            msg_body = f"Monitorando {cpu_name}. Clique aqui para abrir o painel ou use Ctrl+Shift+F12."

        QTimer.singleShot(800, lambda: self.tray.showMessage(
            msg_title,
            msg_body,
            QSystemTrayIcon.MessageIcon.Information,
            3500
        ))

    def _generate_tray_pixmap(self, temp_c: int) -> QPixmap:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QColor("#080C14"))
        painter.setPen(QColor("#1E3A8A"))
        painter.drawRoundedRect(1, 1, 30, 30, 6, 6)

        painter.setBrush(QColor("#38BDF8"))
        painter.setPen(Qt.PenStyle.NoPen)
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint, QRect
        bolt_points = QPolygon([
            QPoint(10, 5), QPoint(4, 16), QPoint(9, 16),
            QPoint(8, 27), QPoint(15, 13), QPoint(10, 13)
        ])
        painter.drawPolygon(bolt_points)

        painter.setPen(QColor("#F8FAFC"))
        font_size = 7 if temp_c >= 100 else 9
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = QRect(11, 0, 20, 32) if temp_c >= 100 else QRect(13, 0, 18, 32)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"{temp_c}")

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
        act_turbo.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_BOLT, "#38BDF8"), 14)))
        act_turbo.triggered.connect(lambda: self.flyout._set_scheme("turbo"))

        act_balanced = menu.addAction("Equilibrado")
        act_balanced.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_SETTINGS, "#94A3B8"), 14)))
        act_balanced.triggered.connect(lambda: self.flyout._set_scheme("balanced"))

        act_silent = menu.addAction("Silencioso (Eco)")
        act_silent.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_SHIELD, "#10B981"), 14)))
        act_silent.triggered.connect(lambda: self.flyout._set_scheme("silent"))

        menu.addSeparator()

        act_ram = menu.addAction("Limpar Memória RAM")
        act_ram.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_MEMORY, "#38BDF8"), 14)))
        act_ram.triggered.connect(self._on_hotkey_ram)

        act_launchers = menu.addAction("Pausar / Retomar Launchers")
        act_launchers.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_PAUSE, "#F59E0B"), 14)))
        act_launchers.triggered.connect(self.flyout._on_toggle_suspend)

        act_timer = menu.addAction("Alternar Timer 0.5ms (Baixa Latência)")
        act_timer.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_TIMER, "#38BDF8"), 14)))
        act_timer.triggered.connect(self.flyout._on_toggle_timer)

        act_disk = menu.addAction("Limpeza Rápida de SSD")
        act_disk.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_CLEAN_DISK, "#38BDF8"), 14)))
        act_disk.triggered.connect(self.flyout._on_clean_disk)

        menu.addSeparator()

        act_diag = menu.addAction("Copiar Diagnóstico da Máquina")
        act_diag.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_SETTINGS, "#38BDF8"), 14)))
        act_diag.triggered.connect(self.flyout._copy_diagnostic_report)

        act_update = menu.addAction("Verificar Atualizações")
        act_update.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_UPDATE, "#38BDF8"), 14)))
        act_update.triggered.connect(self._on_check_update_menu)

        act_open = menu.addAction("Abrir Painel")
        act_open.setIcon(QIcon(create_svg_pixmap(get_svg(ICON_BOLT, "#38BDF8"), 14)))
        act_open.triggered.connect(self.flyout.show_or_toggle)

        act_quit = menu.addAction("Sair")
        act_quit.triggered.connect(self._quit)

        self.tray.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.flyout.show_or_toggle()

    def _on_check_update_menu(self):
        if not self.flyout.wing_expanded:
            self.flyout._toggle_side_wing()
        self.flyout._check_for_updates()
        if not self.flyout.isVisible():
            self.flyout.show_or_toggle()

    def _on_update_available(self, info: dict):
        latest = info.get("latest_version", "")
        self.tray.showMessage(
            "Atualização Disponível",
            f"Nova versão v{latest} do PC Performance Hub já está disponível no GitHub.",
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )

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

    def _handle_ipc_connection(self):
        while self.ipc_server.hasPendingConnections():
            client = self.ipc_server.nextPendingConnection()
            if client:
                if client.bytesAvailable() > 0:
                    self._on_ipc_message(client)
                else:
                    client.readyRead.connect(lambda cl=client: self._on_ipc_message(cl))

    def _on_ipc_message(self, client):
        try:
            msg = bytes(client.readAll()).decode("utf-8", errors="ignore").strip()
            if msg == "show":
                if not self.flyout.isVisible():
                    self.flyout.show_or_toggle()
                else:
                    self.flyout.activateWindow()
                    self.flyout.raise_()
        except Exception:
            pass
        finally:
            try:
                client.disconnectFromServer()
                client.deleteLater()
            except Exception:
                pass

    def _quit(self):
        if getattr(self, "_is_quitting", False):
            return
        self._is_quitting = True
        try:
            if hasattr(self, 'ipc_server'):
                self.ipc_server.close()
                self.ipc_server.removeServer("PCPerformanceTrayHub_IpcServer")
        except Exception:
            pass

        try:
            if hasattr(self.flyout, 'proc_suspender') and self.flyout.proc_suspender.is_any_suspended:
                self.flyout.proc_suspender.resume_all()
        except Exception:
            pass

        try:
            if hasattr(self.flyout, 'timer_mgr') and self.flyout.timer_mgr.is_active:
                self.flyout.timer_mgr.set_low_latency(False)
        except Exception:
            pass

        try:
            if hasattr(self.flyout, 'game_focus') and self.flyout.game_focus.is_active:
                self.flyout.game_focus.toggle()
        except Exception:
            pass

        try:
            self.icon_timer.stop()
        except Exception:
            pass

        try:
            if hasattr(self.flyout, 'telemetry_timer'):
                self.flyout.telemetry_timer.stop()
        except Exception:
            pass

        self.hotkey_worker.stop()
        self.tray.hide()
        self.app.quit()

    def run(self):
        return self.app.exec()

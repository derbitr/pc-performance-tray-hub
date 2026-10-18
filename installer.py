import sys
import os
import time
import shutil
import subprocess
import winreg
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFileDialog, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtSvg import QSvgRenderer

DARK_INSTALLER_STYLE = """
QWidget#InstallerRoot {
    background-color: #07090E;
    border: 1px solid #1E293B;
    border-radius: 12px;
}
QLabel {
    color: #F1F5F9;
    font-family: 'Segoe UI', system-ui, sans-serif;
}
QPushButton {
    background-color: #0E1626;
    border: 1px solid #1E293B;
    border-radius: 6px;
    color: #94A3B8;
    font-size: 11px;
    font-weight: 600;
    padding: 7px 14px;
}
QPushButton:hover {
    background-color: #162238;
    border-color: #38BDF8;
    color: #F8FAFC;
}
QPushButton#PrimaryBtn {
    background-color: #1E3A8A;
    border: 1px solid #38BDF8;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 12px;
    padding: 9px 18px;
}
QPushButton#PrimaryBtn:hover {
    background-color: #2563EB;
}
QProgressBar {
    background: #0B0F19;
    border: 1px solid #161F30;
    border-radius: 4px;
    text-align: center;
    color: #94A3B8;
    font-size: 10px;
}
QProgressBar::chunk {
    background: #38BDF8;
    border-radius: 3px;
}
QCheckBox {
    color: #94A3B8;
    font-size: 11px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #1E293B;
    background: #0B0F19;
}
QCheckBox::indicator:checked {
    background: #38BDF8;
    border-color: #38BDF8;
}
QFrame.Card {
    background-color: #0B0F19;
    border: 1px solid #161F30;
    border-radius: 8px;
    padding: 10px;
}
"""

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def get_bundle_dir() -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def create_windows_shortcut(target_exe: str, lnk_path: str, work_dir: str, icon_path: str):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    created = False
    try:
        import tempfile
        vbs_path = os.path.join(tempfile.gettempdir(), "_create_hub_lnk.vbs")
        t_vbs = target_exe.replace('"', '""')
        l_vbs = lnk_path.replace('"', '""')
        w_vbs = work_dir.replace('"', '""')
        i_vbs = icon_path.replace('"', '""')
        vbs_code = (
            'Set ws = CreateObject("WScript.Shell")\r\n'
            f'Set s = ws.CreateShortcut("{l_vbs}")\r\n'
            f's.TargetPath = "{t_vbs}"\r\n'
            f's.WorkingDirectory = "{w_vbs}"\r\n'
            f's.IconLocation = "{i_vbs},0"\r\n'
            's.Save\r\n'
        )
        with open(vbs_path, "w", encoding="ansi") as f:
            f.write(vbs_code)
        r = subprocess.run(["cscript", "//nologo", vbs_path], capture_output=True, timeout=2.0, creationflags=flags)
        created = (r.returncode == 0)
        try:
            os.remove(vbs_path)
        except Exception:
            pass
    except Exception:
        pass

    if not created:
        try:
            lnk_esc = lnk_path.replace("'", "''")
            target_esc = target_exe.replace("'", "''")
            work_esc = work_dir.replace("'", "''")
            icon_esc = icon_path.replace("'", "''")
            script = (
                f"$ws = New-Object -ComObject WScript.Shell; "
                f"$s = $ws.CreateShortcut('{lnk_esc}'); "
                f"$s.TargetPath = '{target_esc}'; "
                f"$s.WorkingDirectory = '{work_esc}'; "
                f"$s.IconLocation = '{icon_esc},0'; "
                f"$s.Save()"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=flags
            )
        except Exception:
            pass

class InstallWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    install_finished = pyqtSignal(bool, str)

    def __init__(self, target_dir: str, autostart: bool, desktop_lnk: bool, startmenu_lnk: bool):
        super().__init__()
        self.target_dir = target_dir
        self.autostart = autostart
        self.desktop_lnk = desktop_lnk
        self.startmenu_lnk = startmenu_lnk

    def run(self):
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        try:
            self.progress_changed.emit(10, "Fechando instâncias ativas do aplicativo...")
            try:
                import psutil
                for proc in psutil.process_iter(['name']):
                    try:
                        if proc.info['name'] and 'PCTrayHub.exe' in proc.info['name']:
                            proc.kill()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                subprocess.run(
                    ["taskkill", "/f", "/im", "PCTrayHub.exe"],
                    capture_output=True,
                    timeout=2.0,
                    creationflags=flags
                )
            except Exception:
                pass
            time.sleep(0.4)

            self.progress_changed.emit(25, "Criando diretório de instalação...")
            os.makedirs(self.target_dir, exist_ok=True)

            bundle_dir = get_bundle_dir()
            source_exe = os.path.join(bundle_dir, "PCTrayHub.exe")
            if not os.path.exists(source_exe):
                source_exe = os.path.join(bundle_dir, "dist", "PCTrayHub.exe")

            source_icon = os.path.join(bundle_dir, "app_icon.ico")

            dest_exe = os.path.join(self.target_dir, "PCTrayHub.exe")
            dest_icon = os.path.join(self.target_dir, "app_icon.ico")

            self.progress_changed.emit(45, "Copiando executável standalone...")
            if not os.path.exists(source_exe):
                raise FileNotFoundError("Arquivo PCTrayHub.exe não encontrado no pacote de instalação.")

            copied = False
            for attempt in range(5):
                try:
                    shutil.copy2(source_exe, dest_exe)
                    copied = True
                    break
                except PermissionError:
                    try:
                        old_file = dest_exe + f".old_{attempt}"
                        if os.path.exists(old_file):
                            try:
                                os.remove(old_file)
                            except Exception:
                                pass
                        os.replace(dest_exe, old_file)
                        shutil.copy2(source_exe, dest_exe)
                        copied = True
                        break
                    except Exception:
                        time.sleep(0.4)

            if not copied:
                shutil.copy2(source_exe, dest_exe)

            if os.path.exists(source_icon):
                shutil.copy2(source_icon, dest_icon)
            else:
                dest_icon = dest_exe

            self.progress_changed.emit(65, "Criando atalhos no Windows...")
            if self.desktop_lnk:
                desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
                if os.path.exists(desktop):
                    lnk = os.path.join(desktop, "PC Performance Tray Hub.lnk")
                    create_windows_shortcut(dest_exe, lnk, self.target_dir, dest_icon)

            if self.startmenu_lnk:
                start_menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
                if os.path.exists(start_menu):
                    lnk = os.path.join(start_menu, "PC Performance Tray Hub.lnk")
                    create_windows_shortcut(dest_exe, lnk, self.target_dir, dest_icon)

            self.progress_changed.emit(80, "Configurando inicialização elevada no agendador...")
            if self.autostart:
                cmd = [
                    "schtasks", "/create",
                    "/tn", "PCPerformanceTrayHub",
                    "/tr", f'"{dest_exe}"',
                    "/sc", "onlogon",
                    "/rl", "highest",
                    "/f"
                ]
                try:
                    res_task = subprocess.run(cmd, capture_output=True, timeout=3.0, creationflags=flags)
                    if res_task.returncode != 0:
                        cmd_fallback = [
                            "schtasks", "/create",
                            "/tn", "PCPerformanceTrayHub",
                            "/tr", f'"{dest_exe}"',
                            "/sc", "onlogon",
                            "/f"
                        ]
                        subprocess.run(cmd_fallback, capture_output=True, timeout=3.0, creationflags=flags)
                except Exception:
                    pass

            self.progress_changed.emit(90, "Registrando desinstalador no Painel de Controle...")
            uninstaller_bat = os.path.join(self.target_dir, "uninstall.bat")
            with open(uninstaller_bat, "w", encoding="utf-8") as f:
                f.write(
                    "@echo off\r\n"
                    "taskkill /f /im PCTrayHub.exe >nul 2>&1\r\n"
                    "schtasks /delete /tn PCPerformanceTrayHub /f >nul 2>&1\r\n"
                    f'del "%USERPROFILE%\\Desktop\\PC Performance Tray Hub.lnk" >nul 2>&1\r\n'
                    f'del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\PC Performance Tray Hub.lnk" >nul 2>&1\r\n'
                    f'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PCPerformanceTrayHub" /f >nul 2>&1\r\n'
                    f'timeout /t 1 >nul\r\n'
                    f'rmdir /s /q "{self.target_dir}" >nul 2>&1\r\n'
                    "exit\r\n"
                )

            try:
                reg_key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PCPerformanceTrayHub"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_key) as k:
                    winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "PC Performance Tray Hub")
                    winreg.SetValueEx(k, "DisplayIcon", 0, winreg.REG_SZ, dest_exe)
                    winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, "1.0.4")
                    winreg.SetValueEx(k, "Publisher", 0, winreg.REG_SZ, "Performance Hub")
                    winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, self.target_dir)
                    winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_bat}"')
            except Exception:
                pass

            self.progress_changed.emit(95, "Iniciando aplicativo na bandeja do sistema...")
            started = False
            if self.autostart:
                try:
                    res = subprocess.run(["schtasks", "/run", "/tn", "PCPerformanceTrayHub"], capture_output=True, timeout=3.0, creationflags=flags)
                    if res.returncode == 0:
                        started = True
                except Exception:
                    pass
            if not started:
                subprocess.Popen([dest_exe], cwd=self.target_dir, creationflags=flags)

            self.progress_changed.emit(100, "Instalação concluída com sucesso!")
            self.install_finished.emit(True, dest_exe)
        except Exception as e:
            self.install_finished.emit(False, str(e))

class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("InstallerRoot")
        self.setFixedSize(500, 420)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(DARK_INSTALLER_STYLE)

        default_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", "C:\\"),
            "Programs",
            "PCPerformanceTrayHub"
        )
        self.selected_dir = default_dir
        self._build_ui()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#07090E"))
        painter.setPen(QColor("#1E293B"))
        painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 12, 12)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        logo_lbl = QLabel()
        logo_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>"""
        renderer = QSvgRenderer(logo_svg.encode('utf-8'))
        pix = QPixmap(24, 24)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        renderer.render(p)
        p.end()
        logo_lbl.setPixmap(pix)
        header.addWidget(logo_lbl)

        t_box = QVBoxLayout()
        t_box.setSpacing(1)
        title = QLabel("PC PERFORMANCE TRAY HUB")
        title.setStyleSheet("font-size: 13px; font-weight: 800; color: #F8FAFC; letter-spacing: 0.04em;")
        sub = QLabel("Assistente de Instalação Rápida e Silenciosa")
        sub.setStyleSheet("font-size: 10px; color: #64748B;")
        t_box.addWidget(title)
        t_box.addWidget(sub)
        header.addLayout(t_box)
        header.addStretch()

        btn_close = QPushButton("X")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet("background: transparent; border: none; color: #64748B; font-weight: 800; font-size: 12px;")
        btn_close.clicked.connect(self.close)
        header.addWidget(btn_close)
        root.addLayout(header)

        info_card = QFrame()
        info_card.setProperty("class", "Card")
        info_lay = QVBoxLayout(info_card)
        info_lay.setSpacing(4)
        lbl_desc = QLabel("O PC Performance Tray Hub será instalado para todos os recursos de telemetria em tempo real, redução de latência (0.5ms), limpeza de memória RAM e suspensão de launchers.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 10.5px; color: #CBD5E1; line-height: 1.4;")
        info_lay.addWidget(lbl_desc)
        root.addWidget(info_card)

        path_card = QFrame()
        path_card.setProperty("class", "Card")
        path_lay = QVBoxLayout(path_card)
        path_lay.setSpacing(6)

        lbl_dest = QLabel("Pasta de Instalação:")
        lbl_dest.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8;")
        path_lay.addWidget(lbl_dest)

        path_row = QHBoxLayout()
        self.lbl_path = QLabel(self.selected_dir)
        self.lbl_path.setStyleSheet("font-size: 10px; color: #38BDF8; font-family: Consolas; background: #07090E; border: 1px solid #1E293B; border-radius: 4px; padding: 6px;")
        path_row.addWidget(self.lbl_path, stretch=1)

        btn_browse = QPushButton("Alterar...")
        btn_browse.clicked.connect(self._browse_dir)
        path_row.addWidget(btn_browse)
        path_lay.addLayout(path_row)
        root.addWidget(path_card)

        opts_lay = QVBoxLayout()
        opts_lay.setSpacing(6)
        self.chk_autostart = QCheckBox("Iniciar automaticamente com o Windows (Sem aviso de UAC)")
        self.chk_autostart.setChecked(True)
        opts_lay.addWidget(self.chk_autostart)

        self.chk_desktop = QCheckBox("Criar atalho na Área de Trabalho")
        self.chk_desktop.setChecked(True)
        opts_lay.addWidget(self.chk_desktop)

        self.chk_startmenu = QCheckBox("Criar atalho no Menu Iniciar")
        self.chk_startmenu.setChecked(True)
        opts_lay.addWidget(self.chk_startmenu)
        root.addLayout(opts_lay)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Pronto para instalar.")
        self.lbl_status.setStyleSheet("font-size: 10px; color: #64748B;")
        root.addWidget(self.lbl_status)

        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.close)
        actions.addWidget(self.btn_cancel)

        self.btn_install = QPushButton("INSTALAR AGORA")
        self.btn_install.setObjectName("PrimaryBtn")
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install.clicked.connect(self._start_install)
        actions.addWidget(self.btn_install)
        root.addLayout(actions)

    def _browse_dir(self):
        dir_chosen = QFileDialog.getExistingDirectory(self, "Selecione o diretório de instalação", self.selected_dir)
        if dir_chosen:
            self.selected_dir = os.path.join(dir_chosen, "PCPerformanceTrayHub")
            self.lbl_path.setText(self.selected_dir)

    def _start_install(self):
        self.btn_install.setEnabled(False)
        self.btn_install.setText("Instalando...")
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = InstallWorker(
            self.selected_dir,
            self.chk_autostart.isChecked(),
            self.chk_desktop.isChecked(),
            self.chk_startmenu.isChecked()
        )
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.install_finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(msg)

    def _on_finished(self, success: bool, msg: str):
        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText("Instalação concluída com sucesso! Fechando instalador...")
            self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #10B981;")
            self.btn_install.setVisible(False)
            self.btn_cancel.setText("Concluir")
            self.btn_cancel.setEnabled(True)
            try:
                self.btn_cancel.clicked.disconnect()
            except Exception:
                pass
            self.btn_cancel.clicked.connect(self.close)
            QTimer.singleShot(1200, self.close)
        else:
            self.lbl_status.setText(f"Falha na instalação: {msg}")
            self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #F43F5E;")
            self.btn_install.setEnabled(True)
            self.btn_install.setText("INSTALAR AGORA")
            self.btn_cancel.setEnabled(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            del self._drag_pos
            event.accept()

def main():
    app = QApplication(sys.argv)
    window = InstallerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

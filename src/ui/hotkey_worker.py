"""
Módulo de Atalhos Globais de Teclado (HotkeyWorker)
Registra hotkeys globais no Windows via user32.dll (RegisterHotKey)
permitindo acionar as otimizações mesmo com jogos em tela cheia.
Encerramento limpo via PostThreadMessageW (sem deadlock).
"""

import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QThread, pyqtSignal

# Modificadores e Códigos de Tecla Win32
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000

VK_F12 = 0x7B  # F12 -> Limpar RAM
VK_F11 = 0x7A  # F11 -> Ativar Turbo

HOTKEY_RAM_ID = 101
HOTKEY_TURBO_ID = 102

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

class HotkeyWorker(QThread):
    hotkey_ram_triggered = pyqtSignal()
    hotkey_turbo_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self._running = True
        self.thread_id = 0

    def run(self):
        self.thread_id = self.kernel32.GetCurrentThreadId()

        # Registra Ctrl + Shift + F12
        self.user32.RegisterHotKey(
            None,
            HOTKEY_RAM_ID,
            MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT,
            VK_F12
        )
        # Registra Ctrl + Shift + F11
        self.user32.RegisterHotKey(
            None,
            HOTKEY_TURBO_ID,
            MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT,
            VK_F11
        )

        msg = wintypes.MSG()
        while self._running:
            ret = self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:  # 0 significa WM_QUIT, -1 significa erro
                break

            if msg.message == WM_HOTKEY:
                if msg.wParam == HOTKEY_RAM_ID:
                    self.hotkey_ram_triggered.emit()
                elif msg.wParam == HOTKEY_TURBO_ID:
                    self.hotkey_turbo_triggered.emit()

            self.user32.TranslateMessage(ctypes.byref(msg))
            self.user32.DispatchMessageW(ctypes.byref(msg))

        # Desregistra ao encerrar a thread
        try:
            self.user32.UnregisterHotKey(None, HOTKEY_RAM_ID)
            self.user32.UnregisterHotKey(None, HOTKEY_TURBO_ID)
        except Exception:
            pass

    def stop(self):
        self._running = False
        if self.thread_id:
            try:
                # Posta WM_QUIT especificamente na fila da worker thread (evita deadlock)
                self.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
        self.wait(500)

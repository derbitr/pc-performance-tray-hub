"""
Ponto de Entrada Principal: PC Performance Tray Hub
Inicia a aplicação na bandeja do sistema com garantia de instância única.
"""

import sys
import ctypes
from ctypes import wintypes
import os

# Adiciona diretório raiz ao sys.path (suporta PyInstaller frozen e desenvolvimento)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.tray_app import PerformanceTrayApp

MUTEX_NAME = "Global\\PCPerformanceTrayHub_SingleInstance_Mutex"
_mutex_handle = None

def ensure_single_instance() -> bool:
    global _mutex_handle
    kernel32 = ctypes.windll.kernel32
    _mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        return False
    return True

def main():
    if not ensure_single_instance():
        print("PC Performance Tray Hub ja esta em execucao na bandeja do sistema.")
        sys.exit(0)

    app = PerformanceTrayApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()

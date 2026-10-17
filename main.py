import sys
import ctypes
from ctypes import wintypes
import os

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
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    _mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        if _mutex_handle:
            kernel32.CloseHandle(_mutex_handle)
            _mutex_handle = None
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

import sys
import ctypes
from ctypes import wintypes
import os

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.tray_app import PerformanceTrayApp

MUTEX_NAME = "Local\\PCPerformanceTrayHub_SingleInstance_Mutex"
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
    ERROR_ACCESS_DENIED = 5
    if not _mutex_handle or last_error in (ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED):
        if _mutex_handle:
            kernel32.CloseHandle(_mutex_handle)
            _mutex_handle = None
        return False
    return True

def notify_running_instance():
    try:
        from PyQt6.QtCore import QCoreApplication
        from PyQt6.QtNetwork import QLocalSocket
        _app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        socket = QLocalSocket()
        socket.connectToServer("PCPerformanceTrayHub_IpcServer")
        if socket.waitForConnected(800):
            socket.write(b"show\n")
            socket.waitForBytesWritten(800)
            socket.disconnectFromServer()
    except Exception:
        pass

def cleanup_old_binaries():
    try:
        dirs_to_clean = []
        if getattr(sys, 'frozen', False):
            dirs_to_clean.append(os.path.dirname(os.path.abspath(sys.executable)))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
            dirs_to_clean.append(base)
            dirs_to_clean.append(os.path.join(base, "dist"))
        for d in dirs_to_clean:
            if os.path.exists(d):
                for f_name in os.listdir(d):
                    if f_name.startswith("PCTrayHub.exe.old") or f_name.endswith(".download") or f_name.endswith(".part"):
                        try:
                            os.remove(os.path.join(d, f_name))
                        except Exception:
                            pass
    except Exception:
        pass

def main():
    cleanup_old_binaries()
    if not ensure_single_instance():
        notify_running_instance()
        sys.exit(0)

    app = PerformanceTrayApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()

import ctypes
from ctypes import wintypes
import psutil
from typing import Dict, Any, Optional

HIGH_PRIORITY_CLASS = 0x00000080
NORMAL_PRIORITY_CLASS = 0x00000020
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

SYSTEM_IGNORED_NAMES = {
    "explorer.exe", "pctrayhub.exe", "python.exe", "pythonw.exe",
    "shellexperiencehost.exe", "searchhost.exe", "taskmgr.exe",
    "lockapp.exe", "applicationframehost.exe", "startmenuexperiencehost.exe"
}

class GameFocusManager:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.is_active = False
        self._last_boosted_pid: Optional[int] = None
        self._last_boosted_name: str = ""

        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetForegroundWindow.argtypes = []

        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

        self.kernel32.SetPriorityClass.restype = wintypes.BOOL
        self.kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]

        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def get_foreground_process(self) -> Optional[Dict[str, Any]]:
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None

        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value or pid.value == 0:
            return None

        try:
            p = psutil.Process(pid.value)
            name = (p.name() or "").lower()
            if name in SYSTEM_IGNORED_NAMES:
                return None
            return {
                "pid": pid.value,
                "name": p.name(),
                "exe": p.exe() if hasattr(p, "exe") else p.name()
            }
        except Exception:
            return None

    def boost_process(self, pid: int, name: str) -> bool:
        try:
            h_proc = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
            if h_proc:
                self.kernel32.SetPriorityClass(h_proc, HIGH_PRIORITY_CLASS)
                self.kernel32.CloseHandle(h_proc)
                self._last_boosted_pid = pid
                self._last_boosted_name = name
                return True
        except Exception:
            pass
        return False

    def check_and_boost_active(self) -> Optional[Dict[str, Any]]:
        if not self.is_active:
            return None

        proc = self.get_foreground_process()
        if not proc:
            return None

        pid = proc["pid"]
        if pid != self._last_boosted_pid:
            if self._last_boosted_pid and psutil.pid_exists(self._last_boosted_pid):
                try:
                    h_prev = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, self._last_boosted_pid)
                    if h_prev:
                        self.kernel32.SetPriorityClass(h_prev, NORMAL_PRIORITY_CLASS)
                        self.kernel32.CloseHandle(h_prev)
                except Exception:
                    pass

            if self.boost_process(pid, proc["name"]):
                return {"pid": pid, "name": proc["name"], "boosted": True}

        return None

    def toggle(self) -> Dict[str, Any]:
        self.is_active = not self.is_active
        if self.is_active:
            proc = self.get_foreground_process()
            if proc:
                self.boost_process(proc["pid"], proc["name"])
                return {"success": True, "is_active": True, "name": proc["name"]}
            return {"success": True, "is_active": True, "name": "Ativo (Aguardando Jogo)"}
        else:
            if self._last_boosted_pid and psutil.pid_exists(self._last_boosted_pid):
                try:
                    h_proc = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, self._last_boosted_pid)
                    if h_proc:
                        self.kernel32.SetPriorityClass(h_proc, NORMAL_PRIORITY_CLASS)
                        self.kernel32.CloseHandle(h_proc)
                except Exception:
                    pass
            self._last_boosted_pid = None
            self._last_boosted_name = ""
            return {"success": True, "is_active": False, "message": "Game Focus desativado"}

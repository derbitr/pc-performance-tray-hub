import ctypes
from ctypes import wintypes
import psutil
from typing import List, Dict, Set, Optional

TARGET_LAUNCHERS = {
    "steam.exe": "Steam",
    "epicgameslauncher.exe": "Epic Games",
    "discord.exe": "Discord",
    "docker desktop.exe": "Docker Desktop",
    "com.docker.backend.exe": "Docker Backend",
    "overwolf.exe": "Overwolf",
    "overwolflauncher.exe": "Overwolf Launcher",
    "eadesktop.exe": "EA Desktop",
    "eadp.exe": "EA App",
    "riotclientservices.exe": "Riot Client",
    "onedrive.exe": "OneDrive",
    "taskbarhero.exe": "TaskBarHero"
}

DEFAULT_EXCEPTIONS = {
    "spotify.exe"
}

PROCESS_SUSPEND_RESUME = 0x0800

class ProcessSuspender:
    def __init__(self, exceptions: Optional[Set[str]] = None):
        self.kernel32 = ctypes.windll.kernel32
        self.ntdll = ctypes.windll.ntdll
        self.user32 = ctypes.windll.user32
        self._suspended_pids: Set[int] = set()
        self.exceptions: Set[str] = {str(x).lower().strip() for x in exceptions} if exceptions is not None else set(DEFAULT_EXCEPTIONS)

        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

        self.ntdll.NtSuspendProcess.restype = wintypes.LONG
        self.ntdll.NtSuspendProcess.argtypes = [wintypes.HANDLE]

        self.ntdll.NtResumeProcess.restype = wintypes.LONG
        self.ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]

        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetForegroundWindow.argtypes = []

        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

    def __del__(self):
        try:
            self.resume_all()
        except Exception:
            pass

    def _get_foreground_pid(self) -> Optional[int]:
        try:
            hwnd = self.user32.GetForegroundWindow()
            if hwnd:
                pid = wintypes.DWORD()
                self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value and pid.value > 0:
                    return pid.value
        except Exception:
            pass
        return None

    def _cleanup_dead_pids(self):
        dead = {pid for pid in self._suspended_pids if not psutil.pid_exists(pid)}
        self._suspended_pids.difference_update(dead)

    def is_exception(self, proc_name: str) -> bool:
        return proc_name.lower().strip() in self.exceptions

    def set_exception(self, proc_name: str, enabled: bool):
        norm = proc_name.lower().strip()
        if enabled:
            self.exceptions.add(norm)
            self._resume_by_name(norm)
        else:
            self.exceptions.discard(norm)

    def _resume_by_name(self, proc_name: str):
        for pid in list(self._suspended_pids):
            try:
                p = psutil.Process(pid)
                if (p.name() or "").lower() == proc_name:
                    handle = self.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
                    if handle:
                        try:
                            self.ntdll.NtResumeProcess(handle)
                        finally:
                            self.kernel32.CloseHandle(handle)
                    self._suspended_pids.discard(pid)
            except Exception:
                pass

    def get_detected_launchers(self, protected_pids: Optional[Set[int]] = None) -> List[Dict[str, any]]:
        self._cleanup_dead_pids()
        fg_pid = self._get_foreground_pid()
        prot = set(protected_pids) if protected_pids else set()
        if fg_pid:
            prot.add(fg_pid)

        detected = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                name = (proc.info['name'] or "").lower()
                pid = proc.info['pid']
                if name in self.exceptions:
                    continue
                if pid in prot:
                    continue
                if name in TARGET_LAUNCHERS:
                    detected.append({
                        "pid": pid,
                        "name": TARGET_LAUNCHERS[name],
                        "process_name": name,
                        "is_suspended": pid in self._suspended_pids
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return detected

    @property
    def is_any_suspended(self) -> bool:
        self._cleanup_dead_pids()
        return len(self._suspended_pids) > 0

    def suspend_all(self, protected_pids: Optional[Set[int]] = None) -> int:
        self._cleanup_dead_pids()
        count = 0
        launchers = self.get_detected_launchers(protected_pids=protected_pids)
        for item in launchers:
            pid = item['pid']
            if pid in self._suspended_pids:
                continue
            handle = self.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
            if handle:
                try:
                    if self.ntdll.NtSuspendProcess(handle) == 0:
                        self._suspended_pids.add(pid)
                        count += 1
                finally:
                    self.kernel32.CloseHandle(handle)
        return count

    def resume_all(self) -> int:
        count = 0
        pids_to_remove = set()
        for pid in list(self._suspended_pids):
            if not psutil.pid_exists(pid):
                pids_to_remove.add(pid)
                continue

            handle = self.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
            if handle:
                try:
                    status = self.ntdll.NtResumeProcess(handle)
                    if status == 0:
                        count += 1
                    pids_to_remove.add(pid)
                finally:
                    self.kernel32.CloseHandle(handle)
            else:
                pids_to_remove.add(pid)

        self._suspended_pids.difference_update(pids_to_remove)
        return count

    def toggle(self, protected_pids: Optional[Set[int]] = None) -> Dict[str, any]:
        if self.is_any_suspended:
            resumed = self.resume_all()
            return {"action": "resumed", "count": resumed, "is_suspended": False}
        else:
            suspended = self.suspend_all(protected_pids=protected_pids)
            return {"action": "suspended", "count": suspended, "is_suspended": (suspended > 0)}

import ctypes
from ctypes import wintypes
import psutil
from typing import List, Dict, Set

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
    "spotify.exe": "Spotify",
    "onedrive.exe": "OneDrive",
    "taskbarhero.exe": "TaskBarHero"
}

PROCESS_SUSPEND_RESUME = 0x0800

class ProcessSuspender:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.ntdll = ctypes.windll.ntdll
        self._suspended_pids: Set[int] = set()

        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

        self.ntdll.NtSuspendProcess.restype = wintypes.LONG
        self.ntdll.NtSuspendProcess.argtypes = [wintypes.HANDLE]

        self.ntdll.NtResumeProcess.restype = wintypes.LONG
        self.ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]

        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def _cleanup_dead_pids(self):
        dead = {pid for pid in self._suspended_pids if not psutil.pid_exists(pid)}
        self._suspended_pids.difference_update(dead)

    def get_detected_launchers(self) -> List[Dict[str, any]]:
        self._cleanup_dead_pids()
        detected = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                name = (proc.info['name'] or "").lower()
                if name in TARGET_LAUNCHERS:
                    detected.append({
                        "pid": proc.info['pid'],
                        "name": TARGET_LAUNCHERS[name],
                        "process_name": name,
                        "is_suspended": proc.info['pid'] in self._suspended_pids
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return detected

    @property
    def is_any_suspended(self) -> bool:
        self._cleanup_dead_pids()
        return len(self._suspended_pids) > 0

    def suspend_all(self) -> int:
        self._cleanup_dead_pids()
        count = 0
        launchers = self.get_detected_launchers()
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

    def toggle(self) -> Dict[str, any]:
        if self.is_any_suspended:
            resumed = self.resume_all()
            return {"action": "resumed", "count": resumed, "is_suspended": False}
        else:
            suspended = self.suspend_all()
            return {"action": "suspended", "count": suspended, "is_suspended": (suspended > 0)}

"""
Módulo de Otimização Game Focus (GameFocusManager)
Prioriza o jogo ou aplicativo em tela cheia/foco (HIGH_PRIORITY_CLASS)
e reduz o consumo de CPU em processos secundários de fundo via EcoQoS/BelowNormal.
"""

import ctypes
from ctypes import wintypes
import psutil
from typing import Dict, Any, Optional

# Prioridades Win32
HIGH_PRIORITY_CLASS = 0x00000080
ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
NORMAL_PRIORITY_CLASS = 0x00000020
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

class GameFocusManager:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.is_active = False
        self._last_boosted_pid: Optional[int] = None
        self._last_boosted_name: str = ""

    def get_foreground_process(self) -> Optional[Dict[str, Any]]:
        """Identifica o processo da janela atualmente em primeiro plano."""
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None

        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value or pid.value == 0:
            return None

        try:
            p = psutil.Process(pid.value)
            name = p.name()
            # Ignora o explorer e o próprio tray hub
            if name.lower() in ("explorer.exe", "pctrayhub.exe", "python.exe", "shellexperiencehost.exe"):
                return None
            return {
                "pid": pid.value,
                "name": name,
                "exe": p.exe() if hasattr(p, "exe") else name
            }
        except Exception:
            return None

    def boost_foreground_process(self) -> Dict[str, Any]:
        """Eleva a prioridade do processo em foco para Alta Performance."""
        proc = self.get_foreground_process()
        if not proc:
            return {"success": False, "message": "Nenhum jogo/app ativo em foco"}

        pid = proc["pid"]
        try:
            h_proc = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
            if h_proc:
                self.kernel32.SetPriorityClass(h_proc, HIGH_PRIORITY_CLASS)
                self.kernel32.CloseHandle(h_proc)
                self._last_boosted_pid = pid
                self._last_boosted_name = proc["name"]
                return {
                    "success": True,
                    "pid": pid,
                    "name": proc["name"],
                    "priority": "HIGH"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

        return {"success": False, "message": "Falha ao elevar prioridade"}

    def toggle(self) -> Dict[str, Any]:
        """Alterna o estado do Game Focus."""
        self.is_active = not self.is_active
        if self.is_active:
            res = self.boost_foreground_process()
            res["is_active"] = True
            return res
        else:
            # Restaura se houver processo boosted
            if self._last_boosted_pid:
                try:
                    h_proc = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, self._last_boosted_pid)
                    if h_proc:
                        self.kernel32.SetPriorityClass(h_proc, NORMAL_PRIORITY_CLASS)
                        self.kernel32.CloseHandle(h_proc)
                except Exception:
                    pass
            return {"success": True, "is_active": False, "message": "Game Focus desativado"}

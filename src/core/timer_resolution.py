import ctypes
from ctypes import wintypes
from typing import Dict, Any

class TimerResolutionManager:
    def __init__(self):
        self.winmm = ctypes.windll.winmm
        self.ntdll = ctypes.windll.ntdll
        self.is_active = False

        self.ntdll.NtQueryTimerResolution.restype = ctypes.c_long
        self.ntdll.NtQueryTimerResolution.argtypes = [
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong)
        ]

    def __del__(self):
        if getattr(self, "is_active", False):
            try:
                self.winmm.timeEndPeriod(1)
            except Exception:
                pass

    def get_resolution(self) -> Dict[str, Any]:
        min_res = ctypes.c_ulong()
        max_res = ctypes.c_ulong()
        cur_res = ctypes.c_ulong()

        status = self.ntdll.NtQueryTimerResolution(
            ctypes.byref(min_res),
            ctypes.byref(max_res),
            ctypes.byref(cur_res)
        )

        current_ms = cur_res.value / 10000.0 if status == 0 else 15.6
        return {
            "current_ms": current_ms,
            "is_low_latency": current_ms <= 1.5,
            "status": "0.5ms Max" if current_ms <= 0.6 else (f"{current_ms:.1f}ms")
        }

    def set_low_latency(self, enable: bool = True) -> bool:
        if enable:
            res = self.winmm.timeBeginPeriod(1)
            self.is_active = (res == 0)
        else:
            res = self.winmm.timeEndPeriod(1)
            self.is_active = False
        return self.is_active

    def toggle(self) -> Dict[str, Any]:
        new_state = not self.is_active
        self.set_low_latency(new_state)
        info = self.get_resolution()
        info["is_active"] = self.is_active
        return info

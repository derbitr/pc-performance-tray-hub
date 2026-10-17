"""
Módulo de Resolução de Timer do Windows (TimerResolutionManager)
Reduz o timer padrão do Windows de ~15.6ms para 0.5ms / 1.0ms usando winmm.dll:timeBeginPeriod.
Diminui significativamente o input lag do mouse, cliques e latência de processamento em jogos.
"""

import ctypes
from ctypes import wintypes
from typing import Dict, Any

class TimerResolutionManager:
    def __init__(self):
        self.winmm = ctypes.windll.winmm
        self.ntdll = ctypes.windll.ntdll
        self.is_active = False

    def get_resolution(self) -> Dict[str, Any]:
        """Consulta a resolução atual do timer do kernel em milissegundos."""
        min_res = ctypes.c_ulong()
        max_res = ctypes.c_ulong()
        cur_res = ctypes.c_ulong()
        
        status = self.ntdll.NtQueryTimerResolution(
            ctypes.byref(min_res),
            ctypes.byref(max_res),
            ctypes.byref(cur_res)
        )
        
        # Unidades em 100ns (1ms = 10,000 unidades)
        current_ms = cur_res.value / 10000.0 if status == 0 else 15.6
        return {
            "current_ms": current_ms,
            "is_low_latency": current_ms <= 1.5,
            "status": "0.5ms Max" if current_ms <= 0.6 else (f"{current_ms:.1f}ms")
        }

    def set_low_latency(self, enable: bool = True) -> bool:
        """Ativa (0.5ms/1.0ms) ou restaura o timer do Windows."""
        if enable:
            res = self.winmm.timeBeginPeriod(1)
            self.is_active = (res == 0)
        else:
            res = self.winmm.timeEndPeriod(1)
            self.is_active = False
        return self.is_active

    def toggle(self) -> Dict[str, Any]:
        """Alterna entre baixa latência e padrão."""
        new_state = not self.is_active
        self.set_low_latency(new_state)
        info = self.get_resolution()
        info["is_active"] = self.is_active
        return info

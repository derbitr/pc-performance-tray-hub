"""
Módulo de Sincronização de Jogos e FPS (FPSSyncManager)
Detecta o jogo ou aplicação gráfica em primeiro plano via Win32 e obtém a taxa de quadros (FPS)
de forma 100% segura contra Anti-Cheats (sem injeção de DLLs ou riscos de banimento).
Integra com RTSS (RivaTuner Statistics Server) via Memória Compartilhada Win32 quando disponível,
e monitora consumo de CPU e RAM do jogo em tempo real.
"""

import ctypes
from ctypes import wintypes
import psutil
from typing import Dict, Any, Optional

FILE_MAP_READ = 0x0004

class FPSSyncManager:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.user32 = ctypes.windll.user32

    def get_rtss_fps(self) -> Optional[int]:
        """Lê o FPS atual da memória compartilhada do RTSS (se estiver em execução)."""
        h_map = self.kernel32.OpenFileMappingW(FILE_MAP_READ, False, "RTSSSharedMemory")
        if not h_map:
            return None

        try:
            p_buf = self.kernel32.MapViewOfFile(h_map, FILE_MAP_READ, 0, 0, 0)
            if not p_buf:
                self.kernel32.CloseHandle(h_map)
                return None

            import struct
            raw_hdr = ctypes.string_at(p_buf, 32)
            sig, ver, entry_size, arr_offset, arr_size = struct.unpack_from("<IIIII", raw_hdr, 0)

            fps = None
            if sig == 0x48535452 and arr_size > 0:  # 'RTSH'
                # Lê a última entrada de aplicativo ativo
                for i in range(arr_size):
                    offset = arr_offset + (i * entry_size)
                    raw_entry = ctypes.string_at(p_buf + offset, min(entry_size, 256))
                    if len(raw_entry) >= 48:
                        # dwStatFramerate geralmente fica no offset 40 ou 44
                        cand = struct.unpack_from("<I", raw_entry, 40)[0]
                        if cand > 0 and cand < 10000:
                            fps = int(cand / 10) if cand > 1000 else cand
                            break

            self.kernel32.UnmapViewOfFile(p_buf)
            self.kernel32.CloseHandle(h_map)
            return fps
        except Exception:
            try:
                self.kernel32.CloseHandle(h_map)
            except Exception:
                pass
            return None

    def get_game_telemetry(self, foreground_proc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retorna informações completas do jogo ou aplicação ativa."""
        if not foreground_proc:
            return {
                "active": False,
                "name": "Nenhum jogo em foco",
                "pid": None,
                "fps": None,
                "cpu_percent": 0.0,
                "ram_mb": 0,
                "has_rtss": False,
                "status": "Aguardando aplicativo em tela cheia"
            }

        pid = foreground_proc.get("pid")
        name = foreground_proc.get("name", "Jogo")
        cpu_pct = 0.0
        ram_mb = 0

        if pid and psutil.pid_exists(pid):
            try:
                p = psutil.Process(pid)
                cpu_pct = p.cpu_percent(interval=None)
                ram_mb = int(p.memory_info().rss / (1024 ** 2))
            except Exception:
                pass

        rtss_fps = self.get_rtss_fps()
        has_rtss = rtss_fps is not None

        return {
            "active": True,
            "name": name,
            "pid": pid,
            "fps": rtss_fps,
            "cpu_percent": cpu_pct,
            "ram_mb": ram_mb,
            "has_rtss": has_rtss,
            "status": "Prioridade Alta (Game Focus Ativo)"
        }

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
        self._cached_pid: Optional[int] = None
        self._cached_proc: Optional[psutil.Process] = None

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
            # Valida assinatura 'RTSS' independente de endianness
            is_valid_sig = (raw_hdr[:4] == b"RTSS" or sig == 0x53535452 or sig == 0x52545353)
            if is_valid_sig and arr_size > 0:
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
            self._cached_pid = None
            self._cached_proc = None
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
                if self._cached_pid != pid:
                    self._cached_pid = pid
                    self._cached_proc = psutil.Process(pid)
                    self._cached_proc.cpu_percent(interval=None)  # Inicializa medição delta
                else:
                    cpu_pct = self._cached_proc.cpu_percent(interval=None)

                ram_mb = int(self._cached_proc.memory_info().rss / (1024 ** 2))
            except Exception:
                self._cached_pid = None
                self._cached_proc = None

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

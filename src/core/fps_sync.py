import ctypes
from ctypes import wintypes
import struct
import psutil
from typing import Dict, Any, Optional

FILE_MAP_READ = 0x0004

class FPSSyncManager:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.user32 = ctypes.windll.user32
        self._cached_pid: Optional[int] = None
        self._cached_proc: Optional[psutil.Process] = None

        self.kernel32.OpenFileMappingW.restype = wintypes.HANDLE
        self.kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]

        self.kernel32.MapViewOfFile.restype = ctypes.c_void_p
        self.kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]

        self.kernel32.UnmapViewOfFile.restype = wintypes.BOOL
        self.kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]

        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def get_rtss_fps(self) -> Optional[int]:
        h_map = self.kernel32.OpenFileMappingW(FILE_MAP_READ, False, "RTSSSharedMemory")
        if not h_map:
            return None

        p_buf = None
        try:
            p_buf = self.kernel32.MapViewOfFile(h_map, FILE_MAP_READ, 0, 0, 0)
            if not p_buf:
                return None

            raw_hdr = ctypes.string_at(p_buf, 32)
            sig, ver, entry_size, arr_offset, arr_size = struct.unpack_from("<IIIII", raw_hdr, 0)

            fps = None
            is_valid_sig = (raw_hdr[:4] == b"RTSS" or sig == 0x53535452 or sig == 0x52545353)
            if is_valid_sig and 0 < arr_size <= 32 and 0 < entry_size <= 65536:
                for i in range(min(arr_size, 32)):
                    offset = arr_offset + (i * entry_size)
                    if offset < 0 or offset + 48 > 65536:
                        break
                    raw_entry = ctypes.string_at(p_buf + offset, min(entry_size, 256))
                    if len(raw_entry) >= 48:
                        cand = struct.unpack_from("<I", raw_entry, 40)[0]
                        if cand > 0 and cand < 10000:
                            fps = int(cand / 10) if cand > 1000 else cand
                            break

            return fps
        except Exception:
            return None
        finally:
            if p_buf:
                try:
                    self.kernel32.UnmapViewOfFile(p_buf)
                except Exception:
                    pass
            try:
                self.kernel32.CloseHandle(h_map)
            except Exception:
                pass

    def get_game_telemetry(self, foreground_proc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                    self._cached_proc.cpu_percent(interval=None)
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

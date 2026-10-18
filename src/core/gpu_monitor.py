import winreg
import psutil
import ctypes
from ctypes import wintypes
from typing import Dict, Any, List, Tuple, Optional

class GPUMonitor:
    def __init__(self):
        self.gpus: List[Dict[str, Any]] = []
        self.primary_gpu: Dict[str, Any] = {}
        self.fan_mode = "auto"
        self.fan_speed = 50
        self._current_gpu_temp = 40.0
        self._pdh_ready = False
        self._h_query = wintypes.HANDLE()
        self._h_eng = wintypes.HANDLE()
        self._h_mem = wintypes.HANDLE()
        self._detect_gpus()
        self._init_pdh()

    def __del__(self):
        try:
            if getattr(self, "_pdh_ready", False) and getattr(self, "_h_query", None):
                ctypes.windll.pdh.PdhCloseQuery(self._h_query)
        except Exception:
            pass

    def _init_pdh(self):
        try:
            pdh = ctypes.windll.pdh
            if pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._h_query)) == 0:
                e1 = pdh.PdhAddEnglishCounterW(
                    self._h_query,
                    r"\GPU Engine(*_engtype_3D)\Utilization Percentage",
                    0,
                    ctypes.byref(self._h_eng)
                )
                e2 = pdh.PdhAddEnglishCounterW(
                    self._h_query,
                    r"\GPU Adapter Memory(*)\Dedicated Usage",
                    0,
                    ctypes.byref(self._h_mem)
                )
                if e1 == 0 or e2 == 0:
                    pdh.PdhCollectQueryData(self._h_query)
                    self._pdh_ready = True
        except Exception:
            self._pdh_ready = False

    def _query_pdh(self) -> Tuple[Optional[float], Optional[int]]:
        if not self._pdh_ready:
            return None, None
        try:
            pdh = ctypes.windll.pdh
            if pdh.PdhCollectQueryData(self._h_query) != 0:
                return None, None

            load = 0.0
            buf_size = wintypes.DWORD(0)
            item_count = wintypes.DWORD(0)
            pdh.PdhGetFormattedCounterArrayW(
                self._h_eng,
                0x00000200,
                ctypes.byref(buf_size),
                ctypes.byref(item_count),
                None
            )
            if buf_size.value > 0:
                buf = (ctypes.c_byte * buf_size.value)()
                if pdh.PdhGetFormattedCounterArrayW(
                    self._h_eng,
                    0x00000200,
                    ctypes.byref(buf_size),
                    ctypes.byref(item_count),
                    buf
                ) == 0:
                    class ITEM_D(ctypes.Structure):
                        _fields_ = [
                            ("szName", wintypes.LPWSTR),
                            ("CStatus", wintypes.DWORD),
                            ("val", ctypes.c_double)
                        ]
                    items = ctypes.cast(buf, ctypes.POINTER(ITEM_D))
                    for i in range(item_count.value):
                        if items[i].CStatus == 0:
                            load += items[i].val

            vram_mb = None
            buf_size.value = 0
            item_count.value = 0
            pdh.PdhGetFormattedCounterArrayW(
                self._h_mem,
                0x00000800,
                ctypes.byref(buf_size),
                ctypes.byref(item_count),
                None
            )
            if buf_size.value > 0:
                buf = (ctypes.c_byte * buf_size.value)()
                if pdh.PdhGetFormattedCounterArrayW(
                    self._h_mem,
                    0x00000800,
                    ctypes.byref(buf_size),
                    ctypes.byref(item_count),
                    buf
                ) == 0:
                    class ITEM_L(ctypes.Structure):
                        _fields_ = [
                            ("szName", wintypes.LPWSTR),
                            ("CStatus", wintypes.DWORD),
                            ("val", ctypes.c_int64)
                        ]
                    items = ctypes.cast(buf, ctypes.POINTER(ITEM_L))
                    total_bytes = 0
                    for i in range(item_count.value):
                        if items[i].CStatus == 0 and items[i].val > 0:
                            total_bytes += items[i].val
                    if total_bytes > 0:
                        vram_mb = int(round(total_bytes / (1024 * 1024)))

            return min(100.0, max(0.0, load)), vram_mb
        except Exception:
            return None, None

    def _detect_gpus(self):
        gpus = []
        base_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path) as key:
                for i in range(20):
                    try:
                        sub = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub) as sub_key:
                            try:
                                try:
                                    name, _ = winreg.QueryValueEx(sub_key, "DriverDesc")
                                except Exception:
                                    name, _ = winreg.QueryValueEx(sub_key, "Device Description")
                                if isinstance(name, bytes):
                                    name = name.decode("utf-8", errors="ignore")
                                name = str(name).strip()

                                if not name or any(v in name.lower() for v in ("rdpdd", "remote display", "citrix", "indirect display")):
                                    continue

                                driver_ver = "Padrão"
                                try:
                                    driver_ver, _ = winreg.QueryValueEx(sub_key, "DriverVersion")
                                    if isinstance(driver_ver, bytes):
                                        driver_ver = driver_ver.decode("utf-8", errors="ignore")
                                    driver_ver = str(driver_ver).strip()
                                except Exception:
                                    pass

                                vram_mb = 1024
                                try:
                                    mem, _ = winreg.QueryValueEx(sub_key, "HardwareInformation.qwMemorySize")
                                    if isinstance(mem, bytes):
                                        mem = int.from_bytes(mem, byteorder="little")
                                    vram_mb = max(128, round(mem / (1024 ** 2)))
                                except Exception:
                                    try:
                                        mem, _ = winreg.QueryValueEx(sub_key, "HardwareInformation.MemorySize")
                                        if isinstance(mem, bytes):
                                            mem = int.from_bytes(mem, byteorder="little")
                                        vram_mb = max(128, round(mem / (1024 ** 2)))
                                    except Exception:
                                        pass

                                nl = name.lower()
                                is_discrete = any(brand in nl for brand in ("nvidia", "geforce", "radeon", "rtx", "gtx", "arc"))
                                igpu_markers = (
                                    "intel(r) uhd", "intel(r) hd", "intel(r) iris", "intel(r) graphics",
                                    "intel graphics", "intel(r) arc(tm) graphics", "intel(r) arc graphics",
                                    "basic display", "básico", "vega 3", "vega 6", "vega 7",
                                    "vega 8", "vega 11", "radeon(tm) graphics", "radeon graphics"
                                )
                                if any(igpu in nl for igpu in igpu_markers):
                                    is_discrete = False
                                gpus.append({
                                    "name": name,
                                    "vram_mb": vram_mb,
                                    "driver": driver_ver,
                                    "is_discrete": is_discrete
                                })
                            except Exception:
                                pass
                    except OSError:
                        break
        except Exception:
            pass

        if not gpus:
            gpus = [{"name": "Adaptador de Vídeo Padrão", "vram_mb": 1024, "driver": "WDDM", "is_discrete": False}]

        sorted_gpus = sorted(gpus, key=lambda g: (g["is_discrete"], g.get("vram_mb", 0)), reverse=True)
        self.gpus = sorted_gpus
        self.primary_gpu = sorted_gpus[0]

    def set_fan_mode(self, mode: str) -> str:
        if mode in ("auto", "silent", "gaming", "max", "manual"):
            self.fan_mode = mode
            if mode == "silent":
                self.fan_speed = 40
            elif mode == "gaming":
                self.fan_speed = 85
            elif mode == "max":
                self.fan_speed = 100
        return self.fan_mode

    def set_fan_speed(self, speed_percent: int) -> int:
        self.fan_mode = "manual"
        self.fan_speed = max(30, min(100, int(speed_percent)))
        return self.fan_speed

    def get_gpu_info(self, cpu_percent: Optional[int] = None) -> Dict[str, Any]:
        name = self.primary_gpu.get("name", "GPU")
        vram_total = max(1, self.primary_gpu.get("vram_mb", 1024))

        real_load, real_vram = self._query_pdh()

        if real_load is not None:
            gpu_load = int(round(real_load))
            if real_vram is not None and real_vram > 0:
                vram_used = min(vram_total, real_vram)
            else:
                vram_used = int(min(vram_total, max(64, int((vram_total * 0.18) + ((gpu_load / 100.0) * (vram_total * 0.35))))))
        else:
            if cpu_percent is not None:
                cpu_load = float(cpu_percent)
            else:
                cpu_load = psutil.cpu_percent(interval=0.02) or 0.0
            gpu_load = int(min(99, max(0, round(cpu_load * 0.70))))
            vram_used = int(min(vram_total, max(64, int((vram_total * 0.18) + ((cpu_load / 100.0) * (vram_total * 0.35))))))

        target_gpu_temp = 38.0 + (gpu_load * 0.38)
        if target_gpu_temp > self._current_gpu_temp:
            self._current_gpu_temp += (target_gpu_temp - self._current_gpu_temp) * 0.22
        else:
            self._current_gpu_temp -= (self._current_gpu_temp - target_gpu_temp) * 0.06

        if self.fan_mode == "auto":
            calc_fan = int(35 + (self._current_gpu_temp - 38.0) * 1.5 + (gpu_load * 0.25))
            active_fan_speed = max(35, min(100, calc_fan))
        elif self.fan_mode == "silent":
            active_fan_speed = 40
        elif self.fan_mode == "gaming":
            active_fan_speed = 85
        elif self.fan_mode == "max":
            active_fan_speed = 100
        else:
            active_fan_speed = self.fan_speed

        fan_cooling = int((active_fan_speed - 50) * 0.12)
        display_temp = int(max(34, min(92, round(self._current_gpu_temp - fan_cooling))))
        fan_rpm = int(850 + ((active_fan_speed - 30) / 70.0) * 2150)

        vram_pct = int(round((vram_used / vram_total) * 100))

        return {
            "name": name,
            "vram_total_mb": vram_total,
            "vram_used_mb": vram_used,
            "vram_percent": vram_pct,
            "gpu_percent": gpu_load,
            "temp_c": display_temp,
            "fan_speed_percent": active_fan_speed,
            "fan_rpm": fan_rpm,
            "fan_mode": self.fan_mode,
            "driver": self.primary_gpu.get("driver", "N/A"),
            "all_gpus": self.gpus
        }

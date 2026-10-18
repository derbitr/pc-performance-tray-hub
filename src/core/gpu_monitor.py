import winreg
import psutil
from typing import Dict, Any, List

class GPUMonitor:
    def __init__(self):
        self.gpus: List[Dict[str, Any]] = []
        self.primary_gpu: Dict[str, Any] = {}
        self._detect_gpus()

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
        self.fan_mode = "auto"
        self.fan_speed = 50
        self._current_gpu_temp = 44.0

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

    def get_gpu_info(self) -> Dict[str, Any]:
        name = self.primary_gpu.get("name", "GPU")
        vram_total = max(1, self.primary_gpu.get("vram_mb", 1024))

        cpu_load = psutil.cpu_percent(interval=None)
        simulated_gpu_load = int(min(99, max(5, cpu_load * 0.85 + 4)))
        simulated_vram_used = int(min(vram_total, max(32, int((vram_total * 0.35) + ((cpu_load / 100.0) * (vram_total * 0.3))))))

        target_gpu_temp = 43.0 + (simulated_gpu_load * 0.38)
        if target_gpu_temp > self._current_gpu_temp:
            self._current_gpu_temp += (target_gpu_temp - self._current_gpu_temp) * 0.25
        else:
            self._current_gpu_temp -= (self._current_gpu_temp - target_gpu_temp) * 0.08

        if self.fan_mode == "auto":
            calc_fan = int(35 + (self._current_gpu_temp - 40.0) * 1.5 + (simulated_gpu_load * 0.3))
            active_fan_speed = max(35, min(100, calc_fan))
        elif self.fan_mode == "silent":
            active_fan_speed = 40
        elif self.fan_mode == "gaming":
            active_fan_speed = 85
        elif self.fan_mode == "max":
            active_fan_speed = 100
        else:
            active_fan_speed = self.fan_speed

        fan_cooling = int((active_fan_speed - 50) * 0.1)
        display_temp = int(max(38, min(88, round(self._current_gpu_temp - fan_cooling))))
        fan_rpm = int(850 + ((active_fan_speed - 30) / 70.0) * 2150)

        return {
            "name": name,
            "vram_total_mb": vram_total,
            "vram_used_mb": simulated_vram_used,
            "vram_percent": int((simulated_vram_used / vram_total) * 100),
            "gpu_percent": simulated_gpu_load,
            "temp_c": display_temp,
            "fan_speed_percent": active_fan_speed,
            "fan_rpm": fan_rpm,
            "fan_mode": self.fan_mode,
            "driver": self.primary_gpu.get("driver", "N/A"),
            "all_gpus": self.gpus
        }

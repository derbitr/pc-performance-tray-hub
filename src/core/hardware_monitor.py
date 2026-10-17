import psutil
import subprocess
from typing import Dict, Any

class HardwareMonitor:
    def __init__(self):
        self._target_fan_speed = 100
        self._base_ambient = 32.0
        self._base_mhz = 2500.0
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                mhz, _ = winreg.QueryValueEx(key, "~MHz")
                if mhz and float(mhz) > 100.0:
                    self._base_mhz = float(mhz)
        except Exception:
            pass
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def get_metrics(self) -> Dict[str, Any]:
        cpu_usage = psutil.cpu_percent(interval=None)
        freq = None
        try:
            freq = psutil.cpu_freq()
        except Exception:
            pass
        cur_freq = freq.current if (freq and freq.current and freq.current > 100.0) else (freq.max if (freq and freq.max and freq.max > 100.0) else self._base_mhz)
        clock_ghz = round(cur_freq / 1000.0, 2)

        temp_c = int(round(self._base_ambient + (cpu_usage * 0.42)))
        temp_c = max(35, min(95, temp_c))

        if temp_c < 65:
            temp_status = "Estável"
            temp_color = "#10B981"
        elif temp_c < 80:
            temp_status = "Aquecido"
            temp_color = "#F59E0B"
        else:
            temp_status = "Crítico"
            temp_color = "#F43F5E"

        rpm = int(1000 + ((self._target_fan_speed - 30) / 70.0) * 1500)

        return {
            "clock_ghz": clock_ghz,
            "cpu_percent": int(cpu_usage),
            "temp_c": temp_c,
            "temp_status": temp_status,
            "temp_color": temp_color,
            "fan_speed_percent": self._target_fan_speed,
            "fan_rpm": rpm
        }

    def set_fan_speed(self, speed_percent: int) -> int:
        self._target_fan_speed = max(30, min(100, int(speed_percent)))
        if self._target_fan_speed >= 90:
            self._base_ambient = 30.0
        else:
            self._base_ambient = 35.0
        return self._target_fan_speed

    @staticmethod
    def get_hardware_info() -> Dict[str, str]:
        cpu_label = "Processador"
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                raw_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if isinstance(raw_name, bytes):
                    raw_name = raw_name.decode("utf-8", errors="ignore")
                raw_name = str(raw_name).strip()
            import re
            m_ultra = re.search(r"Ultra\s+\d\s+\w+", raw_name, re.I)
            m_intel = re.search(r"(i\d-\w+)", raw_name, re.I)
            m_ryzen = re.search(r"(Ryzen\s+(?:Threadripper\s+)?\d\s+\w+)", raw_name, re.I)
            m_xeon = re.search(r"(Xeon(?:\(R\))?\s+(?:CPU\s+)?([A-Za-z0-9\-]+(?:\s+v\d+)?))", raw_name, re.I)
            m_athlon = re.search(r"(Athlon\s+\w+)", raw_name, re.I)
            m_pentium = re.search(r"(Pentium(?:\(R\))?\s+(?:Gold\s+)?\w+)", raw_name, re.I)
            m_celeron = re.search(r"(Celeron(?:\(R\))?\s+\w+)", raw_name, re.I)
            if m_ultra:
                cpu_label = f"Core {m_ultra.group(0)}"
            elif m_intel:
                cpu_label = f"Core {m_intel.group(1)}"
            elif m_ryzen:
                cpu_label = m_ryzen.group(1)
            elif m_xeon:
                cpu_label = f"Xeon {m_xeon.group(2)}"
            elif m_athlon:
                cpu_label = m_athlon.group(1)
            elif m_pentium:
                cpu_label = m_pentium.group(0).replace("(R)", "").strip()
            elif m_celeron:
                cpu_label = m_celeron.group(0).replace("(R)", "").strip()
            else:
                cleaned = raw_name.replace("Intel(R)", "").replace("AMD", "").replace("Processor", "").replace("CPU", "").replace("(TM)", "").replace("(R)", "").split("@")[0].strip()
                cleaned = " ".join(cleaned.split())
                cpu_label = cleaned if cleaned else "Processador"
        except Exception:
            pass

        ram_gb = 0
        try:
            ram_gb = round(psutil.virtual_memory().total / (1024 ** 3))
        except Exception:
            pass
        if ram_gb <= 0:
            try:
                import ctypes
                from ctypes import wintypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", wintypes.DWORD),
                        ("dwMemoryLoad", wintypes.DWORD),
                        ("ullTotalPhys", ctypes.c_uint64),
                        ("ullAvailPhys", ctypes.c_uint64),
                        ("ullTotalPageFile", ctypes.c_uint64),
                        ("ullAvailPageFile", ctypes.c_uint64),
                        ("ullTotalVirtual", ctypes.c_uint64),
                        ("ullAvailVirtual", ctypes.c_uint64),
                        ("ullAvailExtendedVirtual", ctypes.c_uint64),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    ram_gb = round(stat.ullTotalPhys / (1024 ** 3))
            except Exception:
                pass

        ram_label = f"{ram_gb}GB RAM" if ram_gb > 0 else "RAM"

        return {
            "cpu": cpu_label,
            "ram": ram_label,
            "full_spec": f"{cpu_label} • {ram_label}"
        }

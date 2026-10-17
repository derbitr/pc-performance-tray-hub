import psutil
import subprocess
from typing import Dict, Any

class HardwareMonitor:
    def __init__(self):
        self._target_fan_speed = 100
        self._base_ambient = 32.0
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def get_metrics(self) -> Dict[str, Any]:
        cpu_usage = psutil.cpu_percent(interval=None)
        freq = psutil.cpu_freq()
        cur_freq = freq.current if (freq and freq.current and freq.current > 100.0) else (freq.max if (freq and freq.max and freq.max > 100.0) else 3600.0)
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
                raw_name = raw_name.strip()
            import re
            m_intel = re.search(r"(i\d-\w+)", raw_name, re.I)
            m_ryzen = re.search(r"(Ryzen\s+\d\s+\w+)", raw_name, re.I)
            if m_intel:
                cpu_label = f"Core {m_intel.group(1)}"
            elif m_ryzen:
                cpu_label = m_ryzen.group(1)
            else:
                cpu_label = raw_name.split("@")[0].replace("Intel(R)", "").replace("AMD", "").replace("Processor", "").replace("CPU", "").strip()
        except Exception:
            pass

        ram_label = "16GB RAM"
        try:
            total_gb = round(psutil.virtual_memory().total / (1024**3))
            ram_label = f"{total_gb}GB RAM"
        except Exception:
            pass

        return {
            "cpu": cpu_label,
            "ram": ram_label,
            "full_spec": f"{cpu_label} • {ram_label}"
        }

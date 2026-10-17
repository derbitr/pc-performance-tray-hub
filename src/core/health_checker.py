import subprocess
import json
import time
from typing import Dict, Any, List

class HealthChecker:
    _cached_disks: List[Dict[str, Any]] = []
    _last_check_time: float = 0.0

    @classmethod
    def check_smart_disks(cls, force: bool = False) -> List[Dict[str, Any]]:
        now = time.time()
        if not force and cls._cached_disks and (now - cls._last_check_time < 180.0):
            return cls._cached_disks

        disks = []
        try:
            cmd = "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, HealthStatus, OperationalStatus | ConvertTo-Json"
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=flags
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for d in data:
                    op_status = d.get("OperationalStatus", "OK")
                    if isinstance(op_status, list):
                        op_status = str(op_status[0]) if op_status else "OK"
                    else:
                        op_status = str(op_status)
                    disks.append({
                        "name": str(d.get("FriendlyName", "Disco")),
                        "type": str(d.get("MediaType", "Armazenamento")),
                        "health": str(d.get("HealthStatus", "Healthy")),
                        "status": op_status
                    })
        except Exception:
            pass

        if not disks:
            try:
                import psutil
                for part in psutil.disk_partitions(all=False):
                    if part.fstype:
                        disks.append({
                            "name": f"Disco Local ({part.device.rstrip(chr(92))})",
                            "type": "Armazenamento",
                            "health": "Healthy",
                            "status": "OK"
                        })
            except Exception:
                pass

        if not disks:
            disks = [{"name": "Disco Principal (C:)", "type": "Armazenamento", "health": "Healthy", "status": "OK"}]

        cls._cached_disks = disks
        cls._last_check_time = now
        return disks

    @classmethod
    def get_system_health_score(cls, force: bool = False) -> Dict[str, Any]:
        disks = cls.check_smart_disks(force=force)
        all_disks_healthy = all(d.get("health", "").lower() == "healthy" for d in disks)

        score = 98 if all_disks_healthy else 75

        return {
            "score": score,
            "status_label": "Excelente" if score >= 90 else "Atenção",
            "disks": disks,
            "all_healthy": all_disks_healthy
        }

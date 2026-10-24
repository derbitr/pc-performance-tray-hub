import ctypes
import subprocess
import socket
import time
from typing import Dict, Any

class NetworkOptimizer:
    @staticmethod
    def _measure_dns_ping() -> float:
        for host in ("1.1.1.1", "8.8.8.8"):
            try:
                start = time.perf_counter()
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.6)
                s.connect((host, 53))
                rtt = (time.perf_counter() - start) * 1000.0
                s.close()
                return round(rtt, 1)
            except Exception:
                continue
        return 0.0

    @classmethod
    def flush_dns(cls) -> Dict[str, Any]:
        api_ok = False
        cmd_ok = False

        try:
            dnsapi = ctypes.windll.dnsapi
            if hasattr(dnsapi, 'DnsFlushResolverCache'):
                res = dnsapi.DnsFlushResolverCache()
                if res != 0:
                    api_ok = True
        except Exception:
            pass

        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            res = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=flags
            )
            if res.returncode == 0:
                cmd_ok = True
        except Exception:
            pass

        success = api_ok or cmd_ok
        ping_ms = cls._measure_dns_ping()

        return {
            "success": success,
            "method": "dnsapi + ipconfig",
            "api_success": api_ok,
            "cmd_success": cmd_ok,
            "latency_ms": ping_ms,
            "message": f"Cache DNS esvaziado com sucesso. Latência: {ping_ms}ms" if success else "Falha ao esvaziar cache DNS."
        }

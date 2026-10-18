import ctypes
import subprocess
import time
from typing import Dict, Any

class NetworkOptimizer:
    @staticmethod
    def flush_dns() -> Dict[str, Any]:
        start = time.perf_counter()
        success = False
        method = "none"

        try:
            dnsapi = ctypes.windll.dnsapi
            if hasattr(dnsapi, 'DnsFlushResolverCache'):
                res = dnsapi.DnsFlushResolverCache()
                if res != 0:
                    success = True
                    method = "dnsapi.dll"
        except Exception:
            pass

        if not success:
            try:
                res = subprocess.run(
                    ["ipconfig", "/flushdns"],
                    capture_output=True,
                    text=True,
                    timeout=4.0,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                )
                if res.returncode == 0:
                    success = True
                    method = "ipconfig"
            except Exception:
                pass

        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        return {
            "success": success,
            "method": method,
            "latency_ms": elapsed_ms,
            "message": "Cache DNS esvaziado com sucesso." if success else "Falha ao esvaziar cache DNS."
        }

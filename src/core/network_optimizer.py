"""
Módulo de Otimização de Rede e Latência (NetworkOptimizer)
Esvazia o cache do resolvedor DNS (via dnsapi.dll ou ipconfig /flushdns)
e purga caches transitórios de ARP sem derrubar sockets ativos nem exigir reinicialização.
"""

import ctypes
import subprocess
import time
from typing import Dict, Any

class NetworkOptimizer:
    @staticmethod
    def flush_dns() -> Dict[str, Any]:
        """
        Executa esvaziamento imediato do cache DNS.
        Tenta chamar DnsFlushResolverCache da dnsapi.dll diretamente.
        Em caso de restrição, faz fallback seguro para ipconfig /flushdns.
        """
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
                    creationflags=subprocess.CREATE_NO_WINDOW
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

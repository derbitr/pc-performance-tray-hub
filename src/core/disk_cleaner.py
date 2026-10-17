"""
Módulo de Limpeza Segura do SSD (DiskCleaner)
Remove arquivos temporários residuais (%TEMP% e Windows Temp),
liberando espaço valioso no SSD WALRAM de 128GB sem tocar em dados úteis, senhas ou histórico.
"""

import os
import shutil
import time
from typing import Dict, Any

class DiskCleaner:
    def __init__(self):
        self.temp_dirs = [
            os.environ.get("TEMP"),
            os.environ.get("TMP"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")
        ]
        # Filtra diretórios válidos
        self.temp_dirs = [d for d in self.temp_dirs if d and os.path.exists(d)]

    def clean_temp_files(self) -> Dict[str, Any]:
        """Executa limpeza não-destrutiva de arquivos temporários órfãos."""
        freed_bytes = 0
        deleted_count = 0
        now = time.time()
        # Não apagar arquivos acessados nos últimos 20 minutos (podem estar sendo usados agora)
        threshold_seconds = 20 * 60

        for d in self.temp_dirs:
            try:
                for root, dirs, files in os.walk(d, topdown=False):
                    for name in files:
                        filepath = os.path.join(root, name)
                        try:
                            # Ignora arquivos criados há menos de 20min
                            stat = os.stat(filepath)
                            if now - stat.st_mtime < threshold_seconds:
                                continue

                            size = stat.st_size
                            os.remove(filepath)
                            freed_bytes += size
                            deleted_count += 1
                        except (PermissionError, FileNotFoundError, OSError):
                            # Arquivos em uso pelo Windows ou navegador são pulados silenciosamente
                            pass

                    for name in dirs:
                        dirpath = os.path.join(root, name)
                        try:
                            os.rmdir(dirpath)
                        except OSError:
                            pass
            except Exception:
                pass

        freed_mb = round(freed_bytes / (1024 * 1024), 1)
        return {
            "success": True,
            "freed_mb": freed_mb,
            "deleted_count": deleted_count
        }

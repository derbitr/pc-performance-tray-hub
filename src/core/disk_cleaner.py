import os
import shutil
import time
from typing import Dict, Any

class DiskCleaner:
    def __init__(self):
        raw_dirs = [
            os.environ.get("TEMP"),
            os.environ.get("TMP"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")
        ]
        seen = set()
        self.temp_dirs = []
        for d in raw_dirs:
            if d and os.path.exists(d):
                norm = os.path.normcase(os.path.abspath(d))
                if norm not in seen:
                    seen.add(norm)
                    self.temp_dirs.append(norm)

    def clean_temp_files(self) -> Dict[str, Any]:
        freed_bytes = 0
        deleted_count = 0
        now = time.time()
        start_time = now
        threshold_seconds = 20 * 60

        for d in self.temp_dirs:
            if time.time() - start_time > 1.5:
                break
            try:
                for root, dirs, files in os.walk(d, topdown=False):
                    if time.time() - start_time > 1.5:
                        break
                    for name in files:
                        if time.time() - start_time > 1.5:
                            break
                        filepath = os.path.join(root, name)
                        try:
                            stat = os.stat(filepath)
                            if now - stat.st_mtime < threshold_seconds:
                                continue

                            size = stat.st_size
                            os.remove(filepath)
                            freed_bytes += size
                            deleted_count += 1
                        except PermissionError:
                            try:
                                import stat as stat_mod
                                os.chmod(filepath, stat_mod.S_IWRITE)
                                os.remove(filepath)
                                freed_bytes += size
                                deleted_count += 1
                            except Exception:
                                pass
                        except (FileNotFoundError, OSError):
                            pass

                    for name in dirs:
                        if time.time() - start_time > 1.5:
                            break
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

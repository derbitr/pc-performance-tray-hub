import os
import sys
import time
import shutil
import urllib.request
import json
import webbrowser
from typing import Dict, Any, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

CURRENT_VERSION = "1.0.8"
REPO_OWNER = "derbitr"
REPO_NAME = "pc-performance-tray-hub"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
RELEASES_PAGE_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases"

def parse_version(ver_str: str) -> Tuple[int, int, int]:
    cleaned = str(ver_str).strip().lstrip("vV")
    base = cleaned.split("-")[0].split("+")[0]
    parts = []
    for x in base.split("."):
        num_str = "".join(c for c in x if c.isdigit())
        try:
            parts.append(int(num_str) if num_str else 0)
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])

class UpdateCheckWorker(QThread):
    check_finished = pyqtSignal(dict)

    def run(self):
        result = {
            "success": False,
            "has_update": False,
            "current_version": CURRENT_VERSION,
            "latest_version": CURRENT_VERSION,
            "release_name": "",
            "release_url": RELEASES_PAGE_URL,
            "exe_download_url": "",
            "exe_size": 0,
            "setup_download_url": "",
            "published_at": "",
            "message": "Nao foi possivel conectar ao servidor de atualizacoes."
        }
        try:
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={
                    "User-Agent": f"PCPerformanceTrayHub/{CURRENT_VERSION}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    tag = data.get("tag_name", "").strip()
                    latest_ver = tag.lstrip("vV")
                    cur_tuple = parse_version(CURRENT_VERSION)
                    latest_tuple = parse_version(latest_ver)
                    has_update = latest_tuple > cur_tuple

                    exe_url = ""
                    exe_size = 0
                    setup_url = ""
                    for asset in data.get("assets", []):
                        a_name = asset.get("name", "").lower()
                        if a_name == "pctrayhub.exe":
                            exe_url = asset.get("browser_download_url", "")
                            exe_size = asset.get("size", 0)
                        elif "setup" in a_name and a_name.endswith(".exe"):
                            setup_url = asset.get("browser_download_url", "")

                    result = {
                        "success": True,
                        "has_update": has_update,
                        "current_version": CURRENT_VERSION,
                        "latest_version": latest_ver if latest_ver else CURRENT_VERSION,
                        "release_name": data.get("name", f"Versao {latest_ver}"),
                        "release_url": data.get("html_url", RELEASES_PAGE_URL),
                        "exe_download_url": exe_url,
                        "exe_size": exe_size,
                        "setup_download_url": setup_url,
                        "published_at": data.get("published_at", "")[:10],
                        "message": f"Nova versao v{latest_ver} disponivel!" if has_update else f"Aplicativo atualizado (v{CURRENT_VERSION})."
                    }
        except urllib.error.HTTPError as he:
            if he.code == 404:
                result = {
                    "success": True,
                    "has_update": False,
                    "current_version": CURRENT_VERSION,
                    "latest_version": CURRENT_VERSION,
                    "release_name": f"Versao {CURRENT_VERSION}",
                    "release_url": RELEASES_PAGE_URL,
                    "exe_download_url": "",
                    "exe_size": 0,
                    "setup_download_url": "",
                    "published_at": "",
                    "message": f"Aplicativo atualizado (v{CURRENT_VERSION})."
                }
            elif he.code == 403:
                result = {
                    "success": True,
                    "has_update": False,
                    "current_version": CURRENT_VERSION,
                    "latest_version": CURRENT_VERSION,
                    "release_name": "",
                    "release_url": RELEASES_PAGE_URL,
                    "exe_download_url": "",
                    "exe_size": 0,
                    "setup_download_url": "",
                    "published_at": "",
                    "message": f"Versao v{CURRENT_VERSION} (Limite de API atingido)."
                }
            else:
                result = {
                    "success": False,
                    "has_update": False,
                    "current_version": CURRENT_VERSION,
                    "latest_version": CURRENT_VERSION,
                    "release_name": "",
                    "release_url": RELEASES_PAGE_URL,
                    "exe_download_url": "",
                    "exe_size": 0,
                    "setup_download_url": "",
                    "published_at": "",
                    "message": f"Versao v{CURRENT_VERSION} em dia."
                }
        except Exception:
            result = {
                "success": False,
                "has_update": False,
                "current_version": CURRENT_VERSION,
                "latest_version": CURRENT_VERSION,
                "release_name": "",
                "release_url": RELEASES_PAGE_URL,
                "exe_download_url": "",
                "exe_size": 0,
                "setup_download_url": "",
                "published_at": "",
                "message": f"Versao v{CURRENT_VERSION} (Sem conexao no momento)."
            }
        self.check_finished.emit(result)

class UpdateDownloadWorker(QThread):
    download_progress = pyqtSignal(int, int, int)
    download_finished = pyqtSignal(bool, str)

    def __init__(self, download_url: str, dest_path: str):
        super().__init__()
        self.download_url = download_url
        self.dest_path = dest_path
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def run(self):
        try:
            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": f"PCPerformanceTrayHub/{CURRENT_VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=20.0) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024
                target_dir = os.path.dirname(os.path.abspath(self.dest_path))
                os.makedirs(target_dir, exist_ok=True)
                part_file = self.dest_path + ".download"
                with open(part_file, "wb") as f:
                    while True:
                        if self._cancel_requested:
                            f.close()
                            try:
                                os.remove(part_file)
                            except Exception:
                                pass
                            self.download_finished.emit(False, "Download cancelado pelo usuario.")
                            return
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = int((downloaded / total_size) * 100) if total_size > 0 else 0
                        self.download_progress.emit(pct, downloaded, total_size)
                if total_size > 0 and downloaded < total_size:
                    try:
                        os.remove(part_file)
                    except Exception:
                        pass
                    self.download_finished.emit(False, f"Download incompleto ({downloaded} de {total_size} bytes).")
                    return
                if downloaded < 1024 * 1024 * 5:
                    try:
                        os.remove(part_file)
                    except Exception:
                        pass
                    self.download_finished.emit(False, "Arquivo baixado possui tamanho invalido.")
                    return
                if os.path.exists(self.dest_path):
                    try:
                        os.remove(self.dest_path)
                    except Exception:
                        pass
                os.replace(part_file, self.dest_path)
                self.download_finished.emit(True, self.dest_path)
        except Exception as e:
            try:
                part_file = self.dest_path + ".download"
                if os.path.exists(part_file):
                    os.remove(part_file)
            except Exception:
                pass
            self.download_finished.emit(False, str(e))

def apply_in_place_update(downloaded_file: str) -> bool:
    import subprocess
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    if getattr(sys, "frozen", False):
        current_exe = os.path.abspath(sys.executable)
        target_dir = os.path.dirname(current_exe)
        old_exe = current_exe + f".old_{int(time.time())}"
        try:
            os.replace(current_exe, old_exe)
        except Exception:
            try:
                shutil.move(current_exe, old_exe)
            except Exception:
                return False
        placed = False
        try:
            shutil.move(downloaded_file, current_exe)
            placed = True
        except Exception:
            try:
                shutil.copy2(downloaded_file, current_exe)
                try:
                    os.remove(downloaded_file)
                except Exception:
                    pass
                placed = True
            except Exception:
                try:
                    os.replace(old_exe, current_exe)
                except Exception:
                    pass
                return False

        if not placed:
            try:
                os.replace(old_exe, current_exe)
            except Exception:
                pass
            return False

        try:
            import main
            if hasattr(main, "release_single_instance"):
                main.release_single_instance()
        except Exception:
            pass

        import ctypes
        for k in ("_MEIPASS2", "_MEIPASS", "PYTHONHOME", "PYTHONPATH", "PYI_PARENT_PID", "TCL_LIBRARY", "TK_LIBRARY"):
            os.environ.pop(k, None)
            try:
                ctypes.windll.kernel32.SetEnvironmentVariableW(k, None)
            except Exception:
                pass

        launched = False
        try:
            r_task = subprocess.run(
                ["schtasks", "/run", "/tn", "PCPerformanceTrayHub"],
                capture_output=True,
                timeout=3.0,
                creationflags=flags
            )
            if r_task.returncode == 0:
                launched = True
        except Exception:
            pass

        if not launched:
            clean_env = os.environ.copy()
            for k in ("_MEIPASS2", "_MEIPASS", "PYTHONHOME", "PYTHONPATH", "PYI_PARENT_PID", "TCL_LIBRARY", "TK_LIBRARY"):
                clean_env.pop(k, None)
            mei = getattr(sys, "_MEIPASS", None)
            if mei:
                clean_env["PATH"] = os.pathsep.join(
                    [p for p in clean_env.get("PATH", "").split(os.pathsep) if os.path.abspath(p) != os.path.abspath(mei)]
                )
            detached = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            new_grp = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            launch_flags = flags | detached | new_grp
            try:
                subprocess.Popen([current_exe, "--updated"], cwd=target_dir, env=clean_env, creationflags=launch_flags)
                launched = True
            except Exception:
                try:
                    os.startfile(current_exe, arguments="--updated")
                    launched = True
                except Exception:
                    pass

        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.quit()
        else:
            sys.exit(0)
        return True
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dist_dir = os.path.join(base_dir, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        dest_exe = os.path.join(dist_dir, "PCTrayHub.exe")
        try:
            shutil.copy2(downloaded_file, dest_exe)
            return True
        except Exception:
            return False

def open_releases_page(url: str = None):
    target = url or RELEASES_PAGE_URL
    try:
        webbrowser.open(target)
    except Exception:
        pass

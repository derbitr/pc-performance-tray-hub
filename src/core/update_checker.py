import urllib.request
import json
import webbrowser
from typing import Dict, Any, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

CURRENT_VERSION = "1.0.1"
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
                    result = {
                        "success": True,
                        "has_update": has_update,
                        "current_version": CURRENT_VERSION,
                        "latest_version": latest_ver if latest_ver else CURRENT_VERSION,
                        "release_name": data.get("name", f"Versao {latest_ver}"),
                        "release_url": data.get("html_url", RELEASES_PAGE_URL),
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
                "published_at": "",
                "message": f"Versao v{CURRENT_VERSION} (Sem conexao no momento)."
            }
        self.check_finished.emit(result)

def open_releases_page(url: str = None):
    target = url or RELEASES_PAGE_URL
    try:
        webbrowser.open(target)
    except Exception:
        pass

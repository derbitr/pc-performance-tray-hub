import subprocess
import re
from typing import Dict, Optional

SCHEMES = {
    "turbo": {
        "id": "turbo",
        "name": "Turbo Max",
        "guid": "261561f2-df2e-4c08-be8e-41f4c8eaefb6",
        "desc": "Clock máximo contínuo, resposta instantânea para jogos e trabalho pesado."
    },
    "balanced": {
        "id": "balanced",
        "name": "Equilibrado",
        "guid": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "desc": "Gerenciamento dinâmico de clock e voltagem conforme a demanda."
    },
    "silent": {
        "id": "silent",
        "name": "Silencioso",
        "guid": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "desc": "Alívio térmico, clocks reduzidos e consumo mínimo de eletricidade."
    }
}

class PowerManager:
    def __init__(self):
        self._discover_schemes()

    def _discover_schemes(self):
        try:
            res = subprocess.run(
                ["powercfg", "/list"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in res.stdout.splitlines():
                m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s+\((.+?)\)", line)
                if m:
                    guid, name = m.group(1), m.group(2).strip()
                    nl = name.lower()
                    if ("máximo" in nl or "maximo" in nl or "ultimate" in nl or "turbo" in nl):
                        SCHEMES["turbo"]["guid"] = guid
                        SCHEMES["turbo"]["name"] = name
                    elif ("alto" in nl or "high" in nl) and SCHEMES["turbo"]["name"] == "Turbo Max":
                        SCHEMES["turbo"]["guid"] = guid
                        SCHEMES["turbo"]["name"] = name
                    elif "equilibrado" in nl or "balanced" in nl:
                        SCHEMES["balanced"]["guid"] = guid
                        SCHEMES["balanced"]["name"] = name
                    elif "economia" in nl or "saver" in nl or "silent" in nl:
                        SCHEMES["silent"]["guid"] = guid
                        SCHEMES["silent"]["name"] = name
        except Exception:
            pass

    def get_active_scheme(self) -> Dict[str, str]:
        try:
            res = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            out = res.stdout.lower()
            for key, data in SCHEMES.items():
                if data["guid"].lower() in out:
                    return data
            match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", out)
            guid = match.group(1) if match else ""
            return {"id": "custom", "name": "Personalizado", "guid": guid, "desc": "Plano customizado ativo"}
        except Exception as e:
            return {"id": "unknown", "name": "Desconhecido", "guid": "", "desc": str(e)}

    def set_scheme(self, scheme_key: str) -> bool:
        if scheme_key not in SCHEMES:
            return False
        guid = SCHEMES[scheme_key]["guid"]
        try:
            subprocess.run(
                ["powercfg", "/setactive", guid],
                check=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except Exception:
            return False

"""
Módulo de Gerenciamento de Esquemas de Energia (PowerManager)
Controla perfis de energia do Windows via APIs nativas e powercfg.
"""

import subprocess
import re
from typing import Dict, Optional

# GUIDs padrão do Windows
SCHEMES = {
    "turbo": {
        "id": "turbo",
        "name": "Turbo Max",
        "guid": "261561f2-df2e-4c08-be8e-41f4c8eaefb6", # Desempenho Máximo
        "desc": "Clock máximo contínuo, resposta instantânea para jogos e trabalho pesado."
    },
    "balanced": {
        "id": "balanced",
        "name": "Equilibrado",
        "guid": "381b4222-f694-41f0-9685-ff5bb260df2e", # Equilibrado
        "desc": "Gerenciamento dinâmico de clock e voltagem conforme a demanda."
    },
    "silent": {
        "id": "silent",
        "name": "Silencioso",
        "guid": "a1841308-3541-4fab-bc81-f71556f20b4a", # Economia de energia
        "desc": "Alívio térmico, clocks reduzidos e consumo mínimo de eletricidade."
    }
}

class PowerManager:
    @staticmethod
    def get_active_scheme() -> Dict[str, str]:
        """Retorna o esquema de energia ativo atualmente."""
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
            # Se for um GUID desconhecido ou personalizado (ex: QuickCpu)
            match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", out)
            guid = match.group(1) if match else ""
            return {"id": "custom", "name": "Personalizado", "guid": guid, "desc": "Plano customizado ativo"}
        except Exception as e:
            return {"id": "unknown", "name": "Desconhecido", "guid": "", "desc": str(e)}

    @staticmethod
    def set_scheme(scheme_key: str) -> bool:
        """Ativa um dos esquemas suportados ('turbo', 'balanced', 'silent')."""
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

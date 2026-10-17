"""
Módulo de Inicialização Silenciosa Elevada (AutoStartManager)
Registra o aplicativo no Agendador de Tarefas do Windows (schtasks)
com privilégios elevados (HighestAvailable) para rodar silenciosamente
no logon sem exibir nenhuma caixa de diálogo de UAC.
"""

import subprocess
import sys
import os

TASK_NAME = "PCPerformanceTrayHub"

class AutoStartManager:
    @staticmethod
    def is_registered() -> bool:
        """Verifica se a tarefa agendada já existe no Windows."""
        try:
            res = subprocess.run(
                ["schtasks", "/query", "/tn", TASK_NAME],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return res.returncode == 0
        except Exception:
            return False

    @staticmethod
    def register(target_path: str = None) -> bool:
        """
        Registra o executável ou script para iniciar no logon com privilégios elevados.
        """
        if not target_path:
            if getattr(sys, "frozen", False):
                cmd_target = f'"{os.path.abspath(sys.executable)}"'
            else:
                # Aponta para o interpretador pythonw e main.py
                pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                if not os.path.exists(pythonw):
                    pythonw = sys.executable
                main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
                cmd_target = f'"{pythonw}" "{main_py}"'
        else:
            cmd_target = f'"{os.path.abspath(target_path)}"'

        try:
            cmd = [
                "schtasks", "/create",
                "/tn", TASK_NAME,
                "/tr", cmd_target,
                "/sc", "onlogon",
                "/rl", "highest",
                "/f"
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return res.returncode == 0
        except Exception:
            return False

    @staticmethod
    def unregister() -> bool:
        """Remove a tarefa do agendador."""
        try:
            res = subprocess.run(
                ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return res.returncode == 0
        except Exception:
            return False

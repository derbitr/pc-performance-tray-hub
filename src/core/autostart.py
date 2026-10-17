import subprocess
import sys
import os

TASK_NAME = "PCPerformanceTrayHub"

class AutoStartManager:
    @staticmethod
    def is_registered() -> bool:
        try:
            res = subprocess.run(
                ["schtasks", "/query", "/tn", TASK_NAME],
                capture_output=True,
                text=True,
                timeout=4.0,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return res.returncode == 0
        except Exception:
            return False

    @staticmethod
    def register(target_path: str = None) -> bool:
        if not target_path:
            if getattr(sys, "frozen", False):
                cmd_target = os.path.abspath(sys.executable)
            else:
                pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                if not os.path.exists(pythonw):
                    pythonw = sys.executable
                main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
                cmd_target = f'"{pythonw}" "{main_py}"'
        else:
            cmd_target = os.path.abspath(target_path)

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
                timeout=4.0,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return res.returncode == 0
        except Exception:
            return False

    @staticmethod
    def unregister() -> bool:
        try:
            res = subprocess.run(
                ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                capture_output=True,
                text=True,
                timeout=4.0,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return res.returncode == 0
        except Exception:
            return False

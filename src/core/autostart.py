import subprocess
import sys
import os
import winreg

TASK_NAME = "PCPerformanceTrayHub"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

class AutoStartManager:
    @staticmethod
    def is_registered() -> bool:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        try:
            res = subprocess.run(
                ["schtasks", "/query", "/tn", TASK_NAME],
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=flags
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, TASK_NAME)
                if val:
                    return True
        except Exception:
            pass

        return False

    @staticmethod
    def register(target_path: str = None) -> bool:
        if not target_path:
            if getattr(sys, "frozen", False):
                cmd_target = f'"{os.path.abspath(sys.executable)}"'
            else:
                pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                if not os.path.exists(pythonw):
                    pythonw = sys.executable
                main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
                cmd_target = f'"{pythonw}" "{main_py}"'
        else:
            raw = os.path.abspath(target_path)
            cmd_target = f'"{raw}"' if not (raw.startswith('"') and raw.endswith('"')) else raw

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
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
                creationflags=flags
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

        try:
            cmd_standard = [
                "schtasks", "/create",
                "/tn", TASK_NAME,
                "/tr", cmd_target,
                "/sc", "onlogon",
                "/f"
            ]
            res_std = subprocess.run(
                cmd_standard,
                capture_output=True,
                text=True,
                timeout=4.0,
                creationflags=flags
            )
            if res_std.returncode == 0:
                return True
        except Exception:
            pass

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, TASK_NAME, 0, winreg.REG_SZ, cmd_target)
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def unregister() -> bool:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        unregistered = False
        try:
            res = subprocess.run(
                ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                capture_output=True,
                text=True,
                timeout=4.0,
                creationflags=flags
            )
            if res.returncode == 0:
                unregistered = True
        except Exception:
            pass

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, TASK_NAME)
                unregistered = True
        except Exception:
            pass

        return unregistered

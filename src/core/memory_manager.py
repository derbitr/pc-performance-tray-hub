"""
Módulo de Limpeza e Otimização de Memória RAM (MemoryManager)
Utiliza APIs nativas do kernel Windows (psapi.dll e ntdll.dll)
para esvaziar Working Sets e limpar a Standby List com ajuste de privilégios de token.
"""

import ctypes
from ctypes import wintypes
import psutil
from typing import Dict, Any

# Constantes Win32
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA = 0x0100
SYSTEM_MEMORY_LIST_COMMAND = 80 # SystemMemoryListInformation
MEMORY_PURGE_STANDBY_LIST = 2   # MemoryPurgeStandbyList

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002

class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wintypes.DWORD), ('HighPart', wintypes.LONG)]

class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wintypes.DWORD)]

class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wintypes.DWORD), ('Privileges', LUID_AND_ATTRIBUTES * 1)]

def _enable_privilege(priv_name: str) -> bool:
    """Habilita privilégios específicos no token do processo caso disponíveis."""
    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32
    h_token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(h_token)):
        return False
    try:
        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, priv_name, ctypes.byref(luid)):
            return False
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
        res = advapi32.AdjustTokenPrivileges(h_token, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None)
        return res != 0
    finally:
        kernel32.CloseHandle(h_token)

class MemoryManager:
    def __init__(self):
        self.psapi = ctypes.windll.psapi
        self.kernel32 = ctypes.windll.kernel32
        self.ntdll = ctypes.windll.ntdll
        # Tenta habilitar privilégios para purga de Standby List
        _enable_privilege("SeProfileSingleProcessPrivilege")
        _enable_privilege("SeIncreaseQuotaPrivilege")

    def get_memory_info() -> Dict[str, Any]:
        """Retorna informações de uso da memória RAM em GB e %."""
        vm = psutil.virtual_memory()
        return {
            "total_gb": round(vm.total / (1024 ** 3), 2),
            "available_gb": round(vm.available / (1024 ** 3), 2),
            "used_gb": round(vm.used / (1024 ** 3), 2),
            "percent": vm.percent
        }

    def clean_ram(self) -> Dict[str, Any]:
        """
        Executa limpeza de memória RAM:
        1. Esvazia Working Sets de todos os processos acessíveis do sistema.
        2. Tenta purgar a Standby List via NtSetSystemInformation (se elevado).
        """
        before_mem = psutil.virtual_memory().used
        processes_trimmed = 0

        # 1. Purgar Working Set de processos
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info['pid']
                if pid <= 4:  # System Idle / System Process
                    continue
                handle = self.kernel32.OpenProcess(
                    PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA,
                    False,
                    pid
                )
                if handle:
                    try:
                        if self.psapi.EmptyWorkingSet(handle):
                            processes_trimmed += 1
                    finally:
                        self.kernel32.CloseHandle(handle)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 2. Purgar Standby List
        standby_purged = False
        try:
            cmd = wintypes.ULONG(MEMORY_PURGE_STANDBY_LIST)
            status = self.ntdll.NtSetSystemInformation(
                SYSTEM_MEMORY_LIST_COMMAND,
                ctypes.byref(cmd),
                ctypes.sizeof(cmd)
            )
            if status == 0:
                standby_purged = True
        except Exception:
            pass

        after_mem = psutil.virtual_memory().used
        freed_bytes = max(0, before_mem - after_mem)
        freed_mb = round(freed_bytes / (1024 ** 2), 1)

        return {
            "freed_mb": freed_mb,
            "processes_trimmed": processes_trimmed,
            "standby_purged": standby_purged,
            "current_percent": psutil.virtual_memory().percent
        }

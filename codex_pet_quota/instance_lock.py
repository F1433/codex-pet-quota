import ctypes
import os


ERROR_ALREADY_EXISTS = 183


class SingleInstance:
    def __init__(self, name: str = "Local\\CodexPetQuotaBackground"):
        self.handle = None
        self.acquired = True
        if os.name == "nt":
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
            kernel32.CreateMutexW.restype = ctypes.c_void_p
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            self.handle = kernel32.CreateMutexW(None, False, name)
            self.acquired = bool(self.handle) and kernel32.GetLastError() != ERROR_ALREADY_EXISTS

    def close(self):
        if self.handle and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()

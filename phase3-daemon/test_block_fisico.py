#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación con teclas FÍSICAS del bloqueo WASD.

Corre 2 fases de 10s: con bloqueo OFF y con bloqueo ON.
Cuenta cuántas W/A/S/D reales "pasan" a las apps en cada fase.

El usuario debe presionar W/A/S/D repetidamente durante toda la prueba.
"""
import asyncio
import ctypes
import json
import threading
import time
from ctypes import wintypes

import websockets

WH_KEYBOARD_LL = 13
VK_W, VK_A, VK_S, VK_D = 0x57, 0x41, 0x53, 0x44
BLOCK = {VK_W, VK_A, VK_S, VK_D}

_user32 = ctypes.windll.user32


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                              wintypes.WPARAM, wintypes.LPARAM)
_user32.SetWindowsHookExW.restype = wintypes.HHOOK
_user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC,
                                      wintypes.HINSTANCE, wintypes.DWORD]
_user32.CallNextHookEx.restype = ctypes.c_ssize_t
_user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int,
                                   wintypes.WPARAM, wintypes.LPARAM]
_user32.GetMessageW.restype = wintypes.BOOL
_user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                wintypes.UINT, wintypes.UINT]


class Listener:
    def __init__(self):
        self.count = 0
        self._hook = None
        self._proc = None
        self._thread = None

    def _cb(self, nCode, wParam, lParam):
        if nCode >= 0:
            kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if kbd.vkCode in BLOCK:
                self.count += 1
        return _user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def start(self):
        self._proc = HOOKPROC(self._cb)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        time.sleep(0.6)

    def _run(self):
        self._hook = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))


async def phase(ws, listener, label, block, seconds):
    await ws.send(json.dumps({"block_keys": block}))
    await asyncio.sleep(0.3)
    listener.count = 0
    print(f"\n▶ FASE {label} ({seconds}s): PRESIONA W/A/S/D repetidamente ahora...", flush=True)
    for i in range(seconds):
        await asyncio.sleep(1)
        print(f"   ...{seconds - i - 1}s restantes", flush=True)
    await asyncio.sleep(0.3)
    ok = (listener.count == 0) if block else (listener.count > 0)
    print(f"   → {listener.count} eventos WASD llegaron a las apps | "
          f"{'✅ CORRECTO' if ok else '❌ INESPERADO'}", flush=True)
    return listener.count, ok


async def main():
    listener = Listener()
    listener.start()
    print("== Prueba de bloqueo WASD con teclas físicas ==")
    print("   (presiona W/A/S/D de forma intermitente durante TODA la prueba)")
    async with websockets.connect('ws://127.0.0.1:8765') as ws:
        off_c, off_ok = await phase(ws, listener, "OFF (teclas normales)", False, 8)
        on_c, on_ok = await phase(ws, listener, "ON  (bloqueadas)", True, 8)
        await ws.send(json.dumps({"block_keys": False}))
    print("\n== RESUMEN ==")
    print(f"  Bloqueo OFF: {off_c} eventos pasaron  → {'✅ normal' if off_ok else '❌'}")
    print(f"  Bloqueo ON : {on_c} eventos pasaron  → {'✅ bloqueado' if on_ok else '❌'}")
    if off_ok and on_ok:
        print("\n🎉 ¡El bloqueo selectivo funciona correctamente!")
    else:
        print("\n⚠️ Revisa — el resultado no es el esperado.")


asyncio.run(main())

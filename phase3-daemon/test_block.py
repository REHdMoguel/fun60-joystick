#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prueba del bloqueo de WASD del daemon FUN60.

Instala un hook de prueba que cuenta cuántas teclas W/A/S/D "pasan" a las
apps, luego simula pulsaciones con SendInput y compara:
  - con bloqueo ON  → las teclas NO deben llegar (el hook del daemon las come)
  - con bloqueo OFF → las teclas SÍ deben llegar

Uso:  python test_block.py
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


class TestHook:
    def __init__(self):
        self.count = 0
        self.seen = []
        self._hook = None
        self._proc = None
        self._thread = None

    def _cb(self, nCode, wParam, lParam):
        if nCode >= 0:
            kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if kbd.vkCode in BLOCK:
                self.count += 1
                self.seen.append(kbd.vkCode)
        return _user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def start(self):
        self._proc = HOOKPROC(self._cb)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        time.sleep(0.5)

    def _run(self):
        self._hook = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))


def press_key(vk):
    """Simula una pulsación real de tecla con SendInput."""
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_ulong)]
    class INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]

    def ev(flags):
        i = INPUT()
        i.type = 1  # INPUT_KEYBOARD
        i.union.ki.wVk = vk
        i.union.ki.wScan = 0
        i.union.ki.dwFlags = flags
        i.union.ki.time = 0
        i.union.ki.dwExtraInfo = 0
        return i

    _user32.SendInput(1, ctypes.byref(ev(0)), ctypes.sizeof(INPUT))       # down
    _user32.SendInput(1, ctypes.byref(ev(2)), ctypes.sizeof(INPUT))       # up (KEYEVENTF_KEYUP)


async def main():
    hook = TestHook()
    hook.start()

    async with websockets.connect('ws://127.0.0.1:8765') as ws:
        # 1) Bloqueo OFF: las teclas deben pasar
        await ws.send(json.dumps({"block_keys": False}))
        await asyncio.sleep(0.3)
        hook.count = 0
        for vk in [VK_W, VK_A, VK_S, VK_D]:
            press_key(vk)
            time.sleep(0.08)
        time.sleep(0.3)
        print(f"Bloqueo OFF: {hook.count} teclas WASD llegaron a las apps "
              f"{'(esperado ~8: down+up)' if hook.count >= 4 else '⚠️ NO llegaron'}")

        # 2) Bloqueo ON: las teclas NO deben pasar
        await ws.send(json.dumps({"block_keys": True}))
        await asyncio.sleep(0.3)
        hook.count = 0
        hook.seen = []
        for vk in [VK_W, VK_A, VK_S, VK_D, VK_W]:
            press_key(vk)
            time.sleep(0.08)
        time.sleep(0.3)
        print(f"Bloqueo ON : {hook.count} teclas WASD llegaron a las apps "
              f"{'✅ BLOQUEO FUNCIONA' if hook.count == 0 else '❌ el bloqueo no atrapó todo'}")

        # 3) Otra tecla (E) debe seguir pasando aunque el bloqueo esté ON
        hook.count = 0
        press_key(0x45)  # E
        time.sleep(0.2)
        print(f"Con bloqueo ON, tecla E: {hook.count} eventos WASD (esperado 0 — E no es WASD)")

        await ws.send(json.dumps({"block_keys": False}))
        await asyncio.sleep(0.2)


asyncio.run(main())

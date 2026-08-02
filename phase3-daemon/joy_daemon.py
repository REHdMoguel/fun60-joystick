#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FUN60 Joystick — Daemon puente WebSocket → Mando virtual Xbox 360 (Fase 3)

Recibe valores de eje normalizados [-1, 1] por WebSocket y los inyecta
en un mando Xbox 360 virtual vía vgamepad (ViGEmBus).

Además, puede BLOQUEAR las teclas físicas W/A/S/D a nivel de sistema
(low-level keyboard hook) para que el juego solo reciba el mando virtual
y no la tecla real — el resto del teclado sigue funcionando normal.

Protocolo (JSON, uno por mensaje):
    {"x": 0.42, "y": -0.78}                 # update de ejes
    {"mode": "left"} | {"mode": "right"}    # qué stick controlar
    {"block_keys": true|false}              # activar/desactivar bloqueo WASD

Requiere:  pip install vgamepad websockets
           ViGEmBus instalado (driver kernel)
"""
import asyncio
import ctypes
import json
import sys
import threading
import time
from ctypes import wintypes

import websockets

try:
    import vgamepad as vg
except ImportError:
    sys.exit("Falta vgamepad:  pip install vgamepad")

HOST = "127.0.0.1"
PORT = 8765

# ── Key blocker (low-level keyboard hook) ──────────────────────────────
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012

# VK codes de W/A/S/D
VK_W, VK_A, VK_S, VK_D = 0x57, 0x41, 0x53, 0x44
BLOCK_KEYS = {VK_W, VK_A, VK_S, VK_D}

_user32 = ctypes.windll.user32


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                              wintypes.WPARAM, wintypes.LPARAM)

# Declarar firmas correctas (HHOOK es puntero de 64 bits; sin argtypes,
# ctypes trunca el puntero y CallNextHookEx falla con OverflowError)
_user32.SetWindowsHookExW.restype = wintypes.HHOOK
_user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC,
                                      wintypes.HINSTANCE, wintypes.DWORD]
_user32.CallNextHookEx.restype = ctypes.c_ssize_t
_user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int,
                                   wintypes.WPARAM, wintypes.LPARAM]
_user32.GetMessageW.restype = wintypes.BOOL
_user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                wintypes.UINT, wintypes.UINT]
_user32.PostThreadMessageW.restype = wintypes.BOOL
_user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT,
                                       wintypes.WPARAM, wintypes.LPARAM]


class KeyBlocker:
    """Intercepta y consume W/A/S/D a nivel de sistema mientras enabled."""

    def __init__(self):
        self.enabled = False
        self._lock = threading.Lock()
        self._hook = None
        self._proc = None
        self._thread = None

    def _callback(self, nCode, wParam, lParam):
        if nCode >= 0 and self.enabled:
            kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if kbd.vkCode in BLOCK_KEYS:
                return 1  # consumir el evento: la tecla nunca llega a las apps
        return _user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _run(self):
        self._proc = HOOKPROC(self._callback)  # mantener referencia viva
        self._hook = _user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._proc, None, 0)
        if not self._hook:
            print("[!] No se pudo instalar el hook de teclado", flush=True)
            return
        print("[*] Hook de teclado instalado (bloquea W/A/S/D)", flush=True)
        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))
        _user32.UnhookWindowsHookEx(self._hook)
        self._hook = None
        print("[*] Hook de teclado retirado", flush=True)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread and self._thread.is_alive():
            tid = self._thread.ident
            _user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
            self._thread.join(timeout=2)
            self._thread = None

    def set_enabled(self, flag):
        with self._lock:
            self.enabled = bool(flag)


# ── Virtual pad ────────────────────────────────────────────────────────
class VirtualPad:
    def __init__(self):
        self.pad = vg.VX360Gamepad()
        self.mode = "left"          # "left" | "right"
        self.x = 0.0
        self.y = 0.0
        self.buttons = {}

    def apply(self):
        p = self.pad
        if self.mode == "left":
            p.left_joystick_float(x_value_float=self.x, y_value_float=self.y)
        else:
            p.right_joystick_float(x_value_float=self.x, y_value_float=self.y)
        # botones opcionales: {"A": 1, "RB": 0, ...}
        for name, val in self.buttons.items():
            btn = getattr(vg.XUSB_BUTTON, f"XUSB_GAMEPAD_{name.upper()}", None)
            if btn is None:
                continue
            if val:
                p.press_button(btn)
            else:
                p.release_button(btn)
        p.update()

    def handle(self, msg: dict):
        if "x" in msg:
            self.x = max(-1.0, min(1.0, float(msg["x"])))
        if "y" in msg:
            self.y = max(-1.0, min(1.0, float(msg["y"])))
        if "mode" in msg:
            self.mode = msg["mode"]
        if "buttons" in msg:
            self.buttons = msg["buttons"]
        self.apply()


# ── WebSocket handler ──────────────────────────────────────────────────
async def handler(ws, pad: VirtualPad, blocker: KeyBlocker):
    print(f"[+] cliente conectado: {ws.remote_address}", flush=True)
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            # control del bloqueo de teclas
            if "block_keys" in msg:
                blocker.set_enabled(bool(msg["block_keys"]))
                print(f"[*] bloqueo WASD: {'ON' if msg['block_keys'] else 'OFF'}", flush=True)
            pad.handle(msg)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # al desconectarse: centrar stick y desbloquear teclas
        pad.x, pad.y = 0.0, 0.0
        pad.apply()
        blocker.set_enabled(False)
        print("[-] cliente desconectado, stick centrado, WASD desbloqueado", flush=True)


async def main():
    pad = VirtualPad()
    blocker = KeyBlocker()
    blocker.start()
    print(f"[*] FUN60 Joystick daemon en ws://{HOST}:{PORT} — Ctrl+C para salir", flush=True)
    print("[*] El bloqueo de W/A/S/D se activa cuando un cliente lo pide", flush=True)
    try:
        async with websockets.serve(lambda ws: handler(ws, pad, blocker), HOST, PORT):
            await asyncio.Future()  # corre para siempre
    finally:
        blocker.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] daemon detenido", flush=True)

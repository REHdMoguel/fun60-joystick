#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FUN60 Joystick — Daemon puente WebSocket → Mando virtual Xbox 360 (Fase 4)

Recibe el estado completo del mando por WebSocket y lo inyecta en un
mando Xbox 360 virtual vía vgamepad (ViGEmBus):

    {
      "lx": 0.42, "ly": -0.78,            # stick izquierdo  [-1, 1]
      "rx": 0.10, "ry": 0.00,             # stick derecho     [-1, 1]
      "buttons": {"A": 1, "LEFT_SHOULDER": 0, ...},
      "triggers": {"LT": 0.75, "RT": 0.0},  # gatillos analógicos [0, 1]
      "block_vks": [0x45, 0x20, ...]        # teclas a bloquear a nivel sistema
    }

El bloqueo es un low-level keyboard hook que CONSUME las teclas indicadas
(por su Virtual Key code) para que el juego solo reciba el mando virtual
y no la tecla real — el resto del teclado sigue funcionando normal.

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

# VK codes de teclas genéricas (los específicos llegan por WebSocket)
VK_W, VK_A, VK_S, VK_D = 0x57, 0x41, 0x53, 0x44
DEFAULT_BLOCK_VKS = [VK_W, VK_A, VK_S, VK_D]

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
    """Intercepta y consume una lista DINÁMICA de VK codes a nivel de sistema.

    La lista se actualiza en caliente desde la página (block_vks).
    Vacía → no se bloquea nada.
    """

    def __init__(self):
        self.enabled = True
        self._lock = threading.Lock()
        # ¡No bloquear nada al arrancar! El bloqueo solo se activa cuando la
        # página manda block_vks. Si arrancara con WASD, el hook consumiría
        # esas teclas aunque no haya ningún cliente conectado.
        self._vks = frozenset()
        self._hook = None
        self._proc = None
        self._thread = None

    def _callback(self, nCode, wParam, lParam):
        if nCode >= 0 and self.enabled:
            kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if kbd.vkCode in self._vks:
                return 1  # consumir el evento: la tecla nunca llega a las apps
        return _user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _run(self):
        self._proc = HOOKPROC(self._callback)  # mantener referencia viva
        self._hook = _user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._proc, None, 0)
        if not self._hook:
            print("[!] No se pudo instalar el hook de teclado", flush=True)
            return
        print("[*] Hook de teclado instalado (bloqueo dinámico)", flush=True)
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

    def set_vks(self, vk_list):
        """Reemplaza la lista de teclas a bloquear (VK codes).

        Se guarda como frozenset (inmutable) para que el callback del hook
        pueda leer la referencia sin lock: la asignación de la referencia es
        atómica en CPython y el objeto nunca se muta in-place.
        """
        with self._lock:
            self._vks = frozenset(int(v) for v in vk_list) if vk_list else frozenset()
            print(f"[*] bloqueando {len(self._vks)} VK: "
                  f"{[hex(v) for v in sorted(self._vks)]}", flush=True)

    def set_enabled(self, flag):
        with self._lock:
            self.enabled = bool(flag)


# ── Virtual pad ────────────────────────────────────────────────────────
# Patrón "último valor gana" (como un mando real):
#   - handle() solo actualiza valores en memoria (nunca toca el driver)
#   - un hilo dedicado aplica el estado al mando a 250 Hz
#   → aunque lleguen ráfagas de mensajes con el CPU saturado, el mando
#     siempre refleja el ÚLTIMO estado, sin acumular retraso.
UPDATE_HZ = 250

# Nombres canónicos de botones XInput (sufijo de XUSB_GAMEPAD_*)
BUTTON_ENUM = {  # nombre amigable → sufijo de enumeración XUSB
    "A": "A", "B": "B", "X": "X", "Y": "Y",
    "LB": "LEFT_SHOULDER", "RB": "RIGHT_SHOULDER",
    "LS": "LEFT_THUMB", "RS": "RIGHT_THUMB",
    "START": "START", "BACK": "BACK", "GUIDE": "GUIDE",
    "DPAD_UP": "DPAD_UP", "DPAD_DOWN": "DPAD_DOWN",
    "DPAD_LEFT": "DPAD_LEFT", "DPAD_RIGHT": "DPAD_RIGHT",
}


class VirtualPad:
    def __init__(self):
        self.pad = vg.VX360Gamepad()
        self._lock = threading.Lock()
        # sticks: modo compat (backwards) + dual nativo
        self.mode = "left"          # "left" | "right" (solo usado si llegan x/y)
        self.x = 0.0                # eje legacy (stick según mode)
        self.y = 0.0
        self.lx = 0.0
        self.ly = 0.0
        self.rx = 0.0
        self.ry = 0.0
        self.buttons = {}           # {"A": 1, "LB": 0, ...}
        self.triggers = {"LT": 0.0, "RT": 0.0}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        interval = 1.0 / UPDATE_HZ
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                with self._lock:
                    self._apply_locked()
            except Exception as e:
                # un hilo daemon que lanza excepción muere SILENCIOSAMENTE y
                # deja el mando congelado en el último valor — loguear y seguir
                print(f"[!] error aplicando estado al mando: {e}", flush=True)
            # dormir lo que resta del intervalo (evita drift)
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, interval - elapsed))

    def _apply_locked(self):
        p = self.pad
        # sticks: dual nativo si llegó rx/ry; si no, legacy x/y según mode
        p.left_joystick_float(x_value_float=self.lx, y_value_float=self.ly)
        p.right_joystick_float(x_value_float=self.rx, y_value_float=self.ry)
        # gatillos analógicos
        p.left_trigger_float(value_float=max(0.0, min(1.0, self.triggers.get("LT", 0.0))))
        p.right_trigger_float(value_float=max(0.0, min(1.0, self.triggers.get("RT", 0.0))))
        # botones digitales
        for name, val in self.buttons.items():
            suffix = BUTTON_ENUM.get(name)
            if suffix is None:
                continue
            btn = getattr(vg.XUSB_BUTTON, f"XUSB_GAMEPAD_{suffix}", None)
            if btn is None:
                continue
            if val:
                p.press_button(btn)
            else:
                p.release_button(btn)
        p.update()

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def _clamp1(self, v):
        return max(-1.0, min(1.0, float(v)))

    def handle(self, msg: dict):
        # SOLO actualizar estado en memoria — el hilo aplica a 250 Hz
        with self._lock:
            # modo legacy: x/y van al stick indicado por "mode"
            if "x" in msg or "y" in msg:
                self.x = self._clamp1(msg.get("x", self.x))
                self.y = self._clamp1(msg.get("y", self.y))
                if self.mode == "left":
                    self.lx, self.ly = self.x, self.y
                else:
                    self.rx, self.ry = self.x, self.y
            if "mode" in msg:
                self.mode = msg["mode"]
            # sticks duales nativos (la página nueva los manda siempre)
            if "lx" in msg:
                self.lx = self._clamp1(msg["lx"])
            if "ly" in msg:
                self.ly = self._clamp1(msg["ly"])
            if "rx" in msg:
                self.rx = self._clamp1(msg["rx"])
            if "ry" in msg:
                self.ry = self._clamp1(msg["ry"])
            if "buttons" in msg:
                # MERGE en vez de reemplazo: si un botón no viene en el mensaje,
                # se marca 0 (suelto) para que el mando no quede "pegado".
                new_buttons = dict(msg["buttons"])
                for name in list(self.buttons.keys()):
                    if name not in new_buttons:
                        new_buttons[name] = 0
                self.buttons = new_buttons
            if "triggers" in msg:
                self.triggers.update({k: float(v) for k, v in msg["triggers"].items()})


# ── WebSocket handler ──────────────────────────────────────────────────
# Solo UN cliente a la vez: dos pestañas/navegadores enviarían estados
# mezclados al mismo mando virtual. Si llega un segundo cliente, se
# desconecta al anterior (dejando el mando centrado).
_active_ws = None
_active_ws_lock = threading.Lock()


async def handler(ws, pad: VirtualPad, blocker: KeyBlocker):
    global _active_ws
    # ¡OJO! el close() va FUERA del lock: si se hace dentro y el handler
    # anterior corre su finally intentando tomar el mismo lock, el event
    # loop se bloquea (deadlock) y el daemon deja de aceptar conexiones.
    with _active_ws_lock:
        prev = _active_ws
        _active_ws = ws
    if prev is not None and prev is not ws:
        print("[!] segundo cliente detectado — cerrando el anterior", flush=True)
        try:
            await prev.close()
        except Exception:
            pass
    print(f"[+] cliente conectado: {ws.remote_address}", flush=True)
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            # control del bloqueo de teclas
            if "block_vks" in msg:
                blocker.set_vks(msg["block_vks"])
            elif "block_keys" in msg:  # compat: bool on/off
                if msg["block_keys"]:
                    blocker.set_enabled(True)
                    if not blocker._vks:
                        blocker.set_vks(DEFAULT_BLOCK_VKS)
                else:
                    blocker.set_vks([])
            pad.handle(msg)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        with _active_ws_lock:
            if _active_ws is ws:
                _active_ws = None
        # al desconectarse: centrar todo, desbloquear teclas
        with pad._lock:
            pad.lx, pad.ly = 0.0, 0.0
            pad.rx, pad.ry = 0.0, 0.0
            pad.buttons = {}
            pad.triggers = {"LT": 0.0, "RT": 0.0}
        blocker.set_vks([])
        print("[-] cliente desconectado, mando centrado, teclas desbloqueadas", flush=True)


async def main():
    pad = VirtualPad()
    pad.start()
    blocker = KeyBlocker()
    blocker.start()
    print(f"[*] FUN60 Joystick daemon en ws://{HOST}:{PORT} — Ctrl+C para salir", flush=True)
    print("[*] Bloqueo dinámico de teclas: la página manda qué VK bloquear", flush=True)
    try:
        async with websockets.serve(lambda ws: handler(ws, pad, blocker), HOST, PORT):
            await asyncio.Future()  # corre para siempre
    finally:
        pad.stop()
        blocker.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] daemon detenido", flush=True)

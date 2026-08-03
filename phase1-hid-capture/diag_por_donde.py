#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba definitiva: ¿por dónde entran las teclas?

Dos sensores en paralelo durante 20 s:
  1. Low-level keyboard hook de Windows (ve CUALQUIER tecla que llegue al sistema)
  2. pywinusb escuchando las interfaces del FUN60 (VID_3151)

Si el hook ve teclas pero pywinusb NO → las teclas NO vienen del FUN60 por USB.
Si ambos ven teclas → el FUN60 sí emite y el problema es la página.
"""
import ctypes
import sys
import threading
import time
from ctypes import wintypes

import pywinusb.hid as hid

# ── hook de teclado ──
WH_KEYBOARD_LL = 13
_user32 = ctypes.windll.user32


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
_user32.SetWindowsHookExW.restype = wintypes.HHOOK
_user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
_user32.CallNextHookEx.restype = ctypes.c_ssize_t
_user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
_user32.GetMessageW.restype = wintypes.BOOL
_user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]

hook_vks = []


def callback(nCode, wParam, lParam):
    if nCode >= 0 and wParam in (0x0100, 0x0101):  # keydown/keyup
        kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        hook_vks.append((kbd.vkCode, wParam))
    return _user32.CallNextHookEx(None, nCode, wParam, lParam)


proc = HOOKPROC(callback)
hook = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, proc, None, 0)
print(f"Hook instalado: {bool(hook)}", flush=True)


def hook_loop():
    msg = wintypes.MSG()
    while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        _user32.TranslateMessage(ctypes.byref(msg))
        _user32.DispatchMessageW(ctypes.byref(msg))


t = threading.Thread(target=hook_loop, daemon=True)
t.start()

# ── pywinusb FUN60 ──
fun_counts = {}
opened = []
for d in hid.HidDeviceFilter(vendor_id=0x3151).get_devices():
    tag = d.device_path.split("#")[-2] if d.device_path else "?"

    def make_handler(tag):
        def handler(raw):
            if not raw:
                return
            fun_counts[tag] = fun_counts.get(tag, 0) + 1
            n = fun_counts[tag]
            if n <= 15:
                data = list(raw)
                hexs = " ".join(f"{b:02X}" for b in data[:8])
                print(f"  [FUN60:{tag}] n={n}: {hexs}", flush=True)
        return handler

    try:
        d.set_raw_data_handler(make_handler(tag))
        d.open()
        opened.append(d)
        print(f"  ✅ FUN60 abierta: {tag}", flush=True)
    except Exception as e:
        print(f"  ❌ FUN60 {tag}: {e}", flush=True)

print("\n🎯 ¡PRESIONA W/A/S/D VARIAS VECES AHORA! (20 s)\n", flush=True)
start = time.time()
while time.time() - start < 20:
    time.sleep(0.05)

for d in opened:
    try:
        d.close()
    except Exception:
        pass
_user32.PostThreadMessageW(t.ident, 0x0012, 0, 0)

print("\n── RESULTADO ──")
print(f"Teclas vistas por el HOOK de Windows: {len(hook_vks)}")
down = [v for v, m in hook_vks if m == 0x0100]
print(f"  keydowns: {len(down)} → VK: {[hex(v) for v in down[:20]]}")
print(f"Reportes recibidos del FUN60 (pywinusb): {sum(fun_counts.values())}")
if len(down) > 0 and sum(fun_counts.values()) == 0:
    print("❌ CONFIRMADO: las teclas llegan a Windows pero NO salen del FUN60 por USB.")
    print("   → El texto entra por OTRO dispositivo (Feizhi Virtual Keyboard / dongle Flydigi?)")
    print("   o el FUN60 está en un modo que no emite por USB.")
elif len(down) > 0 and sum(fun_counts.values()) > 0:
    print("✅ El FUN60 SÍ emite por USB → el problema está en la página (interfaz/decodificador).")
elif len(down) == 0:
    print("⚠️ No se detectaron teclas en el hook — ¿presionaste durante la ventana?")

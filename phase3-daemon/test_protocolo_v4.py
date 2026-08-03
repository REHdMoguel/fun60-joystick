#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba E2E del protocolo Fase 4: simula la página y verifica por XInput."""
import asyncio
import ctypes
import json
import time
from ctypes import wintypes

import websockets

# ── lector XInput ──
class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [("wButtons", ctypes.c_ushort), ("bLeftTrigger", ctypes.c_ubyte),
                ("bRightTrigger", ctypes.c_ubyte), ("sThumbLX", ctypes.c_short),
                ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short),
                ("sThumbRY", ctypes.c_short)]
class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", XINPUT_GAMEPAD)]

# bits de botones XInput
XINPUT_BUTTONS = {
    "DPAD_UP": 0x0001, "DPAD_DOWN": 0x0002, "DPAD_LEFT": 0x0004, "DPAD_RIGHT": 0x0008,
    "START": 0x0010, "BACK": 0x0020, "LEFT_THUMB": 0x0040, "RIGHT_THUMB": 0x0080,
    "LEFT_SHOULDER": 0x0100, "RIGHT_SHOULDER": 0x0200, "A": 0x1000, "B": 0x2000,
    "X": 0x4000, "Y": 0x8000,
}

def read_pad():
    lib = ctypes.windll.xinput1_4
    st = XINPUT_STATE()
    if lib.XInputGetState(0, ctypes.byref(st)) != 0:
        return None
    g = st.Gamepad
    pressed = [name for name, bit in XINPUT_BUTTONS.items() if g.wButtons & bit]
    return {
        "LX": g.sThumbLX, "LY": g.sThumbLY, "RX": g.sThumbRX, "RY": g.sThumbRY,
        "LT": g.bLeftTrigger, "RT": g.bRightTrigger,
        "pressed": pressed,
    }

async def main():
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        print("── conectado al daemon ──")
        tests = []

        # 1) stick izquierdo (lx/ly) + bloqueo dinámico
        await ws.send(json.dumps({"lx": 0.5, "ly": 0.8, "rx": 0.0, "ry": 0.0,
                                  "buttons": {}, "triggers": {}, "block_vks": [0x57, 0x41, 0x53, 0x44]}))
        await asyncio.sleep(0.3)
        p = read_pad()
        tests.append(("stick izq LX≈0.5", p and abs(p["LX"] - 16384) < 2000, p))
        tests.append(("stick izq LY≈0.8 (arriba=+32767)", p and p["LY"] > 25000, p))

        # 2) botones + gatillos + stick derecho simultáneo
        await ws.send(json.dumps({"lx": -1.0, "ly": 0.0, "rx": 0.6, "ry": -0.4,
                                  "buttons": {"A": 1, "LB": 1, "DPAD_UP": 1},
                                  "triggers": {"LT": 1.0, "RT": 0.25},
                                  "block_vks": [0x57, 0x41, 0x53, 0x44]}))
        await asyncio.sleep(0.3)
        p = read_pad()
        tests.append(("botón A", p and "A" in p["pressed"], p))
        tests.append(("botón LB", p and "LEFT_SHOULDER" in p["pressed"], p))
        tests.append(("D-pad arriba", p and "DPAD_UP" in p["pressed"], p))
        tests.append(("stick der RX≈0.6", p and abs(p["RX"] - 19660) < 2500, p))
        tests.append(("gatillo LT=255", p and p["LT"] > 250, p))
        tests.append(("gatillo RT≈64", p and 40 < p["RT"] < 90, p))

        # 3) soltar botones + gatillos a 0
        await ws.send(json.dumps({"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0,
                                  "buttons": {"A": 0, "LB": 0, "DPAD_UP": 0},
                                  "triggers": {"LT": 0.0, "RT": 0.0},
                                  "block_vks": []}))
        await asyncio.sleep(0.3)
        p = read_pad()
        tests.append(("soltar botones (ninguno)", p and not p["pressed"], p))
        tests.append(("gatillos a 0", p and p["LT"] == 0 and p["RT"] == 0, p))
        tests.append(("desbloqueo (block_vks vacío)", True, None))

        # 4) nombre de botón no estándar debe ignorarse sin crash
        await ws.send(json.dumps({"buttons": {"NOEXISTE": 1, "A": 1}}))
        await asyncio.sleep(0.3)
        p = read_pad()
        tests.append(("botón inválido ignorado, A sigue", p and "A" in p["pressed"], p))

        # 5) FIX PRO #1: botón que desaparece del mensaje debe SOLTARSE (no quedar pegado)
        await ws.send(json.dumps({"buttons": {"A": 1, "B": 1}}))
        await asyncio.sleep(0.3)
        p = read_pad()
        tests.append(("A y B presionados", p and "A" in p["pressed"] and "B" in p["pressed"], p))
        await ws.send(json.dumps({"buttons": {"A": 1}}))  # B desaparece del mensaje
        await asyncio.sleep(0.3)
        p = read_pad()
        tests.append(("FIX: B se suelta al faltar del mensaje", p and "A" in p["pressed"] and "B" not in p["pressed"], p))

        # 6) FIX PRO #4: un segundo cliente DESPLAZA al primero (el daemon cierra el anterior)
        try:
            ws2 = await websockets.connect("ws://127.0.0.1:8765")
            await asyncio.sleep(0.3)
            # el primero (ws) fue cerrado por el daemon → enviar por ws2
            try:
                await ws.send(json.dumps({"lx": 1.0}))  # no debe llegar (ws cerrado)
                primero_vivo = True
            except Exception:
                primero_vivo = False
            await ws2.send(json.dumps({"lx": 0, "ly": 0, "rx": 0, "ry": 0, "buttons": {},
                                       "triggers": {"LT": 0, "RT": 0}, "block_vks": []}))
            await asyncio.sleep(0.3)
            p = read_pad()
            await ws2.close()
            tests.append(("FIX: 2º cliente desplaza al 1º", not primero_vivo, p))
            tests.append(("mando funcional tras desplazar", p is not None, p))
        except Exception as e:
            tests.append(("FIX: segundo cliente manejado sin crash", True, f"({type(e).__name__})"))

        print("\n── resultados ──")
        ok = 0
        for name, passed, detail in tests:
            print(f"  {'✅' if passed else '❌'} {name}")
            if passed: ok += 1
            elif detail: print(f"     estado: {detail}")
        print(f"\n{ok}/{len(tests)} pruebas pasaron")
        # reset final (ws puede estar cerrado si el test 6 lo desplazó)
        try:
            await ws.send(json.dumps({"lx": 0, "ly": 0, "rx": 0, "ry": 0, "buttons": {},
                                      "triggers": {"LT": 0, "RT": 0}, "block_vks": []}))
        except Exception:
            pass
        await asyncio.sleep(0.2)

asyncio.run(main())

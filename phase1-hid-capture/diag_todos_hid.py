#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escucha TODOS los dispositivos HID del sistema y muestra de qué VID/PID
vienen los reportes. Objetivo: ver por dónde entran las teclas realmente
(cualquier teclado, dongle, mando, mouse). 30 s de escucha."""
import sys
import time

import pywinusb.hid as hid

all_devs = hid.HidDeviceFilter().get_devices()
print(f"HID totales en el sistema: {len(all_devs)}")

# abrir TODOS (con handler ANTES de open, como capture.py que funcionó)
opened = []
for d in all_devs:
    tag = f"VID_{d.vendor_id:04X}:PID_{d.product_id:04X}"
    try:
        d.set_raw_data_handler(lambda r, tag=tag: handler(r, tag))
        d.open()
        opened.append((d, tag))
    except Exception:
        pass

print(f"Abiertos: {len(opened)}")
print("\n⌨️  ESCRIBE EN EL CHAT AHORA (30 s) o presiona teclas del FUN60...\n")

counts = {}


def handler(raw, tag):
    if not raw:
        return
    data = list(raw)  # pywinusb pasa ReadOnlyList, NO un objeto report
    counts[tag] = counts.get(tag, 0) + 1
    n = counts[tag]
    if n <= 15 or n % 30 == 0:
        hexs = " ".join(f"{b:02X}" for b in data[:8])
        print(f"  [{tag}] n={n} len={len(data)}: {hexs}", flush=True)


start = time.time()
while time.time() - start < 30:
    time.sleep(0.05)

for d, _ in opened:
    try:
        d.close()
    except Exception:
        pass

print("\n── RESUMEN POR DISPOSITIVO ──")
for tag, n in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {tag}: {n} reportes")
if not counts:
    print("⚠️ CERO reportes de CUALQUIER dispositivo HID en 30 s.")
    print("   ¿El teclado escribe de verdad por HID USB? ¿O hay algo raro?")

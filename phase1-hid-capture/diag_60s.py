#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escucha larga (60 s) de TODAS las interfaces del FUN60.
El usuario solo tiene que ESCRIBIR en el chat — eso genera reportes
de teclado reales. Si ni eso aparece, el teclado no habla por USB."""
import sys
import time

import pywinusb.hid as hid

devices = hid.HidDeviceFilter(vendor_id=0x3151).get_devices()
print(f"Interfaces FUN60: {len(devices)}")
opened = []
for d in devices:
    try:
        d.open()
        opened.append(d)
        tag = d.device_path.split("#")[-2] if d.device_path else "?"
        print(f"  ✅ abierta: {tag}")
    except Exception as e:
        print(f"  ❌ {d.device_path}: {e}")

counts = {}
start = time.time()
print("\n⌨️  ESCRIBE CUALQUIER COSA EN EL CHAT durante 60 s (o presiona teclas).\n")


def make_handler(tag):
    def handler(raw):
        if not raw:
            return
        data = list(raw)  # pywinusb pasa ReadOnlyList, NO un objeto report
        counts[tag] = counts.get(tag, 0) + 1
        n = counts[tag]
        if n <= 40 or n % 50 == 0:
            hexs = " ".join(f"{b:02X}" for b in data[:6])
            press = data[2] * 256 + data[1] if len(data) >= 4 else -1
            code = data[3] if len(data) >= 4 else -1
            print(f"  [{tag}] n={n} len={len(data)} bytes: {hexs}  presión={press} tecla={code} (0x{code:02X})")
    return handler


for d in opened:
    tag = d.device_path.split("#")[-2] if d.device_path else "?"
    try:
        d.set_raw_data_handler(make_handler(tag))
    except Exception as e:
        print(f"  handler {tag}: {e}")

while time.time() - start < 60:
    time.sleep(0.05)

for d in opened:
    try:
        d.close()
    except Exception:
        pass

print("\n── RESUMEN ──")
total = 0
for tag, n in sorted(counts.items(), key=lambda x: -x[1]):
    total += n
    print(f"  {tag}: {n} reportes")
print(f"\nTOTAL: {total} reportes en 60 s")
if total == 0:
    print("❌ CERO reportes → el teclado NO está enviando por USB.")
    print("   Posibles causas: modo inalámbrico/Bluetooth activo,")
    print("   cable desconectado, o el HID está capturado por otra app.")
else:
    print("✅ El teclado SÍ habla por USB — el problema está en la página.")

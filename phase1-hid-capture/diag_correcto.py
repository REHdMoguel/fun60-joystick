#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escucha CORRECTA del FUN60 (handler pywinusb bien escrito):
el raw handler recibe ReadOnlyList de bytes, NO un objeto report.
15 s. Presiona W/A/S/D cuando veas el aviso."""
import sys
import time

import pywinusb.hid as hid

# handler correcto: recibe ReadOnlyList directamente
def make_handler(tag, counts):
    def handler(raw):
        if not raw:
            return
        counts[tag] = counts.get(tag, 0) + 1
        n = counts[tag]
        if n <= 25 or n % 30 == 0:
            data = list(raw)
            hexs = " ".join(f"{b:02X}" for b in data[:8])
            if len(data) >= 4:
                pressure = data[2] * 256 + data[1]
                print(f"  [{tag}] n={n} len={len(data)}: {hexs}  presión={pressure} tecla={data[3]} (0x{data[3]:02X})", flush=True)
            else:
                print(f"  [{tag}] n={n} len={len(data)}: {hexs}", flush=True)
    return handler

devices = hid.HidDeviceFilter(vendor_id=0x3151).get_devices()
print(f"Interfaces FUN60: {len(devices)}")
counts = {}
opened = []
for d in devices:
    tag = d.device_path.split("#")[-2] if d.device_path else "?"
    try:
        # handler ANTES de open (como capture.py que funcionó en Fase 1)
        d.set_raw_data_handler(make_handler(tag, counts))
        d.open()
        opened.append(d)
        print(f"  ✅ abierta: {tag}", flush=True)
    except Exception as e:
        print(f"  ❌ {tag}: {e}", flush=True)

print("\n🎯 ¡PRESIONA W/A/S/D VARIAS VECES AHORA! (15 s)\n", flush=True)
start = time.time()
while time.time() - start < 15:
    time.sleep(0.05)

for d in opened:
    try:
        d.close()
    except Exception:
        pass

total = sum(counts.values())
print(f"\n── RESUMEN ── TOTAL: {total} reportes en 15 s")
for tag, n in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {tag}: {n}")
if total == 0:
    print("❌ Sigue sin llegar nada (con handler CORRECTO) → problema real de teclado/driver.")
else:
    print("✅ ¡El teclado SÍ emite presión! El problema está en la PÁGINA (selección de interfaz).")

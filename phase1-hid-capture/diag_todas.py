#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnóstico definitivo: abre TODAS las interfaces HID del FUN60 a la vez
y escucha 15 s. Muestra de qué interfaz llega cada reporte, para saber cuál
es la de presión real y con qué códigos de tecla habla."""
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

if not opened:
    print("❌ NINGUNA interfaz se pudo abrir → el navegador la tiene capturada.")
    sys.exit(1)

counts = {}
start = time.time()
print("\n🎯 ¡PRESIONA W, A, S, D VARIAS VECES AHORA durante 15 segundos!\n")


def make_handler(tag):
    def handler(raw):
        if not raw:
            return
        data = list(raw)  # pywinusb pasa ReadOnlyList, NO un objeto report
        counts[tag] = counts.get(tag, 0) + 1
        n = counts[tag]
        if n <= 25 or n % 30 == 0:
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

while time.time() - start < 15:
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
print(f"\nTOTAL: {total} reportes en 15 s")
if total == 0:
    print("⚠️ CERO reportes en NINGUNA interfaz → el teclado no envía nada")
    print("   (modo inalámbrico? driver? iot_manager relanzado?)")
else:
    print("✅ El teclado SÍ habla — la interfaz con más reportes de presión es la buena.")

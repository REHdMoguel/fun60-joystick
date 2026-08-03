#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escucha TODAS las interfaces HID del FUN60 a la vez durante 12 s.

Sin pausas entre interfaces — el usuario presiona W/A/S/D de forma
sostenida. Esto distingue entre "el teclado no emite" vs
"el usuario presionó en el hueco entre interfaces"."""
import pywinusb.hid as hid
import time

devs = hid.HidDeviceFilter(vendor_id=0x3151).get_devices()
print(f"{len(devs)} interfaces — escuchando TODAS a la vez 12 s\n", flush=True)

abiertas = []
contadores = {}
primeros = {}


def make_handler(name):
    def h(report):
        data = list(report)[:8]  # report YA es la lista de bytes
        contadores[name] = contadores.get(name, 0) + 1
        if name not in primeros:
            primeros[name] = data
    return h


for i, d in enumerate(devs):
    try:
        d.open()
        d.set_raw_data_handler(make_handler(f"iface{i}"))
        abiertas.append(d)
        print(f"  iface{i} abierta", flush=True)
    except Exception as e:
        print(f"  iface{i} ERROR: {e}", flush=True)

print("\n🎯 ¡PRESIONA W/A/S/D AHORA, de forma continua y variada, 12 segundos!", flush=True)
time.sleep(12)

print("\n=== RESUMEN ===")
for i in range(len(devs)):
    name = f"iface{i}"
    n = contadores.get(name, 0)
    if n:
        print(f"✅ {name}: {n} reportes | primero: {primeros[name]}")
    else:
        print(f"❌ {name}: 0 reportes")

for d in abiertas:
    try:
        d.close()
    except Exception:
        pass

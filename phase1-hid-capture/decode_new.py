#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descifra el NUEVO formato de reportes del FUN60 tras la reinstalación.

Captura reportes crudos y prueba 3 hipótesis de layout:
  A) [rid, 0x1B, pres_lo, pres_hi, tecla, ...]  (rid explícito)
  B) [rid, 0x1B, tecla, pres_lo, pres_hi, ...]
  C) layout viejo pero con rid: presión y tecla en distintas posiciones
Imprime los primeros reportes crudos para inspección manual."""
import pywinusb.hid as hid
import time

devs = hid.HidDeviceFilter(vendor_id=0x3151).get_devices()
d = devs[0]
print("escuchando iface0 12 s — ¡presiona W/A/S/D!", flush=True)
raws = []


def h(report):
    data = list(report)
    if len(raws) < 40:
        raws.append(data)


d.open()
d.set_raw_data_handler(h)
time.sleep(12)
d.close()

print(f"\n{len(raws)} reportes capturados (máx 40)")
print("\n=== PRIMEROS 25 REPORTES CRUDOS ===")
for r in raws[:25]:
    print(" ".join(f"{b:02X}" for b in r[:10]))

# análisis: frecuencia de cada byte en posiciones clave
if raws:
    from collections import Counter
    for pos, label in [(0, "byte0"), (1, "byte1"), (2, "byte2"), (3, "byte3")]:
        c = Counter(r[pos] if pos < len(r) else -1 for r in raws)
        print(f"\n{label}: valores más comunes -> {c.most_common(4)}")

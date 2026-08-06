#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnóstico: frecuencia de reportes del FUN60 durante pulsación sostenida.

Responde la pregunta clave para ajustar STATE_DECAY_MS:
  ¿El teclado envía reportes CONTINUOS mientras mantienes una tecla presionada,
  o solo cuando el valor CAMBIA?

Uso: mantén W presionado a profundidad constante ~3s, luego suéltala.
"""
import sys
import time
from collections import defaultdict

import pywinusb.hid as hid

VENDOR = 0x3151


def find_pressure():
    devs = hid.HidDeviceFilter(vendor_id=VENDOR).get_devices()
    for d in devs:
        try:
            if d.usage_page == 0xFFFF and d.usage == 1:
                return d
        except Exception:
            continue
    # fallback: la interfaz col05 suele ser la 1ª (idx 0) de las 4
    if devs:
        return devs[0]
    return None


dev = find_pressure()
if not dev:
    print("❌ No se encontró la interfaz de presión (0xFFFF/1)")
    sys.exit(1)

print("✅ Interfaz de presión encontrada. Escuchando 12s...")
print("   ▶ AHORA: mantén W presionado a profundidad CONSTANTE ~3s, luego suelta.")
print("   (cuando sueltes, verás la curva de soltado)")
print()

reports = []
t0 = time.time()


def handler(raw):
    if not raw:
        return
    data = list(raw)
    # pywinusb recibe el reporte COMPLETO con RID al inicio (a diferencia de
    # WebHID, que separa e.reportId). Formato FUN60: [RID=0x05][header=0x1B]
    # [presión low][presión high][código de tecla]...
    if len(data) < 5:
        return
    p = data[2] + data[3] * 256
    code = data[4]
    t = time.time() - t0
    reports.append((t, p, code))


dev.set_raw_data_handler(handler)
try:
    dev.open()
    time.sleep(12)
finally:
    dev.close()

print(f"\n📊 {len(reports)} reportes en 12s")
if not reports:
    print("❌ 0 reportes — la presión está DORMIDA (hay que reactivar con app.monsgeek.com)")
    sys.exit(0)

by_code = defaultdict(list)
for t, p, c in reports:
    by_code[c].append((t, p))

print("\n── Reportes por código de tecla (top 5 por cantidad) ──")
for code, items in sorted(by_code.items(), key=lambda kv: -len(kv[1]))[:5]:
    gaps = [(items[i+1][0] - items[i][0]) * 1000 for i in range(len(items)-1)]
    maxp = max(p for _, p in items)
    gaps_str = " ".join(f"{g:.0f}" for g in gaps[:14])
    print(f"  0x{code:02X}: {len(items)} reportes | presión máx {maxp:.0f} | huecos(ms): {gaps_str}")

print("\n── Conclusión ──")
for code, items in sorted(by_code.items(), key=lambda kv: -len(kv[1]))[:3]:
    if len(items) < 2:
        continue
    gaps = [(items[i+1][0] - items[i][0]) * 1000 for i in range(len(items)-1)]
    max_gap = max(gaps)
    streaming = "✅ streaming continuo" if max_gap <= 200 else "⚠️ NO hace streaming continuo"
    print(f"  0x{code:02X}: hueco máximo {max_gap:.0f}ms — {streaming}")

all_gaps = []
for code, items in by_code.items():
    for i in range(len(items)-1):
        all_gaps.append((items[i+1][0] - items[i][0]) * 1000)
if all_gaps:
    max_gap = max(all_gaps)
    p95 = sorted(all_gaps)[int(len(all_gaps)*0.95)]
    print(f"\n  Hueco máximo global: {max_gap:.0f}ms | p95: {p95:.0f}ms")
    print(f"  → STATE_DECAY_MS seguro ≈ {max(max_gap * 1.5, 200):.0f}ms")

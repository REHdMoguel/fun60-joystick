#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnóstico: escucha los reportes HID crudos del FUN60 durante 8 s.
Si el navegador tiene el HID abierto, falla al abrir → eso explica el síntoma.
Si abre, muestra cada reporte para ver si llega presión y con qué códigos."""
import sys
import time

try:
    import pywinusb.hid as hid
except ImportError:
    print("pywinusb no instalado")
    sys.exit(2)

devices = hid.HidDeviceFilter(vendor_id=0x3151).get_devices()
print(f"Dispositivos FUN60 visibles: {len(devices)}")

# la interfaz de presión es la que tiene usagePage 0xFFFF (collection de vendor)
target = None
for d in devices:
    try:
        caps = d.get_capabilities()
        up = getattr(caps, 'usage_page', None) or getattr(caps, 'usagePage', None)
        print(f"  {d.product_name} | path={d.device_path.split('#')[-1] if d.device_path else '?'} | usagePage={up}")
        if up == 0xFFFF:
            target = d
    except Exception as e:
        print(f"  {d.product_name} | error caps: {e}")

if target is None and devices:
    target = devices[0]

if target is None:
    print("❌ No hay dispositivos FUN60")
    sys.exit(1)

print(f"\nAbriendo: {target.device_path}")
try:
    target.open()
except Exception as e:
    print(f"❌ NO se pudo abrir el HID: {e}")
    print("   → El navegador (u otra app) lo tiene abierto. Cierra la pestaña")
    print("     de la página FUN60 y vuelve a intentar.")
    sys.exit(1)

print("✅ HID abierto. Escuchando 8 segundos — ¡PRESIONA W/A/S/D varias veces!\n")
count = 0
start = time.time()


def handler(raw):
    global count
    if not raw:
        return
    data = list(raw)  # pywinusb pasa ReadOnlyList, NO un objeto report
    count += 1
    if count <= 30 or count % 20 == 0:
        hexs = " ".join(f"{b:02X}" for b in data[:8])
        print(f"  [{count}] RID={report.report_id} len={len(data)} bytes: {hexs} ...")
        if len(data) >= 4:
            pressure = data[2] * 256 + data[1]
            print(f"        → presión={pressure} código_tecla={data[3]} (0x{data[3]:02X})")


target.set_raw_data_handler(handler)
while time.time() - start < 8:
    time.sleep(0.05)

target.close()
print(f"\nTotal reportes recibidos: {count}")
if count == 0:
    print("⚠️ CERO reportes en 8 s → el teclado no envía datos por esta interfaz,")
    print("   o se abrió la interfaz equivocada (teclado normal / señuelo).")
else:
    print("✅ El teclado SÍ envía reportes — el problema está en la PÁGINA (selección/decodificación).")

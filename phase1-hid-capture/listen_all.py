#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escucha las 4 interfaces HID del FUN60 por turnos (5 s cada una).

El usuario debe presionar W/A/S/D durante toda la escucha.
Muestra los primeros reportes de cada interfaz para ver cuál emite
y con qué formato (¿cambió con la reinstalación del iot_manager?)."""
import pywinusb.hid as hid
import time

devs = hid.HidDeviceFilter(vendor_id=0x3151).get_devices()
print(f"{len(devs)} interfaces encontradas\n")

reportes_por_iface = {}


def make_handler(name):
    def h(report):
        data = list(report.get_raw_data())[:8]
        if len(reportes_por_iface[name]) < 3:
            reportes_por_iface[name].append((report.report_id, data))
    return h


for i, d in enumerate(devs):
    name = f"iface{i} ({d.device_path.split('&')[-2] if '&' in d.device_path else '?'})"
    reportes_por_iface[name] = []
    print(f"--- escuchando {name} por 5 s (¡presiona WASD ahora!) ---", flush=True)
    try:
        d.open()
        d.set_raw_data_handler(make_handler(name))
        time.sleep(5)
    except Exception as e:
        print(f"    error abriendo: {e}", flush=True)
    finally:
        try:
            d.close()
        except Exception:
            pass

print("\n=== RESUMEN ===")
for name, reps in reportes_por_iface.items():
    if reps:
        print(f"✅ {name}: EMITE {len(reps)} reportes (primeros: {reps})")
    else:
        print(f"❌ {name}: 0 reportes en 5 s")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lee los FEATURE reports del FUN60 Ultra TMR.
El driver web usa GetFeatureReport/SendFeatureReport; algunos teclados
magnéticos solo envían presión analógica tras activar un modo vía feature
report. Esto lista los feature reports disponibles y su contenido.

Uso:  python features.py
"""
import time, sys
try:
    import pywinusb.hid as hid
except ImportError:
    print("Falta pywinusb:  pip install pywinusb"); sys.exit(1)

VENDOR = 0x3151

def find():
    devs = hid.HidDeviceFilter().get_devices()
    return [d for d in devs if d.vendor_id == VENDOR]

hits = find()
if not hits:
    print("No se encontró el FUN60"); sys.exit(1)

for idx, dev in enumerate(hits):
    try:
        dev.open()
    except Exception as e:
        print(f"[if{idx}] no se pudo abrir: {e}")
        continue
    print(f"\n=== Interfaz {idx}: {dev.device_path} ===")
    frs = dev.find_feature_reports()
    print(f"  feature reports: {len(frs)}")
    for fr in frs:
        try:
            fr.get()  # solicita el reporte actual
            data = fr.get_raw_data()
            print(f"  report_id={fr.report_id}  data={bytes(data).hex(' ')}")
        except Exception as e:
            print(f"  report_id={getattr(fr,'report_id','?')}  error={e}")
    try:
        dev.close()
    except Exception:
        pass

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FUN60 Ultra TMR — Capturador de reportes HID (alternativa sin navegador)
Fase 1: descubrir en qué bytes del reporte vive el valor de presión.

Requisitos:  pip install pywinusb
Uso:
  python capture.py --list          # listar dispositivos HID (buscar FUN60)
  python capture.py --watch         # leer reportes en vivo y resaltar bytes que cambian
  python capture.py --watch --len 64
"""
import argparse, time, sys
try:
    import pywinusb.hid as hid
except ImportError:
    print("Falta pywinusb. Instala con:  pip install pywinusb")
    sys.exit(1)

VENDOR = 0x3151   # 12625 — VID real reportado por el hardware MonsGeek
# El PID real detectado en este equipo es 0x5029 (20521). El catálogo web usa
# placeholders (0x38EE/0x0001); por eso buscamos por VID o por nombre.
KNOWN_PIDS = {0x5029, 0x5028, 0x5025, 0x5021, 0x0001}

def all_devices():
    return hid.HidDeviceFilter().get_devices()

def find_fun60():
    devs = all_devices()
    hits = [d for d in devs if d.vendor_id == VENDOR]
    if hits:
        return hits
    hits = [d for d in devs if d.product_name and "monsgeek" in d.product_name.lower()]
    if hits:
        return hits
    return []

def cmd_list():
    devs = all_devices()
    print(f"{'VID':>6} {'PID':>6} {'usagePage':>9} {'usage':>5}  {'path'}  {'product'}")
    for d in devs:
        try:
            usage = d.usage
            upage = d.usage_page
        except Exception:
            usage = upage = '?'
        name = d.product_name or d.vendor_name or ''
        print(f"{d.vendor_id:6} {d.product_id:6} {upage:>9} {usage:>5}  {d.device_path}  {name}")
    print()
    hits = find_fun60()
    if hits:
        print(f"✅ FUN60 Ultra TMR detectado: {len(hits)} interfaz(ces)")
        for h in hits:
            print("   path:", h.device_path, "| usage_page:", hex(getattr(h, 'usage_page', 0) or 0))
    else:
        print("⚠️  No se encontró VID 0x38EE / PID 0x0001. ¿Teclado conectado y despierto?")

def cmd_watch(args):
    hits = find_fun60()
    if not hits:
        print("⚠️  No se encontró el FUN60. Ejecuta --list para ver dispositivos.")
        return
    print(f"✅ FUN60 detectado: {len(hits)} interfaces. Escuchando TODAS en paralelo...")
    print("   Presiona W/A/S/D lentamente con profundidad variable. Ctrl+C para salir.")
    all_counts = {}

    def make_handler(idx, dev):
        prev = [None]

        def handler(raw):
            # OJO: pywinusb pasa ReadOnlyList de bytes directamente al raw handler
            if not raw:
                return
            bytes_ = list(raw)
            changed = []
            if prev[0] is not None and len(prev[0]) == len(bytes_):
                changed = [i for i in range(len(bytes_)) if bytes_[i] != prev[0][i]]
                for i in changed:
                    all_counts[i] = all_counts.get(i, 0) + 1
            prev[0] = bytes_
            ts = time.strftime('%H:%M:%S') + f'.{int((time.time() % 1) * 1000):03d}'
            hexs = ' '.join(f'{b:02X}' for b in bytes_)
            mark = f"  ← idx {','.join(map(str, changed))}" if changed else ""
            print(f"[if{idx}] {ts}  {hexs}{mark}", flush=True)
        return handler

    opened = []
    for idx, dev in enumerate(hits):
        try:
            dev.set_raw_data_handler(make_handler(idx, dev))
            dev.open()
            opened.append(dev)
            print(f"   interfaz {idx} abierta: {dev.device_path}", flush=True)
        except Exception as e:
            print(f"   interfaz {idx} NO disponible: {e}", flush=True)
    if not opened:
        print("❌ Ninguna interfaz pudo abrirse. ¿El driver web de MonsGeek la tiene bloqueada?")
        return
    print("   Escuchando...", flush=True)
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nResumen de cambios por byte (índice -> nº de cambios):")
        print(sorted(all_counts.items(), key=lambda x: -x[1]))
    finally:
        for d in opened:
            try: d.close()
            except Exception: pass

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Capturador HID FUN60 Ultra TMR')
    p.add_argument('--list', action='store_true', help='listar dispositivos HID')
    p.add_argument('--watch', action='store_true', help='leer reportes en vivo')
    p.add_argument('--len', type=int, default=64, help='longitud esperada del reporte')
    p.add_argument('--quiet', action='store_true', help='solo imprimir cuando algo cambia')
    a = p.parse_args()
    if a.list or not a.watch:
        cmd_list()
    if a.watch:
        cmd_watch(a)

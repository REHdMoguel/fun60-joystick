#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Obtiene los USAGE PAGES reales de cada colección HID del FUN60.

Usa hid.dll (HidD_GetPreparsedData + HidP_GetCaps) — la fuente de
verdad de Windows. Esto dice qué filtro WebHID necesita la página."""
import ctypes
from ctypes import wintypes
import pywinusb.hid as hid

# ── hid.dll API ────────────────────────────────────────────────────────
hid_dll = ctypes.WinDLL("hid.dll")
kernel32 = ctypes.WinDLL("kernel32")

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", ctypes.c_ushort),
        ("UsagePage", ctypes.c_ushort),
        ("InputReportByteLength", ctypes.c_ushort),
        ("OutputReportByteLength", ctypes.c_ushort),
        ("FeatureReportByteLength", ctypes.c_ushort),
        ("Reserved", ctypes.c_ushort * 17),
        ("NumberLinkCollectionNodes", ctypes.c_ushort),
        ("NumberInputButtonCaps", ctypes.c_ushort),
        ("NumberInputValueCaps", ctypes.c_ushort),
        ("NumberInputDataIndices", ctypes.c_ushort),
        ("NumberOutputButtonCaps", ctypes.c_ushort),
        ("NumberOutputValueCaps", ctypes.c_ushort),
        ("NumberOutputDataIndices", ctypes.c_ushort),
        ("NumberFeatureButtonCaps", ctypes.c_ushort),
        ("NumberFeatureValueCaps", ctypes.c_ushort),
        ("NumberFeatureDataIndices", ctypes.c_ushort),
    ]


hid_dll.HidD_GetPreparsedData.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
hid_dll.HidD_GetPreparsedData.restype = wintypes.BOOL
hid_dll.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
hid_dll.HidP_GetCaps.restype = ctypes.c_long
hid_dll.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]

kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def get_caps(path):
    h = kernel32.CreateFileW(path, 0, FILE_SHARE_READ | FILE_SHARE_WRITE, None,
                             OPEN_EXISTING, 0, None)
    if h is None or h == wintypes.HANDLE(-1).value:
        return None
    try:
        pdata = ctypes.c_void_p()
        if not hid_dll.HidD_GetPreparsedData(h, ctypes.byref(pdata)):
            return None
        try:
            caps = HIDP_CAPS()
            r = hid_dll.HidP_GetCaps(pdata, ctypes.byref(caps))
            if r != 0:
                return None
            return caps
        finally:
            hid_dll.HidD_FreePreparsedData(pdata)
    finally:
        kernel32.CloseHandle(h)


print("=== Usage pages reales de cada colección HID (hid.dll) ===")
devs = hid.HidDeviceFilter(vendor_id=0x3151).get_devices()
for i, d in enumerate(devs):
    path = d.device_path
    caps = get_caps(path)
    if caps:
        print(f"\nDev {i}: {path.split('#')[1]}")
        print(f"  UsagePage=0x{caps.UsagePage:04X}  Usage=0x{caps.Usage:04X}")
        print(f"  InputReportLen={caps.InputReportByteLength}")
    else:
        print(f"\nDev {i}: no se pudo leer caps")

# FUN60 Ultra TMR → Joystick Analógico — Plan del Proyecto

**Proyecto:** Convertir el teclado magnético MonsGeek FUN60 Ultra TMR en un joystick analógico virtual.

**Hardware identificado (desde el driver web de MonsGeek):**

| Campo | Valor |
|---|---|
| displayName | FUN60 Ultra TMR |
| name | `ry5088_akko_fun60_ultra_tmr_3m_8k_8k` |
| vendorId | 14574 (0x38EE) |
| productId | 1 (0x0001) |
| type | keyboard |
| magnetism | true |
| travel | min 0.1 mm, max 3.4 mm, step 0.005, default 2 mm |
| keyLayout | Common61_gk06 |
| fnSysLayer | win:2, mac:2 |

**Puentes detectados en el driver web:**
- WebHID directo (`navigator.hid.*`, `inputreport`, `sendFeatureReport`...)
- App local `iot_manager` → puertos TCP `127.0.0.1:6015` y `127.0.0.1:3838` (gRPC/Connect: `hid.HidService` con `ListenToReports`, `Write`, `GetFeatureReport`, `LockDevice`...)

---

## Fases

### Fase 1 — Descubrir el protocolo de presión (EN CURSO)
**Objetivo:** Confirmar que una app externa puede leer el nivel de pulsación de W/A/S/D y averiguar en qué bytes del reporte HID vive ese valor.

**Entregables:**
- [x] `docs/plan.md` — este documento
- [x] `phase1-hid-capture/index.html` — capturador WebHID (Chrome/Edge)
- [x] `phase1-hid-capture/capture.py` — capturador Python vía pywinusb (sin navegador)
- [x] `phase1-hid-capture/features.py` — lector de feature reports
- [x] **Protocolo descifrado** → `docs/protocolo-reporte.md`
  - RID 5, 31 bytes, header 0x1B
  - Presión 9-bit = byte2×256 + byte1, rango 0–325, satura ~325 (≈3.4 mm)
  - byte3 = código de tecla (0x09, 0x0F, 0x15 observados)
  - Una tecla por reporte; presión salta a ~20 al activarse
- [ ] **Mapear códigos de tecla → W/A/S/D** (presionar una tecla a la vez)
- [ ] Confirmar si hay reporte multi-tecla (crítico para joystick X/Y)

**Hallazgos de la primera sesión de captura (2026-08-02):**

1. **VID/PID reales del hardware**: el FUN60 conectado por USB reporta
   **VID 12625 (0x3151) / PID 20521 (0x5029)** como "MonsGeek Keyboard",
   con 4 interfaces HID (`mi_01 col01/col02/col05` + `mi_02`). El
   catálogo web usa placeholders (0x38EE/0x0001) — **no usar esos**.
2. **El iot_manager se cae si abres el HID con otro cliente**: al abrir
   las 4 interfaces con pywinusb, los servicios locales (puertos
   6015/3838) dejaron de responder. El acceso HID al FUN60 es
   semi-exclusivo: **un solo cliente a la vez**.
3. **La vía correcta es WebHID desde el navegador** (modo `web` del
   driver: `hidConnectMethod`), no pywinusb directo. El filtro del
   driver para el reporte de presión es `usagePage 0xFFFF, usage 1,
   interfaceNumber 1`.
4. El instalador del puente es `Downloads/Programs/iot_manager_setup_v0.1.6.exe`.
5. La interfaz `mi_02` tiene 1 feature report de 64 bytes (todo ceros en reposo).

**Procedimiento de captura (corregido):**
1. Cerrar cualquier app que use el HID del FUN60 (driver web, nuestro capture.py).
2. Abrir `index.html` en Chrome/Edge (WebHID) — funciona como el driver web.
3. Si hace falta el `iot_manager`: ejecutar `iot_manager_setup_v0.1.6.exe` o abrir app.monsgeek.com.

### Fase 2 — Prototipo lector ✅ COMPLETADA
App que lee W/A/S/D y muestra el valor analógico normalizado 0.00–1.00 en pantalla.
- [x] `phase2-lector/index.html` — joystick visual 2D en vivo
- [x] Fórmula: X = D−A, Y = S−W, rango [−1,1], **circle clamp** (WASD forma cuadrado → recorte circular como stick real)
- [x] Zona muerta mínima (0.005) para evitar temblor
- [x] Verificado por el usuario: "todo increible" ✅
- [ ] Decidir arquitectura Fase 3: ¿Electron + ViGEm, Python + ViGEm, o app nativa?

### Fase 3 — Joystick virtual ✅ COMPLETADA (verificada 2026-08-02)
- [x] ViGEmBus v1.22.0 instalado (driver kernel, `sc query ViGEmBus` = RUNNING)
- [x] `pip install vgamepad websockets`
- [x] `phase3-daemon/joy_daemon.py` — WebSocket (127.0.0.1:8765) → VX360Gamepad (vgamepad)
- [x] `phase3-joystick/index.html` — lector WebHID + emisor WebSocket (envía X/Y + modo left/right)
- [x] Verificación XInput: derecha=+32767, izquierda=-32767, arriba=-32767 (Y), diagonal=±23170, centro=0 ✅
- [x] Nota: la Flydigi CD2 del usuario aparece en otro slot de XInput (con drift) — no confundir
- [ ] **Pendiente usuario:** probar en un juego real (¿el juego detecta el mando?)

### Fase 4 — App final (PENDIENTE)
Interfaz con perfiles por juego, zona muerta, sensibilidad, teclas configurables.
- Ideas: selector de stick (left/right ya implementado), zona muerta configurable, curvas de sensibilidad, botones WASD→A/B/X/Y, perfil por juego, auto-arranque del daemon.

---

## Notas técnicas

- El teclado es "3m 8k 8k": 3 modos de conexión, polling 8000 Hz.
- `travelSetting.travel` (0.1–3.4 mm, paso 0.005) sugiere resolución fina (posiblemente 12-16 bits por tecla).
- El `iot_manager` expone RPC listos para suscribirse a reportes (`ListenManyReports`), útil como ruta alternativa si WebHID no expone todo.
- Cuidado: no romper la funcionalidad normal del teclado; el driver web y nuestra app pueden compartir el HID, pero hay que probar conflictos de acceso exclusivo (`LockDevice`).

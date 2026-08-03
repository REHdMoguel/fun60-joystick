# 📋 RESUMEN DE SESIÓN — FUN60 Joystick (continuar aquí)

**Fecha:** 2026-08-03 (Fase 4 completada)
**Estado global: ✅ TODO FUNCIONANDO** — mando completo (2 sticks + 14 botones + 2 gatillos + perfiles).

---

## 🎯 Estado actual (al cerrar la sesión)

| Componente | Estado |
|---|---|
| Protocolo HID descifrado | ✅ Completo (RID 5, header 0x1B, presión 9-bit, W=0x0E/A=0x09/S=0x0F/D=0x15) |
| Página web detecta el teclado | ✅ FUNCIONA (interfaz de presión 0xFFFF/usage 1) |
| Daemon (WebSocket 8765 → vgamepad) | ✅ **Protocolo Fase 4**: sticks duales `lx/ly/rx/ry`, `buttons`, `triggers` (LT/RT analógicos), `block_vks` (bloqueo dinámico) |
| Mando virtual Xbox 360 (ViGEmBus) | ✅ Verificado — **12/12 pruebas XInput** (sticks duales, botones, gatillos, bloqueo, tolerancia a nombres inválidos) |
| **Editor visual del mando** | ✅ Nuevo: clic en botón del diagrama → presionas la tecla física → se asigna |
| **Keymap aprendible** | ✅ W/A/S/D conocidos; el resto se aprende emparejando keydown (`e.code`) + reporte HID |
| **Asistente 🧙** | ✅ Aprende todas las teclas que usa el perfil actual |
| **Perfiles por juego** | ✅ 3 presets (Mando completo / Shooter / Aventura) + guardar/duplicar/eliminar/exportar/importar |
| Bloqueo selectivo | ✅ **Dinámico**: solo bloquea teclas aprendidas y mapeadas; se apaga solo durante aprendizaje |
| Lógica de página | ✅ **33/33 pruebas node** (ejes, histeresis, gatillos, bloqueo, emparejamiento) |
| Repo GitHub | ⏳ Pendiente commit de la Fase 4 |

---

## 🔑 LECCIONES CRÍTICAS (no olvidar nunca)

### 1. El FUN60 tiene DOS interfaces con usagePage 0xFFFF
```
Dev 0: 0xffff/0x2  ← SEÑUELO (¡no filtrar solo por usagePage!)
Dev 1: 0xffff/0x1  ← ★ LA DE PRESIÓN (la correcta)
Dev 2: 0x1/0x6     ← teclado normal
```
Filtro WebHID: `usagePage===0xFFFF Y usage===1` exacto.

### 2. iot_manager de MonsGeek SECUESTRA el teclado
- Binarios en `C:\Program Files\iot_manager\` (puertos 6015 y 3838)
- Se auto-inicia al abrir `app.monsgeek.com`; acceso HID semi-exclusivo
- **Solución:** `taskkill /F /IM iot_manager_rs.exe /IM common_hid_rs.exe`

### 3. El keymap NO está completo de fábrica — se aprende
- Solo W/A/S/D venían mapeados (14/9/15/21). **Todas las demás teclas se aprenden en la UI** (clic en botón del mando → presionar tecla física).
- El emparejamiento usa `window keydown` (nombre estándar `e.code`) + reporte HID (código del vendor). Si no llega keydown, no se aprende → **el bloqueo se desactiva solo durante el aprendizaje** para que el navegador reciba las teclas.

### 4. XInput muestrea ~125 Hz — el 8k del teclado no aporta más allá

---

## 🧪 Protocolo Fase 4 (página → daemon)

```json
{"lx": 0.42, "ly": -0.78, "rx": 0.1, "ry": 0.0,     // sticks [-1,1]
 "buttons": {"A": 1, "LB": 0, "DPAD_UP": 0, ...},    // 14 botones
 "triggers": {"LT": 0.75, "RT": 0.0},                 // gatillos [0,1]
 "block_vks": [0x45, 0x20, ...]}                      // teclas a bloquear (VK)
```

- `block_vks` reemplaza al viejo `block_keys: true/false` (compat mantenida)
- El daemon hace **último-valor-gana a 250 Hz**; los gatillos suben/bajan con rampa desde la página

---

## 📌 PENDIENTES (para la próxima sesión)

### 1. Probar en Hades de verdad (verificación final de la Fase 4)
1. Arrancar con `iniciar.bat` (o manual: daemon + abrir index.html)
2. Cerrar iot_manager si la página no detecta el teclado
3. 🔌 Conectar teclado → 🔗 Conectar daemon
4. Perfil **"Aventura (Hades)"** → clic en **🧙 Asistente** → presionar las teclas que pida (E, Q, Espacio, F, Shift, Ctrl, Tab, Esc)
5. 🚫 Bloqueo activado → lanzar Hades → movimiento suave con WASD, botones del mando asignados
6. **Ojo:** si el juego alterna esquema teclado/mando, es la Fase 4C (HidHide) la que lo resuelve

### 2. Fase 4A — Genérico (cualquier teclado magnético)
`decodeReport(bytes)` en `index.html` es el ÚNICO punto FUN60-específico. Plan:
- Moverlo a descriptor JSON: `{rid, header, bits_presion, mapa_codigos}`
- El keymap aprendible + la UI ya son universales
- Probar con otro teclado magnético (DrunkDeer, Wooting, Akko...) cuando haya acceso

### 3. Fase 4C — HidHide (si algún juego alterna esquema)
- Instalar HidHide, ocultar el FUN60 del juego → solo ve el mando virtual
- El teclado deja de funcionar DENTRO de ese juego (chat, etc.)

### 4. Advertencias al usuario (repetir si hace falta)
- **The First Descendant** (online, anticheat Nexon): usar con cautela, revisar ToS
- Juegos online competitivos (Valorant, CS2, CoD...): la emulación de mando + aim assist puede ser detectada

---

## 🚀 Cómo arrancar todo (recordatorio)

**Opción A (recomendada):** doble clic en `iniciar.bat`
**Opción B (manual):**
```bash
cd C:\Users\edson\Documents\proyectos\fun60-joystick
python -u phase3-daemon\joy_daemon.py   # en una terminal
# luego abrir phase3-joystick\index.html en Chrome
```

**ANTES de conectar:** `taskkill /F /IM iot_manager_rs.exe /IM common_hid_rs.exe 2>nul`

**En la página:** 🔌 Conectar teclado → 🔗 Conectar al daemon → elegir perfil → 🧙 asistente (primera vez) → 🚫 bloqueo activado → jugar.

**Para apagar:** cerrar la ventana del daemon (el mando virtual desaparece).

---

## 🔗 Referencias
- Repo: https://github.com/REHdMoguel/fun60-joystick
- Plan completo: `docs/plan.md`
- Protocolo: `docs/protocolo-reporte.md`
- Proyecto local: `C:\Users\edson\Documents\proyectos\fun60-joystick\`
- Tests: `phase3-daemon/test_protocolo_v4.py` (daemon, XInput) y `phase3-daemon/test_page_logic.js` (lógica página, node)

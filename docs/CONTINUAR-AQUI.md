# 📋 RESUMEN DE SESIÓN — FUN60 Joystick (continuar aquí)

**Fecha:** 2026-08-03 (madrugada)
**Estado global: ✅ TODO FUNCIONANDO** — el pipeline completo está operativo.

---

## 🎯 Estado actual (al cerrar la sesión)

| Componente | Estado |
|---|---|
| Protocolo HID descifrado | ✅ Completo (RID 5, header 0x1B, presión 9-bit, W=0x0E/A=0x09/S=0x0F/D=0x15) |
| Página web detecta el teclado | ✅ **FUNCIONA** (tras el fix de la interfaz doble 0xFFFF) |
| Daemon (WebSocket 8765 → vgamepad) | ✅ Funciona, patrón último-valor-gana a 250 Hz, anti-congelación |
| Mando virtual Xbox 360 (ViGEmBus) | ✅ Verificado (responde en XInput slot 0) |
| Bloqueo selectivo WASD | ✅ Funciona (WASD no escriben en Bloc de notas = correcto) |
| Repo GitHub | ✅ Todo commiteado y subido (último: `f12cc06`) |

---

## 🔑 LECCIÓN CRÍTICA de hoy (no olvidar nunca)

### 1. El FUN60 tiene DOS interfaces con usagePage 0xFFFF
```
Dev 0: 0xffff/0x2  ← SEÑUELO (¡no filtrar solo por usagePage!)
Dev 1: 0xffff/0x1  ← ★ LA DE PRESIÓN (la correcta)
Dev 2: 0x1/0x6     ← teclado normal
```
**El filtro WebHID debe exigir `usagePage===0xFFFF Y usage===1` exacto** — ya aplicado en las 3 páginas (commit `f12cc06`). El bug anterior conectaba al señuelo y no recibía nada.

### 2. iot_manager de MonsGeek SECUESTRA el teclado
- Binarios en `C:\Program Files\iot_manager\` (puertos 6015 y 3838)
- **Se auto-inicia/relanza** al abrir `app.monsgeek.com` (y a veces solo)
- Acceso HID **semi-exclusivo**: mientras corre, WebHID NO puede conectar
- **Solución:** matarlo antes de usar la app:
  ```bash
  taskkill /F /IM iot_manager_rs.exe /IM common_hid_rs.exe
  ```
  (o cerrar la pestaña de app.monsgeek.com)

### 3. Protocolo NO cambió con la reinstalación del driver
Los reportes crudos capturados tras reinstalar: `05 1B 15 00 0E ...`
= RID 5, header 0x1B, presión 21 (0x15), tecla 0x0E (W). **Idéntico al original.**

---

## 🧪 Medición de tasa real (respondida la duda del 8k)

```
Teclado 8k → Navegador → WebSocket → Daemon 250 Hz → ViGEmBus → XInput → Juego
                                                          └── XInput muestrea ~125 Hz
```
**XInput (lo que ven los juegos) muestrea a ~125 Hz** — el 8k del teclado y los 250 Hz del daemon son más que suficientes. El límite es el protocolo del mando Xbox 360. No vale la pena subir `UPDATE_HZ`.

---

## 📌 PENDIENTES (para la próxima sesión)

### 1. Probar en Hades de verdad (verificación final)
- Recargar página, conectar teclado + daemon, checkbox 🚫 activado
- El movimiento debe ser suave y solo del stick

### 2. Fase 4 — Esquema de control único en juegos (pendiente de decidir)
El problema: los juegos alternan entre esquema teclado/mando porque ven ambos dispositivos.
Opciones (el usuario pidió que se las explicara, luego se interrumpió):
- **Opción 1 (gratis):** Forzar "Modo Mando" en los ajustes del juego
- **Opción 2:** HidHide (ocultar teclado del juego) — deja el teclado inútil dentro del juego
- **Opción 3 (completa, recomendada):** Mapeo de teclas físicas → botones Xbox (E→A, Espacio→X, etc.) + bloqueo total de teclas hacia el juego. Es la solución profesional (como Wooting).

### 3. Advertencias al usuario (ya dadas, repetir si hace falta)
- **The First Descendant** (online, anticheat Nexon): usar con cautela, revisar ToS. El "atoramiento" a mitad de partida probablemente era el hilo congelado (ya arreglado) + latencia de Frame Generation (inherente).
- Los juegos online competitivos (Valorant, CS2, CoD...) pueden detectar emulación de mando.

### 4. Pendientes menores
- Opcional: subir `UPDATE_HZ` si algún juego raro lo pide (no recomendado)
- Opcional: screenshot en el README
- Los scripts de diagnóstico quedaron en `phase1-hid-capture/` (decode_new.py, listen_all.py, listen_all2.py, usage_pages.py) — útiles para futuras depuraciones

---

## 🚀 Cómo arrancar todo (recordatorio)

**Opción A (recomendada):** doble clic en `iniciar.bat`
**Opción B (manual):**
```bash
cd C:\Users\edson\Documents\proyectos\fun60-joystick
python -u phase3-daemon\joy_daemon.py   # en una terminal
# luego abrir phase3-joystick\index.html en Chrome
```

**ANTES de conectar:** asegurarse de que el iot_manager NO corra:
```bash
taskkill /F /IM iot_manager_rs.exe /IM common_hid_rs.exe 2>nul
```

**En la página:** 🔌 Conectar teclado → 🔗 Conectar al daemon → 🚫 checkbox activado → jugar.

**Para apagar:** cerrar la ventana del daemon (el mando virtual desaparece).

---

## 🔗 Referencias
- Repo: https://github.com/REHdMoguel/fun60-joystick
- Plan completo: `docs/plan.md`
- Protocolo: `docs/protocolo-reporte.md`
- Proyecto local: `C:\Users\edson\Documents\proyectos\fun60-joystick\`

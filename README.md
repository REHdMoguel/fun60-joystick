# 🎮 FUN60 Joystick

Convierte un **teclado magnético MonsGeek FUN60 Ultra TMR** en un **joystick analógico virtual**
(controlador Xbox 360) usando la presión real de las teclas W/A/S/D.

> Los switches magnéticos (TMR) del FUN60 detectan la **profundidad de pulsación** de cada tecla.
> Este proyecto lee ese valor analógico por WebHID y lo convierte en ejes de stick
> (X = D−A, Y = S−W) con circle-clamp, inyectándolos en un mando Xbox 360 virtual vía ViGEmBus.

## ✨ Características

- 🕹️ **Joystick analógico real** — la profundidad de pulsación controla la magnitud del stick
  (presiona W suave = poco movimiento; a fondo = stick al máximo)
- 🚫 **Bloqueo selectivo de WASD** — W/A/S/D se bloquean a nivel de sistema solo para el juego
  (el resto del teclado sigue funcionando normal; sin HidHide)
- 🎯 Stick izquierdo o derecho seleccionable
- ⭕ Circle-clamp (diagonales correctas, sin "cuadrado" digital)
- 🖥️ UI web con visualización del stick en tiempo real

## 📋 Requisitos

- Windows 10/11
- [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases) instalado (driver kernel)
- Python 3.10+ con: `pip install vgamepad websockets`
- Chrome o Edge (WebHID)

## 🚀 Uso

```bat
iniciar.bat
```

O manualmente:

```bash
# 1. Servidor web (la página lee el teclado por WebHID)
python -m http.server 8080

# 2. Daemon (crea el mando virtual)
python phase3-daemon/joy_daemon.py

# 3. Abrir en Chrome/Edge
#    http://localhost:8080/phase3-joystick/
```

En la página: **Conectar teclado** → **Conectar al daemon** → jugar.

## 🧩 Arquitectura

```
FUN60 Ultra TMR (teclado magnético)
        │  WebHID (reportes analógicos)
        ▼
phase3-joystick/index.html   ← lee presión, calcula X/Y, circle-clamp
        │  WebSocket (127.0.0.1:8765)
        ▼
phase3-daemon/joy_daemon.py  ← daemon Python (vgamepad + hook de teclado)
        │  ViGEmBus
        ▼
MANDO XBOX 360 VIRTUAL  ← lo que ven los juegos
```

## 📡 Protocolo HID (descifrado de la Fase 1)

- Report ID 5, 31 bytes, header `0x1B`
- Presión 9-bit: `byte2 × 256 + byte1` → rango 0–325 (≈ 3.4 mm de recorrido)
- Códigos de tecla (byte 3): W=`0x0E`, A=`0x09`, S=`0x0F`, D=`0x15`
- El teclado multiplexa teclas simultáneas a ~1 kHz (permite X/Y diagonal)

Detalles completos en [`docs/protocolo-reporte.md`](docs/protocolo-reporte.md).

## 📁 Estructura

```
fun60-joystick/
├── iniciar.bat              ← lanzador de un clic
├── docs/
│   ├── plan.md
│   └── protocolo-reporte.md
├── phase1-hid-capture/      ← herramientas de captura/mapeo (Fase 1)
├── phase2-lector/           ← prototipo visual del stick (Fase 2)
├── phase3-daemon/           ← daemon del mando virtual (Fase 3)
│   ├── joy_daemon.py
│   └── test_block_fisico.py
└── phase3-joystick/         ← página web principal
    └── index.html
```

## 📜 Licencia

MIT

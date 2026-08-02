# 🎮 FUN60 Joystick

Convierte un **teclado magnético MonsGeek FUN60 Ultra TMR** en un **joystick analógico virtual**
(controlador Xbox 360) usando la presión real de las teclas W/A/S/D.

> Los switches magnéticos (TMR) del FUN60 detectan la **profundidad de pulsación** de cada tecla.
> Este proyecto lee ese valor analógico por WebHID y lo convierte en ejes de stick
> (X = D−A, Y = W−S) con circle-clamp, inyectándolos en un mando Xbox 360 virtual vía ViGEmBus.

---

## ✨ ¿Qué hace y por qué es especial?

Con un teclado normal, presionar W es "todo o nada" (tecla apretada o no). Con el FUN60
y esta herramienta, **la fuerza con la que presionas W controla cuánto se mueve el stick**:

- Presionas W **suave** → el personaje camina lento
- Presionas W **a fondo** → corre a máxima velocidad
- Presionas W **y D a la vez** → diagonal perfecta (como un mando de verdad)

Es ideal para juegos que se juegan mejor con mando (Hades, Forza, RPGs, etc.)
pero donde prefieres usar tu teclado.

**Características:**
- 🕹️ Joystick analógico real (profundidad de pulsación = magnitud del stick)
- 🚫 **Bloqueo selectivo de WASD**: W/A/S/D se bloquean solo para el juego (el resto
  del teclado sigue funcionando normal — sin afectar nada más)
- 🎯 Stick izquierdo o derecho seleccionable (útil para cámara en shooters)
- ⭕ Circle-clamp (diagonales correctas, sin el "cuadrado" de los teclados digitales)
- 🖥️ Pantalla con el stick en vivo para verificar antes de jugar

---

## 📋 Requisitos (qué necesitas)

| Requisito | Qué es | ¿Cómo sé si lo tengo? |
|---|---|---|
| **Windows 10 u 11** | Tu sistema operativo | Ajustes → Sistema → Acerca de |
| **Teclado MonsGeek FUN60 Ultra TMR** | Tu teclado | ✅ (por eso estás aquí) |
| **Python** (gratis) | Programa que ejecuta el daemon | El lanzador te lo verifica y te dice cómo instalarlo |
| **ViGEmBus** (gratis) | Driver que crea el mando virtual | El lanzador te lo verifica y te dice cómo instalarlo |
| **Chrome o Edge** | Navegador (viene con Windows) | Cualquiera de los dos sirve |

> 💡 **La buena noticia:** el lanzador (`iniciar.bat`) revisa por ti si falta Python
> o ViGEmBus, y te explica en pantalla exactamente qué hacer. No necesitas saber nada técnico.

---

## 🚀 Guía de instalación paso a paso (para principiantes)

### Paso 1 — Descargar el proyecto

- En esta página de GitHub, clic en el botón verde **"Code"** → **"Download ZIP"**
- Descomprime el ZIP en cualquier carpeta (ej: `C:\fun60-joystick`)
- Dentro verás un archivo llamado **`iniciar.bat`**

### Paso 2 — Instalar ViGEmBus (solo la primera vez)

1. Ve a https://github.com/nefarius/ViGEmBus/releases
2. Descarga **`ViGEmBus_1.22.0_x64_x86_arm64.exe`**
3. Clic derecho sobre el archivo descargado → **"Ejecutar como administrador"**
4. Acepta e instala. **Reinicia el equipo** cuando termine.

### Paso 3 — Ejecutar el lanzador

1. **Doble clic** en `iniciar.bat`
2. El lanzador **encuentra Python solo** (no necesitas tenerlo en el PATH del sistema)
   y la primera vez instalará las librerías necesarias (tarda un minuto, solo pasa una vez)
3. Al final se abrirá **automáticamente** la página del joystick en tu navegador

> 💡 **¿Y el servidor localhost?** No es necesario. La página funciona abierta
> directamente como archivo local (Chrome/Edge permiten WebHID en `file://`).
> El lanzador abre el archivo `phase3-joystick/index.html` sin servidor.
> Si prefieres usarlo con servidor (opcional), abre `http://localhost:8080`
> después de ejecutar `python -m http.server 8080` en la carpeta del proyecto.

### Paso 4 — Conectar y jugar

En la página web que se abrió:

1. Clic en **🔌 Conectar teclado** → elige tu FUN60 en la ventana que aparece
2. Clic en **🔗 Conectar al daemon**
3. Deja activado el checkbox **🚫 Bloquear teclas W/A/S/D**
4. ¡Abre tu juego y a jugar! 🎮

> ⚠️ **Importante:** cierra la página del driver web de MonsGeek (`app.monsgeek.com`)
> mientras juegas — el teclado solo puede ser usado por un programa a la vez.

### Paso 5 — Apagar

Cierra las **2 ventanas negras minimizadas** (o la ventana del lanzador).
El mando virtual desaparece y todo vuelve a la normalidad.

---

## ❓ Preguntas frecuentes (FAQ)

**¿Puedo escribir con el teclado mientras el bloqueo está activado?**
Las teclas W/A/S/D no escribirán mientras el bloqueo esté activado (van al mando).
El resto del teclado funciona normal. Desmarca el checkbox 🚫 para desactivar el bloqueo.

**¿Esto sirve para cualquier juego?**
Funciona con cualquier juego que soporte mando Xbox. En juegos **solo para un jugador**
o cooperativos no hay ningún problema. En juegos **online competitivos** (Valorant, CS2,
CoD, Fortnite...), algunos anticheat pueden detectar drivers de emulación de mando:
revisa las reglas del juego antes de usarlo ahí.

**¿Se mueve el personaje en dirección contraria?**
Eso era un bug del eje Y que ya está corregido (W = arriba). Asegúrate de tener la
última versión descargada y recarga la página con F5.

**¿Por qué no aparece el mando en el juego?**
Verifica que el checkbox 🚫 esté activado y que el juego tenga configurado el control
por mando (no solo teclado). En Windows, escribe `joy.cpl` (Win+R) para ver si el
"Controlador de Xbox 360" aparece.

**¿Puedo cambiar qué stick controla?**
Sí — en la página hay un selector 🎯 **Stick: Izquierdo / Derecho**. El izquierdo es
el de movimiento; el derecho es el de cámara.

**¿El teclado se daña por usar la presión?**
No. Es exactamente para lo que fue diseñado: los switches magnéticos miden presión
de fábrica (el driver oficial de MonsGeek muestra la misma información).

---

## 🧩 Cómo funciona (por dentro)

```
FUN60 Ultra TMR (teclado magnético)
        │  WebHID (reportes analógicos de presión)
        ▼
phase3-joystick/index.html   ← lee presión, calcula X/Y, circle-clamp
        │  WebSocket (127.0.0.1:8765)
        ▼
phase3-daemon/joy_daemon.py  ← daemon Python (vgamepad + bloqueo de teclas)
        │  ViGEmBus
        ▼
MANDO XBOX 360 VIRTUAL  ← lo que ven los juegos
```

- **La página web** (navegador) es la única que puede leer el teclado por WebHID
- **El daemon** (Python) es el que crea el mando virtual y bloquea las teclas WASD
- Ambos se comunican por WebSocket en tu propio equipo (nada sale a internet)

## 📡 Protocolo HID (para curiosos)

- Report ID 5, 31 bytes, header `0x1B`
- Presión 9-bit: `byte2 × 256 + byte1` → rango 0–325 (≈ 3.4 mm de recorrido)
- Códigos de tecla (byte 3): W=`0x0E`, A=`0x09`, S=`0x0F`, D=`0x15`
- El teclado multiplexa teclas simultáneas a ~1 kHz (permite X/Y diagonal)

Detalles completos en [`docs/protocolo-reporte.md`](docs/protocolo-reporte.md).

---

## 📁 Estructura del proyecto

```
fun60-joystick/
├── iniciar.bat              ← ⭐ LANZADOR: doble clic y listo
├── requirements.txt         ← librerías necesarias (las instala el lanzador)
├── docs/
│   ├── plan.md              ← plan del proyecto (fases)
│   └── protocolo-reporte.md ← protocolo HID descifrado
├── phase1-hid-capture/      ← herramientas de investigación (para desarrolladores)
├── phase2-lector/           ← prototipo visual del stick (para desarrolladores)
├── phase3-daemon/           ← daemon del mando virtual
│   ├── joy_daemon.py        ← ⭐ el daemon (no tocar a menos que sepas)
│   └── test_block_fisico.py ← prueba del bloqueo de teclas
└── phase3-joystick/         ← página web principal
    └── index.html
```

> Para jugar solo necesitas: `iniciar.bat` + `phase3-daemon\` + `phase3-joystick\`
> + `requirements.txt`. El resto es documentación y herramientas de desarrollo.

---

## 📜 Licencia

MIT — puedes usar, copiar y modificar libremente, dando crédito al autor.

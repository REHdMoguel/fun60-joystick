# Protocolo de reporte HID del FUN60 Ultra TMR — Descifrado

**Fecha:** 2026-08-02 · **Origen:** log `fun60_reportes_1785690113883.txt` (1718 reportes)

## Formato del reporte

- **Report ID:** 5 (`[RID 5]`)
- **Longitud:** 31 bytes (30 + 1 de padding al inicio; primer reporte capturado 30 bytes = truncado)
- **Tasa:** hasta ~1000 reportes/s durante el movimiento (intervalos de 1 ms)

| Índice | Tamaño | Contenido | Valor |
|---|---|---|---|
| 0 | 1 byte | Header | `0x1B` (constante, todos los reportes) |
| 1 | 1 byte | Presión baja (LOW) | 0–255 |
| 2 | 1 byte | Carry / bit alto (HIGH) | 0 o 1 |
| 3 | 1 byte | Código de tecla | 0x09, 0x0F, 0x15 observados |
| 4–30 | 27 bytes | Relleno | Siempre 0 |

## Valor de presión

```
presión (9 bits efectivos) = byte2 * 256 + byte1
```

- El byte1 hace **wrap 255 → 0** y el byte2 sube a 1 (carry). Ejemplo real:
  `b1=255,b2=0 → b1=0,b2=1 → b1=1,b2=1 → ...`
- **Rango observado: 0 – 325** (el teclado satura en ~325, no llega a 511)
- 0 = tecla liberada / reposo
- El driver web configura `travel: 0.1–3.4 mm` → 325 unidades ≈ 3.4 mm de recorrido (~95.6 unid/mm)
- La presión **salta a ~20 al activarse** (actuation point del firmware) y sube gradualmente hasta el fondo

## Códigos de tecla (byte 3)

**✅ MAPEO CONFIRMADO (2026-08-02, asistente v2 — `fun60_keymap.json`):**

| Tecla | Código decimal | Hex |
|---|---|---|
| W | 14 | `0x0E` |
| A | 9 | `0x09` |
| S | 15 | `0x0F` |
| D | 21 | `0x15` |

Cada tecla tiene un código único (sin duplicados). El protocolo queda:

```
presión (9-bit) = byte2 × 256 + byte1   →  0–325 (≈3.4 mm)
tecla (byte3)   →  W=0x0E, A=0x09, S=0x0F, D=0x15
```

**Historial del mapeo:** el primer intento falló por un bug del asistente (no esperaba a que se soltara la tecla entre pulsaciones → todas las teclas se asignaron a 0x0E). Corregido en v2 con máquina de estados `wait_down → wait_up`.

**✅ SIMULTANEIDAD CONFIRMADA (2026-08-02, `fun60_simultaneidad.json`):**

Cuando se presionan 2-4 teclas juntas, el teclado **alterna/multiplexa** entre ellas:
los 4 códigos (W=14, A=9, S=15, D=21) aparecen en la misma ventana de prueba.
→ Se puede reconstruir el estado X/Y del joystick manteniendo el último valor
de presión de cada tecla (los reportes llegan a ~1 kHz).

**Prueba pendiente (opcional, Fase 2):** verificar la tasa real de alternancia
entre 2 teclas sostenidas (¿cada tecla recibe reporte cada ~2 ms?).

**Prueba pendiente:** presionar UNA tecla a la vez (W sola, luego A, S, D) para mapear cada código.

## Comportamiento temporal

- Cuando una tecla se suelta: la presión baja gradualmente a 0, luego cambia el código de tecla y la nueva tecla empieza en ~20.
- No se observaron 2 teclas simultáneas en el mismo reporte (el reporte solo trae 1 tecla).
- **IMPORTANTE para el joystick:** si el teclado solo reporta 1 tecla a la vez, habrá que:
  1. Buscar si existe otro reporte/RID con múltiples teclas, o
  2. Interpolar el vector X/Y desde la tecla reportada + estado anterior, o
  3. Usar la ruta `iot_manager` (ListenManyReports) que quizás trae más datos.

## Siguiente paso

1. Mapear teclas: prueba con W, A, S, D individuales.
2. Probar simultaneidad WASD → ¿alterna entre teclas o solo una?
3. Decidir estrategia de joystick según lo anterior.

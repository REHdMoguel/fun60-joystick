## 🐛 Bugs encontrados

**1. Pérdida de estado de botones al omitir teclas en el mensaje (desconexión lógica de botones)**
- **Archivo:** `joy_daemon.py`, método `VirtualPad.handle()`, línea: `if "buttons" in msg: self.buttons = dict(msg["buttons"])`
- **Explicación:** Al reemplazar por completo `self.buttons` con el nuevo diccionario, cualquier botón que estuviera presionado pero no venga en `msg` queda fuera del diccionario. En la siguiente aplicación (`_apply_locked`) no se llamará `release_button` para esos botones, por lo que el mando virtual los mantendrá presionados permanentemente hasta que se reciba un `0` explícito. Esto contradice el diseño de “último valor gana”.
- **Fix:**
  ```python
  if "buttons" in msg:
      self.buttons.update(msg["buttons"])   # solo actualiza las teclas enviadas
  ```

**2. VK codes incorrectos para teclas modificadoras → bloqueo de sistema ineficaz**
- **Archivo:** `index.html`, función `vksFor`, línea donde devuelve `[0x10, 0xA0]` para `ShiftLeft`.
- **Explicación:** Un low-level keyboard hook (`WH_KEYBOARD_LL`) informa el `vkCode` como `0x10` (VK_SHIFT) para **ambas** teclas shift, independientemente de la física. El código `0xA0` (VK_LSHIFT) no aparece nunca en el campo `vkCode` del hook; se usa con `GetAsyncKeyState`. Por tanto:
  - Enviar `0xA0` al daemon no bloquea nada.
  - Enviar `0x10` bloquea **los dos shifts**, cuando el usuario quiere bloquear sólo el izquierdo.
  - El mismo problema existe con Control y Alt.
- **Fix:** Para discriminar izquierda/derecha en el hook hay que examinar el flag `LLKHF_EXTENDED` (bit 0 de `flags`). Como solución simple, se podría bloquear `0x10` sin distinción y documentarlo, o implementar la comprobación de flags en el callback del hook para consumir selectivamente.

**3. Condición de carrera en aprendizaje: la tecla puede ser consumida antes del desbloqueo**
- **Archivos:** `index.html` (envío de `block_vks: []` al entrar en modo aprendizaje) y `joy_daemon.py` (procesamiento asíncrono del mensaje WebSocket).
- **Explicación:** Al activar `learnTarget` o `learnAnyMode`, la página calcula `block_vks = []` y envía el mensaje al daemon. Pero la tecla podría presionarse **inmediatamente**, antes de que el hilo del hook reciba el nuevo conjunto vacío. El hook con la lista anterior (aún activa) consumirá la tecla, el navegador no verá el `keydown` y el aprendizaje fallará silenciosamente.
- **Fix:** Después de enviar el desbloqueo, introducir un pequeño retardo (p.ej. 100 ms) antes de permitir al usuario presionar, o implementar un *handshake* donde la página espere confirmación del daemon de que el bloqueo está vacío.

## ⚠️ Riesgos / mejoras

**4. Múltiples conexiones WebSocket corrompen el estado del mando virtual**
- **Archivo:** `joy_daemon.py`, creación del servidor (`websockets.serve(lambda ws: handler(ws, pad, blocker), …`).
- **Problema:** El servidor acepta cualquier número de clientes simultáneos. Dos pestañas/navegadores enviarán estados al mismo `VirtualPad` y `KeyBlocker`, causando mezcla de comandos y un comportamiento errático/impredecible.
- **Sugerencia:** Permitir una sola conexión activa; al recibir una nueva, rechazarla o finalizar la anterior dejando el mando centrado.

**5. Acceso no sincronizado en `KeyBlocker._callback` (riesgo teórico de carrera)**
- **Archivo:** `joy_daemon.py`, línea `if kbd.vkCode in self._vks:` dentro de `_callback`.
- **Problema:** La lista `self._vks` se lee sin el candado que protege la escritura en `set_vks`. Aunque en CPython la reasignación de la referencia es atómica y no muta el objeto, es una violación del modelo de memoria y podría dar problemas en otros intérpretes o si el código mutara el set in-place.
- **Sugerencia:** O bien adquirir el lock también en el callback (con cuidado de no bloquear el hook), o garantizar explícitamente que `_vks` siempre se sustituye por un objeto inmutable (p.ej., un `frozenset`) y documentar el patrón.

**6. Emparejamiento tecla–reporte HID frágil (timeout fijo y posibles reportes desfasados)**
- **Archivo:** `index.html`, función `tryLearnPair`, `const dt = performance.now() - lastKeyDown.t; if (lastKeyDown.code && dt < 400) ...`.
- **Riesgos:** En condiciones de carga alta, el reporte HID puede tardar más de 400 ms y la tecla no se aprende. Además, si el firmware envía antes el reporte de otra tecla (por ejemplo, por presión residual), se podría asignar mal.
- **Sugerencia:** Aumentar el timeout (800 ms) y/o validar que el código HID reportado es coherente mediante un mapeo previo o un análisis de similitud con el keydown.

**7. Bloqueo de teclas modificadoras puede interferir con combinaciones del sistema**
- **Archivo:** diseño del perfil y `computeBlockVks`.
- **Riesgo:** Si el usuario mapea `ControlLeft` a un botón y activa el bloqueo, el hook consumirá `0x10` (VK_CONTROL) y también `0xA2` (que como vimos es inútil). Esto suprimirá **ambas** teclas Control, impidiendo combinaciones como Ctrl+C incluso fuera del juego.
- **Sugerencia:** Mostrar una advertencia en la interfaz cuando se mapean modificadores, o limitar el bloqueo sólo a teclas de impresión.

## ✅ Verificación (lo que confirmaste que está correcto)

- Instalación del hook y firmas de `SetWindowsHookExW`/`CallNextHookEx`: correctas, sin truncamiento de punteros en 64 bits.
- Estructura `KBDLLHOOKSTRUCT` y uso de `GetMessageW` para el bucle de mensajes del hilo del hook: correcto.
- Hilo dedicado a 250 Hz aplica correctamente sticks y gatillos mediante `vgamepad` sin acumular retraso.
- Manejo de desconexión: centra ejes, vacía botones y desbloquea teclas, evitando que el mando virtual quede en un estado incorrecto.
- Rampa de gatillos en el frontend (`computeTriggers`) simula fielmente un recorrido analógico.
- Decodificador HID (`decodeReport`) extrae presión y código de tecla del formato de 9 bits correctamente.
- Histeresis de botones digitales (`computeButtons`) funciona según lo esperado.

**Prioridad de corrección:** 1 (botones pegados) > 2 (modificadores) > 3 (race aprendizaje) > 4 (multicliente).
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FUN60 Joystick — Revisor de código con el modelo PRO (deepseek-v4-pro)

Lee los archivos del proyecto que se quieran revisar, los envía a la API
de DeepSeek con el modelo pro y devuelve su crítica técnica.

Uso:
    python tools/review_pro.py                     # revisa los archivos por defecto
    python tools/review_pro.py archivo1 archivo2   # revisa archivos específicos

La API key se lee de %HERMES_HOME%/.env (DEEPSEEK_API_KEY).
El informe NO se guarda: se imprime en consola (redirige a archivo si quieres).
"""
import argparse
import json
import os
import re
import sys
import urllib.request

# ── config ──
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-pro"
DEFAULT_FILES = [
    "phase3-daemon/joy_daemon.py",
    "phase3-joystick/index.html",
    "phase3-daemon/test_protocolo_v4.py",
    "phase3-daemon/test_page_logic.js",
]

PROMPT_TEMPLATE = """Eres un revisor de código senior experto en Windows, HID, WebSocket,
ctypes, drivers de mando virtual (ViGEmBus/vgamepad) y JavaScript de navegador (WebHID).

Revisa este proyecto (teclado magnético → mando Xbox 360 virtual) con ojo crítico.
El pipeline es: página web lee presión de teclas por WebHID → calcula sticks/botones/
gatillos → envía JSON por WebSocket → daemon Python inyecta en mando virtual vía vgamepad
y bloquea teclas a nivel sistema con un low-level keyboard hook (ctypes).

Busca y reporta:
1. BUGS reales (lógica incorrecta, condiciones que nunca se cumplen, off-by-one)
2. RACE CONDITIONS (hilos, WebSocket vs bucle 250 Hz, estado compartido)
3. PROBLEMAS ESPECÍFICOS DE WINDOWS (ctypes: firmas de punteros, HHOOK, threads)
4. FALLAS EN EL BLOQUEO DE TECLAS (VK codes incorrectos, teclas que se escapan)
5. EDGE CASES del protocolo HID (multiplexado de teclas, presión que no vuelve a 0)
6. PROBLEMAS DE SEGURIDAD o de robustez (crash si llega JSON raro, deadlocks)
7. COSAS QUE SIMPLEMENTE ESTÁN MAL o sobran

Sé específico: cita la línea/función y propón el fix concreto. Si algo está bien,
no lo alabes, solo omítelo. Prioriza lo que realmente rompería el funcionamiento.

RESPONDE EN ESPAÑOL. Formato:
## 🐛 Bugs encontrados
## ⚠️ Riesgos / mejoras
## ✅ Verificación (lo que confirmaste que está correcto)

ARCHIVOS:
{files}
"""


RECHECK_TEMPLATE = """
════════════════════════════════════════════════════
SEGUNDA RONDA DE REVISIÓN (verificación de fixes)

Esta es una RE-VERIFICACIÓN. En la ronda anterior este
mismo modelo encontró los problemas de abajo. El código
fue corregido. Tu tarea:

1. Para CADA punto del informe anterior: ¿está realmente
   corregido? (mira el código nuevo, no confíes en el fix
   declarado). Di "✅ CORREGIDO" o "❌ SIGUE ROTO" y por qué.
2. Busca NUEVOS bugs introducidos por los fixes.
3. Solo reporta lo que importa; no repitas alabanzas.

INFORME DE LA RONDA ANTERIOR:
{prev_report}
════════════════════════════════════════════════════
"""


def load_key():
    """Lee DEEPSEEK_API_KEY del .env de Hermes."""
    env_path = os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~/AppData/Local/hermes")), ".env")
    if not os.path.exists(env_path):
        # fallback: ruta ~/.hermes/.env
        env_path = os.path.expanduser("~/.hermes/.env")
    if not os.path.exists(env_path):
        sys.exit(f"[!] No se encontró .env en: {env_path}")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*DEEPSEEK_API_KEY\s*=\s*(\S+)", line)
            if m:
                return m.group(1)
    sys.exit("[!] DEEPSEEK_API_KEY no está definida en el .env")


def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_prompt(files):
    blocks = []
    for path in files:
        if not os.path.exists(path):
            print(f"[!] No existe: {path} — se omite", file=sys.stderr)
            continue
        content = read_file(path)
        blocks.append(f"### ARCHIVO: {path}\n```\n{content}\n```")
    if not blocks:
        sys.exit("[!] No hay archivos válidos para revisar.")
    return PROMPT_TEMPLATE.format(files="\n".join(blocks))


def call_api(prompt, key):
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Eres un revisor de código senior riguroso y específico."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 16000,
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    })
    with urllib.request.urlopen(req, timeout=900) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    if not content.strip():
        # deepseek-v4-pro razona antes de responder; si content viene vacío,
        # el razonamiento se comió el presupuesto de tokens o falló el finish
        fin = data["choices"][0].get("finish_reason")
        usage = data.get("usage", {})
        raise RuntimeError(
            f"Respuesta vacía (finish={fin}, tokens={usage.get('completion_tokens')}). "
            f"Sube max_tokens o reduce el tamaño del prompt."
        )
    return content


def main():
    parser = argparse.ArgumentParser(description="Revisa código con deepseek-v4-pro")
    parser.add_argument("files", nargs="*", help="Archivos a revisar (por defecto los de la Fase 4)")
    parser.add_argument("--out", default=None, help="Archivo de salida del informe (por defecto docs/review-pro-informe.md)")
    parser.add_argument("--recheck", default=None, metavar="INFORME_ANTERIOR",
                        help="Segunda ronda: incluye el informe anterior y verifica los fixes")
    args = parser.parse_args()
    files = args.files or DEFAULT_FILES
    print(f"── Revisando {len(files)} archivos con {MODEL} ──\n", file=sys.stderr)
    prompt = build_prompt(files)
    if args.recheck:
        with open(args.recheck, encoding="utf-8") as f:
            prev = f.read()
        prompt = prompt + "\n" + RECHECK_TEMPLATE.format(prev_report=prev)
        print("── MODO RECHECK: verificando fixes de la ronda anterior ──", file=sys.stderr)
    print(f"Prompt enviado: {len(prompt)} caracteres", file=sys.stderr)
    key = load_key()
    report = call_api(prompt, key)
    # guardar siempre en archivo (la consola de Windows no imprime bien emojis/unicode)
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "review-pro-informe.md")
    out = os.path.normpath(out)
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ Informe guardado en: {out}", file=sys.stderr)
    print(report[:2000])


if __name__ == "__main__":
    main()

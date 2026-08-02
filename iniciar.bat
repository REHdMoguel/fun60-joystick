@echo off
REM ============================================================
REM  FUN60 Joystick - Lanzador de un clic
REM  Encuentra Python solo (no depende del PATH), arranca el
REM  daemon del mando virtual y abre la pagina web directamente.
REM  El servidor localhost NO es necesario: la pagina funciona
REM  abierta como archivo local (WebHID lo permite en file://).
REM ============================================================
setlocal
cd /d "%~dp0"
chcp 65001 >nul 2>&1

echo.
echo   ============================================
echo     FUN60 Joystick - Iniciando...
echo   ============================================
echo.

REM ---- 1. Encontrar Python (en varios lugares posibles) ----
set "PYTHON="
where python >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON (where python3 >nul 2>&1 && set "PYTHON=python3")
if not defined PYTHON (where py >nul 2>&1 && set "PYTHON=py -3")
if not defined PYTHON (
    REM rutas comunes de instalacion de Python en Windows
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "C:\Python313\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
        "C:\Python310\python.exe"
    ) do if not defined PYTHON if exist "%%P" set "PYTHON=%%P"
)
if not defined PYTHON (
    REM ultimo recurso: el python del entorno Hermes (si existe)
    if exist "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe" set "PYTHON=%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe"
)
if not defined PYTHON (
    echo   [ERROR] No se encontro Python en este equipo.
    echo.
    echo   Para instalarlo:
    echo     1. Ve a https://www.python.org/downloads/
    echo     2. Descarga la ultima version de Windows
    echo     3. AL INSTALAR, MARCA la casilla "Add python.exe to PATH"
    echo     4. Termina la instalacion y vuelve a ejecutar este archivo
    echo.
    pause
    exit /b 1
)
echo   [1/4] Python encontrado: %PYTHON%

REM ---- 2. Instalar dependencias si faltan ----
echo   [2/4] Verificando librerias (vgamepad, websockets)...
%PYTHON% -c "import vgamepad, websockets" >nul 2>&1
if errorlevel 1 (
    echo         Instalando dependencias (primera vez, tarda un poco)...
    %PYTHON% -m pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo   [ERROR] No se pudieron instalar las librerias.
        echo           Revisa tu conexion a internet e intenta de nuevo.
        pause
        exit /b 1
    )
)
echo         Librerias listas: OK

REM ---- 3. Verificar que ViGEmBus este instalado ----
echo   [3/4] Verificando ViGEmBus (driver del mando virtual)...
sc query ViGEmBus >nul 2>&1
if errorlevel 1 (
    echo   [AVISO] ViGEmBus NO esta instalado. Sin el, el mando virtual no existe.
    echo.
    echo   Instalalo asi:
    echo     1. Descarga ViGEmBus_1.22.0_x64_x86_arm64.exe desde:
    echo        https://github.com/nefarius/ViGEmBus/releases
    echo     2. Clic derecho -^> "Ejecutar como administrador"
    echo     3. Instala y REINICIA el equipo
    echo.
    pause
    exit /b 1
)
echo         ViGEmBus instalado: OK

REM ---- 4. Arrancar daemon y abrir la pagina ----
echo   [4/4] Arrancando daemon del mando virtual...
start "FUN60 Daemon" /MIN cmd /k "cd /d %~dp0 && %PYTHON% -u phase3-daemon\joy_daemon.py"

echo.
echo   Abriendo la pagina (se abre directamente el archivo local)...
timeout /t 3 /nobreak >nul
start "" "%~dp0phase3-joystick\index.html"

echo.
echo   ============================================
echo     LISTO. En la pagina que se abrio:
echo       1) Clic en "Conectar teclado"  (elige el FUN60)
echo       2) Clic en "Conectar al daemon"
echo       3) ¡A jugar!
echo.
echo     El servidor localhost NO es necesario:
echo     la pagina funciona abierta como archivo.
echo     Para apagar: cierra la ventana minimizada
echo     "FUN60 Daemon".
echo   ============================================
echo.
pause

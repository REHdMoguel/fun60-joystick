@echo off
REM ============================================================
REM  FUN60 Joystick - Lanzador de un clic (versión robusta)
REM  Verifica Python y dependencias, arranca servidor + daemon,
REM  y abre el navegador. Con mensajes claros para cualquiera.
REM ============================================================
setlocal
cd /d "%~dp0"
chcp 65001 >nul 2>&1

echo.
echo   ============================================
echo     FUN60 Joystick - Iniciando...
echo   ============================================
echo.

REM ---- 1. Verificar que Python existe ----
where python >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] No se encontro Python en este equipo.
    echo.
    echo   Para instalar Python:
    echo     1. Ve a https://www.python.org/downloads/
    echo     2. Descarga la ultima version de Windows
    echo     3. AL INSTALAR, MARCA la casilla "Add python.exe to PATH"
    echo     4. Termina la instalacion y vuelve a ejecutar este archivo
    echo.
    pause
    exit /b 1
)
echo   [1/5] Python encontrado: OK

REM ---- 2. Instalar dependencias si faltan ----
echo   [2/5] Verificando librerias (vgamepad, websockets)...
python -c "import vgamepad, websockets" >nul 2>&1
if errorlevel 1 (
    echo         Instalando dependencias (primera vez, tarda un poco)...
    python -m pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo   [ERROR] No se pudieron instalar las librerias.
        echo           Revisa tu conexion a internet e intenta de nuevo.
        pause
        exit /b 1
    )
)
echo         Librerias listas: OK

REM ---- 3. Verificar que ViGEmBus este instalado ----
sc query ViGEmBus >nul 2>&1
if errorlevel 1 (
    echo   [3/5] AVISO: ViGEmBus (el driver del mando virtual) NO esta instalado.
    echo         Sin el, el mando virtual no puede crearse.
    echo.
    echo         Instalalo asi:
    echo         1. Descarga ViGEmBus_1.22.0_x64_x86_arm64.exe desde:
    echo            https://github.com/nefarius/ViGEmBus/releases
    echo         2. Clic derecho sobre el archivo -^> "Ejecutar como administrador"
    echo         3. Acepta e instala, y REINICIA el equipo
    echo.
    echo         (Si ya lo instalaste, reinicia el equipo y vuelve a abrir este archivo)
    echo.
    pause
    exit /b 1
)
echo         ViGEmBus instalado: OK

REM ---- 4. Verificar que los puertos no esten ocupados ----
netstat -ano | findstr ":8080 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo   [ERROR] El puerto 8080 ya esta en uso por otro programa.
    echo           Cierra el otro servidor o reinicia el equipo.
    pause
    exit /b 1
)

REM ---- 5. Arrancar servidor web + daemon ----
echo   [4/5] Arrancando servidor web en http://localhost:8080
start "FUN60 WebServer" /MIN cmd /c "cd /d %~dp0 && python -m http.server 8080"

echo   [5/5] Arrancando daemon del mando virtual
start "FUN60 Daemon" /MIN cmd /k "cd /d %~dp0 && python -u phase3-daemon\joy_daemon.py"

REM ---- Abrir el navegador ----
echo.
echo   Abriendo el navegador...
timeout /t 4 /nobreak >nul
start "" "http://localhost:8080/phase3-joystick/"

echo.
echo   ============================================
echo     LISTO. En la pagina que se abrio:
echo       1) Clic en "Conectar teclado"  (elige el FUN60)
echo       2) Clic en "Conectar al daemon"
echo       3) ¡A jugar!
echo.
echo     Para apagar: cierra las 2 ventanas minimizadas
echo     (o cierra esta ventana negra).
echo   ============================================
echo.
pause

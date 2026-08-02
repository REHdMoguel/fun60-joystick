@echo off
REM ============================================
REM  FUN60 Joystick - Lanzador de un clic
REM  Arranca: servidor web + daemon + navegador
REM ============================================
cd /d "%~dp0"

echo ============================================
echo   FUN60 Joystick - Iniciando...
echo ============================================

REM 1. Verificar que el daemon no esté ya corriendo
tasklist /FI "IMAGENAME eq python.exe" 2>nul | findstr /I "python.exe" >nul
if errorlevel 1 (
    echo [1/3] Servidor web + daemon no estaban corriendo.
) else (
    echo [1/3] Detectando procesos python existentes...
)

REM 2. Arrancar el servidor web (http.server) en una ventana minimizada
start "FUN60 WebServer" /MIN cmd /c "python -m http.server 8080 --directory "%~dp0""

REM 3. Arrancar el daemon del mando virtual en otra ventana
start "FUN60 Daemon" /MIN cmd /k "cd /d "%~dp0" && python -u phase3-daemon\joy_daemon.py"

echo [2/3] Servidor web en http://localhost:8080
echo [3/3] Daemon del mando virtual iniciado...

REM 4. Esperar un poco y abrir el navegador
timeout /t 4 /nobreak >nul
start "" "http://localhost:8080/phase3-joystick/"

echo.
echo   Listo. En la pagina:
echo     1) Conectar teclado (WebHID)
echo     2) Conectar al daemon
echo   Cierra las ventanas MINIMIZADAS para apagar todo.
echo.
pause

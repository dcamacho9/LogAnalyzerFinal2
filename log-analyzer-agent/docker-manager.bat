# ==============================================
# Quick Start Script para Deployment
# Log Analyzer Agent en Docker
# ==============================================

@echo off
setlocal enabledelayedexpansion

REM Colores para output
for /F %%A in ('echo prompt $H ^| cmd') do set "BS=%%A"

title Log Analyzer Agent - Docker Deployment Helper

:menu
cls
echo.
echo ============================================================
echo   LOG ANALYZER AGENT - DOCKER DEPLOYMENT HELPER
echo ============================================================
echo.
echo   1. Construir imagen Docker
echo   2. Ejecutar localmente (docker run)
echo   3. Ejecutar con docker-compose
echo   4. Ver logs
echo   5. Detener y limpiar
echo   6. Push a registry
echo   7. Ver información de la imagen
echo   8. Test API
echo   9. Exit
echo.
set /p choice="Selecciona opción (1-9): "

if "%choice%"=="1" goto build
if "%choice%"=="2" goto docker_run
if "%choice%"=="3" goto docker_compose
if "%choice%"=="4" goto logs
if "%choice%"=="5" goto cleanup
if "%choice%"=="6" goto push
if "%choice%"=="7" goto inspect
if "%choice%"=="8" goto test
if "%choice%"=="9" exit /b 0

echo.
echo Opción inválida.
pause
goto menu

:build
cls
echo.
echo ============================================================
echo   CONSTRUYENDO IMAGEN DOCKER
echo ============================================================
echo.

set /p tag="Tag de versión [latest]: "
if "!tag!"=="" set tag=latest

set /p cache="Usar cache? (s/n) [s]: "
if "!cache!"=="" set cache=s

cd log-analyzer-agent
if "!cache!"=="n" (
    echo.
    echo Construyendo sin cache...
    docker build -t log-analyzer-agent:!tag! --no-cache .
) else (
    echo.
    echo Construyendo con cache...
    docker build -t log-analyzer-agent:!tag! .
)

if !errorlevel! equ 0 (
    echo.
    echo ✓ Imagen construida exitosamente: log-analyzer-agent:!tag!
    echo.
    docker images log-analyzer-agent
) else (
    echo.
    echo ✗ Error al construir la imagen.
)

pause
goto menu

:docker_run
cls
echo.
echo ============================================================
echo   EJECUTANDO CON DOCKER RUN
echo ============================================================
echo.

set /p tag="Tag de versión [latest]: "
if "!tag!"=="" set tag=latest

set /p port="Puerto local [5000]: "
if "!port!"=="" set port=5000

set /p ollama_url="URL OLLAMA [http://host.docker.internal:11434]: "
if "!ollama_url!"=="" set ollama_url=http://host.docker.internal:11434

echo.
echo Ejecutando contenedor...
docker run -d ^
    --name log-analyzer-agent ^
    -p !port!:5000 ^
    -e OLLAMA_API_URL=!ollama_url! ^
    -e FLASK_ENV=production ^
    -v %cd%\log-analyzer-agent\logs:/app/logs ^
    log-analyzer-agent:!tag!

if !errorlevel! equ 0 (
    echo.
    echo ✓ Contenedor iniciado
    echo.
    docker ps
    echo.
    echo Esperando a que inicie...
    timeout /t 5 /nobreak
    echo.
    echo Health check:
    curl http://localhost:!port!/api/health
) else (
    echo.
    echo ✗ Error al iniciar contenedor
)

pause
goto menu

:docker_compose
cls
echo.
echo ============================================================
echo   EJECUTANDO CON DOCKER COMPOSE
echo ============================================================
echo.

cd log-analyzer-agent

if not exist ".env" (
    echo Creando .env desde plantilla...
    (
        echo OLLAMA_API_URL=http://host.docker.internal:11434
        echo MODEL_NAME=log-analyzer-agent
        echo FLASK_ENV=production
        echo LOG_LEVEL=INFO
        echo AGENT_PORT=5000
    ) > .env
    echo ✓ Archivo .env creado
)

echo.
set /p action="Acción (up/down/logs) [up]: "
if "!action!"=="" set action=up

if "!action!"=="up" (
    echo Iniciando servicios...
    docker-compose -f docker-compose-agent.yml up -d
    timeout /t 5 /nobreak
    docker-compose -f docker-compose-agent.yml ps
) else if "!action!"=="down" (
    echo Deteniendo servicios...
    docker-compose -f docker-compose-agent.yml down
) else if "!action!"=="logs" (
    docker-compose -f docker-compose-agent.yml logs -f log-analyzer-agent
    goto menu
)

cd ..
pause
goto menu

:logs
cls
echo.
echo ============================================================
echo   LOGS DEL CONTENEDOR
echo ============================================================
echo.

docker logs -f --tail 100 log-analyzer-agent

pause
goto menu

:cleanup
cls
echo.
echo ============================================================
echo   LIMPIEZA
echo ============================================================
echo.

echo Deteniendo contenedor...
docker stop log-analyzer-agent 2>nul

echo Removiendo contenedor...
docker rm log-analyzer-agent 2>nul

set /p remove_image="¿Remover imagen? (s/n) [n]: "
if "!remove_image!"=="s" (
    docker rmi log-analyzer-agent:latest 2>nul
    echo ✓ Imagen removida
)

echo.
echo ✓ Limpieza completada
echo.

pause
goto menu

:push
cls
echo.
echo ============================================================
echo   PUSH A REGISTRY
echo ============================================================
echo.

set /p registry="Registry (ej: docker.io/tuusuario): "
set /p tag="Tag [latest]: "
if "!tag!"=="" set tag=latest

if "!registry!"=="" (
    echo ✗ Registry requerido
    pause
    goto menu
)

echo.
echo Login a registry...
docker login

echo.
echo Tagging imagen...
docker tag log-analyzer-agent:!tag! !registry!/log-analyzer-agent:!tag!

echo.
echo Enviando a !registry!...
docker push !registry!/log-analyzer-agent:!tag!

if !errorlevel! equ 0 (
    echo.
    echo ✓ Push completado: !registry!/log-analyzer-agent:!tag!
) else (
    echo.
    echo ✗ Error al hacer push
)

pause
goto menu

:inspect
cls
echo.
echo ============================================================
echo   INFORMACIÓN DE LA IMAGEN
echo ============================================================
echo.

docker images log-analyzer-agent

echo.
echo ============================================================
echo   HISTORIAL DE CAPAS
echo ============================================================
echo.

docker history log-analyzer-agent:latest

echo.
echo ============================================================
echo   DETALLES
echo ============================================================
echo.

docker inspect log-analyzer-agent:latest | findstr "Id\|Created\|Architecture" | more

pause
goto menu

:test
cls
echo.
echo ============================================================
echo   TEST API
echo ============================================================
echo.

set /p port="Puerto [5000]: "
if "!port!"=="" set port=5000

echo.
echo 1. Health check
curl -X GET http://localhost:!port!/api/health
echo.

echo.
echo 2. Analizar logs de ejemplo
curl -X POST http://localhost:!port!/api/analyze ^
    -H "Content-Type: application/json" ^
    -d "{\"logs\":\"ERROR: Connection failed\nWARNING: Retry attempt 1\"}"
echo.

pause
goto menu

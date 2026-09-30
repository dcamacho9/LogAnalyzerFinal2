# ===============================================
# Script: Configurar OLLAMA Cloud con Autenticación
# Uso: .\setup-ollama-cloud.ps1
# ===============================================

param(
    [string]$APIKey = "",
    [string]$Model = "llama3.2:1b:cloud",
    [switch]$Test = $false
)

# Colores para output
$Colors = @{
    Green  = "`e[32m"
    Red    = "`e[31m"
    Yellow = "`e[33m"
    Cyan   = "`e[36m"
    Reset  = "`e[0m"
}

function Write-ColorOutput($Message, $Color = "Cyan") {
    Write-Host "$($Colors[$Color])$Message$($Colors.Reset)"
}

function Write-Section($Title) {
    Write-Host ""
    Write-ColorOutput "=" * 60 "Cyan"
    Write-ColorOutput $Title "Yellow"
    Write-ColorOutput "=" * 60 "Cyan"
}

Write-Section "🔐 Configurador OLLAMA Cloud"

# Paso 1: Obtener API Key si no se proporciona
if (-not $APIKey) {
    Write-ColorOutput "`n[!] Se requiere API Key para OLLAMA Cloud" "Yellow"
    Write-ColorOutput "    Obtener en: https://ollama.com/account/keys" "Cyan"
    Write-Host ""
    $APIKey = Read-Host "Ingrese su API Key"
}

if (-not $APIKey -or $APIKey.Length -eq 0) {
    Write-ColorOutput "✗ API Key no proporcionada" "Red"
    exit 1
}

# Paso 2: Crear/actualizar .env.production
Write-Section "Creando configuración"

$EnvContent = @"
# OLLAMA Cloud Configuration
OLLAMA_API_URL=https://api.ollama.com
OLLAMA_API_KEY=$APIKey
OLLAMA_MODEL=$Model

# Flask Configuration
FLASK_ENV=production
LOG_LEVEL=WARNING

# Streaming & Cache
ENABLE_STREAMING=true
CACHE_ENABLED=true

# Docker Resources
AGENT_CPU_LIMIT=2
AGENT_MEMORY_LIMIT=2G
AGENT_PORT=5000

# ServiceNow (Optional)
SERVICENOW_CREATE_INCIDENTS=false
"@

try {
    # Crear backup si el archivo ya existe
    if (Test-Path ".env.production") {
        $BackupFile = ".env.production.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item ".env.production" $BackupFile
        Write-ColorOutput "✓ Backup creado: $BackupFile" "Green"
    }
    
    # Guardar nuevo archivo
    Set-Content -Path ".env.production" -Value $EnvContent -Encoding UTF8
    Write-ColorOutput "✓ Archivo .env.production creado" "Green"
    
} catch {
    Write-ColorOutput "✗ Error al crear archivo: $_" "Red"
    exit 1
}

# Paso 3: Validar configuración
Write-Section "Validando configuración"

$Env:OLLAMA_API_URL = "https://api.ollama.com"
$Env:OLLAMA_API_KEY = $APIKey
$Env:OLLAMA_MODEL = $Model

Write-ColorOutput "  ✓ OLLAMA_API_URL: $Env:OLLAMA_API_URL" "Cyan"
Write-ColorOutput "  ✓ OLLAMA_MODEL: $Model" "Cyan"
Write-ColorOutput "  ✓ API Key configurada (longitud: $($APIKey.Length) caracteres)" "Cyan"

# Paso 4: Test opcional
if ($Test) {
    Write-Section "Probando conexión"
    
    Write-ColorOutput "  Buscando Docker..." "Yellow"
    
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-ColorOutput "  ✗ Docker no está instalado o no accesible" "Red"
    } else {
        Write-ColorOutput "  ✓ Docker encontrado" "Green"
        
        Write-ColorOutput "`n  Probando imagen Docker..." "Yellow"
        
        # Verificar si la imagen existe
        $ImageExists = docker images log-analyzer-agent 2>$null | Select-Object -Skip 1
        
        if ($ImageExists) {
            Write-ColorOutput "  ✓ Imagen Docker encontrada" "Green"
            
            Write-ColorOutput "`n  Iniciando contenedor de prueba..." "Yellow"
            
            try {
                # Crear contenedor temporal para test
                docker run --rm `
                    -e OLLAMA_API_URL="https://api.ollama.com" `
                    -e OLLAMA_API_KEY=$APIKey `
                    -e OLLAMA_MODEL=$Model `
                    log-analyzer-agent:latest `
                    python -c "
import os
print(f\"URL: {os.getenv('OLLAMA_API_URL')}\")
print(f\"Model: {os.getenv('OLLAMA_MODEL')}\")
print(f\"Auth: {'Configurada' if os.getenv('OLLAMA_API_KEY') else 'No configurada'}\")
"
                
                Write-ColorOutput "  ✓ Test completado" "Green"
            } catch {
                Write-ColorOutput "  ! Test no concluyó exitosamente: $_" "Yellow"
            }
        } else {
            Write-ColorOutput "  ⚠ Imagen Docker no encontrada - construir primero con: .\docker-build.ps1" "Yellow"
        }
    }
}

# Paso 5: Próximos pasos
Write-Section "Próximos Pasos"

Write-ColorOutput "1. Construir imagen Docker:" "Yellow"
Write-ColorOutput "   .\docker-build.ps1" "Cyan"

Write-ColorOutput "`n2. Iniciar servicio:" "Yellow"
Write-ColorOutput "   docker-compose -f docker-compose-agent.yml up -d" "Cyan"

Write-ColorOutput "`n3. Verificar estado:" "Yellow"
Write-ColorOutput "   docker-compose -f docker-compose-agent.yml logs -f log-analyzer-agent" "Cyan"

Write-ColorOutput "`n4. Test API:" "Yellow"
Write-ColorOutput "   curl -X POST http://localhost:5000/api/analyze -H 'Content-Type: application/json' -d '{""logs"":""ERROR test""}'`n" "Cyan"

Write-ColorOutput "✓ Configuración completada" "Green"

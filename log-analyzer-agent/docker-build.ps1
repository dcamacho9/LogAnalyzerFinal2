# ==============================================
# Script de Construcción de Imagen Docker
# Log Analyzer Agent
# ==============================================

param(
    [string]$ImageName = "log-analyzer-agent",
    [string]$ImageTag = "latest",
    [string]$Registry = "",
    [switch]$Push = $false,
    [switch]$Clean = $false,
    [string]$Dockerfile = "Dockerfile",
    [switch]$NoCache = $false
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

# Validar Docker instalado
Write-Section "Verificando Docker"
try {
    $dockerVersion = docker --version
    Write-ColorOutput "✓ Docker disponible: $dockerVersion" "Green"
} catch {
    Write-ColorOutput "✗ Docker no está instalado o no es accesible" "Red"
    exit 1
}

# Limpiar imágenes anteriores si se solicita
if ($Clean) {
    Write-Section "Limpiando imágenes anteriores"
    $fullImageName = if ($Registry) { "$Registry/$ImageName" } else { $ImageName }
    
    try {
        Write-ColorOutput "Eliminando imágenes: $fullImageName" "Yellow"
        docker image rm "$fullImageName`:$ImageTag" -f 2>$null
        Write-ColorOutput "✓ Imágenes anteriores eliminadas" "Green"
    } catch {
        Write-ColorOutput "Nota: No había imágenes previas para limpiar" "Cyan"
    }
}

# Validar que el Dockerfile existe
if (-not (Test-Path $Dockerfile)) {
    Write-ColorOutput "✗ Dockerfile no encontrado: $Dockerfile" "Red"
    exit 1
}

# Validar que requirements.txt existe
if (-not (Test-Path "requeriments.txt")) {
    Write-ColorOutput "✗ requeriments.txt no encontrado" "Red"
    exit 1
}

# Construir imagen
Write-Section "Construyendo imagen Docker"
$fullImageName = if ($Registry) { "$Registry/$ImageName" } else { $ImageName }
$imageFullTag = "$fullImageName`:$ImageTag"

Write-ColorOutput "Imagen: $imageFullTag" "Cyan"
Write-ColorOutput "Dockerfile: $Dockerfile" "Cyan"
Write-ColorOutput "Contexto: $(Get-Location)" "Cyan"

$buildArgs = @(
    "build",
    "-t", $imageFullTag,
    "-f", $Dockerfile,
    "."
)

if ($NoCache) {
    $buildArgs += "--no-cache"
}

try {
    & docker $buildArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✓ Imagen construida exitosamente" "Green"
    } else {
        Write-ColorOutput "✗ Error al construir la imagen" "Red"
        exit 1
    }
} catch {
    Write-ColorOutput "✗ Error durante la construcción: $_" "Red"
    exit 1
}

# Listar información de la imagen
Write-Section "Información de la imagen"
try {
    $imageInfo = docker image inspect $imageFullTag | ConvertFrom-Json
    $imageSize = [math]::Round($imageInfo[0].Size / 1MB, 2)
    $imageId = $imageInfo[0].Id.Substring(0, 12)
    
    Write-ColorOutput "ID: $imageId" "Cyan"
    Write-ColorOutput "Tamaño: $imageSize MB" "Cyan"
    Write-ColorOutput "Created: $($imageInfo[0].Created)" "Cyan"
} catch {
    Write-ColorOutput "Nota: No se pudo obtener información detallada de la imagen" "Yellow"
}

# Mostrar capas
Write-Section "Capas de la imagen"
try {
    docker history $imageFullTag --no-trunc
} catch {
    Write-ColorOutput "Advertencia: No se pudo mostrar el historial de capas" "Yellow"
}

# Push a registro si se solicita
if ($Push) {
    if (-not $Registry) {
        Write-ColorOutput "✗ --Push requiere --Registry especificado" "Red"
        exit 1
    }
    
    Write-Section "Enviando imagen a registro"
    Write-ColorOutput "Registering: $imageFullTag" "Cyan"
    
    try {
        docker push $imageFullTag
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✓ Imagen enviada exitosamente a $Registry" "Green"
        } else {
            Write-ColorOutput "✗ Error al enviar la imagen" "Red"
            exit 1
        }
    } catch {
        Write-ColorOutput "✗ Error durante el push: $_" "Red"
        exit 1
    }
}

Write-Section "Resumen"
Write-ColorOutput "✓ Construcción completada" "Green"
Write-ColorOutput "Imagen lista: $imageFullTag" "Cyan"
Write-ColorOutput "" "Reset"
Write-ColorOutput "Para ejecutar la imagen:" "Yellow"
Write-ColorOutput "  docker run -p 5000:5000 -e OLLAMA_API_URL=http://host.docker.internal:11434 $imageFullTag" "Cyan"
Write-ColorOutput "" "Reset"
Write-ColorOutput "Para usar con docker-compose:" "Yellow"
Write-ColorOutput "  docker-compose up -d" "Cyan"

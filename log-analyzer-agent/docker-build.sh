#!/bin/bash

# ==============================================
# Script de Construcción de Imagen Docker
# Log Analyzer Agent - Linux/macOS
# ==============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parámetros por defecto
IMAGE_NAME="log-analyzer-agent"
IMAGE_TAG="latest"
REGISTRY=""
DOCKERFILE="Dockerfile"
PUSH=false
CLEAN=false
NO_CACHE=false

# Funciones de utilidad
print_section() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${CYAN}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}$1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --dockerfile)
            DOCKERFILE="$2"
            shift 2
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        *)
            echo "Argumento desconocido: $1"
            exit 1
            ;;
    esac
done

# Verificar Docker instalado
print_section "Verificando Docker"
if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    exit 1
fi

DOCKER_VERSION=$(docker --version)
print_success "Docker disponible: $DOCKER_VERSION"

# Construir nombre completo de la imagen
if [ -z "$REGISTRY" ]; then
    FULL_IMAGE_NAME="$IMAGE_NAME"
else
    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME"
fi
IMAGE_FULL_TAG="$FULL_IMAGE_NAME:$IMAGE_TAG"

# Limpiar imágenes anteriores si se solicita
if [ "$CLEAN" = true ]; then
    print_section "Limpiando imágenes anteriores"
    print_warn "Eliminando: $IMAGE_FULL_TAG"
    
    if docker image rm "$IMAGE_FULL_TAG" -f &>/dev/null; then
        print_success "Imágenes anteriores eliminadas"
    else
        print_info "No había imágenes previas para limpiar"
    fi
fi

# Validar que Dockerfile existe
if [ ! -f "$DOCKERFILE" ]; then
    print_error "Dockerfile no encontrado: $DOCKERFILE"
    exit 1
fi

# Validar que requirements.txt existe
if [ ! -f "requeriments.txt" ]; then
    print_error "requeriments.txt no encontrado"
    exit 1
fi

# Construir imagen
print_section "Construyendo imagen Docker"
print_info "Imagen: $IMAGE_FULL_TAG"
print_info "Dockerfile: $DOCKERFILE"
print_info "Contexto: $(pwd)"

BUILD_ARGS=("build" "-t" "$IMAGE_FULL_TAG" "-f" "$DOCKERFILE" ".")

if [ "$NO_CACHE" = true ]; then
    BUILD_ARGS+=("--no-cache")
fi

if ! docker "${BUILD_ARGS[@]}"; then
    print_error "Error al construir la imagen"
    exit 1
fi

print_success "Imagen construida exitosamente"

# Mostrar información de la imagen
print_section "Información de la imagen"
if docker inspect "$IMAGE_FULL_TAG" &>/dev/null; then
    IMAGE_ID=$(docker inspect -f '{{.ID}}' "$IMAGE_FULL_TAG" | cut -c8-19)
    IMAGE_SIZE=$(docker images "$IMAGE_FULL_TAG" --format='{{.Size}}')
    IMAGE_CREATED=$(docker inspect -f '{{.Created}}' "$IMAGE_FULL_TAG")
    
    print_info "ID: $IMAGE_ID"
    print_info "Tamaño: $IMAGE_SIZE"
    print_info "Creada: $IMAGE_CREATED"
fi

# Mostrar capas
print_section "Capas de la imagen"
docker history "$IMAGE_FULL_TAG" --no-trunc

# Push a registro si se solicita
if [ "$PUSH" = true ]; then
    if [ -z "$REGISTRY" ]; then
        print_error "--push requiere --registry especificado"
        exit 1
    fi
    
    print_section "Enviando imagen a registro"
    print_info "Enviando: $IMAGE_FULL_TAG"
    
    if ! docker push "$IMAGE_FULL_TAG"; then
        print_error "Error al enviar la imagen"
        exit 1
    fi
    
    print_success "Imagen enviada exitosamente a $REGISTRY"
fi

# Resumen final
print_section "Resumen"
print_success "Construcción completada"
print_info "Imagen lista: $IMAGE_FULL_TAG"
echo ""
print_warn "Para ejecutar la imagen:"
print_info "  docker run -p 5000:5000 -e OLLAMA_API_URL=http://localhost:11434 $IMAGE_FULL_TAG"
echo ""
print_warn "Para usar con docker-compose:"
print_info "  docker-compose -f docker-compose-agent.yml up -d"

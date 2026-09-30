#!/bin/bash

# ==============================================
# Quick Start Script para Deployment
# Log Analyzer Agent en Docker - Linux/macOS
# ==============================================

set +e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funciones de utilidad
print_header() {
    clear
    echo -e "${CYAN}"
    echo "============================================================"
    echo "  LOG ANALYZER AGENT - DOCKER DEPLOYMENT HELPER"
    echo "============================================================"
    echo -e "${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${CYAN}============================================================"
    echo "  $1"
    echo "============================================================${NC}"
    echo ""
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

# Menú principal
show_menu() {
    print_header
    echo -e "  ${BLUE}1.${NC} Construir imagen Docker"
    echo -e "  ${BLUE}2.${NC} Ejecutar localmente (docker run)"
    echo -e "  ${BLUE}3.${NC} Ejecutar con docker-compose"
    echo -e "  ${BLUE}4.${NC} Ver logs"
    echo -e "  ${BLUE}5.${NC} Detener y limpiar"
    echo -e "  ${BLUE}6.${NC} Push a registry"
    echo -e "  ${BLUE}7.${NC} Ver información de la imagen"
    echo -e "  ${BLUE}8.${NC} Test API"
    echo -e "  ${BLUE}9.${NC} Exit"
    echo ""
    read -p "Selecciona opción (1-9): " choice
}

# Opción 1: Construir imagen
build_image() {
    print_section "CONSTRUYENDO IMAGEN DOCKER"
    
    read -p "Tag de versión [latest]: " tag
    tag=${tag:-latest}
    
    read -p "Usar cache? (s/n) [s]: " use_cache
    use_cache=${use_cache:-s}
    
    cd log-analyzer-agent || return
    
    echo ""
    if [ "$use_cache" = "n" ]; then
        print_info "Construyendo sin cache..."
        docker build -t log-analyzer-agent:"$tag" --no-cache .
    else
        print_info "Construyendo con cache..."
        docker build -t log-analyzer-agent:"$tag" .
    fi
    
    if [ $? -eq 0 ]; then
        echo ""
        print_success "Imagen construida exitosamente: log-analyzer-agent:$tag"
        echo ""
        docker images log-analyzer-agent
    else
        echo ""
        print_error "Error al construir la imagen"
    fi
    
    cd ..
    read -p "Presiona Enter para continuar..."
}

# Opción 2: Docker run
docker_run() {
    print_section "EJECUTANDO CON DOCKER RUN"
    
    read -p "Tag de versión [latest]: " tag
    tag=${tag:-latest}
    
    read -p "Puerto local [5000]: " port
    port=${port:-5000}
    
    read -p "URL OLLAMA [http://host.docker.internal:11434]: " ollama_url
    ollama_url=${ollama_url:-http://host.docker.internal:11434}
    
    echo ""
    print_info "Ejecutando contenedor..."
    docker run -d \
        --name log-analyzer-agent \
        -p "$port:5000" \
        -e OLLAMA_API_URL="$ollama_url" \
        -e FLASK_ENV=production \
        -v "$(pwd)/log-analyzer-agent/logs:/app/logs" \
        log-analyzer-agent:"$tag"
    
    if [ $? -eq 0 ]; then
        echo ""
        print_success "Contenedor iniciado"
        echo ""
        docker ps
        echo ""
        print_info "Esperando a que inicie..."
        sleep 5
        echo ""
        print_info "Health check:"
        curl -s http://localhost:"$port"/api/health | json_pp 2>/dev/null || curl http://localhost:"$port"/api/health
    else
        echo ""
        print_error "Error al iniciar contenedor"
    fi
    
    read -p "Presiona Enter para continuar..."
}

# Opción 3: Docker Compose
docker_compose_menu() {
    print_section "EJECUTANDO CON DOCKER COMPOSE"
    
    cd log-analyzer-agent || return
    
    if [ ! -f ".env" ]; then
        print_info "Creando .env desde plantilla..."
        cat > .env << 'EOF'
OLLAMA_API_URL=http://host.docker.internal:11434
MODEL_NAME=log-analyzer-agent
FLASK_ENV=production
LOG_LEVEL=INFO
AGENT_PORT=5000
EOF
        print_success "Archivo .env creado"
    fi
    
    echo ""
    read -p "Acción (up/down/logs) [up]: " action
    action=${action:-up}
    
    case $action in
        up)
            print_info "Iniciando servicios..."
            docker-compose -f docker-compose-agent.yml up -d
            sleep 5
            docker-compose -f docker-compose-agent.yml ps
            ;;
        down)
            print_info "Deteniendo servicios..."
            docker-compose -f docker-compose-agent.yml down
            ;;
        logs)
            docker-compose -f docker-compose-agent.yml logs -f log-analyzer-agent
            cd ..
            return
            ;;
    esac
    
    cd ..
    read -p "Presiona Enter para continuar..."
}

# Opción 4: Ver logs
view_logs() {
    print_section "LOGS DEL CONTENEDOR"
    
    docker logs -f --tail 100 log-analyzer-agent
}

# Opción 5: Limpiar
cleanup() {
    print_section "LIMPIEZA"
    
    print_info "Deteniendo contenedor..."
    docker stop log-analyzer-agent 2>/dev/null
    
    print_info "Removiendo contenedor..."
    docker rm log-analyzer-agent 2>/dev/null
    
    read -p "¿Remover imagen? (s/n) [n]: " remove_image
    if [ "$remove_image" = "s" ]; then
        docker rmi log-analyzer-agent:latest 2>/dev/null
        print_success "Imagen removida"
    fi
    
    echo ""
    print_success "Limpieza completada"
    read -p "Presiona Enter para continuar..."
}

# Opción 6: Push
push_image() {
    print_section "PUSH A REGISTRY"
    
    read -p "Registry (ej: docker.io/tuusuario): " registry
    read -p "Tag [latest]: " tag
    tag=${tag:-latest}
    
    if [ -z "$registry" ]; then
        print_error "Registry requerido"
        read -p "Presiona Enter para continuar..."
        return
    fi
    
    echo ""
    print_info "Login a registry..."
    docker login
    
    echo ""
    print_info "Tagging imagen..."
    docker tag log-analyzer-agent:"$tag" "$registry"/log-analyzer-agent:"$tag"
    
    echo ""
    print_info "Enviando a $registry..."
    docker push "$registry"/log-analyzer-agent:"$tag"
    
    if [ $? -eq 0 ]; then
        echo ""
        print_success "Push completado: $registry/log-analyzer-agent:$tag"
    else
        echo ""
        print_error "Error al hacer push"
    fi
    
    read -p "Presiona Enter para continuar..."
}

# Opción 7: Inspeccionar
inspect_image() {
    print_section "INFORMACIÓN DE LA IMAGEN"
    
    docker images log-analyzer-agent
    
    echo ""
    print_section "HISTORIAL DE CAPAS"
    
    docker history log-analyzer-agent:latest
    
    echo ""
    print_section "DETALLES"
    
    docker inspect log-analyzer-agent:latest 2>/dev/null | grep -E "Id|Created|Architecture" || \
    docker inspect log-analyzer-agent:latest
    
    read -p "Presiona Enter para continuar..."
}

# Opción 8: Test API
test_api() {
    print_section "TEST API"
    
    read -p "Puerto [5000]: " port
    port=${port:-5000}
    
    echo ""
    print_info "1. Health check"
    echo ""
    curl -s -X GET http://localhost:"$port"/api/health | json_pp 2>/dev/null || \
    curl -s http://localhost:"$port"/api/health
    
    echo ""
    echo ""
    print_info "2. Analizar logs de ejemplo"
    echo ""
    curl -s -X POST http://localhost:"$port"/api/analyze \
        -H "Content-Type: application/json" \
        -d '{"logs":"ERROR: Connection failed\nWARNING: Retry attempt 1"}' | json_pp 2>/dev/null || \
    curl -X POST http://localhost:"$port"/api/analyze \
        -H "Content-Type: application/json" \
        -d '{"logs":"ERROR: Connection failed\nWARNING: Retry attempt 1"}'
    
    echo ""
    echo ""
    read -p "Presiona Enter para continuar..."
}

# Loop principal
while true; do
    show_menu
    
    case $choice in
        1) build_image ;;
        2) docker_run ;;
        3) docker_compose_menu ;;
        4) view_logs ;;
        5) cleanup ;;
        6) push_image ;;
        7) inspect_image ;;
        8) test_api ;;
        9) print_success "¡Hasta luego!"; exit 0 ;;
        *) print_error "Opción inválida"; sleep 2 ;;
    esac
done

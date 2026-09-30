#!/usr/bin/env python3
"""
Script de Configuración Interactiva - OLLAMA Cloud
Ayuda a configurar la API Key de OLLAMA Cloud
"""

import os
import sys
from pathlib import Path

def main():
    print("\n" + "="*60)
    print("⚙️  CONFIGURADOR OLLAMA CLOUD")
    print("="*60)
    
    print("\n[PASO 1] Verificar API Key")
    print("-" * 60)
    print("Tu API Key debe obtenerse de: https://ollama.com/account/keys")
    print("Formato esperado: sk_...")
    print()
    
    api_key = input("Ingresa tu API Key: ").strip()
    
    if not api_key:
        print("\n❌ Error: API Key no proporcionada")
        sys.exit(1)
    
    if not api_key.startswith("sk_"):
        print("\n⚠️  Advertencia: La API Key parece inválida (no comienza con 'sk_')")
        confirm = input("¿Continuar de todas formas? (s/n): ").strip().lower()
        if confirm != 's':
            sys.exit(1)
    
    print(f"\n✓ API Key ingresada: {api_key[:10]}... (últimos {len(api_key)-10} caracteres ocultos)")
    
    # Paso 2: Actualizar archivo .env.production
    print("\n[PASO 2] Configurar archivo .env.production")
    print("-" * 60)
    
    env_file = Path(".env.production")
    
    if env_file.exists():
        print(f"Archivo {env_file.name} ya existe")
        overwrite = input("¿Sobrescribir con nueva configuración? (s/n): ").strip().lower()
        if overwrite != 's':
            print("Cancelado")
            sys.exit(0)
    
    env_content = f"""# ===============================================
# Archivo de Configuración - OLLAMA Cloud
# Generado automáticamente
# ===============================================

# OLLAMA Cloud Configuration
OLLAMA_API_URL=https://api.ollama.com
OLLAMA_API_KEY={api_key}
OLLAMA_MODEL=llama3.2:1b:cloud

# Flask Configuration
FLASK_ENV=production
LOG_LEVEL=WARNING
ENABLE_STREAMING=true

# Docker Resources
AGENT_CPU_LIMIT=2
AGENT_MEMORY_LIMIT=2G
AGENT_PORT=5000

# ServiceNow (Optional)
SERVICENOW_CREATE_INCIDENTS=false
"""
    
    try:
        env_file.write_text(env_content)
        print(f"\n✓ Archivo {env_file.name} actualizado correctamente")
    except Exception as e:
        print(f"\n❌ Error al escribir archivo: {e}")
        sys.exit(1)
    
    # Paso 3: Mostrar próximos pasos
    print("\n[PASO 3] Próximos Pasos")
    print("-" * 60)
    print("\n1️⃣  Construir imagen Docker:")
    print("   pwsh .\\docker-build.ps1")
    print("\n2️⃣  Iniciar servicio:")
    print("   docker-compose -f docker-compose-agent.yml up -d")
    print("\n3️⃣  Verificar estado:")
    print("   docker-compose -f docker-compose-agent.yml logs -f log-analyzer-agent")
    print("\n4️⃣  Test API:")
    print("   curl -X POST http://localhost:5000/api/analyze \\")
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"logs":"ERROR test"}\'')
    
    print("\n" + "="*60)
    print("✅ Configuración completada")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

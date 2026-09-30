#!/usr/bin/env python3
"""
Script de prueba para verificar que la API Flask funciona con Ollama Cloud
"""

import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env con manejo robusto
def load_env_safe(env_file):
    try:
        load_dotenv(env_file, encoding='utf-8', override=True)
        return True
    except UnicodeDecodeError:
        try:
            load_dotenv(env_file, encoding='latin-1', override=True)
            return True
        except:
            return False

for env_file in [".env.production", ".env"]:
    if Path(env_file).exists():
        if load_env_safe(env_file):
            print(f"✓ Cargado: {env_file}\n")
            break

API_URL = "http://localhost:5000"
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi:2.7b")

print("=" * 70)
print("VERIFICACIÓN DE CONFIGURACIÓN DE OLLAMA CLOUD")
print("=" * 70)
print(f"\n📋 Configuración actual:")
print(f"  OLLAMA_API_URL: {OLLAMA_API_URL}")
print(f"  OLLAMA_MODEL: {OLLAMA_MODEL}")
print(f"  API_KEY: {'✓ Configurada' if OLLAMA_API_KEY else '✗ NO configurada'}")
print(f"  API Flask: {API_URL}")

print(f"\n{'-' * 70}")
print("1️⃣  PRUEBA: Health Check de la API Flask")
print(f"{'-' * 70}\n")

try:
    response = requests.get(f"{API_URL}/api/health", timeout=5)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Respuesta:\n{json.dumps(data, indent=2)}\n")
    
    if response.status_code == 200:
        print("✅ API Flask respondiendo correctamente")
    else:
        print(f"⚠️  API respondió pero con estado {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ Error: No se puede conectar a la API Flask")
    print("   Asegúrate de que está corriendo: python api_optimized.py")
except Exception as e:
    print(f"❌ Error: {e}")

print(f"\n{'-' * 70}")
print("2️⃣  PRUEBA: Análisis de Logs Simple")
print(f"{'-' * 70}\n")

test_logs = """2024-09-24T10:15:32Z [ERROR] Conexión rechazada a base de datos
2024-09-24T10:15:33Z [ERROR] Reintentos agotados
2024-09-24T10:15:34Z [WARN] Esperando reconexión
2024-09-24T10:15:35Z [INFO] Reconectado exitosamente"""

try:
    response = requests.post(
        f"{API_URL}/api/analyze",
        json={"logs": test_logs},
        headers={"Content-Type": "application/json"},
        timeout=60
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        print(f"\n✅ Análisis exitoso!")
        print(f"\nReporte diagnóstico:")
        print(f"  {data.get('diagnostic_report', 'N/A')[:300]}...\n")
        print(f"Timing:")
        timing = data.get('timing', {})
        print(f"  Total: {timing.get('total_seconds', 'N/A')}s")
        print(f"  Ollama: {timing.get('ollama_seconds', 'N/A')}s")
        print(f"  Cache: {'✓ HIT' if timing.get('cache_hit') else '✗ MISS'}")
    else:
        print(f"\n❌ Error en análisis:")
        print(f"{json.dumps(data, indent=2)}")
        
except requests.exceptions.Timeout:
    print("⚠️  Timeout (más de 60 segundos)")
    print("   Esto es normal si es la primera llamada a Ollama Cloud")
except requests.exceptions.ConnectionError:
    print("❌ Error: No se puede conectar a la API Flask")
except Exception as e:
    print(f"❌ Error: {e}")

print(f"\n{'-' * 70}")
print("3️⃣  PRUEBA: Análisis Solo Patrones (Rápido)")
print(f"{'-' * 70}\n")

try:
    response = requests.post(
        f"{API_URL}/api/patterns",
        json={"logs": test_logs},
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        print(f"\n✅ Análisis de patrones exitoso!")
        print(f"\nPatrones encontrados:")
        for pattern in data.get('pattern_summary', [])[:3]:
            print(f"  - {pattern}")
        print(f"\nErrores principales:")
        for error in data.get('top_errors', [])[:3]:
            print(f"  - {error}")
    else:
        print(f"\n❌ Error:")
        print(f"{json.dumps(data, indent=2)}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print(f"\n{'-' * 70}")
print("RESUMEN")
print(f"{'-' * 70}\n")

print("✅ Próximos pasos:")
print("1. Si Health Check pasó: Tu API está conectada a Ollama Cloud ✓")
print("2. Si Análisis pasó: El flujo completo funciona ✓")
print("3. Si Patrones pasó: El análisis local está funcionando ✓")
print("\n💡 Para exponer tu API a internet:")
print("   - Con ngrok: ngrok http 5000")
print("   - Con Cloudflare: cloudflared tunnel run")
print("\n📝 Endpoints disponibles:")
print("   GET  http://localhost:5000/api/health")
print("   POST http://localhost:5000/api/analyze")
print("   POST http://localhost:5000/api/analyze-fast")
print("   POST http://localhost:5000/api/patterns")
print("   POST http://localhost:5000/api/incidents")

#!/usr/bin/env python3
"""
Script para descubrir los endpoints correctos de Ollama Cloud
Prueba varios paths comunes
"""

import requests
import json
from dotenv import load_dotenv
import os
from pathlib import Path

# Cargar variables de entorno con manejo robusto de encoding
def load_env_safe(env_file):
    """Carga archivo .env con manejo robusto de encoding"""
    try:
        load_dotenv(env_file, encoding='utf-8', override=True)
        return True
    except UnicodeDecodeError:
        try:
            load_dotenv(env_file, encoding='latin-1', override=True)
            return True
        except Exception as e:
            print(f"Error loading {env_file}: {e}")
            return False

# Intentar cargar archivos .env
for env_file in [".env.production", ".env"]:
    if Path(env_file).exists():
        load_env_safe(env_file)
        break

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "https://api.ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b:cloud")

print(f"🔍 Descubriendo endpoints de Ollama Cloud")
print(f"URL Base: {OLLAMA_API_URL}")
print(f"Modelo: {OLLAMA_MODEL}")
print(f"API Key: {'✓ Configurada' if OLLAMA_API_KEY else '✗ NO configurada'}")
print("-" * 70)

# Preparar headers con autenticación
headers = {}
if OLLAMA_API_KEY:
    headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
headers["Content-Type"] = "application/json"

# Lista de endpoints a probar
endpoints_to_test = [
    # Variantes comunes de health check
    ("GET", "/health", None, "Health check (raíz)"),
    ("GET", "/api/health", None, "Health check (/api)"),
    ("GET", "/v1/health", None, "Health check (/v1)"),
    ("GET", "/api/tags", None, "Lista de modelos (/api/tags)"),
    ("GET", "/v1/models", None, "Lista de modelos (/v1 OpenAI)"),
    ("POST", "/api/generate", {"model": OLLAMA_MODEL, "prompt": "test"}, "Generate (/api)"),
    ("POST", "/v1/chat/completions", {"model": OLLAMA_MODEL, "messages": [{"role": "user", "content": "test"}]}, "Chat completions (OpenAI)"),
    ("POST", "/v1/completions", {"model": OLLAMA_MODEL, "prompt": "test"}, "Completions (/v1)"),
]

print("\n📡 Pruebas de endpoints:\n")

for method, path, data, description in endpoints_to_test:
    url = f"{OLLAMA_API_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        else:  # POST
            response = requests.post(url, headers=headers, json=data, timeout=5)
        
        status = response.status_code
        status_emoji = "✓" if status < 400 else "✗"
        
        print(f"{status_emoji} [{status}] {method:6} {path:30} - {description}")
        
        if status < 400:
            try:
                response_data = response.json()
                # Mostrar primeras 200 chars de la respuesta
                resp_str = json.dumps(response_data, indent=2)[:200]
                print(f"    Respuesta: {resp_str}...\n")
            except:
                print(f"    Respuesta: {response.text[:200]}...\n")
        else:
            print(f"    Error: {response.text[:200]}\n")
            
    except requests.exceptions.Timeout:
        print(f"✗ [TIMEOUT] {method:6} {path:30} - {description}\n")
    except requests.exceptions.ConnectionError as e:
        print(f"✗ [ERROR]   {method:6} {path:30} - {description}")
        print(f"    Error: {str(e)[:100]}\n")
    except Exception as e:
        print(f"✗ [ERROR]   {method:6} {path:30} - {description}")
        print(f"    Error: {str(e)[:100]}\n")

print("-" * 70)
print("\n💡 Recomendaciones:")
print("1. Si algún endpoint respondió con 200, ese es el correcto")
print("2. Si recibiste 401, necesitas agregar la API Key al header")
print("3. Si recibiste 404, ese endpoint no existe en tu instancia")
print("4. Si recibiste 500, hay un error del servidor")
print("\n📝 Una vez identifiques el endpoint correcto, actualiza .env.production:")
print("   OLLAMA_API_URL=https://api.ollama.com")
print("   OLLAMA_API_KEY=tu-clave-aqui")
print("   OLLAMA_MODEL=llama3.2:1b:cloud")

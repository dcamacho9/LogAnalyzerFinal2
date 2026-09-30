#!/usr/bin/env python
"""
Cliente Interactivo para la API REST del Agente
Permite chatear con el agente desde la línea de comandos usando la API
"""

import requests
import json
import sys

API_BASE_URL = "http://localhost:5000/api"

class APIClient:
    def __init__(self):
        self.base_url = API_BASE_URL
        
    def check_health(self):
        """Verificar que la API está disponible"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def load_logs(self, limit=100):
        """Cargar logs"""
        try:
            response = requests.post(
                f"{self.base_url}/load-logs",
                json={"limit": limit},
                timeout=30
            )
            data = response.json()
            if data["status"] == "success":
                print(f"✅ {data['logs_loaded']} logs cargados")
                print(f"   {data['events_annotated']} eventos anotados")
                print(f"   {data['patterns_found']} patrones detectados\n")
                return True
            else:
                print(f"❌ {data.get('message', 'Error')}\n")
                return False
        except Exception as e:
            print(f"❌ Error: {e}\n")
            return False
    
    def send_message(self, message):
        """Enviar mensaje al agente"""
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json={"message": message},
                timeout=300
            )
            data = response.json()
            if data["status"] == "success":
                return data["message"]
            else:
                return f"❌ Error: {data.get('message', 'Error desconocido')}"
        except requests.exceptions.Timeout:
            return "⏱️ Timeout: La respuesta tardó demasiado"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def get_stats(self):
        """Obtener estadísticas"""
        try:
            response = requests.get(f"{self.base_url}/stats", timeout=10)
            data = response.json()
            if data["status"] == "success":
                print("\n" + "="*60)
                print("ESTADÍSTICAS DE LOGS")
                print("="*60)
                print(f"Total de eventos: {data['total_events']}")
                print("\nPor nivel:")
                for level, count in sorted(data['by_level'].items(), key=lambda x: x[1], reverse=True):
                    pct = (count / data['total_events']) * 100
                    print(f"  {level:10} {count:5} ({pct:5.1f}%)")
                print("="*60 + "\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    def get_patterns(self):
        """Obtener patrones"""
        try:
            response = requests.get(f"{self.base_url}/patterns", timeout=10)
            data = response.json()
            if data["status"] == "success":
                print("\n" + "="*60)
                print("PATRONES DETECTADOS")
                print("="*60)
                for i, pattern in enumerate(data['patterns'], 1):
                    print(f"{i}. {pattern}")
                print("="*60 + "\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    def get_errors(self):
        """Obtener errores principales"""
        try:
            response = requests.get(f"{self.base_url}/errors", timeout=10)
            data = response.json()
            if data["status"] == "success":
                print("\n" + "="*60)
                print("ERRORES PRINCIPALES")
                print("="*60)
                for i, error in enumerate(data['errors'], 1):
                    count = error.get('count', 1)
                    msg = error.get('message', 'Unknown')[:70]
                    print(f"{i:2}. [{count:3}x] {msg}")
                print("="*60 + "\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    def get_history(self):
        """Ver historial"""
        try:
            response = requests.get(f"{self.base_url}/history", timeout=10)
            data = response.json()
            if data["status"] == "success":
                print("\n" + "="*60)
                print("HISTORIAL DE CONVERSACIÓN")
                print("="*60)
                for msg in data['history']:
                    role = "👤 Usuario" if msg["role"] == "user" else "🤖 Asistente"
                    print(f"{role}: {msg['content'][:100]}...")
                print("="*60 + "\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    def clear_history(self):
        """Limpiar historial"""
        try:
            response = requests.post(f"{self.base_url}/clear-history", timeout=10)
            data = response.json()
            if data["status"] == "success":
                print("✅ Historial limpiado\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    def show_help(self):
        """Mostrar ayuda"""
        print("\n" + "="*60)
        print("COMANDOS DISPONIBLES")
        print("="*60)
        print("/help      - Mostrar esta ayuda")
        print("/stats     - Ver estadísticas de logs")
        print("/patterns  - Ver patrones detectados")
        print("/errors    - Ver errores principales")
        print("/history   - Ver historial de chat")
        print("/clear     - Limpiar historial")
        print("/exit      - Salir")
        print("\nO escribe tu pregunta para analizar los logs")
        print("="*60 + "\n")

def main():
    client = APIClient()
    
    print("\n" + "="*60)
    print("🤖 CLIENTE API - AGENTE IA INTERACTIVO")
    print("="*60)
    
    # Verificar que API está disponible
    print("\n🔍 Conectando con API...")
    if not client.check_health():
        print("❌ Error: API no disponible en http://localhost:5000")
        print("Inicia la API con: python api_interactive.py")
        sys.exit(1)
    
    print("✅ API disponible")
    
    # Cargar logs
    print("\n📂 Cargando logs...")
    if not client.load_logs():
        sys.exit(1)
    
    print("✅ Listo para chatear. Escribe /help para ver comandos\n")
    
    # Loop interactivo
    while True:
        try:
            message = input("📝 Tú: ").strip()
            
            if not message:
                continue
            
            # Comandos
            if message.lower() == "/exit":
                print("\n👋 ¡Hasta luego!")
                break
            elif message.lower() == "/help":
                client.show_help()
            elif message.lower() == "/stats":
                client.get_stats()
            elif message.lower() == "/patterns":
                client.get_patterns()
            elif message.lower() == "/errors":
                client.get_errors()
            elif message.lower() == "/history":
                client.get_history()
            elif message.lower() == "/clear":
                client.clear_history()
            else:
                # Mensaje normal
                print("\n🤖 Analizando...")
                response = client.send_message(message)
                print(f"🤖 Asistente: {response}\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    main()

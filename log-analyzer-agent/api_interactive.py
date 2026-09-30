#!/usr/bin/env python
"""
API REST Interactiva - Agente de Análisis de Logs
Expone funcionalidades interactivas vía HTTP
"""

from flask import Flask, request, jsonify
import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
from skills.log_ingestion import fetch_logs
from skills.log_pattern_matcher import run_log_pattern_matcher

load_dotenv()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_GENERATE_URL = f"{OLLAMA_API_URL}/api/generate"
MODEL_NAME = os.getenv("OLLAMA_MODEL", "mistral:7b")

# Estado global (en producción usar base de datos)
agent_state = {
    "logs": None,
    "pattern_result": None,
    "conversation_history": []
}

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "OK",
        "service": "Log Analyzer Chat API",
        "model": MODEL_NAME,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/load-logs', methods=['POST'])
def load_logs():
    """Cargar logs para análisis"""
    try:
        limit = request.json.get('limit', 100) if request.json else 100
        
        print(f"[API] Cargando logs (limit={limit})...")
        raw_log_lines = fetch_logs(source_id="prod-k8s-cluster", limit=limit)
        
        if not raw_log_lines:
            return jsonify({
                "status": "error",
                "message": "No se recuperaron logs"
            }), 400
        
        # Parsear logs
        from agent import parse_log_lines
        agent_state["logs"] = parse_log_lines(raw_log_lines)
        
        # Analizar patrones
        agent_state["pattern_result"] = run_log_pattern_matcher(agent_state["logs"])
        agent_state["conversation_history"] = []
        
        return jsonify({
            "status": "success",
            "logs_loaded": len(agent_state["logs"]),
            "events_annotated": len(agent_state["pattern_result"].get('annotated_events', [])),
            "patterns_found": len(agent_state["pattern_result"].get('pattern_summary', []))
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Enviar mensaje al agente"""
    try:
        if not agent_state.get("logs"):
            return jsonify({
                "status": "error",
                "message": "Primero debes cargar logs con POST /api/load-logs"
            }), 400
        
        data = request.json or {}
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                "status": "error",
                "message": "El mensaje no puede estar vacío"
            }), 400
        
        # Agregar al historial
        agent_state["conversation_history"].append({
            "role": "user",
            "content": message
        })
        
        # Construir system prompt con contexto
        pattern_summary = agent_state["pattern_result"].get("pattern_summary", [])
        top_errors = agent_state["pattern_result"].get("top_errors", [])
        
        system_prompt = """Eres un Asistente Experto en Análisis de Logs.
Ayuda a los ingenieros a diagnosticar problemas de infraestructura.

CONTEXTO:
"""
        if pattern_summary:
            system_prompt += "\nPatrones detectados:\n"
            for p in pattern_summary[:5]:
                system_prompt += f"  - {p}\n"
        
        if top_errors:
            system_prompt += "\nErrores principales:\n"
            for e in top_errors[:3]:
                system_prompt += f"  - {e.get('message')} ({e.get('count', 1)}x)\n"
        
        # Construir prompt con conversación
        prompt = system_prompt + "\nCONVERSACIÓN:\n"
        
        for msg in agent_state["conversation_history"][-5:]:
            prefix = "Usuario:" if msg["role"] == "user" else "Asistente:"
            prompt += f"{prefix} {msg['content']}\n"
        
        prompt += "Asistente:"
        
        # Llamar a Ollama
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,
                "num_predict": 500
            },
            timeout=300
        )
        response.raise_for_status()
        
        assistant_response = response.json().get("response", "").strip()
        
        # Guardar en historial
        agent_state["conversation_history"].append({
            "role": "assistant",
            "content": assistant_response
        })
        
        return jsonify({
            "status": "success",
            "message": assistant_response,
            "conversation_length": len(agent_state["conversation_history"])
        })
    
    except requests.exceptions.ConnectionError:
        return jsonify({
            "status": "error",
            "message": "No se puede conectar a Ollama. ¿Está ejecutándose 'ollama serve'?"
        }), 503
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtener estadísticas de logs"""
    if not agent_state.get("logs"):
        return jsonify({"status": "error", "message": "No hay logs cargados"}), 400
    
    logs = agent_state["logs"]
    levels = {}
    
    for log in logs:
        level = log.get("level", "UNKNOWN")
        levels[level] = levels.get(level, 0) + 1
    
    return jsonify({
        "status": "success",
        "total_events": len(logs),
        "by_level": levels
    })

@app.route('/api/patterns', methods=['GET'])
def get_patterns():
    """Obtener patrones detectados"""
    if not agent_state.get("pattern_result"):
        return jsonify({"status": "error", "message": "No hay análisis"}), 400
    
    patterns = agent_state["pattern_result"].get("pattern_summary", [])
    
    return jsonify({
        "status": "success",
        "patterns": patterns,
        "count": len(patterns)
    })

@app.route('/api/errors', methods=['GET'])
def get_errors():
    """Obtener errores principales"""
    if not agent_state.get("pattern_result"):
        return jsonify({"status": "error", "message": "No hay análisis"}), 400
    
    errors = agent_state["pattern_result"].get("top_errors", [])
    
    return jsonify({
        "status": "success",
        "errors": errors[:10],  # Top 10
        "count": len(errors)
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Obtener historial de conversación"""
    return jsonify({
        "status": "success",
        "history": agent_state["conversation_history"]
    })

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Limpiar historial de conversación"""
    agent_state["conversation_history"] = []
    return jsonify({"status": "success", "message": "Historial limpiado"})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🤖 API REST - AGENTE IA INTERACTIVO")
    print("="*60)
    print("\nEndpoints disponibles:")
    print("  POST /api/load-logs        - Cargar logs para análisis")
    print("  POST /api/chat             - Enviar mensaje al agente")
    print("  GET  /api/stats            - Ver estadísticas")
    print("  GET  /api/patterns         - Ver patrones detectados")
    print("  GET  /api/errors           - Ver errores principales")
    print("  GET  /api/history          - Ver historial de chat")
    print("  POST /api/clear-history    - Limpiar historial")
    print("  GET  /api/health           - Health check")
    print("\n🌐 Iniciando en http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=5000)

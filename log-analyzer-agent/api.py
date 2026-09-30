"""
API REST para el Agente de Análisis de Logs
Expone el agente como un servicio web accesible vía HTTP
"""

from flask import Flask, request, jsonify
import json
from agent import (
    parse_log_lines, 
    call_ollama, 
    MODEL_NAME, 
    OLLAMA_API_URL
)

# NOTA: Usar agent_optimized.py en produccion
from skills.log_ingestion import fetch_logs
from skills.log_pattern_matcher import run_log_pattern_matcher
from skills.servicenow_token_generator import run_servicenow_token_generator
from skills.servicenow_incident_creator import run_servicenow_incident_creator
import os

app = Flask(__name__)

# Configuración para soportar payloads grandes
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['JSON_SORT_KEYS'] = False

# Manejador para errores de JSON
@app.errorhandler(400)
def handle_bad_request(e):
    """Manejador mejorado para errores 400"""
    return jsonify({
        "status": "error",
        "message": f"400 Bad Request: {str(e)}",
        "hint": "Verifique que Content-Type sea 'application/json' y que el JSON esté bien formado",
        "step": "unknown"
    }), 400

@app.route('/api/health', methods=['GET'])
def health():
    """Verificar que el servicio está activo"""
    return jsonify({
        "status": "OK",
        "service": "Log Analyzer Agent",
        "model": MODEL_NAME,
        "ollama_url": OLLAMA_API_URL
    }), 200

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Analizar logs y generar diagnóstico
    
    POST /api/analyze
    Content-Type: application/json
    
    Body:
    {
        "logs": "string de logs (opcional, si no se proporciona carga desde test_logs.txt)",
        "limit": 100,
        "only_pattern_analysis": false
    }
    
    Response:
    {
        "status": "success|error",
        "step": "nombre del paso actual",
        "annotated_events": [...],
        "pattern_summary": [...],
        "diagnostic_report": "texto del diagnóstico",
        "timestamp": "ISO timestamp"
    }
    """
    try:
        # Intentar obtener JSON con manejo robusto
        # Verificar Content-Type primero
        content_type = request.headers.get('Content-Type', '').lower()
        
        if not content_type.startswith('application/json'):
            # Intentar parsear de todas formas con force=True
            data = request.get_json(force=True, silent=True)
            if data is None:
                # Si falla, intentar del request raw
                try:
                    data = json.loads(request.get_data(as_text=True)) if request.get_data() else {}
                except (json.JSONDecodeError, ValueError) as e:
                    return jsonify({
                        "status": "error",
                        "message": f"Error al parsear JSON: {str(e)}",
                        "hint": "Verifique que: 1) Content-Type sea 'application/json; charset=utf-8', 2) El JSON esté bien formado",
                        "step": "json_parsing"
                    }), 400
        else:
            # Content-Type es correcto, parsear JSON
            data = request.get_json(force=True, silent=True)
            if data is None:
                # Intentar del request raw si falla
                try:
                    data = json.loads(request.get_data(as_text=True)) if request.get_data() else {}
                except (json.JSONDecodeError, ValueError) as e:
                    return jsonify({
                        "status": "error",
                        "message": f"Error al parsear JSON: {str(e)}",
                        "hint": "Verifique que el JSON esté bien formado",
                        "step": "json_parsing"
                    }), 400
        
        if data is None:
            data = {}
        
        # Paso 1: Ingesta de logs
        if data.get('logs'):
            logs_str = data['logs']
            if not isinstance(logs_str, str):
                return jsonify({
                    "status": "error",
                    "message": "El campo 'logs' debe ser un string",
                    "step": "1_ingestion"
                }), 400
            raw_log_lines = logs_str.split('\n')
        else:
            raw_log_lines = fetch_logs(limit=data.get('limit', 100))
        
        if not raw_log_lines or all(not line.strip() for line in raw_log_lines):
            return jsonify({
                "status": "error",
                "message": "No se encontraron logs válidos",
                "step": "1_ingestion"
            }), 400
        
        # Filtrar líneas vacías
        raw_log_lines = [line for line in raw_log_lines if line.strip()]
        
        # Paso 2: Parsear logs
        raw_logs = parse_log_lines(raw_log_lines)
        
        # Paso 3: Análisis de patrones
        pattern_result = run_log_pattern_matcher(raw_logs)
        annotated_events = pattern_result.get("annotated_events", [])
        pattern_summary = pattern_result.get("pattern_summary", [])
        top_errors = pattern_result.get("top_errors", [])
        
        # Si solo se quiere análisis de patrones
        if data.get('only_pattern_analysis'):
            return jsonify({
                "status": "success",
                "step": "2_pattern_analysis",
                "annotated_events": annotated_events,
                "pattern_summary": pattern_summary,
                "top_errors": top_errors
            }), 200
        
        # Paso 4: Generar prompt para Ollama
        correlation_data = {
            "pattern_summary": pattern_summary,
            "top_errors": top_errors
        }
        
        prompt_for_llm = f"""
Analice los siguientes eventos anotados y genere un Reporte Diagnóstico Causa-Raíz breve (máximo 500 palabras).

Eventos Anotados (JSON):
{json.dumps(annotated_events[:20], indent=2)}  

Datos de Correlación:
{json.dumps(correlation_data, indent=2)}

Estructura del reporte esperada:
1. Resumen Ejecutivo (1-2 líneas)
2. Patrones Identificados (lista)
3. Análisis Causa-Raíz (2-3 líneas)
4. Acciones Recomendadas (lista)
"""
        
        # Paso 5: Llamar a Ollama
        diagnostic_report = call_ollama(prompt_for_llm)
        
        if not diagnostic_report:
            return jsonify({
                "status": "error",
                "message": "Timeout esperando respuesta de Ollama",
                "step": "3_ollama_inference"
            }), 504
        
        return jsonify({
            "status": "success",
            "step": "4_complete",
            "diagnostic_report": diagnostic_report,
            "total_events_processed": len(annotated_events)
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc() if app.debug else None,
            "step": "error"
        }), 500

@app.route('/api/patterns', methods=['POST'])
def analyze_patterns_only():
    """
    Análisis rápido de patrones sin invocar Ollama
    
    POST /api/patterns
    Content-Type: application/json
    
    Body:
    {
        "logs": "string de logs"
    }
    """
    try:
        # Intentar obtener JSON con manejo robusto
        content_type = request.headers.get('Content-Type', '').lower()
        
        if not content_type.startswith('application/json'):
            data = request.get_json(force=True, silent=True)
            if data is None:
                try:
                    data = json.loads(request.get_data(as_text=True)) if request.get_data() else {}
                except (json.JSONDecodeError, ValueError):
                    data = {}
        else:
            data = request.get_json(force=True, silent=True)
            if data is None:
                try:
                    data = json.loads(request.get_data(as_text=True)) if request.get_data() else {}
                except (json.JSONDecodeError, ValueError):
                    data = {}
        
        if data is None:
            data = {}
        
        if data.get('logs'):
            logs_str = data['logs']
            if not isinstance(logs_str, str):
                return jsonify({
                    "status": "error",
                    "message": "El campo 'logs' debe ser un string",
                    "step": "1_ingestion"
                }), 400
            raw_log_lines = logs_str.split('\n')
        else:
            raw_log_lines = fetch_logs(limit=100)
        
        raw_log_lines = [line for line in raw_log_lines if line.strip()]
        raw_logs = parse_log_lines(raw_log_lines)
        pattern_result = run_log_pattern_matcher(raw_logs)
        
        return jsonify({
            "status": "success",
            "annotated_events": pattern_result.get("annotated_events", [])[:20],
            "pattern_summary": pattern_result.get("pattern_summary", []),
            "top_errors": pattern_result.get("top_errors", [])
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc() if app.debug else None
        }), 500

@app.route('/api/ollama/chat', methods=['POST'])
def ollama_chat():
    """
    Llamada directa a Ollama (chatbot)
    
    POST /api/ollama/chat
    Content-Type: application/json
    
    Body:
    {
        "prompt": "Tu pregunta aquí"
    }
    """
    try:
        # Intentar obtener JSON con manejo robusto
        content_type = request.headers.get('Content-Type', '').lower()
        
        if not content_type.startswith('application/json'):
            data = request.get_json(force=True, silent=True)
            if data is None:
                try:
                    data = json.loads(request.get_data(as_text=True)) if request.get_data() else {}
                except (json.JSONDecodeError, ValueError):
                    data = {}
        else:
            data = request.get_json(force=True, silent=True)
            if data is None:
                try:
                    data = json.loads(request.get_data(as_text=True)) if request.get_data() else {}
                except (json.JSONDecodeError, ValueError):
                    data = {}
        
        if data is None:
            data = {}
        
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({
                "status": "error",
                "message": "Campo 'prompt' requerido"
            }), 400
        
        response = call_ollama(prompt)
        
        return jsonify({
            "status": "success",
            "model": "phi:2.7b",
            "prompt": prompt,
            "response": response
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc() if app.debug else None
        }), 500

@app.route('/api/incidents', methods=['POST'])
def create_incidents():
    """
    Crear incidentes en ServiceNow (requiere configuración de variables de entorno)
    
    POST /api/incidents
    Content-Type: application/json
    
    Body:
    {
        "logs": "string de logs",
        "dedup_mode": "pattern",
        "time_range": "Últimos 15 minutos"
    }
    """
    try:
        # Intentar obtener JSON con manejo robusto
        content_type = request.headers.get('Content-Type', '').lower()
        
        if not content_type.startswith('application/json'):
            data = request.get_json(force=True, silent=True)
            if data is None:
                try:
                    data = json.loads(request.get_data(as_text=True)) if request.get_data() else {}
                except (json.JSONDecodeError, ValueError):
                    data = {}
        else:
            data = request.get_json(force=True, silent=True)
            if data is None:
                try:
                    data = json.loads(request.get_data(as_text=True)) if request.get_data() else {}
                except (json.JSONDecodeError, ValueError):
                    data = {}
        
        if data is None:
            data = {}
        
        # Verificar que ServiceNow está configurado
        if not os.environ.get("SERVICENOW_CREATE_INCIDENTS", "").lower() == "true":
            return jsonify({
                "status": "info",
                "message": "La creación de incidentes está deshabilitada",
                "hint": "Configure SERVICENOW_CREATE_INCIDENTS=true"
            }), 400
        
        if data.get('logs'):
            logs_str = data['logs']
            if not isinstance(logs_str, str):
                return jsonify({
                    "status": "error",
                    "message": "El campo 'logs' debe ser un string",
                    "step": "1_ingestion"
                }), 400
            raw_log_lines = logs_str.split('\n')
        else:
            raw_log_lines = fetch_logs(limit=100)
        
        raw_log_lines = [line for line in raw_log_lines if line.strip()]
        raw_logs = parse_log_lines(raw_log_lines)
        pattern_result = run_log_pattern_matcher(raw_logs)
        annotated_events = pattern_result.get("annotated_events", [])
        
        incident_result = run_servicenow_incident_creator(
            annotated_events=annotated_events,
            correlation_data={"pattern_summary": pattern_result.get("pattern_summary", [])},
            dedup_mode=data.get('dedup_mode', 'pattern'),
            log_source=data.get('log_source', 'api'),
            time_range=data.get('time_range', 'unknown')
        )
        
        return jsonify(incident_result), 200 if incident_result.get("status") == "OK" else 400
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc() if app.debug else None
        }), 500

@app.route('/', methods=['GET'])
def index():
    """Documentación de la API"""
    return jsonify({
        "service": "Log Analyzer Agent API",
        "version": "1.0",
        "endpoints": {
            "GET /api/health": "Verificar que el servicio está activo",
            "POST /api/analyze": "Análisis completo con diagnóstico",
            "POST /api/patterns": "Análisis rápido de patrones (sin Ollama)",
            "POST /api/ollama/chat": "Chat directo con Ollama",
            "POST /api/incidents": "Crear incidentes en ServiceNow"
        },
        "ejemplo": {
            "curl": "curl -X POST http://localhost:5000/api/analyze -H 'Content-Type: application/json' -d '{\"limit\": 50}'"
        }
    }), 200

if __name__ == '__main__':
    import os
    
    # Obtener configuración del entorno
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV', 'production') != 'production'
    host = os.getenv('HOST', '0.0.0.0')
    
    print("=" * 60)
    print(" 🚀 Iniciando API del Agente de Análisis de Logs")
    print("=" * 60)
    print(f"\n🔧 Configuración:")
    print(f"  • Host: {host}")
    print(f"  • Puerto: {port}")
    print(f"  • Modo Debug: {debug_mode}")
    print(f"  • Entorno: {os.getenv('FLASK_ENV', 'production')}")
    print("\n📋 Endpoints disponibles:")
    print(f"  • GET  http://<tu-domain>:{port}/api/health")
    print(f"  • POST http://<tu-domain>:{port}/api/analyze")
    print(f"  • POST http://<tu-domain>:{port}/api/patterns")
    print(f"  • POST http://<tu-domain>:{port}/api/ollama/chat")
    print(f"  • POST http://<tu-domain>:{port}/api/incidents")
    print(f"\n📖 Documentación: http://<tu-domain>:{port}/")
    print("\n")
    app.run(debug=debug_mode, host=host, port=port)

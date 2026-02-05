import logging
import threading
import time
import psutil
import os
from flask import Flask, jsonify, render_template, Response, request
from prometheus_client import generate_latest, Gauge, Counter
from utils.metrics import get_system_metrics
from services.ai_service import AIService  # New AI service import

# ---------------------------------------------------------
# 1. PROMETHEUS SETUP
# ---------------------------------------------------------
PROM_CPU = Gauge('system_cpu_usage', 'Current CPU usage percentage')
PROM_MEM = Gauge('system_memory_usage', 'Current RAM usage percentage')
PROM_DISK = Gauge('system_disk_usage', 'Current Disk usage percentage')
PROM_LOGS = Counter('system_logs_generated', 'Total number of logs generated', ['level'])
PROM_AI_ALERTS = Counter('ai_alerts_generated', 'AI-enhanced alerts generated', ['severity'])

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

logs_store = []
ai_alerts_store = []  # Store AI-enhanced alerts

# Initialize AI Service
ai_service = None
try:
    ai_service = AIService()
    print(" -> AI Service Initialized Successfully")
except Exception as e:
    print(f" -> AI Service Failed: {e}. Running in fallback mode.")

# ---------------------------------------------------------
# 2. MONITORING THREAD WITH AI ENHANCEMENT
# ---------------------------------------------------------
def add_log(level, message, metrics=None):
    """Add log with optional AI enhancement for warnings/errors"""
    timestamp = time.strftime("%H:%M:%S")
    entry = f"{timestamp} | {level.upper()} | {message}"
    logs_store.append(entry)
    
    # AI Enhancement for critical alerts
    if level in ["warning", "error", "critical"] and ai_service:
        try:
            enhanced = ai_service.enhance_alert(
                alert_type=level,
                metric=message.split(":")[0] if ":" in message else "System",
                value=metrics.get('cpu') if metrics else 0,
                server={"name": "localhost", "type": "monitoring_server"}
            )
            
            # Add AI insights to the alert
            ai_entry = {
                "timestamp": timestamp,
                "level": level,
                "original_message": message,
                "ai_explanation": enhanced.get("explanation", ""),
                "likely_causes": enhanced.get("causes", []),
                "recommended_actions": enhanced.get("actions", []),
                "severity": enhanced.get("severity", "medium")
            }
            
            ai_alerts_store.append(ai_entry)
            PROM_AI_ALERTS.labels(severity=ai_entry["severity"]).inc()
            
            # Keep only last 20 AI alerts
            if len(ai_alerts_store) > 20:
                ai_alerts_store.pop(0)
                
        except Exception as e:
            print(f"AI enhancement failed: {e}")
    
    # Keep only last 100 regular logs
    if len(logs_store) > 100:
        logs_store.pop(0)
    
    PROM_LOGS.labels(level=level).inc()

def background_monitor():
    print(" -> Live Monitor & Prometheus Exporter Started...")
    print(" -> AI Enhancement: " + ("ENABLED" if ai_service else "DISABLED"))
    
    while True:
        try:
            time.sleep(2)
            metrics = get_system_metrics()
            cpu = metrics['cpu']
            mem = metrics['memory']['percent']
            disk = metrics['disk']['percent']

            # Update Prometheus metrics
            PROM_CPU.set(cpu)
            PROM_MEM.set(mem)
            PROM_DISK.set(disk)

            # Generate Intelligent Logs with AI Context
            if cpu > 90:
                add_log("critical", f"CPU Critical: {cpu}%", metrics)
            elif cpu > 70:
                add_log("warning", f"High CPU Load: {cpu}%", metrics)
            elif mem > 90:
                add_log("critical", f"Memory Critical: {mem}%", metrics)
            elif mem > 80:
                add_log("warning", f"High Memory Usage: {mem}%", metrics)
            elif disk > 90:
                add_log("critical", f"Disk Critical: {disk}%", metrics)
            elif disk > 80:
                add_log("warning", f"High Disk Usage: {disk}%", metrics)
            else:
                # Periodically add system status with AI insights
                if int(time.time()) % 30 == 0:  # Every 30 seconds
                    add_log("info", f"System Status: CPU {cpu}%, RAM {mem}%, Disk {disk}%", metrics)
                else:
                    add_log("info", f"System Stable: CPU {cpu}%, RAM {mem}%", metrics)

        except Exception as e:
            add_log("error", f"Monitor Error: {str(e)}")

# Start monitoring thread
t = threading.Thread(target=background_monitor, daemon=True)
t.start()

# ---------------------------------------------------------
# 3. ROUTES
# ---------------------------------------------------------
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/ai-dashboard")
def ai_dashboard():
    """New dashboard with AI insights"""
    return render_template("ai_dashboard.html")

# Prometheus Scraper URL
@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

# Frontend Data API
@app.route("/api/data")
def api_data():
    metrics_data = get_system_metrics()
    
    # Get AI insights if service is available
    ai_insights = {}
    if ai_service:
        try:
            ai_insights = ai_service.get_system_insights(metrics_data, logs_store[-10:])
        except Exception as e:
            ai_insights = {"error": str(e)}
    
    return jsonify({
        "metrics": metrics_data,
        "logs": logs_store[-20:],  # Last 20 logs
        "ai_alerts": ai_alerts_store[-10:],  # Last 10 AI-enhanced alerts
        "ai_insights": ai_insights,
        "ai_enabled": ai_service is not None
    })

# ---------------------------------------------------------
# 4. NEW AI ENDPOINTS
# ---------------------------------------------------------
@app.route("/api/ai/analyze", methods=["POST"])
def ai_analyze():
    """Analyze current system state with AI"""
    if not ai_service:
        return jsonify({"error": "AI service unavailable"}), 503
    
    try:
        metrics_data = get_system_metrics()
        recent_logs = logs_store[-50:]  # Last 50 logs
        
        analysis = ai_service.analyze_system_state(metrics_data, recent_logs)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/query", methods=["POST"])
def ai_query():
    """Natural language query about system"""
    if not ai_service:
        return jsonify({"error": "AI service unavailable"}), 503
    
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "Question required"}), 400
    
    try:
        response = ai_service.query_logs_natural_language(
            question=data['question'],
            logs=logs_store[-100:]  # Last 100 logs
        )
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/recommendations")
def ai_recommendations():
    """Get AI recommendations for system optimization"""
    if not ai_service:
        return jsonify({"error": "AI service unavailable"}), 503
    
    try:
        metrics_data = get_system_metrics()
        recommendations = ai_service.generate_recommendations(metrics_data)
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/explain-alert", methods=["POST"])
def explain_alert():
    """Explain an alert in detail"""
    if not ai_service:
        return jsonify({"error": "AI service unavailable"}), 503
    
    data = request.get_json()
    required_fields = ['message', 'level']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Message and level required"}), 400
    
    try:
        explanation = ai_service.enhance_alert(
            alert_type=data['level'],
            metric=data.get('metric', 'Unknown'),
            value=data.get('value', 0),
            server=data.get('server', {"name": "unknown", "type": "unknown"})
        )
        return jsonify(explanation)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Health check endpoint
@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "ai_service": "available" if ai_service else "unavailable",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

# ---------------------------------------------------------
# 5. START APPLICATION
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "="*50)
    print("CLOUD MONITOR WITH GENAI INTEGRATION")
    print("="*50)
    print("SYSTEM ONLINE: http://localhost:8000")
    print("DASHBOARD:     http://localhost:8000/dashboard")
    print("AI DASHBOARD:  http://localhost:8000/ai-dashboard")
    print("METRICS:       http://localhost:8000/metrics")
    print("HEALTH:        http://localhost:8000/health")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)

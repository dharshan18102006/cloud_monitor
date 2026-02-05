# Add to api.py or create new ai_routes.py
from flask import Blueprint, request, jsonify
from services.ai_service import AIService

ai_bp = Blueprint('ai', __name__)
ai_service = AIService()

@ai_bp.route('/analyze-alert', methods=['POST'])
def analyze_alert():
    """Enhance alerts with AI explanations"""
    data = request.json
    enhanced_alert = ai_service.enhance_alert(
        alert_type=data['type'],
        metric=data['metric'],
        value=data['value'],
        server=data.get('server')
    )
    return jsonify(enhanced_alert)

@ai_bp.route('/query-logs', methods=['POST'])
def query_logs_nl():
    """Natural language query for logs"""
    question = request.json.get('question')
    results = ai_service.query_logs_natural_language(question)
    return jsonify(results)

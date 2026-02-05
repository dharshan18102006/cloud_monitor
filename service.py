import os
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

class AIService:
    def __init__(self):
        self.setup_ai_client()
        self.alert_history = []
        self.setup_prompts()
        
    def setup_ai_client(self):
        """Initialize AI client - supports both OpenAI and fallback"""
        self.model = "openai"  # Change to "ollama" for local
        
        try:
            # Option 1: OpenAI (recommended for production)
            from openai import OpenAI
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print("⚠️  OPENAI_API_KEY not set. Using simulated AI.")
                self.client = None
                return
                
            self.client = OpenAI(api_key=api_key)
            self.model_name = "gpt-3.5-turbo"
            print(f"✅ Using OpenAI ({self.model_name})")
            
        except ImportError:
            print("⚠️  OpenAI not installed. Using simulated AI.")
            self.client = None
            
    def setup_prompts(self):
        """Define prompt templates for different scenarios"""
        self.prompts = {
            'alert_explanation': """You are a cloud monitoring expert. Analyze this alert:

Alert Type: {alert_type}
Metric: {metric}
Current Value: {value}%
Threshold: Usually {threshold}%
Server: {server_name} ({server_type})
Context: {context}

Provide JSON response with:
- "explanation": Simple one-sentence explanation
- "causes": Array of 3 most likely causes
- "actions": Array of 3 recommended actions
- "severity": "low", "medium", or "high"
- "related_metrics": Other metrics to check""",

            'system_analysis': """Analyze this system state:

CPU: {cpu}%
Memory: {memory}%
Disk: {disk}%
Recent Logs: {recent_logs}

Provide JSON response with:
- "status": "healthy", "warning", or "critical"
- "findings": Array of key observations
- "risks": Potential risks if not addressed
- "optimization": Suggestions for better performance""",

            'log_query': """Answer this question about system logs:
Question: {question}

Recent Logs:
{logs}

Provide JSON response with:
- "answer": Direct answer to the question
- "evidence": Log entries that support the answer
- "confidence": 0.0 to 1.0
- "follow_up": Questions to investigate further"""
        }
    
    def enhance_alert(self, alert_type: str, metric: str, value: float, 
                     server: Dict = None, threshold: float = None) -> Dict:
        """Add AI explanation to alerts"""
        
        # Default response if AI is not available
        default_response = {
            "explanation": f"{metric} is at {value}%",
            "causes": ["System load", "Application demand", "Background processes"],
            "actions": ["Check running processes", "Monitor trends", "Consider scaling"],
            "severity": "high" if value > 80 else "medium" if value > 60 else "low",
            "related_metrics": ["memory_usage", "disk_io", "network_traffic"]
        }
        
        # If no AI client, return simulated response
        if not self.client:
            return default_response
        
        # Determine threshold based on metric
        if not threshold:
            thresholds = {
                'cpu': 70, 'memory': 80, 'disk': 85,
                'CPU': 70, 'Memory': 80, 'Disk': 85
            }
            threshold = thresholds.get(metric, 70)
        
        # Prepare context
        context = ""
        if self.alert_history:
            recent = self.alert_history[-3:]
            context = f"Recent alerts: {', '.join([a.get('metric', '') for a in recent])}"
        
        try:
            prompt = self.prompts['alert_explanation'].format(
                alert_type=alert_type,
                metric=metric,
                value=value,
                threshold=threshold,
                server_name=server.get('name', 'Unknown') if server else 'Unknown',
                server_type=server.get('type', 'server') if server else 'server',
                context=context
            )
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a Senior DevOps Engineer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Store in history
            alert_record = {
                "timestamp": datetime.now().isoformat(),
                "metric": metric,
                "value": value,
                "severity": result.get("severity", "medium")
            }
            self.alert_history.append(alert_record)
            if len(self.alert_history) > 10:
                self.alert_history.pop(0)
                
            return result
            
        except Exception as e:
            print(f"AI enhancement failed: {e}")
            return default_response
    
    def analyze_system_state(self, metrics: Dict, recent_logs: List[str]) -> Dict:
        """Analyze overall system health"""
        if not self.client:
            return self.simulate_analysis(metrics, recent_logs)
        
        try:
            prompt = self.prompts['system_analysis'].format(
                cpu=metrics.get('cpu', 0),
                memory=metrics.get('memory', {}).get('percent', 0),
                disk=metrics.get('disk', {}).get('percent', 0),
                recent_logs='\n'.join(recent_logs[-10:])
            )
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a System Reliability Engineer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"System analysis failed: {e}")
            return self.simulate_analysis(metrics, recent_logs)
    
    def query_logs_natural_language(self, question: str, logs: List[str]) -> Dict:
        """Answer questions about logs in natural language"""
        if not self.client:
            return self.simulate_query(question, logs)
        
        try:
            prompt = self.prompts['log_query'].format(
                question=question,
                logs='\n'.join(logs[-50:])
            )
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are analyzing system monitoring logs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Log query failed: {e}")
            return self.simulate_query(question, logs)
    
    def generate_recommendations(self, metrics: Dict) -> Dict:
        """Generate optimization recommendations"""
        recommendations = []
        
        # CPU recommendations
        cpu = metrics.get('cpu', 0)
        if cpu > 70:
            recommendations.append({
                "type": "cpu",
                "priority": "high",
                "action": "Optimize CPU usage",
                "details": f"Current CPU is {cpu}%. Consider: 1. Identify CPU-intensive processes 2. Optimize application code 3. Add CPU limits"
            })
        
        # Memory recommendations
        mem = metrics.get('memory', {}).get('percent', 0)
        if mem > 80:
            recommendations.append({
                "type": "memory",
                "priority": "high",
                "action": "Address memory usage",
                "details": f"Memory at {mem}%. Consider: 1. Check for memory leaks 2. Increase swap space 3. Add more RAM"
            })
        
        # Disk recommendations
        disk = metrics.get('disk', {}).get('percent', 0)
        if disk > 85:
            recommendations.append({
                "type": "disk",
                "priority": "critical",
                "action": "Free up disk space",
                "details": f"Disk at {disk}%. Consider: 1. Clean up temporary files 2. Archive old logs 3. Increase storage"
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "recommendations": recommendations,
            "summary": f"Found {len(recommendations)} optimization opportunities"
        }
    
    def get_system_insights(self, metrics: Dict, recent_logs: List[str]) -> Dict:
        """Generate quick insights for dashboard"""
        insights = []
        
        # CPU insight
        if metrics.get('cpu', 0) > 70:
            insights.append("CPU usage is high. Consider optimizing processes.")
        
        # Memory insight
        if metrics.get('memory', {}).get('percent', 0) > 80:
            insights.append("Memory usage is elevated. Monitor for leaks.")
        
        # Check logs for patterns
        error_count = sum(1 for log in recent_logs if 'ERROR' in log or 'error' in log.lower())
        if error_count > 5:
            insights.append(f"Found {error_count} errors in recent logs. Review application health.")
        
        return {
            "insights": insights,
            "generated_at": datetime.now().isoformat(),
            "ai_available": self.client is not None
        }
    
    def simulate_analysis(self, metrics: Dict, recent_logs: List[str]) -> Dict:
        """Fallback analysis when AI is unavailable"""
        status = "healthy"
        if metrics.get('cpu', 0) > 80 or metrics.get('memory', {}).get('percent', 0) > 85:
            status = "warning"
        
        return {
            "status": status,
            "findings": ["System monitoring active", "Using simulated AI analysis"],
            "risks": ["No real AI insights available"],
            "optimization": ["Enable AI service for detailed analysis"]
        }
    
    def simulate_query(self, question: str, logs: List[str]) -> Dict:
        """Fallback for log queries"""
        return {
            "answer": "AI service is currently unavailable. Please enable OpenAI integration.",
            "evidence": [],
            "confidence": 0.1,
            "follow_up": ["Enable AI service for detailed log analysis?"]
        }

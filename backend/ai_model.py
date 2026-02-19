"""
AI Model wrapper for backward compatibility.
Delegates to AIService for actual AI operations.
"""
from ai_service import AIService

# Initialize AI service
_ai_service = AIService()

def predict_risk_score(code_content):
    """
    Predict risk score for code content.
    This function maintains backward compatibility with existing code.
    
    Args:
        code_content: The code content to analyze
        
    Returns:
        Risk score as float between 0.0 and 1.0
    """
    return _ai_service.predict_risk_score(code_content)

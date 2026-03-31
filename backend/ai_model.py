"""
model.py — Backward compatibility wrapper.
Delegates to AIService for actual analysis.
"""
from ai_service import AIService

_ai_service = AIService()


def predict_risk_score(code_content: str) -> float:
    """Predict risk score for code content. Returns float 0.0–1.0."""
    return _ai_service.predict_risk_score(code_content)
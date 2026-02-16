def predict_risk_score(code_content: str) -> float:
    """
    Simple heuristic-based risk analysis (PoC).
    """

    indicators = [
        "eval(", "exec(", "os.system", "subprocess",
        "base64", "fetch(", "XMLHttpRequest"
    ]

    score = 10.0

    for item in indicators:
        if item in code_content:
            score += 20.0

    return min(score, 100.0)

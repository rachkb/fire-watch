from firewatch.config import LOW_CONFIDENCE_THRESHOLD, HIGH_CONFIDENCE_THRESHOLD


def get_risk_level(predicted_class: str, confidence: float) -> str:
    confidence = float(confidence)          # Keras returns np.float32
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        return "Uncertain"
    if predicted_class == "Fire":
        return "High" if confidence >= HIGH_CONFIDENCE_THRESHOLD else "Medium"
    if predicted_class == "Smoke":
        return "Medium" if confidence >= HIGH_CONFIDENCE_THRESHOLD else "Low"
    if predicted_class == "Non-Fire":
        return "None"
    return "Uncertain"
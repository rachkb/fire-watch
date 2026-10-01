import random
from PIL import Image, ImageEnhance
from firewatch.config import CLASS_NAMES
from firewatch.inference.risk import get_risk_level


def load_model():
    return None


def classify(model, image: Image.Image) -> dict:
    raw = [random.random() ** 2 for _ in CLASS_NAMES]   # skewed, so you see varied results
    probs = {c: v / sum(raw) for c, v in zip(CLASS_NAMES, raw)}
    cls = max(probs, key=probs.get)
    conf = probs[cls]
    return {
        "predicted_class": cls,
        "confidence": conf,
        "probabilities": probs,
        "risk_level": get_risk_level(cls, conf),
    }


def generate_heatmap(model, image: Image.Image) -> Image.Image:
    return ImageEnhance.Color(image.convert("RGB")).enhance(4.0)   # placeholder
"""classify(): image -> class, confidence, probabilities, risk level."""
import numpy as np

from firewatch.config import CLASS_NAMES
from firewatch.inference.preprocess import preprocess_image
from firewatch.inference.risk import get_risk_level


def classify(model, image) -> dict:
    x = preprocess_image(image)
    probs = np.asarray(model(x, training=False))[0].astype("float64")

    idx = int(np.argmax(probs))
    predicted = CLASS_NAMES[idx]          # CLASS_NAMES is in the model's OUTPUT order
    confidence = float(probs[idx])
    return {
        "predicted_class": predicted,
        "confidence": confidence,
        "probabilities": {name: float(p) for name, p in zip(CLASS_NAMES, probs)},
        "risk_level": get_risk_level(predicted, confidence),
    }
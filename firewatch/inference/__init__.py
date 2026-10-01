"""Single entry point for the model. The UI only imports from here:

    from firewatch import inference
    inference.load_model(); inference.classify(model, img); inference.generate_heatmap(model, img)

Imports are lazy, so importing firewatch.inference.risk (for example in tests)
never loads TensorFlow, and the mock needs no TensorFlow at all.
"""
from firewatch.config import USE_MOCK_MODEL


def load_model():
    if USE_MOCK_MODEL:
        from .mock import load_model as fn
    else:
        from .classifier import load_model as fn
    return fn()


def classify(model, image):
    if USE_MOCK_MODEL:
        from .mock import classify as fn
    else:
        from .predictor import classify as fn
    return fn(model, image)


def generate_heatmap(model, image):
    if USE_MOCK_MODEL:
        from .mock import generate_heatmap as fn
    else:
        from .heatmap import generate_heatmap as fn
    return fn(model, image)
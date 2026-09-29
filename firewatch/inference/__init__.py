from firewatch.config import USE_MOCK_MODEL

if USE_MOCK_MODEL:
    from .mock import load_model, classify, generate_heatmap
else:
    from .classifier import load_model
    from .predictor import classify
    from .heatmap import generate_heatmap
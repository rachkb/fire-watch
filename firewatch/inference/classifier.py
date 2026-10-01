"""Loads the trained Keras model once."""
from pathlib import Path

from firewatch.config import CLASS_NAMES, INPUT_SIZE, MODEL_PATH

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_model():
    import tensorflow as tf

    path = _PROJECT_ROOT / MODEL_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Model file not found: {path}. Put the .keras file in models/ "
            f"and check MODEL_PATH in firewatch/config.py.")

    model = tf.keras.models.load_model(path, compile=False)   # inference only

    # Fail loudly if someone swaps in a model that doesn't match config.py.
    expected_in = (None, INPUT_SIZE[0], INPUT_SIZE[1], 3)
    if tuple(model.input_shape) != expected_in:
        raise ValueError(f"Model expects input {model.input_shape}, "
                         f"but config.INPUT_SIZE implies {expected_in}.")
    if model.output_shape[-1] != len(CLASS_NAMES):
        raise ValueError(f"Model has {model.output_shape[-1]} outputs, "
                         f"but config.CLASS_NAMES has {len(CLASS_NAMES)} classes.")
    return model
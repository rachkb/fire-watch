"""Integration tests for the real model. Skipped automatically if TensorFlow or
the model file is missing. Run: python -m pytest tests/test_inference.py -v"""
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("tensorflow")

from firewatch.config import CLASS_NAMES, INPUT_SIZE, MODEL_PATH  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / MODEL_PATH).exists(),
                                reason="model file not found")


@pytest.fixture(scope="module")
def model():
    from firewatch.inference.classifier import load_model
    return load_model()


@pytest.fixture
def image():
    rng = np.random.default_rng(0)
    return Image.fromarray(rng.integers(0, 256, (240, 320, 3), dtype="uint8"))


def test_class_order_matches_training():
    # The notebook printed ['Smoke', 'fire', 'non fire'] (alphabetical folder order).
    assert CLASS_NAMES == ["Smoke", "Fire", "Non-Fire"]


def test_preprocess_shape_and_range(image):
    from firewatch.inference.preprocess import preprocess_image
    x = preprocess_image(image)
    assert x.shape == (1, *INPUT_SIZE, 3) and x.dtype == np.float32
    assert x.max() > 1.0                    # raw 0-255, NOT divided by 255


def test_classify_contract(model, image):
    from firewatch.inference.predictor import classify
    r = classify(model, image)
    assert set(r) == {"predicted_class", "confidence", "probabilities", "risk_level"}
    assert r["predicted_class"] in CLASS_NAMES
    assert set(r["probabilities"]) == set(CLASS_NAMES)
    assert abs(sum(r["probabilities"].values()) - 1.0) < 1e-4
    assert r["confidence"] == max(r["probabilities"].values())


def test_handles_rgba_and_grayscale():
    from firewatch.inference.preprocess import preprocess_image
    for mode in ("RGBA", "L", "P"):
        assert preprocess_image(Image.new(mode, (50, 40))).shape == (1, *INPUT_SIZE, 3)


def test_heatmap_returns_image(model, image):
    from firewatch.inference.heatmap import generate_heatmap
    out = generate_heatmap(model, image)
    assert isinstance(out, Image.Image) and out.size == image.size


def _scene(kind):
    from PIL import ImageDraw
    im = Image.new("RGB", (640, 480), (110, 160, 90))
    d = ImageDraw.Draw(im)
    if kind == "fire":
        d.ellipse((250, 200, 400, 430), fill=(240, 110, 20))
    elif kind == "smoke":
        for i in range(8):
            d.ellipse((200 + i * 20, 60 + i * 25, 420 + i * 20, 200 + i * 25), fill=(150, 150, 155))
    return im


@pytest.mark.parametrize("kind", ["fire", "smoke"])
def test_gradcam_is_not_flat(model, kind):
    """Regression: a confident prediction used to give an all-zero (flat blue) heatmap."""
    from firewatch.inference.gradcam import compute_gradcam
    from firewatch.inference.preprocess import preprocess_image
    heat, _ = compute_gradcam(model, preprocess_image(_scene(kind)))
    assert heat.max() == pytest.approx(1.0) and heat.min() < 1.0
    assert heat.std() > 0.01


def test_gradcam_uniform_image_raises_instead_of_flat_map(model):
    """A uniform image has no spatial pattern, so no heatmap rather than a misleading flat one."""
    from firewatch.inference.gradcam import compute_gradcam
    from firewatch.inference.preprocess import preprocess_image
    try:
        heat, _ = compute_gradcam(model, preprocess_image(_scene("plain")))
    except ValueError:
        return
    assert heat.std() > 0.01
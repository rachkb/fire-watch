"""Image preparation for the model.

Must match training exactly (SRS REQ-2.1, REQ-2.2). The trained EfficientNetV2
model rescales pixels internally, so it takes RAW 0-255 float pixels at 160x160.
Do NOT divide by 255 here. Resizing uses tf.image.resize (bilinear), the same
call Keras' image_dataset_from_directory used when the model was trained.
"""
import numpy as np
from PIL import Image, ImageOps

from firewatch.config import INPUT_SIZE


def prepare_image(image: Image.Image) -> Image.Image:
    """Upright (EXIF) RGB copy of the image."""
    return ImageOps.exif_transpose(image).convert("RGB")


def preprocess_image(image: Image.Image) -> np.ndarray:
    """Returns a float32 batch of shape (1, 160, 160, 3) with values 0-255."""
    import tensorflow as tf

    arr = np.asarray(prepare_image(image), dtype="float32")
    resized = tf.image.resize(arr[np.newaxis, ...], INPUT_SIZE, method="bilinear")
    return resized.numpy().astype("float32")
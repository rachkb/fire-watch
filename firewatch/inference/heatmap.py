"""generate_heatmap(): overlay image for the UI. Generated on demand, never stored (REQ-6.6)."""
import numpy as np
from PIL import Image

from firewatch.inference.gradcam import compute_gradcam
from firewatch.inference.preprocess import prepare_image, preprocess_image

_MAX_SIDE = 1024      # keep very large photos from producing huge overlays
_MAX_ALPHA = 0.6      # opacity of the hottest areas; cold areas stay see-through


def generate_heatmap(model, image: Image.Image) -> Image.Image:
    """Raises on failure; the UI then shows 'Heatmap unavailable' (REQ-5.4)."""
    from matplotlib import colormaps

    heat, _ = compute_gradcam(model, preprocess_image(image))

    base = prepare_image(image)
    base.thumbnail((_MAX_SIDE, _MAX_SIDE))
    heat_img = Image.fromarray((heat * 255).astype("uint8")).resize(base.size, Image.BILINEAR)
    h = np.asarray(heat_img, dtype="float32") / 255.0

    colored = colormaps["jet"](h)[:, :, :3] * 255
    alpha = 0.4
    blended = np.asarray(base, dtype="float32") * (1 - alpha) + colored * alpha
    return Image.fromarray(blended.astype("uint8"))

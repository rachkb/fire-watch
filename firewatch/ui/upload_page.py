"""Upload section (right column of the landing page, Fig 1)."""
from io import BytesIO

import streamlit as st
from PIL import Image

from firewatch import inference
from firewatch.config import ALLOWED_UPLOAD_FORMATS, MAX_UPLOAD_SIZE_MB
from firewatch.ui import components, data_access


@st.cache_resource          # load the model once (REQ-2.4, NREQ-PERF-2)
def get_model():
    return inference.load_model()


def _read_valid_image(file):
    """Returns (bytes, PIL image) or (None, None) after showing an inline error."""
    if file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:                    # REQ-1.2
        st.error(f"This file is larger than {MAX_UPLOAD_SIZE_MB} MB. Choose a smaller image.")
        return None, None
    data = file.getvalue()                    # a stream: read once, reuse the bytes
    try:
        img = Image.open(BytesIO(data))
        img.load()                                                      # REQ-1.3, NREQ-SEC-2
        if img.format not in ("JPEG", "PNG"):
            raise ValueError("unsupported format")
    except Exception:
        st.error("This file is not a valid JPEG or PNG image.")
        return None, None
    return data, img.convert("RGB")


def render_upload():
    file = st.file_uploader(
        f"Click to browse JPEG or PNG, up to {MAX_UPLOAD_SIZE_MB}MB",
        type=ALLOWED_UPLOAD_FORMATS,
    )
    st.caption("Uploaded images and their results are saved and may appear "
               "in the submission history.")                            # REQ-6.5

    data, img = _read_valid_image(file) if file else (None, None)
    if img is not None:
        st.image(img, caption="Preview", width=320)                     # REQ-1.4

    if st.button("Analyze Image", disabled=img is None, use_container_width=True):
        with st.spinner("Analyzing..."):                                # REQ-1.5
            try:
                result = inference.classify(get_model(), img)
            except Exception:
                st.error("The image could not be analyzed. Try again or use another image.")
                return

        cache = {}

        def heatmap_fn():           # generated on demand and never stored (REQ-6.6)
            if "img" not in cache:
                cache["img"] = inference.generate_heatmap(get_model(), img)
            return cache["img"]

        components.result_dialog(result, img, heatmap_fn)               # show the result first

        try:                                                            # REQ-6.1, 6.3, 6.4
            data_access.add_submission(data, result)
        except Exception:
            st.toast("The result was not saved to the history.", icon="⚠️")
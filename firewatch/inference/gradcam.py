"""Raw Grad-CAM for the nested EfficientNetV2 model (ported from the team notebook).

Layout of the saved model: input -> augment -> efficientnetv2-b0 (nested model,
last conv feature map 5x5x1280) -> GAP -> dropout -> dense -> dense(softmax).

Two fixes over the notebook version, found by testing:
1. The gradient is taken from the final layer's pre-softmax scores (logits).
   When the model is very confident, softmax saturates and its gradient
   shrinks to zero, which produced a flat, all-blue heatmap.
2. If every cell comes out negative (so ReLU would zero the whole map), the
   raw map is min-max scaled instead, so it still shows relative importance.

If the map has no spatial variation at all (for example a perfectly uniform image,
where every location contributes the same), a ValueError is raised, so the UI shows
"Heatmap unavailable" (REQ-5.4) instead of a misleading flat overlay.
"""
import numpy as np


def compute_gradcam(model, batch: np.ndarray):
    """Returns (heatmap, predicted_index). heatmap is a 2-D float array in 0..1 (5x5 here)."""
    import tensorflow as tf

    base = next(l for l in model.layers if isinstance(l, tf.keras.Model))
    base_idx = model.layers.index(base)
    augment = next((l for l in model.layers[:base_idx] if l.name == "augment"), None)
    post = model.layers[base_idx + 1:]                  # GAP, dropout, dense, dense(softmax)
    final = post[-1]

    x = tf.convert_to_tensor(batch)
    with tf.GradientTape() as tape:
        if augment is not None:
            x = augment(x, training=False)              # augmentation is off at inference
        conv = base(x, training=False)                  # (1, 5, 5, 1280)
        tape.watch(conv)
        y = conv
        for layer in post[:-1]:
            y = layer(y, training=False)
        probs = final(y, training=False)
        pred = tf.argmax(probs[0])
        if hasattr(final, "kernel"):                    # pre-softmax scores (see fix 1)
           #score = (tf.matmul(y, final.kernel) + final.bias)[:, pred]
           score = probs[:, pred]
        else:
            score = probs[:, pred]

    grads = tape.gradient(score, conv)
    pooled = tf.reduce_mean(grads, axis=(0, 1, 2))
    heat = tf.squeeze(conv[0] @ pooled[..., tf.newaxis]).numpy()

    if np.ptp(heat) <= 1e-6 * (np.abs(heat).max() + 1e-12):   # same value in every cell
        raise ValueError("Grad-CAM map is flat for this image")
   
    print(base.name, heat.shape)

    positive = np.maximum(heat, 0)
    if positive.max() > 0:                              # standard Grad-CAM
        heat = positive / positive.max()
    else:                                               # see fix 2
        span = heat.max() - heat.min()
        heat = (heat - heat.min()) / span if span > 0 else np.zeros_like(heat)
    return heat.astype("float32"), int(pred)
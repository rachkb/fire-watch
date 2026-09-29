"""
Central configuration and shared constants for FireWatch.

This is the single source of truth for class labels, thresholds, and
risk-level rules. The UI and the (future) real inference module should
both import from here rather than hardcoding these values separately.
"""

CLASS_NAMES = ["Fire", "Non-Fire", "Smoke"]

# Below this confidence, a result is low-confidence and its risk level is
# forced to "Uncertain" regardless of predicted class (SRS REQ-3.4, REQ-4.2).
LOW_CONFIDENCE_THRESHOLD = 0.60

# At or above this confidence, Fire/Smoke results are bumped to a
# higher risk tier.
HIGH_CONFIDENCE_THRESHOLD = 0.80

MAX_UPLOAD_SIZE_MB = 10
ALLOWED_UPLOAD_FORMATS = ["jpg", "jpeg", "png"]

# Rows shown per page on the Submission History list (Figure 1).
HISTORY_PAGE_SIZE = 4

RISK_LEVELS = {
    "High": {
    "color": "#D32F2F",
    "message": "Escalate to the proper authorities if this reflects a real scene.",
},
    "Medium": {
        "color": "#F57C00",
        "message": "Possible fire or smoke detected. Manual review recommended before escalating.",
    },
    "Low": {
    "color": "#FBC02D",
    "message": "Possible smoke detected. Manual verification recommended.",
},
    "None": {
        "color": "#388E3C",
        "message": "No fire or smoke indicators detected.",
    },
    "Uncertain": {
        "color": "#757575",
        "message": "Confidence too low to assess. Manual review recommended.",
    },
}

DISCLAIMER_TEXT = (
    "FireWatch is a decision support tool only. It is not a certified "
    "fire alarm or emergency detection service."
)

INPUT_SIZE = (224, 224)                 # REQ-2.1
MODEL_PATH = "models/firewatch.keras"   # agree on the filename with the model teammate
USE_MOCK_MODEL = True                   # set to False when the real model is ready

STATUSES = ["Pending", "Approved", "Flagged"]
FLAG_REASONS = ["Misclassified", "Inappropriate content", "Other"]

MAX_FAILED_LOGINS = 5                   # REQ-8.4
LOCKOUT_MINUTES = 15
SESSION_TIMEOUT_MINUTES = 30            # proposed; SRS 3.8.2 doesn't give a number
TAGLINE = "Fire & smoke detection"
DISPLAY_CLASS_ORDER = ["Fire", "Non-Fire", "Smoke"]
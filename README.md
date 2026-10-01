# FireWatch

**AI-assisted fire and smoke detection for still images.**

FireWatch classifies an uploaded photo as **Fire**, **Smoke**, or **Non-Fire**, reports a confidence score and a risk level, and shows a Grad-CAM heatmap of the regions that influenced the result. Administrators review every submission before it appears in the public history.

> **FireWatch is a decision-support tool only.** It is an academic prototype, not a certified fire alarm or emergency detection service. It never sends alerts and must not replace smoke detectors, alarms, or official emergency services.

**Live demo:** https://fire-watch-softeng2.streamlit.app *(free tier; the first load after idle may take a minute)*

---

## Features

**General users (no login)**
- Upload a JPEG or PNG image (up to 10 MB) with preview.
- View the predicted class, confidence, and probabilities for all three classes.
- See a colour-coded **risk level** with escalation guidance.
- Toggle a **Grad-CAM heatmap** showing which regions drove the prediction.
- Browse a read-only, filterable, paginated history of **approved** submissions.
- Results under 60% confidence are labelled **Uncertain** with a manual-review recommendation.

**Administrators (login required)**
- Secure login (bcrypt-hashed passwords, temporary lockout after repeated failures).
- Filter submissions by risk level, class, status, and date.
- **Approve**, **flag** (with reason, optional correct class, optional note), or **permanently remove** submissions.
- View analytics: totals by class, risk level, and status, plus administrator-reported false negatives and false positives.

---

## How it works

```
Upload ─► Validate ─► Preprocess ─► EfficientNetV2-B0 ─► Class probabilities
(JPEG/PNG,  (format,    (RGB, 160×160,   (TensorFlow/Keras)      │
 ≤ 10 MB)    size,       raw 0–255)                              ▼
             decodes)                          Predicted class + confidence
                                                         │
                          ┌──────────────────────────────┼─────────────────────┐
                          ▼                              ▼                     ▼
                    Risk level                     Grad-CAM heatmap      Saved as "Pending"
              (class + confidence)              (on demand, not stored)  (image + record)
                                                                               │
                                                  Admin reviews ──► Approved ──► public history
                                                                ├─► Flagged  (hidden)
                                                                └─► Removed  (image + record deleted)
```

1. The upload is validated (type, size, decodability) and previewed.
2. The model outputs a probability per class; the highest is the prediction and its probability is the confidence.
3. The risk level is derived from the predicted class and confidence.
4. The result is shown immediately, then saved as **Pending**. A failure to save never blocks the result.
5. An administrator approves, flags, or removes the submission. Only **Approved** items appear in the public history.

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web UI | Streamlit (frontend and backend in one app) |
| Model | TensorFlow / Keras, EfficientNetV2-B0 (ImageNet transfer learning) |
| Explainability | Grad-CAM (NumPy, Pillow, Matplotlib colour map) |
| Database | Supabase PostgreSQL (deployment), SQLite (local development) |
| Database access | SQLAlchemy 2.x |
| Image storage | Supabase Storage, private bucket (deployment); local folder (development) |
| Authentication | bcrypt hashes, custom `admin_user` table |
| Hosting | Streamlit Community Cloud |
| Testing | pytest and end-to-end smoke-test scripts |

---

## Project structure

```
fire-watch/
├── app.py                  # Streamlit entry point and page routing
├── firewatch/
│   ├── config.py           # Class names, thresholds, limits, risk messages
│   ├── auth/               # bcrypt login, lockout
│   ├── db/                 # SQLAlchemy models, sessions, image storage
│   ├── inference/          # Preprocessing, classifier, predictor, risk rules, Grad-CAM, mock model
│   ├── services/           # Business logic: submissions, moderation, analytics
│   └── ui/                 # Streamlit pages and shared components
├── models/                 # Trained .keras model
├── scripts/                # Admin creation and smoke tests
├── tests/                  # pytest tests
├── training/               # Training notebook and experiments
├── requirements.txt        # Runtime dependencies
└── requirements-train.txt  # Training and development extras
```

The architecture is layered with imports flowing one way: `ui → services → db / auth / inference`. The UI never accesses the database or Keras directly.

---

## Getting started

**Prerequisites:** Python 3.12, Git, and optionally a [Supabase](https://supabase.com) project.

```bash
git clone https://github.com/rachkb/fire-watch.git
cd fire-watch
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.create_admin     # no self-registration; creates the first admin
python -m streamlit run app.py     # opens at http://localhost:8501
```

**Configuration.** Without any secrets file the app runs fully locally, using SQLite (`data/firewatch.db`) and a local image folder (`data/uploads/`). To use Supabase, provide the following in `.streamlit/secrets.toml` (git-ignored):

```toml
DATABASE_URL = "postgresql://postgres.<project-ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres"
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_SERVICE_KEY = "sb_secret_..."
# SUPABASE_BUCKET = "submissions"   # optional default
```

**Supabase notes:** create a private storage bucket named `submissions`; use the Session pooler connection string (the direct host is IPv6-only on the free tier). Tables are created automatically on first run. Later column changes require a manual `ALTER TABLE`, since `create_all` does not modify existing tables.

**Mock mode:** set `USE_MOCK_MODEL = True` in `firewatch/config.py` to run the interface with a fake model and no TensorFlow.

---

## Risk levels

Risk is derived from the predicted class and confidence by a single function, `get_risk_level()` in `firewatch/inference/risk.py`. Thresholds live in `config.py`.

| Predicted class | Confidence | Risk level | Message |
|---|---|---|---|
| Fire | ≥ 80% | **High** | Escalate to the proper authorities if this reflects a real scene. |
| Fire | 60% to < 80% | **Medium** | Possible fire detected. Manual verification recommended. |
| Smoke | ≥ 80% | **Medium** | Smoke detected. Verify the scene and monitor. |
| Smoke | 60% to < 80% | **Low** | Possible smoke. Manual verification recommended. |
| Non-Fire | ≥ 60% | **None** | No visible fire or smoke detected. |
| Any | < 60% | **Uncertain** | Low confidence. Manual review recommended. |

Lower bounds are inclusive. The *Uncertain* check runs first, so a low-confidence result is never shown as a firm verdict.

---

## The model

| | |
|---|---|
| Architecture | EfficientNetV2-B0 (ImageNet-pretrained, frozen backbone) → Global Average Pooling → Dropout 0.3 → Dense 64 (ReLU) → Dense 3 (softmax) |
| Input | RGB, 160 × 160, raw pixel values 0–255 (rescaled internally) |
| Output order | `["Smoke", "Fire", "Non-Fire"]` (matches training folder order) |
| Parameters | about 6.0 million |
| File | `models/firewatch_effnet_phase2_BETTER.keras` (Keras 3 format, about 25 MB) |
| Dataset | [Forest Fire, Smoke and Non-Fire Image Dataset](https://www.kaggle.com/datasets/amerzishminha/forest-fire-smoke-and-non-fire-image-dataset) (Kaggle) |
| Training | Google Colab; notebook in `training/` |

**Test-set results** (10,500 held-out images, 3,500 per class):

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Smoke | 0.99 | 0.98 | 0.98 |
| Fire | 0.98 | 0.99 | 0.98 |
| Non-Fire | 0.99 | 0.99 | 0.99 |
| **Overall accuracy** | | | **98.6%** |

These figures come from the same dataset used for training; real-world photos can score noticeably lower (see [Known limitations](#known-limitations)).

**Grad-CAM.** The heatmap uses gradients of the pre-softmax score with respect to the last convolutional feature map (5 × 5), stretched over the image. It is generated on demand and never stored. Because the grid is coarse, it shows broad regions rather than sharp outlines, and it indicates where the model looked, not whether the prediction is correct.

**Performance.** Classification takes well under a second on a CPU and the heatmap about a second, within the 5-second requirement. The model is loaded once and cached.

---

## Configuration

Shared constants are in `firewatch/config.py`.

| Setting | Default | Purpose |
|---|---|---|
| `INPUT_SIZE` | `(160, 160)` | Model input size |
| `LOW_CONFIDENCE_THRESHOLD` | `0.60` | Below this, the result is *Uncertain* |
| `HIGH_CONFIDENCE_THRESHOLD` | `0.80` | Fire becomes *High*; Smoke becomes *Medium* |
| `MAX_UPLOAD_SIZE_MB` | `10` | Upload size limit |
| `ALLOWED_UPLOAD_FORMATS` | `jpg, jpeg, png` | Accepted formats |
| `HISTORY_PAGE_SIZE` | `4` | Rows per history page |
| `MAX_FAILED_LOGINS` / `LOCKOUT_MINUTES` | `5` / `15` | Login lockout policy |
| `SESSION_TIMEOUT_MINUTES` | `30` | Admin inactivity timeout |

---

## Database schema

| Table | Purpose | Key columns |
|---|---|---|
| `admin_user` | Administrator accounts | `username`, `password_hash`, `failed_attempts`, `locked_until` |
| `submission` | Each classified upload | `image_path`, `predicted_class`, `confidence_score`, class probabilities, `risk_level`, `status` (`Pending` / `Approved` / `Flagged`), `flag_reason`, `correct_class`, `reviewed_by`, `reviewed_at` |
| `note` | Administrator notes | `submission_id`, `admin_id`, `note_text`, `created_at` (deleted with the submission) |
| `moderation_action` | Audit trail of approve / flag / remove | `submission_id` (intentionally not a foreign key, so it survives removal), `admin_id`, `action`, `created_at` |

Allowed values for classes, risk levels, statuses, and flag reasons are enforced with database `CHECK` constraints generated from `config.py`.

---

## Testing

```bash
python -m pip install pytest
python -m pytest tests -v
```

| Test file | Coverage |
|---|---|
| `tests/test_risk.py` | Risk rules at the 59%, 60%, 79%, and 80% boundaries |
| `tests/test_inference.py` | Class order, preprocessing, `classify()` contract, RGBA/grayscale inputs, heatmaps (auto-skipped if TensorFlow or the model is missing) |

End-to-end smoke tests run against the configured database and clean up after themselves:

```bash
python -m scripts.db_smoke_test         # database and storage round trip
python -m scripts.services_smoke_test   # upload, approve, flag, remove, analytics
python -m scripts.auth_smoke_test       # login, wrong password, lockout, reset
```

---

## Deployment

The app is deployed on [Streamlit Community Cloud](https://streamlit.io/cloud) from the `main` branch (`app.py`, Python 3.12), with Supabase secrets supplied through the platform's secrets manager. Pushes to `main` redeploy automatically. Submissions, images, and admin accounts persist in Supabase across redeploys. The free tiers of both services sleep or pause when idle.

---

## Security notes

- Passwords are stored only as salted bcrypt hashes. Login failures return a single generic message, and a username is blocked for 15 minutes after 5 consecutive failures.
- The image bucket is private; images are fetched server-side and no public URLs are exposed.
- Uploads are validated by decoding, not just by file name, and files over 10 MB are rejected.
- Credentials live only in `secrets.toml` or the host's secrets manager.
- Admin pages check the session on every load; sessions expire after 30 minutes of inactivity.
- Removing a submission permanently deletes its image and record, leaving only an audit entry.
- The app is public and uploads stay hidden until approved, but **there is no rate limiting**.

---

## Known limitations

- **Real-world generalisation.** Accuracy was measured on the dataset's own test split. Fog, mist, and haze can be mistaken for smoke or fire (a misty forest photo scored 51% *Fire* and was correctly labelled *Uncertain*). Sunsets and orange foliage are likely weak spots as well.
- **Scope.** Version 1.0 targets still images of visible flames and smoke in outdoor and forest scenes, in daylight, at moderate distance. There is no live camera or video support.
- **Coarse heatmaps.** The 5 × 5 Grad-CAM grid shows regions, not outlines; for a perfectly uniform image the app reports "Heatmap unavailable".
- **Uncalibrated confidence.** The 60% and 80% thresholds are reasonable defaults, not measured probabilities, and may need tuning on real data.
- **No alerts.** FireWatch never sends emails, SMS messages, or alarms, by design.
- **Admin notes are write-only.** They are saved but not yet displayed in the interface.
- **Analytics are not accuracy metrics.** False-negative and false-positive counts reflect only administrator-reviewed submissions.

---

## Authors and acknowledgments

**Authors:** Rach Kolly R. Bongo and Kylle Valerie D. Tanchico
Bachelor of Science in Computer Science, College of Computer Studies, Silliman University (2026).

Developed as a Software Requirements Specification (SRS) and Software Design Description (SDD) project; both documents accompany this repository.

**Built with:** Streamlit, TensorFlow / Keras, Supabase, SQLAlchemy, bcrypt, Pillow, Matplotlib.

**References**
- M. Tan and Q. V. Le, "EfficientNetV2: Smaller Models and Faster Training," ICML 2021. arXiv:2104.00298.
- R. R. Selvaraju et al., "Grad-CAM: Visual Explanations from Deep Networks via Gradient-Based Localization," ICCV 2017. arXiv:1610.02391.
- A. Minha, "Forest Fire, Smoke and Non-Fire Image Dataset," Kaggle.

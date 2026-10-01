# FireWatch

**AI-assisted fire and smoke detection for still images.**
Upload a photo and FireWatch classifies it as **Fire**, **Smoke**, or **Non-Fire**, reports a confidence score and a risk level, and shows a Grad-CAM heatmap of the regions that influenced the result. Administrators review every submission before it appears in the public history.

> **FireWatch is a decision-support tool only.** It is an academic prototype, not a certified fire alarm or emergency detection service. It never sends alerts and must not replace smoke detectors, alarms, or official emergency services.

**Live demo:** https://fire-watch-softeng2.streamlit.app *(the free tier sleeps when idle; the first load can take a minute)*

---

## Table of contents

1. [Features](#features)
2. [How it works](#how-it-works)
3. [Tech stack](#tech-stack)
4. [Project structure](#project-structure)
5. [Getting started](#getting-started)
6. [Supabase setup](#supabase-setup)
7. [Using the app](#using-the-app)
8. [Risk levels](#risk-levels)
9. [The model](#the-model)
10. [Configuration](#configuration)
11. [Database schema](#database-schema)
12. [Testing](#testing)
13. [Deployment](#deployment)
14. [Security notes](#security-notes)
15. [Known limitations](#known-limitations)
16. [Authors and acknowledgments](#authors-and-acknowledgments)

---

## Features

**General users (no login required)**
- Upload a JPEG or PNG image (up to 10 MB) and see a preview.
- View the predicted class, the confidence score, and the probability of all three classes.
- See a colour-coded **risk level** with guidance on whether to escalate.
- Toggle a **Grad-CAM heatmap** showing which parts of the image drove the prediction.
- Browse a read-only, filterable, paginated **submission history** (approved submissions only).
- Low-confidence results (under 60%) are labelled **Uncertain** with a manual-review recommendation.

**Administrators (login required)**
- Log in with a username and password (bcrypt-hashed; temporary lockout after repeated failures).
- **Review and filter** all submissions by risk level, class, status, and date.
- **Approve**, **flag** (with a reason, an optional correct class, and an optional note), or **permanently remove** submissions.
- View **analytics**: totals, counts per class, risk level, and status, plus administrator-reported false negatives and false positives.

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

1. A visitor uploads an image. It is validated (type, size, decodable) and shown as a preview.
2. The model returns a probability for each class. The highest is the prediction, and its probability is the confidence score.
3. The risk level is derived from the predicted class and confidence (see [Risk levels](#risk-levels)).
4. The result is displayed immediately. The image and result are then saved with status **Pending**; a failure to save never blocks the result.
5. An administrator approves, flags, or removes the submission. Only **Approved** submissions appear in the public history.

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web UI | [Streamlit](https://streamlit.io) (frontend and backend in one app) |
| Model | TensorFlow / Keras, EfficientNetV2-B0 (ImageNet transfer learning) |
| Explainability | Grad-CAM (NumPy, Pillow, Matplotlib colour map) |
| Database | Supabase PostgreSQL in deployment, SQLite for local development |
| Database access | SQLAlchemy 2.x |
| Image storage | Supabase Storage (private bucket) in deployment, local folder for development |
| Authentication | bcrypt password hashes, custom `admin_user` table |
| Hosting | Streamlit Community Cloud |
| Testing | pytest, plus end-to-end smoke-test scripts |

---

## Project structure

```
fire-watch/
├── app.py                       # Streamlit entry point and page routing
├── firewatch/
│   ├── config.py                # Class names, thresholds, limits, risk messages
│   ├── auth/
│   │   └── service.py           # bcrypt login, lockout after repeated failures
│   ├── db/
│   │   ├── models.py            # SQLAlchemy tables
│   │   ├── session.py           # Engine/session; Supabase or SQLite fallback
│   │   └── storage.py           # Image storage (Supabase bucket or local folder)
│   ├── inference/
│   │   ├── __init__.py          # Single entry point used by the UI (lazy imports)
│   │   ├── preprocess.py        # RGB conversion, EXIF rotation, 160×160 resize
│   │   ├── classifier.py        # Loads the model once, validates its shape
│   │   ├── predictor.py         # classify(): class, confidence, probabilities, risk
│   │   ├── risk.py              # get_risk_level(): the single home of the risk rules
│   │   ├── gradcam.py           # Raw Grad-CAM computation
│   │   ├── heatmap.py           # Overlay image for the UI
│   │   └── mock.py              # Fake model so the UI can run without TensorFlow
│   ├── services/                # Business logic between the UI and the database
│   │   ├── submission_service.py
│   │   ├── moderation_service.py
│   │   ├── analytics_service.py
│   │   └── rows.py
│   └── ui/                      # Streamlit pages and shared components
│       ├── home_page.py         # History (left) + upload (right)
│       ├── upload_page.py
│       ├── history_page.py
│       ├── admin_login_page.py
│       ├── admin_moderation_page.py
│       ├── admin_analytics_page.py
│       ├── components.py        # Header, risk banner, result popup, admin guard
│       └── data_access.py       # Thin adapter from the UI to the services
├── models/                      # Trained .keras model file
├── scripts/                     # create_admin and smoke tests
├── tests/                       # pytest tests
├── training/                    # Model training notebook and experiments
├── requirements.txt             # Runtime dependencies (used by deployment)
└── requirements-train.txt       # Training and development extras
```

Imports flow in one direction: `ui → services → db / auth / inference`. The UI never touches the database or Keras directly.

---

## Getting started

### Prerequisites

- **Python 3.12.** TensorFlow does not publish stable builds for Python 3.14, and the hosting platform runs Linux, so 3.12 is the safe choice on both.
- Git.
- A [Supabase](https://supabase.com) project (optional for local development; see below).

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/rachkb/fire-watch.git
cd fire-watch
```

Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

TensorFlow is large, so this takes a few minutes. Always use `python -m pip` so packages go into the active environment.

### 3. Configure secrets (optional)

Create `.streamlit/secrets.toml`. **This file must never be committed** (it is listed in `.gitignore`).

```toml
DATABASE_URL = "postgresql://postgres.<project-ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres"
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_SERVICE_KEY = "sb_secret_..."
# SUPABASE_BUCKET = "submissions"   # optional; this is the default
```

**Without this file** the app runs fully locally: it falls back to a SQLite database at `data/firewatch.db` and stores images in `data/uploads/`. That is convenient for development, but the data is local and temporary.

### 4. Create an administrator

There is no self-registration. Create the first administrator from the command line:

```bash
python -m scripts.create_admin
```

You will be asked for a username and a password (at least 8 characters).

### 5. Run the app

```bash
python -m streamlit run app.py
```

Open http://localhost:8501.

> **Model file:** the app expects the trained model at the path set by `MODEL_PATH` in `firewatch/config.py` (currently `models/firewatch_effnet_phase2_BETTER.keras`). Set `USE_MOCK_MODEL = True` in the same file to run the interface with a fake random model and no TensorFlow.

---

## Supabase setup

1. **Create a project.** Save the database password somewhere safe.
2. **Create a storage bucket** named `submissions` and keep it **private** (leave "Public bucket" off).
3. **Get the connection string:** click **Connect** and choose the **Session pooler** string. Use the pooler (not the direct `db.<ref>.supabase.co` host), because the direct connection is IPv6-only on the free tier and some hosts cannot reach it. Replace the password placeholder with your password, and do not keep the square brackets.
4. **Get the keys:** Project Settings > API Keys. Use the **secret key** (`sb_secret_...`) as `SUPABASE_SERVICE_KEY`. It bypasses access rules, so keep it server-side only and rotate it if it ever leaks.
5. **Tables are created automatically** on first run (`create_all`). Row Level Security can stay enabled with no policies: the app connects directly to Postgres, which bypasses RLS, while the public API key is left unable to read anything.

If you change a table's columns later, `create_all` will not alter existing tables. Use Supabase's SQL editor to run an `ALTER TABLE`.

---

## Using the app

### As a general user

1. On the home page, choose an image under **Upload image**, then click **Analyze Image**.
2. A popup shows the class, the three probabilities, the risk banner, and the heatmap toggle.
3. Browse **Submission history** on the left. Filter by risk level or class, page through results, and click **Details** on any row.

New uploads stay hidden from the history until an administrator approves them.

### As an administrator

1. Click **Admin Login** in the header and sign in.
2. **Moderation:** filter submissions, then **Approve**, **Flag**, or **Remove**.
   - **Flag** opens a popup: choose a reason (*Misclassified*, *Inappropriate content*, *Other*), optionally the correct class, and optionally a note.
   - **Remove** asks for confirmation, then permanently deletes the image and the record.
3. **Analytics:** totals, charts by class and risk level, and administrator-reported false negatives and false positives. These counters only reflect submissions an administrator has reviewed; they are **not** a measure of overall model accuracy.
4. Sessions end after 30 minutes of inactivity or when you click **Log out**.

Notes entered when flagging are stored in the `note` table (viewable in Supabase). The interface does not display them yet.

---

## Risk levels

The risk level is derived from the predicted class and confidence. The rules live in one function, `get_risk_level()` in `firewatch/inference/risk.py`, and the thresholds in `firewatch/config.py`.

| Predicted class | Confidence | Risk level | Message |
|---|---|---|---|
| Fire | ≥ 80% | **High** | Escalate to the proper authorities if this reflects a real scene. |
| Fire | 60% to < 80% | **Medium** | Possible fire detected. Manual verification recommended. |
| Smoke | ≥ 80% | **Medium** | Smoke detected. Verify the scene and monitor. |
| Smoke | 60% to < 80% | **Low** | Possible smoke. Manual verification recommended. |
| Non-Fire | ≥ 60% | **None** | No visible fire or smoke detected. |
| Any | < 60% | **Uncertain** | Low confidence. Manual review recommended. |

Boundaries are inclusive at the lower bound (exactly 80% counts as ≥ 80%). The *Uncertain* check runs first, so a low-confidence result is never shown as a firm verdict.

---

## The model

| | |
|---|---|
| Architecture | EfficientNetV2-B0 (ImageNet-pretrained, frozen backbone) → Global Average Pooling → Dropout 0.3 → Dense 64 (ReLU) → Dense 3 (softmax) |
| Input | RGB, **160 × 160**, raw pixel values 0–255 (the network rescales internally; do **not** divide by 255) |
| Output order | `["Smoke", "Fire", "Non-Fire"]` (the training folder order; `CLASS_NAMES` in `config.py` must match it) |
| Parameters | about 6.0 million |
| File | `models/firewatch_effnet_phase2_BETTER.keras` (Keras 3 format) |
| Dataset | [Forest Fire, Smoke and Non-Fire Image Dataset](https://www.kaggle.com/datasets/amerzishminha/forest-fire-smoke-and-non-fire-image-dataset) (Kaggle) |
| Training | Google Colab; notebook in `training/` |

### Test-set results

Evaluated on 10,500 held-out images (3,500 per class):

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Smoke | 0.99 | 0.98 | 0.98 |
| Fire | 0.98 | 0.99 | 0.98 |
| Non-Fire | 0.99 | 0.99 | 0.99 |
| **Overall accuracy** | | | **98.6%** |

These figures come from the same dataset the model was trained on. **Real-world photos can score noticeably lower**; see [Known limitations](#known-limitations).

### Grad-CAM heatmap

The heatmap is computed from the model's last convolutional feature map (a 5 × 5 grid) using gradients of the pre-softmax score, then stretched over the image. It is generated on demand and never stored. Because the grid is coarse, expect broad, soft regions rather than sharp outlines. It shows where the model looked, not proof that the prediction is correct.

### Performance

Classification takes well under a second on a CPU, and the heatmap about a second, comfortably within the 5-second requirement. The model is loaded once at startup and cached.

---

## Configuration

All shared constants live in `firewatch/config.py`.

| Setting | Default | Purpose |
|---|---|---|
| `CLASS_NAMES` | `["Smoke", "Fire", "Non-Fire"]` | Model output order |
| `INPUT_SIZE` | `(160, 160)` | Model input size |
| `MODEL_PATH` | `models/firewatch_effnet_phase2_BETTER.keras` | Model file |
| `USE_MOCK_MODEL` | `False` | `True` runs the UI with a fake model (no TensorFlow needed) |
| `LOW_CONFIDENCE_THRESHOLD` | `0.60` | Below this the result is *Uncertain* |
| `HIGH_CONFIDENCE_THRESHOLD` | `0.80` | Above this Fire becomes *High* and Smoke becomes *Medium* |
| `MAX_UPLOAD_SIZE_MB` | `10` | Upload size limit |
| `ALLOWED_UPLOAD_FORMATS` | `jpg, jpeg, png` | Accepted formats |
| `HISTORY_PAGE_SIZE` | `4` | Rows per page in the history |
| `MAX_FAILED_LOGINS` | `5` | Failed logins before a temporary block |
| `LOCKOUT_MINUTES` | `15` | Length of that block |
| `SESSION_TIMEOUT_MINUTES` | `30` | Admin inactivity timeout |

---

## Database schema

| Table | Purpose | Key columns |
|---|---|---|
| `admin_user` | Administrator accounts | `username`, `password_hash` (bcrypt), `failed_attempts`, `locked_until` |
| `submission` | Each classified upload | `image_path`, `predicted_class`, `confidence_score`, `prob_fire`, `prob_smoke`, `prob_non_fire`, `risk_level`, `status` (`Pending` / `Approved` / `Flagged`), `flag_reason`, `correct_class`, `reviewed_by`, `reviewed_at` |
| `note` | Administrator notes on a submission | `submission_id`, `admin_id`, `note_text`, `created_at` (deleted with the submission) |
| `moderation_action` | Audit trail of approve / flag / remove | `submission_id` (deliberately not a foreign key, so it survives removal), `admin_id`, `action`, `created_at` |

Allowed values for classes, risk levels, statuses, and flag reasons are enforced with database `CHECK` constraints generated from `config.py`.

---

## Testing

Install pytest (it is a development tool and is not part of `requirements.txt`):

```bash
python -m pip install pytest
python -m pytest tests -v
```

| Test file | What it checks |
|---|---|
| `tests/test_risk.py` | Risk-level rules at the 59%, 60%, 79%, and 80% boundaries |
| `tests/test_inference.py` | Class order, preprocessing, the `classify()` contract, RGBA/grayscale inputs, and heatmaps (skipped automatically if TensorFlow or the model file is missing) |

### Smoke tests

End-to-end checks that run against **whichever database your secrets point to** and clean up after themselves:

```bash
python -m scripts.db_smoke_test         # database + storage round trip
python -m scripts.services_smoke_test   # upload, approve, flag, remove, analytics
python -m scripts.auth_smoke_test       # login, wrong password, lockout, reset
```

If `.streamlit/secrets.toml` is present, they use your real Supabase project; remove it (or run elsewhere) to test against local SQLite.

---

## Deployment

The app is designed for [Streamlit Community Cloud](https://streamlit.io/cloud).

1. Push the code to GitHub and make sure the **model file is committed** (it is about 25 MB).
2. On Streamlit Community Cloud, choose **Create app**, select the repository, the `main` branch, and `app.py`.
3. Under **Advanced settings**, select **Python 3.12** and paste your secrets (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) in TOML format.
4. Deploy. The first build takes several minutes because of TensorFlow.

After deployment, pushing to `main` redeploys automatically. Changing secrets restarts the app. Submissions, images, and admin accounts live in Supabase, so redeploys do not erase them (administrators are logged out).

**Checklist after the first deploy:**
- Upload a photo and confirm a row appears in Supabase's `submission` table and an image appears in the `submissions` bucket. (If the secrets are wrong, the app silently falls back to temporary local storage.)
- Log in, approve the submission, and confirm it appears in the public history.
- Check **Manage app > logs** for errors.

Free-tier notes: Streamlit apps sleep when idle, and free Supabase projects can pause after a period of inactivity. Wake both before a demo.

---

## Security notes

- Admin passwords are stored only as salted bcrypt hashes. Login failures return one generic message, and a username is blocked for 15 minutes after 5 consecutive failures.
- The image bucket is **private**. Images are fetched server-side; no public URLs are exposed.
- Uploads are validated by decoding them, not just by file name, and files over 10 MB are rejected.
- The Supabase secret key and database password live only in `secrets.toml` or the host's secrets manager. Never commit them, paste them in chats, or put them in screenshots. If one leaks, rotate it.
- Admin pages check the session on every load, and administrator sessions expire after 30 minutes of inactivity.
- Removing a submission permanently deletes its image and record. Only an audit entry (who, what, when) remains.
- The app is public: anyone with the link can upload an image. Uploads stay hidden until approved, but there is no rate limiting.

---

## Known limitations

- **Real-world generalisation.** Accuracy was measured on the dataset's own test split. On real photos the model can be less certain, and **fog, mist, and haze can be mistaken for smoke or fire** (a misty forest photo scored 51% *Fire* and was correctly flagged *Uncertain*). Other visually similar scenes, such as sunsets and orange foliage, are likely weak spots too.
- **Scope.** Version 1.0 targets still images of visible flames and smoke in outdoor and forest scenes, in daylight, at moderate distance. Other conditions are not prioritised. There is no live camera or video support.
- **Coarse heatmaps.** The Grad-CAM map is 5 × 5 before stretching, so it shows regions, not outlines. For a perfectly uniform image there is no pattern to show, and the app reports "Heatmap unavailable".
- **Softmax confidence is not calibrated.** The 60% and 80% thresholds are reasonable defaults, not measured probabilities, and may need tuning on real data.
- **No alerts.** FireWatch never sends emails, SMS messages, or alarms (by design).
- **Notes are write-only.** Administrator notes are saved but not yet displayed in the interface.
- **Free-tier hosting** limits memory and sleeps when idle.

---

## Authors and acknowledgments

**Authors:** Rach Kolly R. Bongo and Kylle Valerie D. Tanchico
Bachelor of Science in Computer Science, College of Computer Studies, Silliman University (2026).

Built as a Software Requirements Specification and Software Design Description project; the SRS and SDD accompany this repository.

**Built with:** [Streamlit](https://streamlit.io), [TensorFlow / Keras](https://www.tensorflow.org), [Supabase](https://supabase.com), [SQLAlchemy](https://www.sqlalchemy.org), [bcrypt](https://github.com/pyca/bcrypt), [Pillow](https://python-pillow.org), and [Matplotlib](https://matplotlib.org).

**References**
- M. Tan and Q. V. Le, "EfficientNetV2: Smaller Models and Faster Training," ICML 2021. arXiv:2104.00298.
- R. R. Selvaraju et al., "Grad-CAM: Visual Explanations from Deep Networks via Gradient-Based Localization," ICCV 2017. arXiv:1610.02391.
- A. Minha, "Forest Fire, Smoke and Non-Fire Image Dataset," Kaggle.

---

## License

This project was created for academic purposes. Add a license file (for example MIT) before sharing or reusing it more widely; until then, all rights are reserved by the authors.

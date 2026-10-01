"""Image storage behind one interface.

Uses the private Supabase Storage bucket when SUPABASE_URL and
SUPABASE_SERVICE_KEY are set, otherwise a local folder (data/uploads) for
development. The rest of the app only calls save_image / get_image_bytes /
delete_image and stores the returned key in submission.image_path.
"""
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from firewatch.db.session import PROJECT_ROOT, get_secret

LOCAL_DIR = PROJECT_ROOT / "data" / "uploads"
_EXT = {"image/png": "png", "image/jpeg": "jpg"}


def _bucket_name() -> str:
    return get_secret("SUPABASE_BUCKET", "submissions")


@lru_cache(maxsize=1)
def _client():
    url, key = get_secret("SUPABASE_URL"), get_secret("SUPABASE_SERVICE_KEY")
    if not (url and key):
        return None
    from supabase import create_client
    return create_client(url, key)


def backend_name() -> str:
    return "supabase" if _client() else "local"


def save_image(data: bytes, content_type: str = "image/png") -> str:
    """Stores the image and returns its storage key."""
    key = f"{uuid4().hex}.{_EXT.get(content_type, 'png')}"
    client = _client()
    if client:
        client.storage.from_(_bucket_name()).upload(
            key, data, {"content-type": content_type})
    else:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        (LOCAL_DIR / key).write_bytes(data)
    return key


@lru_cache(maxsize=256)
def _fetch(key: str) -> bytes:
    # Keys are unique, immutable uuids, so caching by key is safe. This stops the
    # history list from re-downloading every thumbnail on each Streamlit rerun.
    client = _client()
    if client:
        return client.storage.from_(_bucket_name()).download(key)
    return (LOCAL_DIR / Path(key).name).read_bytes()      # .name blocks path tricks


def get_image_bytes(key: str) -> bytes:
    return _fetch(key)


def delete_image(key: str) -> None:
    """Permanently deletes the stored file (REQ-9.5, NREQ-SEC-3). Missing files are ignored."""
    client = _client()
    if client:
        client.storage.from_(_bucket_name()).remove([key])
    else:
        (LOCAL_DIR / Path(key).name).unlink(missing_ok=True)
    _fetch.cache_clear()
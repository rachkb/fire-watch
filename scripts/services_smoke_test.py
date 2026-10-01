"""Exercises the services end to end. Run: python -m scripts.services_smoke_test
Cleans up after itself."""
from io import BytesIO

from PIL import Image
from sqlalchemy import delete

from firewatch.db import storage
from firewatch.db.models import AdminUser, ModerationAction, Submission
from firewatch.db.session import backend_name, session_scope
from firewatch.services import analytics_service as an
from firewatch.services import moderation_service as mod
from firewatch.services import submission_service as sub


def png():
    b = BytesIO()
    Image.new("RGB", (40, 30), (180, 60, 30)).save(b, format="PNG")
    return b.getvalue()


def result(cls, conf, risk):
    rest = (1 - conf) / 2
    return {"predicted_class": cls, "confidence": conf, "risk_level": risk,
            "probabilities": {c: (conf if c == cls else rest) for c in ("Fire", "Smoke", "Non-Fire")}}


def main():
    print(f"Database: {backend_name()}   Storage: {storage.backend_name()}")
    with session_scope() as db:
        admin = AdminUser(username="svc_test_admin", password_hash="x")
        db.add(admin); db.flush(); aid = admin.admin_id
    before = an.analytics()
    ids = []
    try:
        ids = [sub.add_submission(png(), result("Fire", 0.9, "High")),
               sub.add_submission(png(), result("Non-Fire", 0.8, "None")),
               sub.add_submission(png(), result("Smoke", 0.7, "Low"))]
        print("Added 3 submissions (Pending): OK")

        rows, total = sub.list_approved(1, 4)
        assert all(r["id"] not in ids for r in rows), "Pending item leaked into public history"
        print("Public history hides Pending: OK")

        assert mod.approve(ids[0], aid)
        rows, total = sub.list_approved(1, 4, class_filter="Fire")
        assert ids[0] in [r["id"] for r in rows] and rows[0]["image_bytes"][:4] == b"\x89PNG"
        print("Approve -> appears in history with image: OK")

        assert mod.flag(ids[1], aid, "Misclassified", "Fire", "looks like flames")
        a = an.analytics()
        assert a["false_negatives"] == before["false_negatives"] + 1
        assert a["by_status"]["Flagged"] == before["by_status"]["Flagged"] + 1
        print("Flag + false-negative counter: OK")

        rows, _ = sub.list_approved(1, 50)
        assert ids[1] not in [r["id"] for r in rows], "Flagged item is public"
        print("Flagged stays hidden: OK")

        assert mod.list_all(status="Flagged", limit=5)
        with session_scope() as db:
            key = db.get(Submission, ids[2]).image_path
        assert mod.remove(ids[2], aid)
        try:
            storage.get_image_bytes(key); raise AssertionError("image still exists")
        except AssertionError:
            raise
        except Exception:
            pass
        with session_scope() as db:
            assert db.get(Submission, ids[2]) is None
        assert mod.remove(ids[2], aid) is False        # double click is harmless
        print("Remove deletes image + record: OK")
        print("All checks passed.")
    finally:
        with session_scope() as db:
            for i in ids:
                s = db.get(Submission, i)
                if s:
                    try: storage.delete_image(s.image_path)
                    except Exception: pass
                    db.delete(s)
            db.flush()
            db.execute(delete(ModerationAction).where(ModerationAction.admin_id == aid))
            db.delete(db.get(AdminUser, aid))


if __name__ == "__main__":
    main()
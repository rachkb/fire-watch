"""Checks the database and storage end to end.

Run from the project root:   python -m scripts.db_smoke_test
Uses Supabase if DATABASE_URL / SUPABASE_* are in .streamlit/secrets.toml,
otherwise local SQLite + data/uploads. Leaves no data behind.
"""
from io import BytesIO

from PIL import Image

from firewatch.db import session, storage
from firewatch.db.models import AdminUser, ModerationAction, Note, Submission


def main():
    print(f"Database: {session.backend_name()}   Storage: {storage.backend_name()}")

    buf = BytesIO()
    Image.new("RGB", (32, 32), (200, 60, 30)).save(buf, format="PNG")
    png = buf.getvalue()

    key = storage.save_image(png, "image/png")
    assert storage.get_image_bytes(key) == png, "storage round trip failed"
    print("Storage upload + download: OK")

    with session.session_scope() as db:
        admin = AdminUser(username="smoke_admin", password_hash="not-a-real-hash")
        sub = Submission(image_path=key, predicted_class="Fire", confidence_score=0.87,
                         prob_fire=0.87, prob_smoke=0.09, prob_non_fire=0.04,
                         risk_level="High")
        db.add_all([admin, sub])
        db.flush()
        db.add(Note(submission_id=sub.submission_id, admin_id=admin.admin_id, note_text="test"))
        db.add(ModerationAction(submission_id=sub.submission_id,
                                admin_id=admin.admin_id, action="Flag"))
        sub_id, admin_id = sub.submission_id, admin.admin_id
    print("Insert: OK")

    with session.session_scope() as db:
        got = db.get(Submission, sub_id)
        assert got.status == "Pending" and len(got.notes) == 1
        print(f"Read back: {got.predicted_class} {got.confidence_score:.0%}, "
              f"status={got.status}, notes={len(got.notes)}")

        try:                                   # constraints should reject bad values
            db.add(Submission(image_path="x", predicted_class="Banana", confidence_score=0.5,
                              prob_fire=0, prob_smoke=0, prob_non_fire=0, risk_level="High"))
            db.flush()
            raise AssertionError("bad class was accepted")
        except AssertionError:
            raise
        except Exception:
            db.rollback()
            print("Constraint check (rejects invalid class): OK")

    with session.session_scope() as db:        # clean up
        db.query(ModerationAction).filter_by(submission_id=sub_id).delete()
        db.delete(db.get(Submission, sub_id))  # notes cascade
        db.flush()
        db.delete(db.get(AdminUser, admin_id))
    storage.delete_image(key)
    print("Cleanup + delete: OK\nAll checks passed.")


if __name__ == "__main__":
    main()
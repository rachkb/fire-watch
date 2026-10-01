"""Thin adapter between the UI and the services layer.

The pages call these functions and never touch the database directly. Once
you're comfortable, pages can import firewatch.services.* directly and this
file can be deleted.
"""
from firewatch.auth.service import LoginLocked, authenticate  # noqa: F401  (re-exported)
from firewatch.services import analytics_service, moderation_service, submission_service


def add_submission(image_bytes: bytes, result: dict) -> int:
    return submission_service.add_submission(image_bytes, result)


def list_approved(page, page_size, class_filter=None, risk_filter=None):
    return submission_service.list_approved(page, page_size, class_filter, risk_filter)


def list_all(risk=None, cls=None, status=None, date_from=None, date_to=None, limit=50):
    return moderation_service.list_all(risk, cls, status, date_from, date_to, limit)


def approve(sub_id, admin_id):
    return moderation_service.approve(sub_id, admin_id)


def flag(sub_id, admin_id, reason, correct_class=None, note=""):
    return moderation_service.flag(sub_id, admin_id, reason, correct_class, note)


def remove(sub_id, admin_id):
    return moderation_service.remove(sub_id, admin_id)


def analytics() -> dict:
    return analytics_service.analytics()
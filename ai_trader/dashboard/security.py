"""Simple HTTP authentication helpers for the dashboard API."""

from __future__ import annotations

import os
from functools import wraps
from flask import request, jsonify


def require_auth(fn):
    """Protect an endpoint using optional Basic or Bearer token auth.

    Mode is defined via the ``DASHBOARD_AUTH`` environment variable which can be
    ``disabled`` (default), ``basic`` or ``token``.
    """

    mode = os.getenv("DASHBOARD_AUTH", "disabled")
    user = os.getenv("DASHBOARD_USERNAME", "admin")
    pwd = os.getenv("DASHBOARD_PASSWORD", "change_me")
    token = os.getenv("DASHBOARD_TOKEN", "")

    @wraps(fn)
    def wrapper(*a, **k):
        if mode == "disabled":
            return fn(*a, **k)
        if mode == "token":
            auth = request.headers.get("Authorization", "")
            if auth == f"Bearer {token}":
                return fn(*a, **k)
            return (
                jsonify({"ok": False, "data": None, "error": {"code": "unauthorized", "msg": "bad token"}}),
                401,
            )
        # basic auth
        auth = request.authorization
        if auth and auth.username == user and auth.password == pwd:
            return fn(*a, **k)
        return (
            jsonify({"ok": False, "data": None, "error": {"code": "unauthorized", "msg": "bad credentials"}}),
            401,
        )

    return wrapper

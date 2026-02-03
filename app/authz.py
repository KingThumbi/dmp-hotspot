from __future__ import annotations

from functools import wraps
from flask import abort
from flask_login import current_user, login_required

def roles_required(*roles: str):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if hasattr(current_user, "is_active") and not current_user.is_active:
                abort(403)
            if hasattr(current_user, "has_role") and current_user.has_role(*roles):
                return fn(*args, **kwargs)
            abort(403)
        return wrapper
    return decorator

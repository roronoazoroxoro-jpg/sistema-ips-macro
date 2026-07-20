from functools import wraps
from datetime import datetime, timedelta, timezone

from flask import abort, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash

from config import SESSION_TIMEOUT_MINUTES
from database import _utc_now, get_db


def _session_expired() -> bool:
    expires_at = session.get("expires_at")
    if not expires_at:
        return True
    now = datetime.now(timezone.utc)
    return now > datetime.fromisoformat(expires_at)


def _refresh_session():
    session["expires_at"] = (
        datetime.now(timezone.utc) + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    ).isoformat()


def authenticate(username: str, password: str, ip_origen: str | None = None) -> bool:
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username = ? AND activo = 1",
            (username.strip().lower(),),
        ).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            return False

        session.clear()
        session["user"] = {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "farmacia_id": user["farmacia_id"],
        }
        _refresh_session()
        conn.execute(
            "UPDATE usuarios SET ultimo_login_en = ? WHERE id = ?",
            (_utc_now(), user["id"]),
        )
        conn.execute(
            """
            INSERT INTO auditoria (actor, role, accion, entidad, entidad_id, detalle, ip_origen, creado_en)
            VALUES (?, ?, 'login', NULL, NULL, NULL, ?, ?)
            """,
            (user["username"], user["role"], ip_origen, _utc_now()),
        )
        return True


def logout(ip_origen: str | None = None):
    user = current_user()
    if user:
        log_event(actor=user["username"], role=user["role"], accion="logout", ip_origen=ip_origen)
    session.clear()


def current_user():
    user = session.get("user")
    if not user:
        return None
    if _session_expired():
        session.clear()
        return None
    _refresh_session()
    return user


def login_required(role: str | None = None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login", next=request.path))
            if role and user["role"] != role:
                abort(403)
            g.user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def api_login_required(role: str | None = None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return {"error": "No autenticado"}, 401
            if role and user["role"] != role:
                return {"error": "No autorizado"}, 403
            g.user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def log_event(
    actor: str,
    role: str,
    accion: str,
    entidad: str | None = None,
    entidad_id: str | None = None,
    detalle: str | None = None,
    ip_origen: str | None = None,
):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO auditoria (actor, role, accion, entidad, entidad_id, detalle, ip_origen, creado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (actor, role, accion, entidad, entidad_id, detalle, ip_origen, _utc_now()),
        )


import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from fastapi_app.app.core.config import get_settings


def hash_password(password: str) -> str:
    # PBKDF2-HMAC-SHA256 with per-user random salt.
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return "pbkdf2_sha256$210000$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(dk).decode("ascii").rstrip("="),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters_s, salt_b64, dk_b64 = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = base64.urlsafe_b64decode(salt_b64 + "==")
        expected = base64.urlsafe_b64decode(dk_b64 + "==")
    except Exception:
        return False

    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return hmac.compare_digest(dk, expected)


def _sign(data: bytes) -> str:
    key = get_settings().secret_key.encode("utf-8")
    return base64.urlsafe_b64encode(hmac.new(key, data, hashlib.sha256).digest()).decode("ascii").rstrip("=")


def create_access_token(user_id: int, expires_in_minutes: int = 60) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    payload = f"{user_id}.{int(exp.timestamp())}".encode("utf-8")
    sig = _sign(payload)
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=") + "." + sig


def decode_access_token(token: str) -> tuple[int, int]:
    try:
        payload_b64, sig = token.split(".", 1)
        payload = base64.urlsafe_b64decode(payload_b64 + "==")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not hmac.compare_digest(_sign(payload), sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_id_s, exp_s = payload.decode("utf-8").split(".", 1)
        user_id = int(user_id_s)
        exp = int(exp_s)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    now = int(datetime.now(timezone.utc).timestamp())
    if now > exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    return user_id, exp


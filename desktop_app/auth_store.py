import hashlib
import json
import secrets
from pathlib import Path

from desktop_app.paths import APP_LOCAL_DIR

USERS_FILE = APP_LOCAL_DIR / "users.json"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def _hash_password(password: str, salt_hex: str) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        120_000,
        dklen=32,
    )
    return dk.hex()


def _ensure_store():
    APP_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    if USERS_FILE.is_file():
        return
    salt = secrets.token_hex(16)
    users = {
        DEFAULT_USERNAME: {
            "salt": salt,
            "hash": _hash_password(DEFAULT_PASSWORD, salt),
            "display": "管理员",
        }
    }
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def verify_login(username: str, password: str) -> tuple[bool, str]:
    _ensure_store()
    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False, "用户数据损坏，请删除 .local_data 后重试。"
    user = data.get(username.strip())
    if not user:
        return False, "用户名或密码错误。"
    try:
        ok = secrets.compare_digest(
            user["hash"],
            _hash_password(password, user["salt"]),
        )
    except Exception:
        return False, "用户名或密码错误。"
    if not ok:
        return False, "用户名或密码错误。"
    return True, ""

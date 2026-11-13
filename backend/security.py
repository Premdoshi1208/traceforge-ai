import hashlib
import hmac
import re
import secrets
from typing import Any

from backend.config import settings

_session_key = settings.session_secret.get_secret_value() or secrets.token_urlsafe(48)
_sensitive_values = [s.get_secret_value() for s in (
    settings.groq_api_key, settings.admin_token, settings.github_token,
    settings.session_secret, settings.database_url
) if s.get_secret_value() and len(s.get_secret_value()) > 10]


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: "[REDACTED]" if re.search(r"api.?key|authorization|password|secret|access_token", k, re.I)
                else redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        for secret in _sensitive_values:
            value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"\b(?:gsk_|ghp_|github_pat_|gho_)[A-Za-z0-9_]+", "[REDACTED]", value)
        return re.sub(r"postgres(?:ql)?(?:\+psycopg)?://[^\s\"']+", "[REDACTED_DATABASE_URL]", value)
    return value


def actor_hash(client_address: str) -> str:
    return hmac.new(_session_key.encode(), client_address.encode(), hashlib.sha256).hexdigest()


def admin_authorized(token: str | None) -> bool:
    expected = settings.admin_token.get_secret_value()
    return bool(expected and token and hmac.compare_digest(expected, token))

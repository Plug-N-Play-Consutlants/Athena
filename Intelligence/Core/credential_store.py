"""Persistent local credential store for Athena.

Credentials are runtime state, not source code.  They should survive patch ZIP
application and repository cleanup.  By default Athena stores local secrets in
``~/.athena/secrets.local.json`` and migrates any existing
``Configuration/secrets.local.json`` values into that external store.

The store never exposes secret values through status APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from http.cookies import SimpleCookie
import os
from pathlib import Path
from typing import Any, Dict

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import CONFIGURATION_DIR

REPO_SECRETS_FILE = CONFIGURATION_DIR / "secrets.local.json"
ENV_SECRETS_FILE = "ATHENA_SECRETS_FILE"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def persistent_secrets_file() -> Path:
    configured = os.getenv(ENV_SECRETS_FILE, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".athena" / "secrets.local.json"


def _read_json(path: Path) -> Dict[str, Any]:
    payload = read_optional_json(path)
    return payload if isinstance(payload, dict) else {}


def _deep_merge_preserve(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_preserve(dict(merged[key]), value)
        elif key not in merged or merged.get(key) in (None, "", {}, []):
            merged[key] = value
    return merged


def migrate_repo_secrets_if_needed() -> Dict[str, Any]:
    """Copy repo-local secrets into the persistent store without deleting them."""
    external_path = persistent_secrets_file()
    external = _read_json(external_path)
    repo_local = _read_json(REPO_SECRETS_FILE)
    if repo_local:
        external = _deep_merge_preserve(external, repo_local)
        write_json(external_path, external)
    return external


def load_persistent_secrets() -> Dict[str, Any]:
    migrate_repo_secrets_if_needed()
    return _read_json(persistent_secrets_file())


def save_persistent_secrets(payload: Dict[str, Any]) -> Dict[str, Any]:
    safe_payload = payload if isinstance(payload, dict) else {}
    write_json(persistent_secrets_file(), safe_payload)
    return safe_payload


def parse_cookie_header(value: str) -> Dict[str, str]:
    cleaned = str(value or "").strip()
    if not cleaned:
        return {}
    parsed = SimpleCookie()
    try:
        parsed.load(cleaned)
    except Exception:
        return {}
    return {key: morsel.value for key, morsel in parsed.items() if key and morsel.value}


def classify_auth_value(value: str) -> Dict[str, Any]:
    cleaned = str(value or "").strip().replace("\n", " ").replace("\r", " ")
    cookies = parse_cookie_header(cleaned)
    looks_cookie = bool(cookies) and (";" in cleaned or "=" in cleaned)
    looks_league_secret = bool(cleaned) and not looks_cookie and len(cleaned) >= 8 and " " not in cleaned and ";" not in cleaned
    fmt = "missing"
    if looks_cookie:
        fmt = "browser_cookie_header"
    elif looks_league_secret:
        fmt = "opaque_value"
    elif cleaned:
        fmt = "unrecognized"
    return {
        "present": bool(cleaned),
        "parseable_cookie": bool(cookies),
        "cookie_count": len(cookies),
        "format": fmt,
        "looks_like_cookie_header": looks_cookie,
        "looks_like_league_secret": looks_league_secret,
    }


def save_fantrax_credentials(*, league_secret: str = "", cookie_header: str = "", force_cookie_overwrite: bool = False) -> Dict[str, Any]:
    """Persist Fantrax credentials safely.

    League secret/private token and browser Cookie header are intentionally
    separate.  Opaque values never overwrite a valid saved browser Cookie.
    """
    payload = load_persistent_secrets()
    fantrax = payload.get("fantrax") if isinstance(payload.get("fantrax"), dict) else {}

    cleaned_secret = str(league_secret or "").strip()
    if cleaned_secret:
        fantrax["league_secret"] = cleaned_secret
        fantrax["league_secret_saved_at"] = utc_now_iso()

    cleaned_cookie = str(cookie_header or "").strip().replace("\n", " ").replace("\r", " ")
    supplied = classify_auth_value(cleaned_cookie)
    existing = classify_auth_value(str(fantrax.get("cookie") or fantrax.get("auth_cookie") or ""))
    if cleaned_cookie:
        fantrax["last_supplied_auth_format"] = supplied["format"]
        if supplied["parseable_cookie"]:
            if force_cookie_overwrite or not existing["parseable_cookie"] or cleaned_cookie != fantrax.get("cookie"):
                fantrax["cookie"] = cleaned_cookie
                fantrax["cookie_saved_at"] = utc_now_iso()
            fantrax.pop("last_rejected_auth_reason", None)
        else:
            fantrax["last_rejected_auth_format"] = supplied["format"]
            fantrax["last_rejected_auth_reason"] = (
                "The supplied Fantrax auth value was not a parseable browser Cookie header. "
                "It was not saved as browser-session auth."
            )

    payload["fantrax"] = fantrax
    save_persistent_secrets(payload)
    return credential_status()


def credential_status() -> Dict[str, Any]:
    migrate_repo_secrets_if_needed()
    path = persistent_secrets_file()
    payload = _read_json(path)
    fantrax = payload.get("fantrax") if isinstance(payload.get("fantrax"), dict) else {}
    cookie_value = str(fantrax.get("cookie") or fantrax.get("auth_cookie") or "")
    cookie = classify_auth_value(cookie_value)
    league_secret = str(fantrax.get("league_secret") or fantrax.get("secret") or "").strip()
    return {
        "secrets_file_exists": path.exists(),
        "secrets_file": str(path),
        "repo_secrets_file": str(REPO_SECRETS_FILE),
        "persistent_external_store": True,
        "fantrax_cookie_present": bool(cookie_value.strip()),
        "fantrax_cookie_parseable": bool(cookie["parseable_cookie"]),
        "fantrax_cookie_count": int(cookie["cookie_count"]),
        "fantrax_secret_format": cookie["format"],
        "fantrax_cookie_saved_at": fantrax.get("cookie_saved_at"),
        "fantrax_league_secret_present": bool(league_secret),
        "fantrax_league_secret_format": "opaque_value" if league_secret else "missing",
        "fantrax_league_secret_saved_at": fantrax.get("league_secret_saved_at"),
        "last_rejected_secret_format": fantrax.get("last_rejected_auth_format"),
        "last_rejected_secret_reason": fantrax.get("last_rejected_auth_reason"),
    }

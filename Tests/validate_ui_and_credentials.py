"""Athena stabilization validation: Scout prompt and credential persistence."""
from __future__ import annotations

from pathlib import Path
import importlib
import os
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def validate_scout_question_placeholder():
    app_path = PROJECT_ROOT / "Scout" / "app.py"
    text = app_path.read_text(encoding="utf-8")

    assert 'id="question"' in text
    assert 'placeholder="Ask Scout anything about your league, roster, players, rankings, trades, or public hockey..."' in text
    assert ">Who are the most active managers?</textarea>" not in text
    assert '<textarea id="question"' in text
    assert "</textarea>" in text


def validate_credential_persistence_external_store():
    with tempfile.TemporaryDirectory() as tmp:
        secrets_file = Path(tmp) / "secrets.local.json"
        previous = os.environ.get("ATHENA_SECRETS_FILE")
        os.environ["ATHENA_SECRETS_FILE"] = str(secrets_file)
        try:
            import Core.credential_store as cs
            cs = importlib.reload(cs)

            status_0 = cs.credential_status()
            assert status_0["persistent_external_store"] is True
            assert status_0["secrets_file"] == str(secrets_file)

            saved = cs.save_fantrax_credentials(
                league_secret="test-private-league-secret",
                cookie_header="test_cookie=abc123; another_cookie=xyz789",
            )
            assert saved["fantrax_league_secret_present"] is True
            assert saved["fantrax_cookie_present"] is True
            assert saved["fantrax_cookie_parseable"] is True
            assert saved["fantrax_cookie_count"] == 2
            assert secrets_file.exists()

            reloaded = importlib.reload(cs).credential_status()
            assert reloaded["fantrax_league_secret_present"] is True
            assert reloaded["fantrax_cookie_parseable"] is True
            assert reloaded["fantrax_cookie_count"] == 2

            # Opaque/non-cookie auth must not overwrite a valid browser cookie.
            rejected = cs.save_fantrax_credentials(cookie_header="not-a-cookie-token")
            assert rejected["fantrax_cookie_parseable"] is True
            assert rejected["fantrax_cookie_count"] == 2
            assert rejected["last_rejected_secret_reason"]
        finally:
            if previous is None:
                os.environ.pop("ATHENA_SECRETS_FILE", None)
            else:
                os.environ["ATHENA_SECRETS_FILE"] = previous
            import Core.credential_store as cs
            importlib.reload(cs)


def main():
    print("Athena UI + Credential Stabilization Validation")
    print("===============================================")

    tests = [
        ("Scout question field uses placeholder only", validate_scout_question_placeholder),
        ("Credential persistence external store", validate_credential_persistence_external_store),
    ]

    passed = 0
    for name, fn in tests:
        fn()
        print(f"[PASS] {name}")
        passed += 1

    print()
    print(f"Passed: {passed}")
    print("ATHENA UI + CREDENTIAL STABILIZATION PASS")


if __name__ == "__main__":
    main()

"""Regression: editorial narrative has sections and diagnostic details stay separate."""
from Athena.Investigation.league_editorial import compose_league_editorial
from pathlib import Path

sample = {"headline":"Protect Hronek at the center of trading", "opening":"Two completed trades.",
          "trades":[{"lead":"Team A received Player X.", "interpretation":"Impact requires scoring."}],
          "other_moves":[{"summary":"Team B added Player Y."}]}
article = compose_league_editorial(sample, "2")
assert "\n\nThe major exchanges\n" in article
assert "\n\nElsewhere around the league\n" in article
assert "\n\nWhat remains unresolved\n" in article
assert "Team A received Player X" in article
assert "Transactions in scope" not in article
router = Path(__file__).resolve().parents[1] / "Scout/conversation/router.py"
source = router.read_text(encoding="utf-8")
assert 'answer["editorial_report"] = bool(editorial' in source
assert 'compose_league_editorial(editorial' in source
app = (Path(__file__).resolve().parents[1] / "Scout/app.py").read_text(encoding="utf-8")
assert 'normalDetail && !answer.editorial_report' in app
print("PASS: editorial sections and public diagnostic gating")

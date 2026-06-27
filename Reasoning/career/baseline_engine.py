"""Rolling baseline computation for player season histories."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List


class BaselineEngine:
    def compute(self, seasons: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        rows = [dict(s) for s in seasons or [] if s.get("games")]
        for row in rows:
            row["ppg"] = self._rate(row.get("points"), row.get("games"))
            row["gpg"] = self._rate(row.get("goals"), row.get("games"))
            row["apg"] = self._rate(row.get("assists"), row.get("games"))

        current = rows[-1] if rows else {}
        peak_points = max(rows, key=lambda r: r.get("points", 0), default={})
        peak_goals = max(rows, key=lambda r: r.get("goals", 0), default={})

        def rolling(n: int) -> Dict[str, Any]:
            subset = rows[-n:] if len(rows) >= n else list(rows)
            return self._aggregate(subset, f"last_{n}")

        career = self._aggregate(rows, "career")
        result = {
            "current": current,
            "rolling_3": rolling(3),
            "rolling_5": rolling(5),
            "rolling_8": rolling(8),
            "career": career,
            "peak_points": peak_points,
            "peak_goals": peak_goals,
            "seasons": rows,
        }

        current_ppg = current.get("ppg")
        rolling_3_ppg = result["rolling_3"].get("ppg")
        if current_ppg is not None and rolling_3_ppg:
            result["current_vs_3yr_delta_pct"] = ((current_ppg - rolling_3_ppg) / rolling_3_ppg) * 100.0
        return result

    def _aggregate(self, rows: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
        games = sum(int(r.get("games") or 0) for r in rows)
        goals = sum(int(r.get("goals") or 0) for r in rows)
        assists = sum(int(r.get("assists") or 0) for r in rows)
        points = sum(int(r.get("points") or 0) for r in rows)
        return {
            "label": label,
            "season_count": len(rows),
            "games": games,
            "goals": goals,
            "assists": assists,
            "points": points,
            "ppg": self._rate(points, games),
            "gpg": self._rate(goals, games),
            "apg": self._rate(assists, games),
        }

    def _rate(self, numerator: Any, denominator: Any):
        try:
            denominator = float(denominator)
            if denominator == 0:
                return None
            return float(numerator or 0) / denominator
        except Exception:
            return None

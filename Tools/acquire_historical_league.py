"""Acquire one registered historical Fantrax league into an isolated context."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.json_utils import write_json
from Knowledge.LeagueHistory.context import (
    build_historical_context,
    extract_player_season_stats,
    historical_entry,
    load_historical_registry,
)
from Providers.Fantrax.fantrax_client import FantraxClient
from Providers.Fantrax.fetch.historical_player_stats_discovery import discover_historical_player_stats
from Providers.Fantrax.fetch.historical_draft_results_discovery import discover_historical_draft_results
from Knowledge.LeagueHistory.draft_results import normalize_historical_draft_results
from Knowledge.LeagueHistory.identity import build_historical_identity_resolution, enrich_historical_draft_observations


def acquire(season: int = 2025) -> dict[str, Any]:
    entry = historical_entry(season)
    league_id = str(entry["league_id"]).strip()
    if not league_id:
        raise ValueError(f"Historical league {season} has no registered league_id.")

    client = FantraxClient(league_id=league_id, season=season)
    raw_dir = ROOT / "Raw" / "Historical" / str(season)
    out_dir = ROOT / "Output" / "Historical" / str(season)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    fetchers = {
        "league_info": client.get_league,
        "player_pool": client.get_player_pool_payload,
        "transactions": client.get_transaction_evidence,
        "draft_picks": client.get_draft_picks,
    }
    payloads: dict[str, Any] = {}
    errors: dict[str, str] = {}
    warnings: dict[str, str] = {}
    provenance: dict[str, Any] = {}

    for name, fetcher in fetchers.items():
        try:
            payload = fetcher()
            client.validate_payload(payload, f"Historical {season} {name}")
            payloads[name] = payload
            provenance[name] = {"provider": "Fantrax", "league_id": league_id, "season": season, "mode": "direct"}
            write_json(raw_dir / f"{name}.json", payload)
        except Exception as exc:  # preserve partial historical evidence
            payloads[name] = None
            errors[name] = str(exc)

    # Draft-pick ownership/configuration and completed Draft Results are distinct
    # provider capabilities. Discover the latter from Fantrax's known authenticated
    # Draft Results application surface rather than reconstructing selections.
    draft_discovery = discover_historical_draft_results(client, season=season)
    draft_results_payload = draft_discovery.pop("selected_payload", None)
    write_json(raw_dir / "draft_results_source_discovery.json", draft_discovery)
    if draft_results_payload is not None:
        payloads["draft_results"] = draft_results_payload
        provenance["draft_results"] = {
            "provider": "Fantrax",
            "league_id": league_id,
            "season": season,
            "mode": "discovered_known_application_surface",
            "application_surface": draft_discovery.get("application_surface", ""),
            "transport": draft_discovery.get("selected_transport", ""),
            "source": draft_discovery.get("selected_source", ""),
        }
        write_json(raw_dir / "draft_results.json", draft_results_payload)
        canonical_draft = normalize_historical_draft_results(
            draft_results_payload, season=season, league_id=league_id
        )
        write_json(out_dir / "draft_results_canonical.json", canonical_draft)
    else:
        payloads["draft_results"] = None
        provenance["draft_results"] = {
            "provider": "Fantrax",
            "league_id": league_id,
            "season": season,
            "mode": "known_application_surface_discovery_no_usable_candidate",
            "application_surface": draft_discovery.get("application_surface", ""),
            "discovery_report": str(raw_dir / "draft_results_source_discovery.json"),
            "service_candidates": draft_discovery.get("service_candidates", []),
            "fxpa_method_candidates": draft_discovery.get("fxpa_method_candidates", []),
            "tested_get_candidates": draft_discovery.get("tested_get_candidates", []),
            "tested_fxpa_candidates": draft_discovery.get("tested_fxpa_candidates", []),
        }
        warnings["draft_results"] = (
            "The authenticated Fantrax Draft Results page was inspected, but no usable "
            "completed-draft payload was discovered from its exposed application sources."
        )

    # Fantrax's configured player-stats URL may not be valid for archived leagues.
    # Try it first, then conservatively reuse the already-acquired historical
    # player-pool payload only when it actually contains GP/stat rows. This is
    # evidence fallback, not fabrication: extract_player_season_stats() accepts
    # only rows exposing player identity plus games played.
    try:
        stats_payload = client.get_player_stats()
        client.validate_payload(stats_payload, f"Historical {season} player_stats")
        payloads["player_stats"] = stats_payload
        provenance["player_stats"] = {
            "provider": "Fantrax", "league_id": league_id, "season": season,
            "mode": "direct_player_stats_endpoint",
        }
        write_json(raw_dir / "player_stats.json", stats_payload)
    except Exception as exc:
        direct_error = str(exc)
        pool_payload = payloads.get("player_pool")
        pool_stats = extract_player_season_stats(pool_payload) if pool_payload is not None else []
        if pool_stats:
            # Preserve the original provider payload so downstream normalization
            # remains reproducible and does not confuse normalized rows with raw data.
            payloads["player_stats"] = pool_payload
            provenance["player_stats"] = {
                "provider": "Fantrax", "league_id": league_id, "season": season,
                "mode": "player_pool_evidence_fallback",
                "direct_endpoint_error": direct_error,
            }
            warnings["player_stats"] = (
                "Direct historical player-stats endpoint was unavailable; "
                "player-season statistics were recovered from the historical player-pool payload."
            )
            write_json(raw_dir / "player_stats.json", pool_payload)
        else:
            discovery = discover_historical_player_stats(client, season=season)
            discovery_payload = discovery.pop("selected_payload", None)
            write_json(raw_dir / "player_stats_source_discovery.json", discovery)
            discovered_stats = extract_player_season_stats(discovery_payload) if discovery_payload is not None else []
            if discovered_stats:
                payloads["player_stats"] = discovery_payload
                provenance["player_stats"] = {
                    "provider": "Fantrax", "league_id": league_id, "season": season,
                    "mode": "discovered_application_source",
                    "source": discovery.get("selected_source", ""),
                    "direct_endpoint_error": direct_error,
                }
                warnings["player_stats"] = (
                    "Configured historical player-stats endpoint was unavailable; "
                    "a usable source was discovered from Fantrax application assets."
                )
                write_json(raw_dir / "player_stats.json", discovery_payload)
            else:
                payloads["player_stats"] = None
                errors["player_stats"] = direct_error
                provenance["player_stats"] = {
                    "provider": "Fantrax", "league_id": league_id, "season": season,
                    "mode": "source_discovery_no_usable_candidate",
                    "direct_endpoint_error": direct_error,
                    "player_pool_stat_rows": 0,
                    "discovery_report": str(raw_dir / "player_stats_source_discovery.json"),
                    "service_candidates": discovery.get("service_candidates", []),
                    "fxpa_method_candidates": discovery.get("fxpa_method_candidates", []),
                    "tested_get_candidates": discovery.get("tested_get_candidates", []),
                }

    identity = build_historical_identity_resolution(
        season=season, league_id=league_id, raw_payloads=payloads
    )
    write_json(out_dir / "historical_identity_resolution.json", identity)
    canonical_path = out_dir / "draft_results_canonical.json"
    if canonical_path.exists():
        canonical_draft = json.loads(canonical_path.read_text(encoding="utf-8"))
        enriched = enrich_historical_draft_observations(canonical_draft, identity)
        write_json(out_dir / "draft_observations_enriched.json", enriched)

    context = build_historical_context(
        season=season,
        league_id=league_id,
        raw_payloads=payloads,
        source_provenance=provenance,
    )
    context["acquisition_errors"] = errors
    context["acquisition_warnings"] = warnings
    context["status"] = "complete" if not errors else "partial"
    write_json(out_dir / "league_context.json", context)
    return context


def _summary(context: dict[str, Any]) -> dict[str, Any]:
    season = int(context.get("season", 0))
    canonical_path = ROOT / "Output" / "Historical" / str(season) / "draft_results_canonical.json"
    canonical: dict[str, Any] = {}
    if canonical_path.exists():
        try:
            canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        except Exception:
            canonical = {}
    availability = context.get("source_availability", {})
    return {
        "season": season,
        "league_id": context.get("league_id", ""),
        "status": context.get("status", "unknown"),
        "draft_results": bool(availability.get("draft_results")),
        "draft_state": canonical.get("draft_state"),
        "configured_slots": canonical.get("configured_slot_count", 0),
        "selections": canonical.get("selection_count", 0),
        "no_player_selection": canonical.get("no_player_selection_count", 0),
        "errors": sorted((context.get("acquisition_errors") or {}).keys()),
        "warnings": sorted((context.get("acquisition_warnings") or {}).keys()),
    }


def acquire_all() -> dict[str, Any]:
    registry = load_historical_registry()
    entries = sorted(registry.get("historical_leagues", []), key=lambda item: int(item.get("season", 0)), reverse=True)
    summaries: list[dict[str, Any]] = []
    for entry in entries:
        season = int(entry["season"])
        try:
            summaries.append(_summary(acquire(season)))
        except Exception as exc:
            summaries.append({
                "season": season,
                "league_id": str(entry.get("league_id", "")),
                "status": "failed",
                "draft_results": False,
                "draft_state": None,
                "configured_slots": 0,
                "selections": 0,
                "no_player_selection": 0,
                "errors": [str(exc)],
                "warnings": [],
            })
    successful_drafts = sum(1 for item in summaries if item.get("draft_results"))
    return {
        "schema": "athena.historical_acquisition_sweep.v1",
        "registered_seasons": len(entries),
        "draft_results_acquired": successful_drafts,
        "draft_results_missing": len(entries) - successful_drafts,
        "seasons": summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--season", type=int)
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.all:
        result = acquire_all()
        write_json(ROOT / "Output" / "Historical" / "acquisition_sweep.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0 if result.get("draft_results_missing") == 0 else 1
    season = args.season if args.season is not None else 2025
    result = acquire(season)
    print(json.dumps(_summary(result), indent=2, ensure_ascii=False, default=str))
    return 0 if result.get("source_availability", {}).get("league_info") else 1


if __name__ == "__main__":
    raise SystemExit(main())

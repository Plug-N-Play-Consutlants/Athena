"""Current NHL team performance acquisition and bounded assessment.

Never substitutes seeded team identity for current-season results.
"""
from __future__ import annotations
from datetime import date
from typing import Any
from time import perf_counter


def _complete_league_team_benchmark(rows: list[Any], season: str) -> dict[str, Any] | None:
    """Build rates only from a complete, deduplicated canonical NHL snapshot."""
    from Knowledge.Identity.registry import SEED_IDENTITY_ENTITIES

    expected = {
        entity.entity_id.rsplit(".", 1)[-1].upper()
        for entity in SEED_IDENTITY_ENTITIES
        if entity.entity_type == "team" and entity.league == "NHL"
    }
    if not expected:
        return None

    teams: dict[str, dict[str, float]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        abbreviation = row.get("teamAbbrev")
        if isinstance(abbreviation, dict):
            abbreviation = abbreviation.get("default")
        abbreviation = str(abbreviation or "").upper()
        games, goals_for, goals_against = (
            row.get("gamesPlayed"), row.get("goalFor"), row.get("goalAgainst")
        )
        if (
            abbreviation in expected
            and abbreviation not in teams
            and all(type(value) is int and value >= 0 for value in (games, goals_for, goals_against))
            and games > 0
        ):
            teams[abbreviation] = {
                "games": float(games),
                "goals_for": float(goals_for),
                "goals_against": float(goals_against),
                "gfpg": goals_for / games,
                "gapg": goals_against / games,
            }
    if set(teams) != expected:
        return None
    return {
        "teams": len(teams),
        "gfpg": round(sum(team["goals_for"] for team in teams.values()) / sum(team["games"] for team in teams.values()), 3),
        "gapg": round(sum(team["goals_against"] for team in teams.values()) / sum(team["games"] for team in teams.values()), 3),
        "source": "nhl_official_current_standings",
        "season": season,
    }


def synthesize_verified_team_trends(evidence: dict[str, Any]) -> dict[str, Any]:
    """Report only official observed form; never infer positional need or causation."""
    standings = evidence.get("standings")
    if not isinstance(standings, dict):
        return {"statements": [], "signals": [], "source": "unavailable"}
    statements: list[str] = []
    signals: list[str] = []
    last = [standings.get(k) for k in ("last10Wins", "last10Losses", "last10OtLosses")]
    if all(isinstance(n, int) and not isinstance(n, bool) and n >= 0 for n in last) and sum(last) == 10:
        statements.append(f"Official last-ten form: {last[0]}-{last[1]}-{last[2]} (W-L-OTL).")
        signals.append("verified_last_ten")
    code, count = standings.get("streakCode"), standings.get("streakCount")
    if isinstance(code, str) and code.upper() in {"W", "L", "OT"} and isinstance(count, int) and not isinstance(count, bool) and count > 0:
        statements.append(f"Official current streak: {code.upper()}{count}.")
        signals.append("verified_streak")
    gp, goals_for, goals_against = (standings.get(k) for k in ("gamesPlayed", "goalFor", "goalAgainst"))
    if all(isinstance(n, int) and not isinstance(n, bool) for n in (gp, goals_for, goals_against)) and gp > 0 and goals_for >= 0 and goals_against >= 0:
        differential = goals_for - goals_against
        statements.append(f"Observed goal differential: {differential:+d} over {gp} games ({differential/gp:+.2f} per game).")
        signals.append("verified_goal_differential")
    return {"statements": statements, "signals": signals, "source": "nhl_official_current_standings" if signals else "insufficient_verified_fields"}


def assess_team_performance(question: str, abbreviation: str, name: str) -> dict[str, Any]:
    from Providers.NHL.nhl_client import NHLClient
    from Knowledge.Intelligence.Public.player_evidence import _target_season_id
    season = _target_season_id()
    evidence: dict[str, Any] = {"season": season, "team": abbreviation, "sources": [], "missing": [], "acquisition_timing_ms": {}}
    economic_state = None
    league_context = None
    client = NHLClient()
    acquisition_started = perf_counter()
    stage_started = perf_counter()
    try:
        payload = client.get_club_stats(abbreviation, season)
        if not isinstance(payload, dict): raise ValueError("unexpected_club_stats_payload")
        evidence["sources"].append("nhl_club_stats_season")
        skaters = payload.get("skaters") or []
        goalies = payload.get("goalies") or []
        if not isinstance(skaters, list): skaters = []
        if not isinstance(goalies, list): goalies = []
        skaters = [r for r in skaters if isinstance(r, dict) and isinstance(r.get("gamesPlayed"), (int,float)) and r["gamesPlayed"] > 0]
        ranked = sorted(skaters, key=lambda r: (r.get("points") if isinstance(r.get("points"), (int,float)) else -1), reverse=True)
        leaders = []
        for row in ranked[:5]:
            name_parts = [str(row.get(k) or "") for k in ("firstName", "lastName")]
            name_parts = [x.get("default", "") if isinstance(x, dict) else x for x in (row.get("firstName"), row.get("lastName"))]
            label = " ".join(x for x in name_parts if x).strip()
            if label:
                leaders.append({"name": label, "gp": row.get("gamesPlayed"), "goals": row.get("goals"), "assists": row.get("assists"), "points": row.get("points")})
        evidence["leaders"] = leaders
        evidence["skaters_observed"] = len(skaters)
        evidence["goalies_observed"] = len(goalies)
        # Retain verified season-level goalie observations independently of team
        # goals against. Do not confuse save percentage with team defensive quality.
        goalie_observations = []
        for g in goalies:
            if not isinstance(g, dict) or not isinstance(g.get("gamesPlayed"), (int, float)) or g["gamesPlayed"] <= 0:
                continue
            first, last = (g.get("firstName"), g.get("lastName"))
            label = " ".join(str(v.get("default", "") if isinstance(v, dict) else v or "") for v in (first, last)).strip()
            record = {"name": label, "games": g["gamesPlayed"]}
            for key in ("savePctg", "goalsAgainstAverage", "shotsAgainst", "saves", "goalsAgainst"):
                value = g.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                    record[key] = value
            goalie_observations.append(record)
        evidence["goalie_observations"] = goalie_observations
        goalie_totals = [
            (
                g["saves"],
                g.get("shotsAgainst", g.get("saves", 0) + g.get("goalsAgainst", 0)),
            )
            for g in goalie_observations
            if "saves" in g and ("shotsAgainst" in g or "goalsAgainst" in g)
        ]
        team_saves = sum(saves for saves, _ in goalie_totals)
        team_shots = sum(shots for _, shots in goalie_totals)
        if goalie_totals and team_shots > 0 and team_saves <= team_shots:
            evidence["team_goalie_save_percentage"] = {
                "saves": team_saves,
                "shots_against": team_shots,
                "save_percentage": team_saves / team_shots,
            }
    except Exception as exc:
        evidence["missing"].append("verified_current_season_club_stats")
        evidence["acquisition_error"] = type(exc).__name__
    evidence["acquisition_timing_ms"]["club_stats"] = round((perf_counter() - stage_started) * 1000, 2)
    stage_started = perf_counter()
    # Team-level results are distinct from individual scoring. Keep each source
    # independent so a failed standings endpoint does not erase verified players.
    try:
        standings_payload = client.get_team_standings_now()
        rows = standings_payload.get("standings") if isinstance(standings_payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("standings_rows_missing")
        match = next((r for r in rows if isinstance(r, dict) and
                      str(r.get("teamAbbrev", {}).get("default", "") if isinstance(r.get("teamAbbrev"), dict) else r.get("teamAbbrev", "")).upper() == abbreviation.upper()), None)
        if match is None:
            raise ValueError("team_not_in_standings")
        keys = ("gamesPlayed", "wins", "losses", "otLosses", "points", "pointPctg", "goalFor", "goalAgainst", "streakCode", "streakCount", "last10Wins", "last10Losses", "last10OtLosses")
        evidence["standings"] = {key: match[key] for key in keys if isinstance(match.get(key), (int, float, str))}
        evidence["sources"].append("nhl_official_current_standings")
        # The same official standings snapshot supports an actual league-relative
        # benchmark, rather than treating the team's GF/GA as a league ranking.
        benchmark = _complete_league_team_benchmark(rows, season)
        if benchmark is not None:
            evidence["league_benchmark"] = benchmark
            evidence["sources"].append("nhl_official_standings_league_benchmark")
        else:
            evidence["missing"].append("complete_current_nhl_standings_benchmark")
    except Exception as exc:
        evidence["missing"].append("verified_current_team_standings")
        evidence["standings_acquisition_error"] = type(exc).__name__
    evidence["acquisition_timing_ms"]["standings"] = round((perf_counter() - stage_started) * 1000, 2)
    stage_started = perf_counter()
    try:
        goalie_payload = client.get_goalie_summary(season)
        goalie_rows = goalie_payload.get("data") if isinstance(goalie_payload, dict) else None
        if not isinstance(goalie_rows, list):
            raise ValueError("goalie_summary_rows_missing")
        saves = 0
        shots_against = 0
        qualified_goalies = 0
        for row in goalie_rows:
            if not isinstance(row, dict):
                continue
            row_saves = row.get("saves")
            row_shots = row.get("shotsAgainst")
            if (
                type(row_saves) is int and row_saves >= 0
                and type(row_shots) is int and row_shots > 0
                and row_saves <= row_shots
            ):
                saves += row_saves
                shots_against += row_shots
                qualified_goalies += 1
        if qualified_goalies < 50 or shots_against <= 0:
            raise ValueError("goalie_summary_coverage_insufficient")
        evidence["league_goalie_benchmark"] = {
            "qualified_goalies": qualified_goalies,
            "saves": saves,
            "shots_against": shots_against,
            "save_percentage": saves / shots_against,
            "source": "nhl_official_goalie_summary",
            "season": season,
        }
        evidence["sources"].append("nhl_official_goalie_summary")
    except Exception as exc:
        evidence["missing"].append("league_goalie_comparison")
        evidence["goalie_benchmark_acquisition_error"] = type(exc).__name__
    evidence["acquisition_timing_ms"]["goalie_benchmark"] = round((perf_counter() - stage_started) * 1000, 2)
    stage_started = perf_counter()
    try:
        schedule = client.get_team_schedule_now(abbreviation)
        games = schedule.get("games") if isinstance(schedule, dict) else None
        if not isinstance(games, list):
            raise ValueError("schedule_games_missing")
        completed = []
        for game in games:
            if not isinstance(game, dict) or game.get("gameState") not in ("OFF", "FINAL"):
                continue
            home, away = game.get("homeTeam") or {}, game.get("awayTeam") or {}
            if not isinstance(home, dict) or not isinstance(away, dict):
                continue
            hs, aws = home.get("score"), away.get("score")
            if not isinstance(hs, int) or not isinstance(aws, int):
                continue
            is_home = home.get("abbrev") == abbreviation
            if not is_home and away.get("abbrev") != abbreviation:
                continue
            completed.append({"date": game.get("gameDate"), "opponent": away.get("abbrev") if is_home else home.get("abbrev"), "for": hs if is_home else aws, "against": aws if is_home else hs})
        completed.sort(key=lambda g: str(g["date"] or ""))
        evidence["recent_games"] = completed[-5:]
        if completed:
            evidence["sources"].append("nhl_official_completed_games")
        else:
            evidence["missing"].append("verified_recent_completed_games")
    except Exception as exc:
        evidence["missing"].append("verified_recent_completed_games")
        evidence["schedule_acquisition_error"] = type(exc).__name__
    evidence["acquisition_timing_ms"]["schedule"] = round((perf_counter() - stage_started) * 1000, 2)
    stage_started = perf_counter()
    # Compose the existing roster and economics capabilities only when the question
    # calls for them. Roster membership does not establish deployment or need.
    wants_roster = any(term in question.casefold() for term in
        ("roster", "lineup", "depth", "need", "weakness", "trade", "cap", "salary", "improv"))
    if wants_roster:
        try:
            roster = client.get_current_roster(abbreviation)
            if not isinstance(roster, dict):
                raise ValueError("unexpected_roster_payload")
            groups = ("forwards", "defensemen", "goalies")
            counts = {key: len(roster[key]) for key in groups if isinstance(roster.get(key), list)}
            if not counts:
                raise ValueError("roster_groups_missing")
            evidence["roster_counts"] = counts
            # A positional inventory is useful context but is not deployment,
            # quality, injury status, or evidence of a shortage.
            positions = {}
            for group in groups:
                for player in roster.get(group) or []:
                    if isinstance(player, dict):
                        pos = str(player.get("positionCode") or "").upper()
                        if pos in ("C", "L", "R", "D", "G"):
                            positions[pos] = positions.get(pos, 0) + 1
            if positions:
                evidence["roster_positions"] = positions
            evidence["sources"].append("nhl_current_roster")
        except Exception as exc:
            evidence["missing"].append("verified_current_roster")
            evidence["roster_acquisition_error"] = type(exc).__name__
        try:
            from Knowledge.Teams.team_economic_state import resolve_team_economic_state
            from Knowledge.Economics.league_season_context import resolve_league_season_context
            state = resolve_team_economic_state(abbreviation=abbreviation)
            context = resolve_league_season_context()
            economic_state = state
            league_context = context
            evidence["economics"] = {
                "league_year": context.league_year,
                "upper_limit": context.upper_limit,
                "contract_coverage": len(state.covered_contracts()),
                "aggregate_permitted": state.aggregate_permitted,
            }
            evidence["sources"].extend(["canonical_team_economic_state", "canonical_league_season_context"])
            if not state.aggregate_permitted:
                evidence["missing"].append("complete_verified_team_cap_ledger")
        except (LookupError, ValueError, OSError) as exc:
            evidence["missing"].append("canonical_team_economic_context")
            evidence["economic_acquisition_error"] = type(exc).__name__
        evidence["missing"].append("verified_roster_deployment_and_needs")
    else:
        evidence["missing"].append("verified_roster_deployment_and_cap_state")
    evidence["acquisition_timing_ms"]["roster_economics"] = round((perf_counter() - stage_started) * 1000, 2) if wants_roster else 0.0
    evidence["acquisition_timing_ms"]["total"] = round((perf_counter() - acquisition_started) * 1000, 2)
    if evidence.get("leaders"):
        text = f"Official NHL {str(season)[:4]}-{str(season)[4:]} team player production for {name}: " + "; ".join(f"{r['name']} ({r['points']} points in {r['gp']} games)" for r in evidence["leaders"] if isinstance(r.get("points"),(int,float))) + "."
        text += " These are scoring contributors, not proof of overall team strength, weakness or causation. Standings, game trends, deployment and cap context remain necessary for a complete assessment."
        confidence = 0.56
    else:
        text = f"No verified {season} NHL team production was acquired for {name}. A current-season strengths-and-weaknesses assessment cannot be derived from a historical seed profile."
        confidence = 0.3
    standings = evidence.get("standings")
    if standings:
        text += f" Official standings: {standings.get('wins', '?')}-{standings.get('losses', '?')}-{standings.get('otLosses', '?')} in {standings.get('gamesPlayed', '?')} games, {standings.get('points', '?')} standings points."
        if isinstance(standings.get("goalFor"), int) and isinstance(standings.get("goalAgainst"), int):
            text += f" Goals for/against: {standings['goalFor']}/{standings['goalAgainst']}."
    trend = synthesize_verified_team_trends(evidence)
    if trend["statements"]:
        text += " " + " ".join(trend["statements"])
    recent = evidence.get("recent_games") or []
    if recent:
        wins = sum(g["for"] > g["against"] for g in recent)
        text += f" In the last {len(recent)} verified completed games: {wins} wins and {len(recent)-wins} non-wins (including possible overtime/shootout losses)."
    if wants_roster:
        counts = evidence.get("roster_counts")
        if counts:
            text += " The official current roster lists " + ", ".join(f"{value} {key}" for key, value in counts.items()) + "; these are roster counts, not proof of positional surplus or shortage."
        if evidence.get("roster_positions"):
            text += " Recorded primary-position codes: " + ", ".join(f"{key} {value}" for key, value in sorted(evidence["roster_positions"].items())) + "; these are not depth-chart assignments or a measure of positional quality."
        economic = evidence.get("economics")
        if economic:
            text += f" The {economic['league_year']} NHL upper limit is ${economic['upper_limit']:,}."
            if not economic["aggregate_permitted"]:
                text += f" Canonical contract coverage includes {economic['contract_coverage']} contract(s), not a complete club ledger; team cap usage and available space cannot be calculated reliably."
        text += " A specific roster need or acquisition recommendation requires verified deployment, health, performance and transaction context."
    from Athena.evidence_sufficiency import audit_team_evidence
    evidence["evidence_sufficiency"] = audit_team_evidence(evidence, needs_roster=wants_roster)
    if wants_roster and evidence.get("economics") and not evidence["economics"].get("aggregate_permitted"):
        text += " Contract coverage is sourced from the canonical effective-dated contract pack, not from the current NHL roster endpoint; the latter cannot establish AAV, retained salary, LTIR, or complete cap accounting."
    from Athena.team_comparative_evaluation import evaluate_team, narrative
    comparative = evaluate_team(evidence)
    evidence["comparative_evaluation"] = comparative
    text += " " + narrative(comparative)
    evidence["analytical_synthesis"] = trend
    return {
        "conclusion": text,
        "evidence": evidence,
        "confidence": confidence,
        "economic_state_object": economic_state,
        "league_context_object": league_context,
    }


def official_team_player_row(player_name: str, team_name: str) -> dict[str, Any] | None:
    """Exact identity match in verified current NHL club-season statistics."""
    from Providers.NHL.nhl_client import NHLClient
    from Knowledge.Intelligence.Public.player_evidence import _target_season_id
    from Knowledge.Intelligence.Public.public_team_profiles import public_team_profiles
    import re
    team_key = str(team_name or "").strip().casefold()
    resolved = resolve_nhl_team_subject(team_name)
    abbreviation = resolved[0] if resolved else None
    if abbreviation is None:
        for profile in public_team_profiles() or []:
            if str(getattr(profile, "display_name", "")).casefold() == team_key:
                abbreviation = str(getattr(profile, "abbreviation", "") or "").upper()
                break
    if not abbreviation or not re.fullmatch(r"[A-Z]{3}", abbreviation):
        return None
    season = _target_season_id()
    payload = NHLClient().get_club_stats(abbreviation, season)
    if not isinstance(payload, dict):
        return None
    wanted = " ".join(str(player_name).casefold().split())
    for row in payload.get("skaters") or []:
        if not isinstance(row, dict):
            continue
        parts = []
        for key in ("firstName", "lastName"):
            value = row.get(key)
            parts.append(str(value.get("default", "") if isinstance(value, dict) else value or ""))
        if " ".join(" ".join(parts).casefold().split()) != wanted:
            continue
        gp, points = row.get("gamesPlayed"), row.get("points")
        if not isinstance(gp, (int, float)) or gp <= 0 or not isinstance(points, (int, float)):
            return None
        return {"season": season, "gp": gp, "points": points, "goals": row.get("goals"), "assists": row.get("assists")}
    return None


# Canonical objective selection and execution are Athena-owned. This is a
# bounded team investigation, not a claim of verified positional deficiencies.
def resolve_nhl_team_subject(question: str) -> tuple[str, str] | None:
    """Resolve one explicit NHL team using the existing canonical identity registry.

    Do not resolve bare ambiguous city names (e.g. New York), generic nicknames
    or multi-team comparisons to an arbitrary first match.
    """
    import re
    from Knowledge.Identity.registry import SEED_IDENTITY_ENTITIES
    normalized = re.sub(r"[^a-z0-9\s]", " ", (question or "").casefold())
    normalized = " ".join(normalized.split())
    matches = []
    for entity in SEED_IDENTITY_ENTITIES:
        if entity.entity_type != 'team' or entity.league != 'NHL':
            continue
        abbreviation = entity.entity_id.rsplit('.', 1)[-1].upper()
        # Canonical names are preferred; unique nicknames are acceptable when
        # sufficiently specific. Short city aliases are not assumed unique.
        aliases = [entity.canonical_name, *entity.aliases]
        for alias in aliases:
            key = ' '.join(re.sub(r"[^a-z0-9\s]", " ", alias.casefold()).split())
            if not key or (len(key) < 4 and key != abbreviation.casefold()):
                continue
            if re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", normalized):
                matches.append((abbreviation, entity.canonical_name))
                break
    unique = list(dict.fromkeys(matches))
    return unique[0] if len(unique) == 1 else None


def team_investigation_target(question: str) -> tuple[str, str] | None:
    import re
    subject = resolve_nhl_team_subject(question)
    if subject is None:
        return None
    text = " ".join(re.sub(r"[^a-z0-9\s]", " ", (question or "").casefold()).split())
    primary = bool(re.search(r"\b(roster|lineup|positional|depth)\s+(needs?|holes?|weakness(?:es)?|improvements?|upgrades?)\b", text))
    primary = primary or bool(re.search(r"\b(how|where|ways?|could|should)\b.{0,85}\b(improve|upgrade|strengthen|address)\b", text))
    primary = primary or bool(re.search(r"\b(improve|upgrade|strengthen)\b.{0,55}\b(roster|lineup|team)\b", text))
    primary = primary or bool(re.search(r"\b(biggest|major|main)\b.{0,35}\b(weaknesses|concerns|needs)\b", text))
    performance = bool(re.search(
        r"\b(scoring|goals?\s+for|offens(?:e|ive)|goal\s+prevention|goals?\s+against|"
        r"defens(?:e|ive)|goaltending|goalies?|save\s+percentage|team\s+performance)\b",
        text,
    ))
    comparative = bool(re.search(
        r"\b(compare|compares|compared|comparison|against|versus|vs\.?|league\s+average|"
        r"league-wide|rest\s+of\s+the\s+nhl)\b",
        text,
    ))
    current_season = bool(re.search(
        r"\b(this|current|present|season.to.date)\s+season\b|\bso\s+far\s+this\s+season\b",
        text,
    ))
    primary = primary or (performance and (comparative or current_season))
    return subject if primary else None


def execute_team_investigation(ctx: Any, question: str) -> dict[str, Any]:
    from Scout.conversation.responses import response, developer_info
    team = team_investigation_target(question)
    if team is None:
        return response(intent="public_current_season_team_investigation", title="Team subject unresolved",
                        engine_conclusion="The team and investigation objective could not be established.",
                        known_limitations=["verified_team_investigation_subject"], confidence=0.2)
    request_evidence = getattr(ctx, "request_evidence", None)
    request_bundle_applies = (
        isinstance(request_evidence, dict)
        and request_evidence.get("route") == "public_current_season_team_investigation"
        and request_evidence.get("team") == team[0]
    )
    assessment = (
        request_evidence.get("team_performance_assessment")
        if request_bundle_applies
        and isinstance(request_evidence.get("team_performance_assessment"), dict)
        else None
    )
    if assessment is None and not request_bundle_applies:
        assessment = assess_team_performance(question, *team)
    if assessment is None:
        evidence = request_evidence.get("team_performance_assessment", {}).get("evidence", {}) if isinstance(request_evidence, dict) else {}
        missing = list(request_evidence.get("missing") or ["structured_team_performance_evidence"]) if isinstance(request_evidence, dict) else ["request_owned_team_evidence"]
        return response(
            intent="public_current_season_team_investigation",
            title=f"{team[1]}: evidence unavailable",
            engine_conclusion="Athena's request evidence bundle did not contain a structured team assessment. The specialist did not start a second acquisition path.",
            observed_facts=[],
            known_limitations=missing,
            confidence=0.2,
            developer={**developer_info(
                "public_current_season_team_investigation",
                getattr(ctx, "files_loaded", []),
                missing=missing,
            ), "team_performance_evidence": evidence,
                "team_evidence_consumption": {
                    "owner": "Athena.request_execution",
                    "consumed": False,
                    "acquisition_count": 1,
                    "fallback_used": False,
                    "reason": "request_bundle_missing_structured_assessment",
                }},
        )
    evidence = assessment["evidence"]
    facts = [f"Official NHL season: {evidence['season']}"]
    facts.extend(f"{row['name']}: {row['points']} points in {row['gp']} games"
                 for row in evidence.get("leaders", []) if isinstance(row.get("points"), (int, float)))
    return response(
        intent="public_current_season_team_investigation", title=f"{team[1]}: current-season evidence",
        engine_conclusion=assessment["conclusion"], observed_facts=facts,
        known_limitations=list(evidence["missing"]), confidence=assessment["confidence"],
        developer={**developer_info("public_current_season_team_investigation",
                                   getattr(ctx, "files_loaded", []), knowledge_used=evidence["sources"],
                                   intelligence_used=["nhl_team_performance_investigation"], missing=evidence["missing"]),
                   "team_performance_evidence": evidence,
                   "team_evidence_consumption": {
                       "owner": "Athena.request_execution" if request_bundle_applies else "compatibility_specialist",
                       "consumed": True,
                       "acquisition_count": 1 if request_bundle_applies else 1,
                       "fallback_used": not request_bundle_applies,
                       "sources": list(evidence.get("sources") or []),
                       "missing": list(evidence.get("missing") or []),
                   }},
    )

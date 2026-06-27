"""
Scout Alpha local web application.

Scout is the first experience layer powered by Athena Engine. This module uses
only Python's standard library so the local alpha can run from Spyder without
installing Streamlit, FastAPI, Node, React, or any other web framework.
"""

from __future__ import annotations

import json
import os
import sys
import time
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_optional_json
from Core.project_paths import CONFIGURATION_DIR, OUTPUT_DIR, RAW_DIR
import Athena
from Athena.capabilities import assess_capabilities, capability_dashboard
from Athena.debug_export import write_debug_export
from Scout.conversation.context import load_context, get_team_names
from Scout.conversation.router import analyze_league, route_question
from Providers.Fantrax.auth.connection_wizard import connection_capability_status, guided_connect_and_sync, open_fantrax_login
from Knowledge.Graph.chain_engine import build_evidence_chain
from Knowledge.Graph.reasoning_engine import build_reasoning_package
from Knowledge.Graph.temporal_intelligence import timeline_for_entity
from Knowledge.Graph.evidence_chain import load_graph


HOST = os.environ.get("SCOUT_HOST", "localhost")
PORT = int(os.environ.get("SCOUT_PORT", "8765"))
from Core.version import SCOUT_VERSION
WORKSPACE_FILE = CONFIGURATION_DIR / "workspace.json"
SECRETS_FILE = CONFIGURATION_DIR / "secrets.local.json"
CONFIG_FILE = CONFIGURATION_DIR / "config.json"
LATEST_OPERATION: Dict[str, Any] = {}
LATEST_ANSWER: Dict[str, Any] = {}
SESSION_TRANSCRIPT: list[Dict[str, Any]] = []
TEST_LEAGUE_PLACEHOLDERS = {"", "test_league_id_provider_registry", "test_league_id", "test_league_id_drop2", "validation_league_id", "validation-league", "placeholder"}


def _is_placeholder_league_id(value: Any) -> bool:
    return str(value or "").strip().lower() in TEST_LEAGUE_PLACEHOLDERS


def _configured_provider_league_id() -> str:
    config = read_optional_json(CONFIG_FILE)
    if not isinstance(config, dict):
        return ""
    provider = config.get("provider") if isinstance(config.get("provider"), dict) else {}
    value = provider.get("league_id") or provider.get("leagueId") or ""
    return str(value or "").strip()


def _effective_league_id(workspace_data: Dict[str, Any]) -> str:
    workspace_league_id = str(workspace_data.get("league_id") or "").strip()
    if workspace_league_id and not _is_placeholder_league_id(workspace_league_id):
        return workspace_league_id
    configured = _configured_provider_league_id()
    if configured and not _is_placeholder_league_id(configured):
        return configured
    return ""


def _json_response(handler: BaseHTTPRequestHandler, payload: Dict[str, Any], status: int = 200) -> None:
    body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)



def _session_answer_summary(answer: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact prompt/response summary for acceptance comparison."""
    if not isinstance(answer, dict):
        return {"title": "Invalid answer", "text": str(answer)}
    text = answer.get("public_comment") or answer.get("natural_language_response") or answer.get("response_text") or answer.get("scout_message") or answer.get("engine_conclusion") or ""
    return {
        "title": answer.get("title", "Scout response"),
        "intent": answer.get("intent", ""),
        "confidence": answer.get("confidence"),
        "text": text,
        "engine_conclusion": answer.get("engine_conclusion", ""),
        "observed_facts": list(answer.get("observed_facts") or [])[:12] if answer.get("debug_session") else [],
        "known_limitations": list(answer.get("known_limitations") or [])[:8] if answer.get("debug_session") else [],
    }


def _record_session_turn(question: str, mode: str, answer: Dict[str, Any]) -> None:
    SESSION_TRANSCRIPT.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "question": question,
        "answer": _session_answer_summary(answer),
    })


def _write_session_log() -> Dict[str, Any]:
    """Overwrite the temporary Scout session prompt/response comparison log."""
    reports = PROJECT_ROOT / "Reports"
    reports.mkdir(parents=True, exist_ok=True)
    txt_path = reports / "scout_session_log.txt"
    json_path = reports / "scout_session_log.json"
    payload = {
        "created": datetime.now(timezone.utc).isoformat(),
        "version": SCOUT_VERSION,
        "turn_count": len(SESSION_TRANSCRIPT),
        "turns": SESSION_TRANSCRIPT,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "Scout Session Prompt/Response Log",
        "=================================",
        f"Created: {payload['created']}",
        f"Scout: {SCOUT_VERSION}",
        f"Turns: {len(SESSION_TRANSCRIPT)}",
        "",
    ]
    for idx, turn in enumerate(SESSION_TRANSCRIPT, 1):
        answer = turn.get("answer", {}) if isinstance(turn, dict) else {}
        lines.extend([
            f"--- Turn {idx} ---",
            f"Time: {turn.get('timestamp', '')}",
            f"Mode: {turn.get('mode', '')}",
            f"Prompt: {turn.get('question', '')}",
            f"Title: {answer.get('title', '')}",
            f"Intent: {answer.get('intent', '')}",
            f"Confidence: {answer.get('confidence', '')}",
            "Response:",
            str(answer.get("text") or answer.get("engine_conclusion") or ""),
        ])
        facts = answer.get("observed_facts") or []
        if facts:
            lines.append("Observed facts:")
            lines.extend(f"  - {fact}" for fact in facts)
        limits = answer.get("known_limitations") or []
        if limits:
            lines.append("Known limitations:")
            lines.extend(f"  - {item}" for item in limits)
        lines.append("")
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "ok": True,
        "turn_count": len(SESSION_TRANSCRIPT),
        "text_path": str(txt_path),
        "json_path": str(json_path),
        "text_download_url": "/api/debug/download?file=scout_session_log.txt",
        "json_download_url": "/api/debug/download?file=scout_session_log.json",
    }


def _html_response(handler: BaseHTTPRequestHandler, html: str, status: int = 200) -> None:
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    if content_length <= 0:
        return {}
    raw = handler.rfile.read(content_length).decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _workspace_payload() -> Dict[str, Any]:
    athena_status = Athena.status()
    workspace_data = athena_status.get("workspace", {}) if isinstance(athena_status, dict) else {}
    secrets = athena_status.get("secrets", {}) if isinstance(athena_status, dict) else {}
    effective_league_id = _effective_league_id(workspace_data)
    workspace_display = dict(workspace_data)
    workspace_display["effective_league_id"] = effective_league_id
    workspace_display["league_id_is_placeholder"] = _is_placeholder_league_id(workspace_data.get("league_id"))
    return {
        "workspace": workspace_display,
        "provider_defaults": {"name": workspace_data.get("provider"), "base_url": None},
        "secret_status": {
            "fantrax_cookie_present": bool(secrets.get("fantrax_cookie_present")),
            "fantrax_cookie_parseable": bool(secrets.get("fantrax_cookie_parseable")),
            "fantrax_cookie_count": int(secrets.get("fantrax_cookie_count") or 0),
            "fantrax_secret_format": secrets.get("fantrax_secret_format"),
            "fantrax_league_secret_present": bool(secrets.get("fantrax_league_secret_present")),
            "fantrax_league_secret_format": secrets.get("fantrax_league_secret_format"),
            "fantrax_cookie_saved_at": secrets.get("fantrax_cookie_saved_at"),
            "fantrax_league_secret_saved_at": secrets.get("fantrax_league_secret_saved_at"),
            "persistent_external_store": bool(secrets.get("persistent_external_store")),
            "secrets_file": secrets.get("secrets_file"),
        },
        "athena": athena_status,
    }



def _public_status_payload() -> Dict[str, Any]:
    """Return public-mode status pills without leaking private provider state."""
    rulebook = PROJECT_ROOT / "Knowledge" / "Packs" / "NHL" / "rulebook" / "2025_2026"
    mou = PROJECT_ROOT / "Knowledge" / "Packs" / "NHL" / "cba" / "2025_mou"
    pif_public = PROJECT_ROOT / "Knowledge" / "Intelligence" / "Public" / "public_player_profiles.py"
    rss_registry = PROJECT_ROOT / "Knowledge" / "Events" / "live_sources.py"
    return {
        "public_player_profiles": pif_public.exists(),
        "nhl_rules": rulebook.exists(),
        "nhl_mou": mou.exists(),
        "rss_feeds": rss_registry.exists(),
        "live_intelligence": (PROJECT_ROOT / "Knowledge" / "Events" / "live_intelligence.py").exists(),
    }

def _context_payload() -> Dict[str, Any]:
    ctx = load_context()
    payload = {
        "files_loaded": ctx.files_loaded,
        "raw_status": ctx.raw_status or {},
        "team_names": get_team_names(ctx),
        "public_status": _public_status_payload(),
    }
    payload.update(_workspace_payload())
    return payload


def test_fantrax_connection(league_id: str, cookie: str = "", league_secret: str = "") -> Dict[str, Any]:
    """Connect Scout to Fantrax through Athena and persist the active workspace.

    This is intentionally a thin Scout binding. Athena owns provider resolution,
    workspace persistence, and local secret storage.
    """
    cleaned_league_id = str(league_id or "").strip()
    cleaned_cookie = str(cookie or "").strip()
    cleaned_league_secret = str(league_secret or "").strip()
    if not cleaned_league_id:
        return {
            "ok": False,
            "provider": "Fantrax",
            "provider_key": "fantrax",
            "message": "Fantrax league ID is required.",
            "error": "Fantrax league ID is required.",
        }
    try:
        return Athena.connect_fantrax(
            league_id=cleaned_league_id,
            auth_cookie=cleaned_cookie,
            league_secret=cleaned_league_secret,
            validate=True,
            mode="fantasy_league",
        )
    except Exception as exc:
        return {
            "ok": False,
            "provider": "Fantrax",
            "provider_key": "fantrax",
            "league_id": cleaned_league_id,
            "message": str(exc),
            "error": str(exc),
        }


INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Scout Alpha</title>
  <style>
    :root { --bg:#0f1115; --panel:#171a21; --panel2:#1f2430; --text:#f5f7fb; --muted:#a8b0bf; --line:#2b3140; --accent:#e6edf7; --good:#9ee6b8; --warn:#f6cf8f; --bad:#ff9c9c; }
    * { box-sizing:border-box; }
    body { margin:0; font-family: Arial, Helvetica, sans-serif; background:var(--bg); color:var(--text); }
    main { max-width: 940px; margin: 0 auto; padding: 42px 20px 32px; min-height:100vh; display:flex; flex-direction:column; }
    header { text-align:center; margin-bottom: 28px; }
    h1 { font-size: 42px; line-height:1; margin:0 0 8px; font-weight:700; letter-spacing:-0.04em; }
    .subtitle { color:var(--muted); font-size:14px; }
    .panel, .search { background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:14px; box-shadow: 0 24px 80px rgba(0,0,0,.16); margin-top:14px; }
    .search { position:sticky; bottom:12px; z-index:10; backdrop-filter: blur(10px); }
    #conversation { flex:1; padding: 8px 0 14px; }
    .panel h2 { margin:4px 0 10px; font-size:16px; }
    textarea, input, select { width:100%; background:#0c0e13; color:var(--text); border:1px solid var(--line); border-radius:14px; padding:12px 14px; font-size:15px; outline:none; }
    textarea { min-height:74px; resize:vertical; font-size:17px; }
    textarea:focus, input:focus, select:focus { border-color:#6f7c96; }
    .grid { display:grid; grid-template-columns: 1fr 1fr; gap:10px; }
    .actions { display:flex; gap:10px; align-items:center; justify-content:space-between; margin-top:12px; flex-wrap:wrap; }
    button { border:1px solid var(--line); background:var(--accent); color:#10131a; border-radius:999px; padding:10px 16px; font-weight:700; cursor:pointer; }
    button.secondary { background:transparent; color:var(--text); }
    button:disabled { opacity:.55; cursor:not-allowed; }
    .toggle { display:flex; gap:8px; align-items:center; color:var(--muted); font-size:13px; white-space:nowrap; }
    .toggle input { width:auto; }
    .context { display:flex; gap:8px; flex-wrap:wrap; margin-top:18px; color:var(--muted); font-size:13px; justify-content:center; }
    .pill { border:1px solid var(--line); border-radius:999px; padding:6px 10px; background:rgba(255,255,255,.02); }
    .pill.good { color:var(--good); }
    .pill.warn { color:var(--warn); }
    .answer { margin-top:10px; background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:22px; }
    .you { margin-top:22px; color:var(--muted); padding-left:6px; }
    .answer h2 { margin:0 0 6px; font-size:22px; }
    .confidence { color:var(--muted); font-size:13px; margin-bottom:18px; }
    .cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:10px; margin:14px 0 20px; }
    .card { background:var(--panel2); border:1px solid var(--line); border-radius:14px; padding:14px; }
    .card.action-card { cursor:pointer; transition: transform .12s ease, border-color .12s ease; }
    .card.action-card:hover { transform: translateY(-1px); border-color:#6f7c96; }
    .action-note { margin-top:8px; color:var(--warn); font-size:11px; font-weight:700; }
    .card .label { color:var(--muted); font-size:12px; margin-bottom:6px; }
    .card .value { font-size:22px; font-weight:700; }
    h3 { margin:18px 0 8px; font-size:15px; color:#dbe3f1; text-transform:uppercase; letter-spacing:.08em; }
    ul { margin:8px 0 0 20px; padding:0; }
    li { margin:7px 0; line-height:1.4; }
    details { margin-top:14px; }
    details.dev { border-top:1px solid var(--line); padding-top:14px; }
    summary { cursor:pointer; color:var(--warn); font-weight:700; }
    pre { overflow:auto; background:#0c0e13; border:1px solid var(--line); border-radius:12px; padding:12px; color:#dbe3f1; font-size:12px; }
    .loading { margin-top:18px; color:var(--muted); text-align:center; }
    .footer { margin-top:28px; text-align:center; color:var(--muted); font-size:12px; }
    .note { color:var(--muted); font-size:12px; margin-top:8px; line-height:1.4; }
    .diag { background:#0c0e13; border:1px solid var(--line); border-radius:12px; padding:12px; margin-top:12px; }
    .diag.fail { border-color:rgba(255,156,156,.45); }
    .diag.pass { border-color:rgba(158,230,184,.45); }
    .diag .row { margin:6px 0; color:var(--muted); }
    .diag strong { color:var(--text); }
    .history { margin-top:14px; border-top:1px solid var(--line); padding-top:12px; }
    .history-item { color:var(--muted); font-size:12px; margin:5px 0; }
    .history-item.pass { color:var(--good); }
    .history-item.fail { color:var(--bad); }
    .status { margin-top:12px; border:1px solid var(--line); border-radius:14px; padding:12px 14px; background:#0c0e13; color:var(--muted); font-size:13px; line-height:1.45; display:none; }
    .status.good { display:block; color:var(--good); border-color:rgba(158,230,184,.45); }
    .status.warn { display:block; color:var(--warn); border-color:rgba(246,207,143,.45); }
    .status.bad { display:block; color:var(--bad); border-color:rgba(255,156,156,.45); }
    .status.neutral { display:block; color:var(--muted); }
    .status.working { display:block; color:#dbe3f1; border-color:rgba(219,227,241,.35); }
    .chat-turn { margin-top:16px; }
    .conversation-note { color:var(--muted); font-size:12px; text-align:center; margin:8px 0 14px; }
    .auth-roadmap { border:1px solid var(--line); border-radius:12px; padding:10px 12px; background:#0c0e13; color:var(--muted); font-size:12px; line-height:1.45; margin-top:10px; }
    .pending-card { margin-top:16px; border:1px dashed var(--line); border-radius:18px; padding:16px; color:var(--muted); background:rgba(255,255,255,.025); }
    .answer-copy { margin:12px 0 16px; color:#dbe3f1; line-height:1.55; white-space:pre-wrap; }
    .raw-reasoning { margin:12px 0 16px; border:1px solid var(--line); border-radius:12px; background:rgba(255,255,255,.025); padding:10px 12px; }
    .raw-reasoning summary { cursor:pointer; color:var(--muted); font-size:13px; }
    .raw-reasoning pre, .dev pre { white-space:pre-wrap; overflow:auto; max-height:420px; }
    .source-links { margin:12px 0 16px; display:flex; gap:10px; flex-wrap:wrap; }
    .source-link { border:1px solid var(--line); border-radius:999px; background:rgba(255,255,255,.04); color:#dbe3f1; padding:7px 10px; cursor:pointer; font-size:13px; }
    .source-link:hover { background:rgba(255,255,255,.08); }
    .modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.62); display:flex; align-items:center; justify-content:center; z-index:9999; padding:24px; }
    .modal-card { max-width:780px; width:min(780px, 96vw); max-height:82vh; overflow:auto; background:#101827; border:1px solid var(--line); border-radius:18px; padding:22px; box-shadow:0 24px 70px rgba(0,0,0,.45); }
    .modal-card h2 { margin-top:0; }
    .modal-card pre { white-space:pre-wrap; line-height:1.5; color:#dbe3f1; }
    .modal-actions { margin-top:16px; text-align:right; }
    .jump-controls { position:fixed; right:18px; bottom:18px; display:flex; flex-direction:column; gap:8px; z-index:50; }
    .jump-controls button { width:42px; height:42px; border-radius:999px; padding:0; box-shadow:0 8px 24px rgba(0,0,0,.35); }
    @media (max-width: 700px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
<main>
  <header>
    <h1>Scout</h1>
    <div class="subtitle">Powered by Athena Engine</div>
    <div class="subtitle" style="margin-top:6px;">{SCOUT_VERSION}</div>
  </header>

  <details class="panel" id="fantraxPanel" style="display:none;">
    <summary>Connect Fantrax</summary>
    <form id="fantraxCredentialForm" autocomplete="on" action="#" method="post">
      <input type="text" id="fantraxCredentialUsername" name="username" value="fantrax-personal-profile-secret" autocomplete="username" style="position:absolute; left:-10000px; width:1px; height:1px; opacity:0;" tabindex="-1" aria-hidden="true" />
      <div class="grid" style="margin-top:12px;">
        <input id="leagueId" name="fantrax_league_id" placeholder="Fantrax League ID" autocomplete="section-fantrax organization" />
        <input id="leagueSecret" name="fantrax_personal_profile_secret" placeholder="Fantrax Personal/Profile Secret ID" type="password" autocomplete="section-fantrax current-password" data-lpignore="false" data-1p-ignore="false" />
      </div>
      <div class="actions">
        <div>
          <button type="submit" id="testBtn" class="secondary">Save / Test Connection</button>
          <button type="button" id="openFantraxBtn" class="secondary" style="display:none;">Connect Fantrax & Sync</button>
        </div>
        <span class="note">Athena stores the secret locally by status only; the form also uses standard password-manager fields so your browser or password manager can remember it.</span>
      </div>
    </form>
    <div class="auth-roadmap" id="authStatusNote">
      Automatic browser-session detection is preferred. Manual Cookie entry is hidden unless automatic auth fails or you open advanced fallback.
    </div>
    <details style="margin-top:10px;" id="advancedCookieDetails">
      <summary>Advanced fallback: manual Cookie header</summary>
      <input id="cookie" name="fantrax_cookie_header" placeholder="Paste authenticated browser Cookie header only if automatic auth fails" type="password" autocomplete="off" style="width:100%; margin-top:10px;" />
      <div class="note">Log into Fantrax in your browser, open Developer Tools → Network, refresh Fantrax, select a Fantrax request, and copy the Request Headers value named <strong>Cookie</strong>. Paste the full Cookie header here. Do not paste your password.</div>
    </details>
    <div id="connectionStatus" class="status neutral">Select Fantasy League mode to connect Fantrax. Public Sports does not require Fantrax login.</div>
  </details>

  <div class="context" id="context"></div>
  <section class="panel history" id="operationHistoryPanel" style="display:none;"><h2>Operation History</h2><div id="operationHistory"></div></section>
  <div class="status neutral" id="scoutStatus">Ready.</div>
  <div class="loading" id="loading" style="display:none;">Scout is asking Athena...</div>
  <section id="conversation"><div class="conversation-note">Scout responses appear here. The newest response appears just above the prompt.</div></section>

  <section class="search" id="promptDock">
    <div class="grid">
      <select id="mode">
        <option value="public" selected>Public Sports</option>
        <option value="fantasy">Fantasy League</option>
      </select>
      <label class="toggle"><input type="checkbox" id="devMode" /> Developer Mode</label>
    </div>
    <textarea id="question" placeholder="Ask Scout anything about your league, roster, players, rankings, trades, or public hockey..."></textarea>
    <div class="actions">
      <div>
        <button type="button" id="askBtn">Ask Scout</button>
        <button type="button" class="secondary" id="analyzeBtn" style="display:none;">Sync League</button>
        <button type="button" class="secondary" id="exportBtn">Export Debug</button>
        <button type="button" class="secondary" id="sessionLogBtn">Export Session Log</button>
      </div>
    </div>
  </section>
  <div class="footer">Scout Alpha is intentionally simple. Athena performs the analysis; Scout communicates it.</div>
</main>
<div class="jump-controls" aria-label="Page jump controls">
  <button type="button" class="secondary" id="jumpTopBtn" title="Jump to top">↑</button>
  <button type="button" class="secondary" id="jumpBottomBtn" title="Jump to prompt">↓</button>
</div>
<script>
const conversation = document.getElementById('conversation');
const loading = document.getElementById('loading');
const devMode = document.getElementById('devMode');
const mode = document.getElementById('mode');
const fantraxCredentialForm = document.getElementById('fantraxCredentialForm');
const actionButtons = ['askBtn','analyzeBtn','exportBtn','sessionLogBtn','openFantraxBtn'].map(id => document.getElementById(id)).filter(Boolean);

function setScoutStatus(kind, message) {
  const status = document.getElementById('scoutStatus');
  if (!status) return;
  status.className = `status ${kind || 'neutral'}`;
  status.textContent = message || '';
}

function setBusy(isBusy, message) {
  loading.style.display = isBusy ? 'block' : 'none';
  if (message) loading.textContent = message;
  actionButtons.forEach(button => { button.disabled = Boolean(isBusy); });
  if (isBusy) setScoutStatus('working', message || 'Scout is working...');
}

function isFantasyMode() {
  return mode && mode.value === 'fantasy';
}

function jumpToTop() {
  window.scrollTo({top:0, behavior:'smooth'});
}

function jumpToPrompt() {
  const prompt = document.getElementById('promptDock');
  if (prompt) prompt.scrollIntoView({behavior:'smooth', block:'end'});
}

function persistFantraxFieldsLocally() {
  try {
    const leagueId = document.getElementById('leagueId');
    const leagueSecret = document.getElementById('leagueSecret');
    if (leagueId && leagueId.value) localStorage.setItem('athena.fantrax.league_id', leagueId.value.trim());
    if (leagueSecret && leagueSecret.value) localStorage.setItem('athena.fantrax.personal_profile_secret', leagueSecret.value.trim());
  } catch (err) { console.warn('Scout local credential persistence failed', err); }
}

function restoreFantraxFieldsLocally() {
  try {
    const leagueId = document.getElementById('leagueId');
    const leagueSecret = document.getElementById('leagueSecret');
    const savedLeagueId = localStorage.getItem('athena.fantrax.league_id') || '';
    const savedSecret = localStorage.getItem('athena.fantrax.personal_profile_secret') || '';
    if (leagueId && !leagueId.value && savedLeagueId) leagueId.value = savedLeagueId;
    if (leagueSecret && !leagueSecret.value && savedSecret) leagueSecret.value = savedSecret;
  } catch (err) { console.warn('Scout local credential restore failed', err); }
}

function jumpToFantraxLogin() {
  const panel = document.getElementById('fantraxPanel');
  if (panel) panel.scrollIntoView({behavior:'smooth', block:'start'});
  const leagueId = document.getElementById('leagueId');
  if (leagueId) setTimeout(() => leagueId.focus({preventScroll:true}), 350);
}

function addPendingTurn(label, message) {
  const id = `pending-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
  conversation.insertAdjacentHTML('beforeend', `<div class="pending-card" id="${id}"><strong>${esc(label || 'Scout')}</strong><br>${esc(message || 'Working...')}</div>`);
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({behavior:'smooth', block:'end'});
  return id;
}

function removePendingTurn(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function esc(value) {
  return String(value ?? '').replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));
}


function showSourcePopup(source) {
  const title = source.title || source.label || 'Source evidence';
  const ref = source.rule_reference || source.reference || '';
  const body = source.popup_text || source.rule_text || source.summary || 'No source detail available.';
  const html = `<div class="modal-backdrop" id="sourceModal"><div class="modal-card"><h2>${esc(title)}</h2>${ref ? `<div class="confidence">${esc(ref)}</div>` : ''}<pre>${esc(body)}</pre><div class="modal-actions"><button onclick="closeSourcePopup()">Close</button></div></div></div>`;
  const existing = document.getElementById('sourceModal');
  if (existing) existing.remove();
  document.body.insertAdjacentHTML('beforeend', html);
}

function closeSourcePopup() {
  const modal = document.getElementById('sourceModal');
  if (modal) modal.remove();
}

function renderSourceLinks(answer) {
  const links = Array.isArray(answer.source_links) ? answer.source_links : [];
  if (!links.length) return '';
  window.__athenaSourceLinks = links;
  return `<div class="source-links">${links.map((link, idx) => {
    const label = esc(link.label || link.title || 'Source');
    const ref = link.rule_reference ? '• ' + esc(link.rule_reference) : '';
    const url = String(link.url || '').trim();
    const details = `<button class="source-link" onclick="showSourcePopup(window.__athenaSourceLinks[${idx}])">Details</button>`;
    if (url) {
      return `<span class="source-link-wrap"><a class="source-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${label} ${ref}</a>${details}</span>`;
    }
    return `<button class="source-link" onclick="showSourcePopup(window.__athenaSourceLinks[${idx}])">${label} ${ref}</button>`;
  }).join('')}</div>`;
}

function isDeveloperModeActive() {
  return Boolean(devMode && devMode.checked);
}

function isPublicLikeMode() {
  return !isDeveloperModeActive();
}

function renderAnswer(answer, userText=null) {
  const developerActive = isDeveloperModeActive();
  const developerVisible = developerActive;
  const publicLike = !developerActive;
  const publicText = String(answer.public_comment || '').trim();
  const rawCards = Array.isArray(answer.cards) ? answer.cards : [];
  const answerCards = developerVisible ? rawCards : rawCards.filter(card => {
    const label = String((card && card.label) || '').trim().toLowerCase();
    return label === 'try' || (card && (card.action === 'ask_prompt' || card.prompt));
  });
  window.__athenaCardActions = answerCards;
  const cards = answerCards.map((card, idx) => {
    const label = String((card && card.label) || '');
    const value = String((card && card.value) || '');
    const impliedPrompt = /^try$/i.test(label.trim()) ? value : '';
    if (card && !card.prompt && impliedPrompt) card.prompt = impliedPrompt;
    const actionable = card && (card.prompt || card.action === 'ask_prompt');
    const onclick = actionable ? ` onclick="askCardPrompt(${idx})" role="button" tabindex="0" onkeydown="if(event.key==='Enter'||event.key===' '){askCardPrompt(${idx})}"` : '';
    const cls = actionable ? 'card action-card' : 'card';
    const note = actionable ? '<div class="action-note">Click to continue</div>' : '';
    return `<div class="${cls}"${onclick}><div class="label">${esc(card.label)}</div><div class="value">${esc(card.value)}</div>${note}</div>`;
  }).join('');
  let diagnosticBlock = '';
  let diagnosticLists = false;
  if (developerActive) diagnosticLists = true;
  const facts = diagnosticLists ? (answer.observed_facts || []).map(item => `<li>${esc(item)}</li>`).join('') : '';
  const limits = diagnosticLists ? (answer.known_limitations || []).map(item => `<li>${esc(item)}</li>`).join('') : '';
  const op = answer.operation_result || (answer.developer && answer.developer.operation_result) || null;
  const diag = (developerActive && op) ? `<div class="diag ${op.success ? 'pass' : 'fail'}">
    <div class="row"><strong>Operation:</strong> ${esc(op.operation || '')}</div>
    <div class="row"><strong>Status:</strong> ${esc(op.success ? 'Completed' : 'Failed')}</div>
    <div class="row"><strong>Stage:</strong> ${esc(op.stage || '')}</div>
    <div class="row"><strong>Reason:</strong> ${esc(op.reason || '')}</div>
    <div class="row"><strong>Recommendation:</strong> ${esc(op.recommendation || '')}</div>
  </div>` : '';
  const developer = developerActive ? `<details class="dev"><summary>Developer Mode</summary><pre>${esc(JSON.stringify(answer.developer || {}, null, 2))}</pre></details>` : '';
  const confidence = (developerActive && answer.confidence !== null && answer.confidence !== undefined) ? `<div class="confidence">Confidence: ${esc(answer.confidence)}</div>` : '';
  const natural = publicText || answer.natural_language_response || answer.response_text || answer.scout_message || '';
  const displayText = natural; // compatibility marker: canonical public text selected after diagnostic gating
  const naturalBlock = natural ? `<div class="answer-copy">${esc(natural)}</div>` : '';
  const conclusionText = answer.engine_conclusion || '';
  const conclusionIsRedundant = natural && conclusionText && natural.toLowerCase().includes(String(conclusionText).toLowerCase().slice(0, 120));
  const conclusionBlock = (developerActive && conclusionText && !conclusionIsRedundant) ? `<h3>Engine Conclusion</h3><div>${esc(conclusionText || 'No conclusion available.')}</div>` : '';
  const sourceLinks = renderSourceLinks(answer);
  const rawPayload = answer.raw_reasoning_output || (answer.developer && answer.developer.raw_reasoning_output) || '';
  const rawReasoning = (developerActive && rawPayload) ? `<details class="raw-reasoning"><summary>Developer / Raw Reasoning Output</summary><pre>${esc(rawPayload)}</pre></details>` : '';
  const you = userText ? `<div class="you chat-turn"><strong>You:</strong> ${esc(userText)}</div>` : '';
  conversation.insertAdjacentHTML('beforeend', `${you}<article class="answer chat-turn"><h2>${esc(answer.title || 'Scout response')}</h2>${confidence}${naturalBlock}${(developerActive && cards) ? `<div class="cards">${cards}</div>` : ''}${sourceLinks}${conclusionBlock}${diag}${facts ? `<h3>Observed Facts</h3><ul>${facts}</ul>` : ''}${limits ? `<h3>Known Limitations</h3><ul>${limits}</ul>` : ''}${rawReasoning}${developer}</article>`);
  const last = conversation.lastElementChild;
  if (last) last.scrollIntoView({behavior:'smooth', block:'end'});
}

function setConnectionStatus(kind, message, details=null) {
  const status = document.getElementById('connectionStatus');
  if (!status) return;
  status.className = `status ${kind || 'neutral'}`;
  const detailText = details ? `<br><span class="note">${esc(details)}</span>` : '';
  status.innerHTML = `${esc(message || '')}${detailText}`;
}

async function postJSON(url, payload) {
  try {
    const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload || {})});
    let data = {};
    try { data = await res.json(); } catch (err) { data = {error: 'Server returned a non-JSON response.'}; }
    data.http_status = res.status;
    data.http_ok = res.ok;
    return data;
  } catch (err) {
    return {ok:false, http_ok:false, http_status:0, error: err.message || String(err), message:'Scout could not reach the local Athena server.'};
  }
}

async function askText(text) {
  const cleanText = String(text || '').trim();
  if (!cleanText) return;
  setBusy(true, 'Scout is evaluating your question with Athena...');
  const pendingId = addPendingTurn('Scout', 'Evaluating question, loading available Athena evidence, and preparing a response...');
  const data = await postJSON('/api/ask', {question: cleanText, mode: mode.value});
  removePendingTurn(pendingId);
  setBusy(false);
  if (!data.http_ok || data.error) {
    setScoutStatus('bad', 'Scout request failed.');
    renderAnswer({title:'Scout request failed', confidence:0.1, engine_conclusion:data.error || data.message || 'Request failed.', developer:data}, cleanText);
    return;
  }
  setScoutStatus('good', 'Scout response ready.');
  renderAnswer(data.answer, cleanText);
}

async function askCardPrompt(idx) {
  const card = (window.__athenaCardActions || [])[idx];
  const prompt = card && card.prompt;
  if (!prompt) return;
  const questionEl = document.getElementById('question');
  if (questionEl) questionEl.value = prompt;
  await askText(prompt);
}

async function ask() {
  const questionEl = document.getElementById('question');
  const text = questionEl.value.trim();
  if (!text) return;
  questionEl.value = '';
  await askText(text);
}

async function analyze() {
  setBusy(true, 'Athena is synchronizing available league capabilities...');
  const pendingId = addPendingTurn('Athena', 'Running sync. Optional transaction-market modules may be skipped if browser Cookie auth is unavailable.');
  const data = await postJSON('/api/analyze', {mode: mode.value});
  removePendingTurn(pendingId);
  setBusy(false);
  if ((!data.http_ok || data.error) && !data.answer) {
    setScoutStatus('bad', 'League sync failed.');
    renderAnswer({title:'League sync failed', confidence:0.1, engine_conclusion:data.error || data.message || 'Sync failed.', developer:data}, 'Sync League');
    return;
  }
  const answer = data.answer;
  answer.developer = answer.developer || {};
  answer.developer.pipeline_run = data.pipeline_run || {};
  setScoutStatus('good', answer.title || 'League sync complete.');
  renderAnswer(answer, 'Sync League');
  await loadContext();
}

async function testConnection() {
  if (mode) mode.value = 'fantasy';
  updateProviderVisibility();
  const button = document.getElementById('testBtn');
  const leagueId = document.getElementById('leagueId').value.trim();
  const cookie = document.getElementById('cookie').value.trim();
  const leagueSecretEl = document.getElementById('leagueSecret');
  const leagueSecret = leagueSecretEl ? leagueSecretEl.value.trim() : '';
  persistFantraxFieldsLocally();
  if (!leagueId) {
    setConnectionStatus('bad', 'Fantrax league ID is required.');
    renderAnswer({title:'Fantrax connection failed', confidence:0.1, engine_conclusion:'Fantrax league ID is required.'}, 'Test Fantrax Connection');
    return;
  }
  const previousText = button.textContent;
  button.textContent = 'Testing...';
  setBusy(true, 'Testing Fantrax connection...');
  setConnectionStatus('neutral', 'Testing Fantrax connection...');
  const data = await postJSON('/api/connect/fantrax', {league_id: leagueId, cookie, league_secret: leagueSecret});
  setBusy(false);
  button.textContent = previousText;
  const ok = Boolean(data.ok && data.http_ok !== false);
  const detail = data.warning || data.error || (data.provider_test && data.provider_test.error) || (data.connection && data.connection.error) || '';
  setConnectionStatus(ok ? 'good' : 'bad', data.message || (ok ? 'Fantrax connection succeeded.' : 'Fantrax connection failed.'), detail);
  const observed = data.inferred_context ? Object.entries(data.inferred_context).map(([k,v]) => `${k}: ${v}`) : [];
  if (data.secret_status) {
    observed.push(`secret_present: ${Boolean(data.secret_status.fantrax_cookie_present)}`);
    observed.push(`cookie_parseable: ${Boolean(data.secret_status.fantrax_cookie_parseable)}`);
    observed.push(`cookie_count: ${Number(data.secret_status.fantrax_cookie_count || 0)}`);
    observed.push(`secret_format: ${data.secret_status.fantrax_secret_format || data.secret_status.supplied_secret_format || "unknown"}`);
    observed.push(`league_secret_saved: ${Boolean(data.secret_status.fantrax_league_secret_present || data.secret_status.supplied_league_secret_saved)}`);
    observed.push(`browser_cookie_saved: ${Boolean(data.secret_status.fantrax_cookie_parseable || data.secret_status.supplied_secret_saved)}`);
    observed.push(`secrets_file_exists: ${Boolean(data.secret_status.secrets_file_exists)}`);
  }
  const answer = {
    title: ok ? 'Fantrax connected' : 'Fantrax connection failed',
    confidence: ok ? 0.9 : 0.2,
    engine_conclusion: data.message || (ok ? 'Connection test completed.' : 'Connection failed.'),
    observed_facts: observed,
    known_limitations: ['Scout stores the Fantrax Personal/Profile Secret ID and browser Cookie header separately in Athena\'s persistent local credential store. Personal/Profile Secret ID supports workspace/league access. Browser Cookie header unlocks authenticated transaction sync. Password fields are intentionally not prefilled; saved auth is shown by status, not by revealing values.'],
    developer: data
  };
  renderAnswer(answer, 'Test Fantrax Connection');
  if (mode) mode.value = 'fantasy';
  await loadContext();
  if (mode) mode.value = 'fantasy';
  updateProviderVisibility();
}


async function openFantraxLogin() {
  const leagueId = document.getElementById('leagueId').value.trim();
  const cookie = document.getElementById('cookie').value.trim();
  const leagueSecretEl = document.getElementById('leagueSecret');
  const leagueSecret = leagueSecretEl ? leagueSecretEl.value.trim() : '';
  persistFantraxFieldsLocally();
  setBusy(true, 'Connecting Fantrax and syncing if session auth is available...');
  setConnectionStatus('neutral', 'Opening Fantrax and checking saved authentication...');
  const data = await postJSON('/api/fantrax/connect-and-sync', {league_id: leagueId, league_secret: leagueSecret, cookie});
  setBusy(false);
  const ready = Boolean(data.ok);
  const needsSession = data.status === 'browser_session_required';
  setConnectionStatus(ready ? 'good' : (needsSession ? 'warn' : 'bad'), data.message || 'Fantrax connection workflow completed.', data.next_action || data.known_limitation || '');
  const facts = [];
  if (data.opened && data.opened.url) facts.push(`Opened: ${data.opened.url}`);
  if (data.credential_status) {
    facts.push(`Personal/Profile Secret ID saved: ${Boolean(data.credential_status.fantrax_league_secret_present)}`);
    facts.push(`Browser session ready: ${Boolean(data.credential_status.browser_session_ready || data.credential_status.fantrax_cookie_parseable)}`);
    facts.push(`Cookie count: ${Number(data.credential_status.fantrax_cookie_count || 0)}`);
    facts.push(`Persistent credential store: ${Boolean(data.credential_status.persistent_external_store)}`);
  }
  if (data.sync_result && data.sync_result.summary) {
    facts.push(`Canonical transactions: ${data.sync_result.summary.canonical_transactions || 0}`);
    facts.push(`Managers analyzed: ${data.sync_result.summary.managers_analyzed || 0}`);
  }
  renderAnswer({
    title: ready ? 'Fantrax connected and synced' : (needsSession ? 'Fantrax browser session needed' : 'Fantrax connection workflow stopped'),
    confidence: ready ? 0.92 : (needsSession ? 0.65 : 0.25),
    engine_conclusion: data.message || 'Fantrax connection workflow completed.',
    observed_facts: facts,
    known_limitations: [data.next_action || 'Automatic browser-session capture is not enabled yet.', data.known_limitation || 'Advanced Cookie paste remains available as a validation bridge.'].filter(Boolean),
    developer:data
  }, 'Connect Fantrax & Sync');
  if (ready && data.sync_result) {
    renderAnswer(buildClientSyncAnswer(data.sync_result), 'Sync League');
  }
  await loadContext();
}

function buildClientSyncAnswer(syncResult) {
  const summary = syncResult.summary || {};
  return {
    title:'League sync',
    confidence:0.9,
    engine_conclusion:'Athena synchronized the active Fantrax league using the guided connection workflow.',
    cards:[
      {label:'Transactions', value:summary.canonical_transactions || 0},
      {label:'Asset movements', value:summary.asset_movements || 0},
      {label:'Managers', value:summary.managers_analyzed || 0},
      {label:'Market', value:summary.market_liquidity || 'unknown'}
    ],
    observed_facts:[
      `Sync status: ${syncResult.ok ? 'completed' : 'limited'}.`,
      `Canonical transactions: ${summary.canonical_transactions || 0}.`,
      `Managers analyzed: ${summary.managers_analyzed || 0}.`
    ],
    known_limitations:['Finance page data is not yet synchronized.'],
    developer:syncResult
  };
}

async function exportDebug() {
  const button = document.getElementById('exportBtn');
  const previousText = button.textContent;
  button.textContent = 'Exporting...';
  setBusy(true, 'Creating downloadable debug export...');
  setConnectionStatus('neutral', 'Creating debug export...');
  const data = await postJSON('/api/debug/export', {mode: mode.value});
  setBusy(false);
  button.textContent = previousText;
  if (!data.http_ok || data.error || !data.ok) {
    setConnectionStatus('bad', 'Debug export failed.', data.error || data.message || 'Unknown export error.');
    renderAnswer({title:'Debug export failed', confidence:0.1, engine_conclusion:data.error || data.message || 'Debug export failed.', developer:data}, 'Export Debug');
    return;
  }
  const txtUrl = data.text_download_url || '';
  const jsonUrl = data.json_download_url || '';
  const details = `TXT: ${data.text_filename || data.text_path || 'created'}${jsonUrl ? ' | JSON: ' + (data.json_filename || data.json_path || 'created') : ''}`;
  setConnectionStatus('good', 'Debug export created. Your browser should download the text report.', details);
  if (txtUrl) {
    window.open(txtUrl, '_blank');
  }
  const observed = [
    `TXT export: ${data.text_path || data.text_filename || 'created'}`,
    `JSON export: ${data.json_path || data.json_filename || 'created'}`,
    `Download TXT: ${txtUrl || 'unavailable'}`,
    `Download JSON: ${jsonUrl || 'unavailable'}`,
  ];
  renderAnswer({
    title:'Debug export ready',
    confidence:0.95,
    engine_conclusion:'Scout generated redacted JSON and text debug files under Reports and exposed downloadable local links.',
    observed_facts: observed,
    known_limitations:['Secret values and browser Cookie headers are intentionally omitted from the export.'],
    developer:{
      ok: data.ok,
      json_path: data.json_path,
      text_path: data.text_path,
      json_download_url: data.json_download_url,
      text_download_url: data.text_download_url,
      message: data.message
    }
  }, 'Export Debug');
}


async function exportSessionLog() {
  const button = document.getElementById('sessionLogBtn');
  const previousText = button ? button.textContent : '';
  if (button) button.textContent = 'Exporting...';
  setBusy(true, 'Creating session prompt/response log...');
  const data = await postJSON('/api/session/export', {mode: mode.value});
  setBusy(false);
  if (button) button.textContent = previousText;
  if (!data.http_ok || data.error || !data.ok) {
    renderAnswer({title:'Session log failed', confidence:0.1, engine_conclusion:data.error || data.message || 'Session log export failed.', developer:data}, 'Export Session Log');
    return;
  }
  if (data.text_download_url) window.open(data.text_download_url, '_blank');
  renderAnswer({
    title:'Session log ready',
    confidence:0.95,
    engine_conclusion:'Scout wrote the current session prompt/response log for comparison testing. The files are in Reports and the TXT download should open in a new tab if popups are allowed.',
    observed_facts:[
      `Turns: ${data.turn_count || 0}`,
      `TXT export: ${data.text_path || 'created'}`,
      `JSON export: ${data.json_path || 'created'}`
    ],
    known_limitations:['This is a temporary acceptance-testing log and may be overwritten by the next export.'],
    developer:data
  }, 'Export Session Log');
}

async function loadContext() {
  const res = await fetch('/api/context');
  const data = await res.json();
  const raw = data.raw_status || {};
  const workspace = data.workspace || {};
  const secret = data.secret_status || {};
  const rawPills = Object.entries(raw).map(([name, exists]) => `<span class="pill ${exists ? 'good' : 'warn'}">${exists ? '✓' : '✗'} ${esc(name)}</span>`).join('');
  const publicStatus = data.public_status || {};
  const publicPills = [
    ['Public player profiles', Boolean(publicStatus.public_player_profiles)],
    ['NHL Rules', Boolean(publicStatus.nhl_rules)],
    ['NHL/NHLPA MOU', Boolean(publicStatus.nhl_mou)],
    ['RSS feeds', Boolean(publicStatus.rss_feeds)],
  ].map(([label, exists]) => `<span class="pill ${exists ? 'good' : 'warn'}">${exists ? '✓' : '✗'} ${esc(label)}</span>`).join('');
  const league = workspace.league_id ? `<span class="pill good">League: ${esc(workspace.name || workspace.league_id)}</span>` : `<span class="pill warn">No league connected</span>`;
  const sport = `<span class="pill">Sport: ${esc(workspace.sport || 'unknown')}</span>`;
  const season = `<span class="pill">Season: ${esc(workspace.season || 'unknown')}</span>`;
  const teams = (data.team_names || []).length ? `<span class="pill good">${data.team_names.length} teams loaded</span>` : `<span class="pill warn">No team profiles loaded</span>`;
  const cookieOk = Boolean(secret.fantrax_cookie_parseable);
  const cookiePresent = Boolean(secret.fantrax_cookie_present);
  const leagueSecretSaved = Boolean(secret.fantrax_league_secret_present);
  const authLabel = cookieOk ? 'Browser session detected' : (cookiePresent ? 'Cookie saved but not parseable' : 'Limited mode: no browser session');
  const cookie = `<span class="pill ${cookieOk ? 'good' : 'warn'}">${cookieOk ? '✓' : '✗'} ${esc(authLabel)}</span>`;
  const leagueSecret = `<span class="pill ${leagueSecretSaved ? 'good' : 'warn'}">${leagueSecretSaved ? '✓' : '✗'} Personal/Profile Secret ID ${leagueSecretSaved ? 'saved' : 'not saved'}</span>`;
  if (isFantasyMode()) {
    document.getElementById('context').innerHTML = league + sport + season + cookie + leagueSecret + rawPills + teams;
  } else {
    document.getElementById('context').innerHTML = publicPills;
  }
  const effectiveLeagueId = workspace.effective_league_id || '';
  if (effectiveLeagueId) {
    document.getElementById('leagueId').value = effectiveLeagueId;
  } else if (workspace.league_id && !workspace.league_id_is_placeholder) {
    document.getElementById('leagueId').value = workspace.league_id;
  } else {
    document.getElementById('leagueId').value = '';
  }
  const history = Array.isArray(workspace.operation_history) ? workspace.operation_history : [];
  const historyPanel = document.getElementById('operationHistoryPanel');
  const historyEl = document.getElementById('operationHistory');
  if (history.length && isFantasyMode()) {
    historyPanel.style.display = 'block';
    historyEl.innerHTML = history.slice(0,5).map(item => {
      const cls = item.success ? 'pass' : 'fail';
      const status = item.success ? '✓' : '✗';
      return `<div class="history-item ${cls}">${status} ${esc(item.operation || 'Operation')} — ${esc(item.stage || '')}: ${esc(item.reason || item.summary || '')}</div>`;
    }).join('');
  } else {
    historyPanel.style.display = 'none';
  }
  if (workspace.league_id_is_placeholder && effectiveLeagueId) {
    setConnectionStatus('warn', 'Scout ignored a stale test workspace league ID and prefilled the configured Fantrax league ID instead.', 'Click Test & Save Connection to update the active workspace.');
  } else if (effectiveLeagueId) {
    const authMsg = cookieOk ? 'Browser session detected. Fuller private-league sync should be available.' : 'Limited private-league mode. Scout can use saved public/private outputs, but authenticated transaction sync may be less complete.';
    setConnectionStatus(cookieOk ? 'good' : 'warn', authMsg, 'Saved Personal/Profile Secret ID and browser auth are shown by status; password fields are intentionally not prefilled.');
  }
  updateProviderVisibility();
}


function updateProviderVisibility() {
  const panel = document.getElementById('fantraxPanel');
  const syncButton = document.getElementById('analyzeBtn');
  const historyPanel = document.getElementById('operationHistoryPanel');
  const selected = mode ? mode.value : 'public';
  const fantasySelected = selected === 'fantasy';
  if (panel) {
    panel.style.display = fantasySelected ? 'block' : 'none';
    if (fantasySelected) { panel.setAttribute('open', 'open'); }
    else { panel.removeAttribute('open'); }
  }
  if (syncButton) {
    syncButton.style.display = fantasySelected ? 'inline-block' : 'none';
  }
  if (historyPanel && !fantasySelected) {
    historyPanel.style.display = 'none';
  } else if (historyPanel && fantasySelected) {
    const historyEl = document.getElementById('operationHistory');
    if (historyEl && historyEl.innerHTML.trim()) historyPanel.style.display = 'block';
  }
  if (selected === 'public') {
    setConnectionStatus('neutral', 'Public Sports selected. Fantrax login, league sync, and operation history are hidden because private league data is not needed.');
  } else {
    setConnectionStatus('neutral', 'Fantasy League selected. Fantrax login and sync controls are available.');
    jumpToFantraxLogin();
  }
}

function bindButton(id, handler) {
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`Scout UI: missing button ${id}`);
    return;
  }
  el.addEventListener('click', async e => {
    e.preventDefault();
    try {
      await handler();
    } catch (err) {
      console.error(`Scout UI action failed: ${id}`, err);
      setBusy(false);
      setScoutStatus('bad', `Scout UI action failed: ${err.message || err}`);
      renderAnswer({
        title:'Scout UI action failed',
        confidence:0.1,
        engine_conclusion:err.message || String(err),
        developer:{button:id, error:String(err), stack:err.stack || ''}
      }, id);
    }
  });
}

if (fantraxCredentialForm) {
  fantraxCredentialForm.addEventListener('submit', async e => {
    e.preventDefault();
    if (mode) mode.value = 'fantasy';
    try {
      await testConnection();
    } catch (err) {
      console.error('Fantrax test failed', err);
      setBusy(false);
      setConnectionStatus('bad', `Fantrax test failed: ${err.message || err}`);
    }
  });
}

bindButton('askBtn', ask);
bindButton('analyzeBtn', analyze);
bindButton('exportBtn', exportDebug);
bindButton('sessionLogBtn', exportSessionLog);
bindButton('openFantraxBtn', openFantraxLogin);
bindButton('jumpTopBtn', jumpToTop);
bindButton('jumpBottomBtn', jumpToPrompt);
const questionInput = document.getElementById('question');
if (questionInput) {
  questionInput.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      ask().catch(err => {
        console.error('Scout ask failed', err);
        setBusy(false);
        setScoutStatus('bad', `Scout ask failed: ${err.message || err}`);
      });
    }
  });
}
if (mode) {
  mode.addEventListener('change', updateProviderVisibility);
  updateProviderVisibility();
}
restoreFantraxFieldsLocally();
loadContext().catch(err => {
  console.error('Scout context load failed', err);
  setScoutStatus('warn', `Scout loaded, but context failed: ${err.message || err}`);
});
</script>
</body>
</html>'''




def build_sync_answer(sync_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Athena sync result into Scout's simple answer card format."""
    summary = sync_result.get("summary") if isinstance(sync_result, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    ok = bool(sync_result.get("ok"))
    steps = sync_result.get("completed_steps") if isinstance(sync_result.get("completed_steps"), list) else []
    step_labels = [str(step.get("label")) for step in steps if isinstance(step, dict) and step.get("label")]
    operation_result = sync_result.get("operation_result") if isinstance(sync_result.get("operation_result"), dict) else {}
    capability_dash = sync_result.get("capability_dashboard") if isinstance(sync_result.get("capability_dashboard"), dict) else capability_dashboard(assess_capabilities("Fantrax"))
    capability_lines = capability_dash.get("lines") if isinstance(capability_dash.get("lines"), list) else []

    if ok:
        conclusion = operation_result.get("summary") or "Athena synchronized the active league workspace and refreshed the canonical knowledge and intelligence outputs."
        operation_warnings = operation_result.get("warnings") if isinstance(operation_result.get("warnings"), list) else []
        limitations = [str(item) for item in operation_warnings] or [
            "Finance page data is not yet synchronized; financial totals remain outside the authoritative Athena sync pipeline.",
            "Relationship graph and historical player trends are not yet available.",
            "Natural-language answers are deterministic templates in this alpha, not freeform AI reasoning.",
        ]
        confidence = operation_result.get("confidence", 0.86)
    else:
        stage = operation_result.get("stage") or (sync_result.get("failed_step") or {}).get("label") or "unknown"
        reason = operation_result.get("reason") or sync_result.get("error") or "Unknown sync error."
        recommendation = operation_result.get("recommendation") or "Enable Developer Mode and inspect the sync result."
        conclusion = f"Athena could not complete league synchronization. Failed stage: {stage}. Reason: {reason} Recommendation: {recommendation}"
        limitations = [reason]
        confidence = operation_result.get("confidence", 0.1)

    return {
        "title": ("League sync — partial" if ok and (operation_result.get("warnings") or capability_dash.get("status") == "partial") else "League sync") if ok else "League sync failed",
        "confidence": confidence,
        "cards": [
            {"label": "Available capabilities", "value": capability_dash.get("available_count", summary.get("available_capabilities", 0))},
            {"label": "Limited capabilities", "value": capability_dash.get("limited_count", summary.get("limited_capabilities", 0))},
            {"label": "Transactions", "value": summary.get("canonical_transactions", 0)},
            {"label": "Market", "value": summary.get("market_liquidity", "unknown")},
        ],
        "engine_conclusion": conclusion,
        "operation_result": operation_result,
        "observed_facts": [
            f"Sync status: {'completed' if ok else 'failed'}.",
            f"Current stage: {operation_result.get('stage', 'unknown')}.",
            f"Completed/skipped steps: {len(steps)}.",
            f"Canonical transactions: {summary.get('canonical_transactions', 0)}.",
            f"Asset movements: {summary.get('asset_movements', 0)}.",
            f"Managers analyzed: {summary.get('managers_analyzed', 0)}.",
            f"Market liquidity: {summary.get('market_liquidity', 'unknown')}.",
            f"Knowledge readiness: {summary.get('knowledge_readiness', 'unknown')}.",
        ] + [f"Capability: {line}" for line in capability_lines[:8]] + (["Pipeline: " + " → ".join(step_labels)] if step_labels else []),
        "known_limitations": limitations,
        "developer": {**sync_result, "capability_dashboard": capability_dash},
    }


class ScoutRequestHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for Scout Alpha."""

    def log_message(self, format: str, *args: Any) -> None:  # keep Spyder output clean
        return

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler naming
        path = urlparse(self.path).path
        if path == "/":
            _html_response(self, INDEX_HTML.replace("{SCOUT_VERSION}", SCOUT_VERSION))
            return
        if path == "/api/version":
            _json_response(self, {
                "version": SCOUT_VERSION,
                "app": "Scout",
                "engine": "Athena",
                "project_root": str(PROJECT_ROOT),
                "host": HOST,
                "port": PORT,
            })
            return
        if path == "/api/health":
            _json_response(self, {
                "ok": True,
                "version": SCOUT_VERSION,
                "athena": Athena.status().get("athena_version"),
            })
            return
        if path == "/api/context":
            _json_response(self, _context_payload())
            return
        if path == "/api/debug/download":
            query = parse_qs(urlparse(self.path).query)
            filename = Path(str((query.get("file") or [""])[0])).name
            valid_debug = filename.startswith("scout_debug_export_") and (filename.endswith(".txt") or filename.endswith(".json"))
            valid_session = filename in {"scout_session_log.txt", "scout_session_log.json"}
            if not (valid_debug or valid_session):
                _json_response(self, {"error": "Invalid debug/session export filename."}, HTTPStatus.BAD_REQUEST)
                return
            file_path = PROJECT_ROOT / "Reports" / filename
            if not file_path.exists() or not file_path.is_file():
                _json_response(self, {"error": "Debug export file not found."}, HTTPStatus.NOT_FOUND)
                return
            content_type = "text/plain; charset=utf-8" if filename.endswith(".txt") else "application/json; charset=utf-8"
            body = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/capabilities":
            _json_response(self, capability_dashboard(assess_capabilities("Fantrax")))
            return
        if path == "/api/graph/evidence-chain":
            query = parse_qs(urlparse(self.path).query)
            entity_id = str((query.get("entity_id") or [""])[0]).strip()
            max_depth_raw = str((query.get("max_depth") or ["2"])[0]).strip()
            try:
                max_depth = max(1, min(4, int(max_depth_raw)))
            except ValueError:
                max_depth = 2
            if not entity_id:
                graph = load_graph(PROJECT_ROOT)
                player_ids = sorted([nid for nid, node in graph.nodes.items() if node.type == "player"])
                entity_id = player_ids[0] if player_ids else ""
            if not entity_id:
                _json_response(self, {"status": "not_found", "message": "No graph entity is available."}, HTTPStatus.NOT_FOUND)
                return
            _json_response(self, build_evidence_chain(entity_id, max_depth=max_depth, project_root=PROJECT_ROOT))
            return
        if path == "/api/graph/timeline":
            query = parse_qs(urlparse(self.path).query)
            entity_id = str((query.get("entity_id") or [""])[0]).strip()
            limit_raw = str((query.get("limit") or ["20"])[0]).strip()
            try:
                limit = max(1, min(100, int(limit_raw)))
            except ValueError:
                limit = 20
            if not entity_id:
                graph = load_graph(PROJECT_ROOT)
                player_ids = sorted([nid for nid, node in graph.nodes.items() if node.type == "player"])
                entity_id = player_ids[0] if player_ids else ""
            if not entity_id:
                _json_response(self, {"status": "not_found", "message": "No graph entity is available."}, HTTPStatus.NOT_FOUND)
                return
            _json_response(self, timeline_for_entity(entity_id, project_root=PROJECT_ROOT, limit=limit))
            return
        if path == "/api/graph/reasoning":
            query = parse_qs(urlparse(self.path).query)
            entity_id = str((query.get("entity_id") or [""])[0]).strip()
            context_profile = str((query.get("context_profile") or ["fantasy"])[0]).strip() or "fantasy"
            traversal = str((query.get("traversal") or ["weighted"])[0]).strip() or "weighted"
            focus_raw = str((query.get("focus") or [""])[0]).strip()
            focus = [item.strip() for item in focus_raw.split(",") if item.strip()]
            max_depth_raw = str((query.get("max_depth") or ["3"])[0]).strip()
            try:
                max_depth = max(1, min(5, int(max_depth_raw)))
            except ValueError:
                max_depth = 3
            if not entity_id:
                graph = load_graph(PROJECT_ROOT)
                player_ids = sorted([nid for nid, node in graph.nodes.items() if node.type == "player"])
                entity_id = player_ids[0] if player_ids else ""
            if not entity_id:
                _json_response(self, {"status": "not_found", "message": "No graph entity is available."}, HTTPStatus.NOT_FOUND)
                return
            _json_response(self, build_reasoning_package(entity_id, context_profile=context_profile, focus=focus, max_depth=max_depth, traversal=traversal, project_root=PROJECT_ROOT))
            return
        _json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler naming
        global LATEST_OPERATION, LATEST_ANSWER
        path = urlparse(self.path).path
        try:
            if path == "/api/connect/fantrax":
                body = _read_json_body(self)
                result = test_fantrax_connection(str(body.get("league_id") or ""), str(body.get("cookie") or ""), str(body.get("league_secret") or ""))
                LATEST_OPERATION = {"operation": "Test Fantrax Connection", "result": result}
                LATEST_ANSWER = {}
                _json_response(self, result, 200 if result.get("ok") else 400)
                return
            if path == "/api/ask":
                body = _read_json_body(self)
                ctx = load_context()
                question_text = str(body.get("question") or "")
                selected_mode = str(body.get("mode") or "fantasy")
                answer = route_question(question_text, ctx, mode=selected_mode)
                LATEST_ANSWER = {"question": question_text, "answer": answer}
                _record_session_turn(question_text, selected_mode, answer)
                _json_response(self, {"answer": answer})
                return
            if path in {"/api/sync", "/api/analyze"}:
                body = _read_json_body(self)
                selected_mode = str(body.get("mode") or "fantasy")
                if selected_mode == "public":
                    answer = route_question("public sports overview", load_context(), mode="public")
                    _json_response(self, {"sync": {"completed_steps": [], "mode": "public", "ok": True}, "answer": answer})
                    return
                sync_result = Athena.sync(mode="fantasy_league", provider="Fantrax", fetch=True)
                answer = build_sync_answer(sync_result)
                LATEST_OPERATION = sync_result.get("operation_result") if isinstance(sync_result, dict) else {}
                LATEST_ANSWER = {"question": "Sync League", "answer": answer}
                _json_response(self, {"sync": sync_result, "answer": answer}, 200)
                return
            if path == "/api/fantrax/connect-and-sync":
                body = _read_json_body(self)
                result = guided_connect_and_sync(
                    league_id=str(body.get("league_id") or ""),
                    league_secret=str(body.get("league_secret") or ""),
                    cookie_header=str(body.get("cookie") or ""),
                    open_browser=True,
                    run_sync=True,
                )
                LATEST_OPERATION = {"operation": "Connect Fantrax & Sync", "result": result}
                _json_response(self, result, 200 if result.get("ok") else 200)
                return
            if path == "/api/fantrax/open-login":
                body = _read_json_body(self)
                result = open_fantrax_login(str(body.get("league_id") or ""))
                _json_response(self, result, 200 if result.get("ok") else 500)
                return
            if path == "/api/session/export":
                result = _write_session_log()
                _json_response(self, result, 200)
                return
            if path == "/api/debug/export":
                result = write_debug_export(source="Scout", latest_operation=LATEST_OPERATION, latest_answer=LATEST_ANSWER)
                if result.get("ok"):
                    json_name = Path(str(result.get("json_path") or "")).name
                    text_name = Path(str(result.get("text_path") or "")).name
                    response = {
                        "ok": True,
                        "message": "Debug export created.",
                        "json_path": result.get("json_path"),
                        "text_path": result.get("text_path"),
                        "json_filename": json_name,
                        "text_filename": text_name,
                        "json_download_url": f"/api/debug/download?file={json_name}",
                        "text_download_url": f"/api/debug/download?file={text_name}",
                    }
                    _json_response(self, response, 200)
                else:
                    _json_response(self, result, 500)
                return
            _json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:  # visible local alpha diagnostics
            _json_response(self, {"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


class ScoutHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def create_server(host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    return ScoutHTTPServer((host, port), ScoutRequestHandler)


def serve(host: str = HOST, port: int = PORT) -> None:
    server = create_server(host, port)
    print(f"Scout Alpha {SCOUT_VERSION} running at http://{host}:{port}")
    print("Press Ctrl+C in this console to stop Scout.")
    server.serve_forever()


if __name__ == "__main__":
    serve()

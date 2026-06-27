
const conversation = document.getElementById('conversation');
const loading = document.getElementById('loading');
const devMode = document.getElementById('devMode');
const mode = document.getElementById('mode');
const actionButtons = ['askBtn','analyzeBtn','testBtn','exportBtn','openFantraxBtn'].map(id => document.getElementById(id)).filter(Boolean);

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

function renderAnswer(answer, userText=null) {
  const cards = (answer.cards || []).map(card => `<div class="card"><div class="label">${esc(card.label)}</div><div class="value">${esc(card.value)}</div></div>`).join('');
  const developerVisible = Boolean(devMode && devMode.checked);
  const diagnosticLists = developerVisible;
  const facts = diagnosticLists ? (answer.observed_facts || []).map(item => `<li>${esc(item)}</li>`).join('') : '';
  const limits = diagnosticLists ? (answer.known_limitations || []).map(item => `<li>${esc(item)}</li>`).join('') : '';
  const op = answer.operation_result || (answer.developer && answer.developer.operation_result) || null;
  const diag = op ? `<div class="diag ${op.success ? 'pass' : 'fail'}">
    <div class="row"><strong>Operation:</strong> ${esc(op.operation || '')}</div>
    <div class="row"><strong>Status:</strong> ${esc(op.success ? 'Completed' : 'Failed')}</div>
    <div class="row"><strong>Stage:</strong> ${esc(op.stage || '')}</div>
    <div class="row"><strong>Reason:</strong> ${esc(op.reason || '')}</div>
    <div class="row"><strong>Recommendation:</strong> ${esc(op.recommendation || '')}</div>
  </div>` : '';
  const developer = developerVisible ? `<details class="dev"><summary>Developer Mode</summary><pre>${esc(JSON.stringify(answer.developer || {}, null, 2))}</pre></details>` : '';
  const confidence = (developerVisible && answer.confidence !== null && answer.confidence !== undefined) ? `<div class="confidence">Confidence: ${esc(answer.confidence)}</div>` : '';
  const natural = answer.public_comment || answer.natural_language_response || answer.response_text || answer.scout_message || '';
  const conclusionText = answer.engine_conclusion || '';
  const naturalBlock = natural ? `<div class="answer-copy">${esc(natural)}</div>` : '';
  const you = userText ? `<div class="you chat-turn"><strong>You:</strong> ${esc(userText)}</div>` : '';
  conversation.insertAdjacentHTML('beforeend', `${you}<article class="answer chat-turn"><h2>${esc(answer.title || 'Scout response')}</h2>${confidence}${naturalBlock}${(developerVisible && cards) ? `<div class="cards">${cards}</div>` : ''}${developerVisible && conclusionText ? `<h3>Engine Conclusion</h3><div>${esc(conclusionText || 'No conclusion available.')}</div>` : ''}${diag}${facts ? `<h3>Observed Facts</h3><ul>${facts}</ul>` : ''}${limits ? `<h3>Known Limitations</h3><ul>${limits}</ul>` : ''}${developer}</article>`);
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

async function ask() {
  const questionEl = document.getElementById('question');
  const text = questionEl.value.trim();
  if (!text) return;
  questionEl.value = '';
  setBusy(true, 'Scout is evaluating your question with Athena...');
  const pendingId = addPendingTurn('Scout', 'Evaluating question, loading available Athena evidence, and preparing a response...');
  const data = await postJSON('/api/ask', {question: text, mode: mode.value});
  removePendingTurn(pendingId);
  setBusy(false);
  if (!data.http_ok || data.error) {
    setScoutStatus('bad', 'Scout request failed.');
    renderAnswer({title:'Scout request failed', confidence:0.1, engine_conclusion:data.error || data.message || 'Request failed.', developer:data}, text);
    return;
  }
  setScoutStatus('good', 'Scout response ready.');
  renderAnswer(data.answer, text);
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
  const button = document.getElementById('testBtn');
  const leagueId = document.getElementById('leagueId').value.trim();
  const cookie = document.getElementById('cookie').value.trim();
  const leagueSecretEl = document.getElementById('leagueSecret');
  const leagueSecret = leagueSecretEl ? leagueSecretEl.value.trim() : '';
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
  await loadContext();
}


async function openFantraxLogin() {
  const leagueId = document.getElementById('leagueId').value.trim();
  const cookie = document.getElementById('cookie').value.trim();
  const leagueSecretEl = document.getElementById('leagueSecret');
  const leagueSecret = leagueSecretEl ? leagueSecretEl.value.trim() : '';
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

async function loadContext() {
  const res = await fetch('/api/context');
  const data = await res.json();
  const raw = data.raw_status || {};
  const workspace = data.workspace || {};
  const secret = data.secret_status || {};
  const rawPills = Object.entries(raw).map(([name, exists]) => `<span class="pill ${exists ? 'good' : 'warn'}">${exists ? '✓' : '✗'} ${esc(name)}</span>`).join('');
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
  document.getElementById('context').innerHTML = league + sport + season + cookie + leagueSecret + rawPills + teams;
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
  if (history.length) {
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
  if (selected === 'public') {
    setConnectionStatus('neutral', 'Public Sports selected. Fantrax login and league sync are hidden because private league data is not needed.');
  } else {
    setConnectionStatus('neutral', 'Fantasy League selected. Fantrax controls are available. Use Save / Test Connection for credentials and Sync League for data refresh.');
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

bindButton('askBtn', ask);
bindButton('analyzeBtn', analyze);
bindButton('testBtn', testConnection);
bindButton('exportBtn', exportDebug);
bindButton('openFantraxBtn', openFantraxLogin);
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
loadContext().catch(err => {
  console.error('Scout context load failed', err);
  setScoutStatus('warn', `Scout loaded, but context failed: ${err.message || err}`);
});

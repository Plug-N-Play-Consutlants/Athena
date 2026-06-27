/*
Scout UI Action Repair

Loaded by app.py patch or paste-in fallback. This script binds Scout controls
without depending on inline onclick handlers or fragile script order.
*/
(function () {
  function $(id) { return document.getElementById(id); }

  function setStatus(message, isError) {
    var el = $("status") || $("scout-status") || $("result") || $("answer");
    if (!el) return;
    if (el.tagName && el.tagName.toLowerCase() === "textarea") {
      el.value = message;
    } else {
      el.textContent = message;
    }
    if (isError) el.classList && el.classList.add("error");
  }

  async function postJSON(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload || {})
    });
    const text = await response.text();
    let data;
    try { data = JSON.parse(text); } catch (e) { data = {raw: text}; }
    if (!response.ok) throw new Error(data.error || data.message || text || ("HTTP " + response.status));
    return data;
  }

  function renderAnswer(data) {
    var target = $("answer") || $("response") || $("result") || $("output");
    if (!target) {
      alert(JSON.stringify(data, null, 2));
      return;
    }
    var text = data.natural_language_response || data.engine_conclusion || data.answer || data.raw || JSON.stringify(data, null, 2);
    if (target.tagName && target.tagName.toLowerCase() === "textarea") {
      target.value = text;
    } else {
      target.textContent = text;
    }
  }

  async function askScout() {
    var q = $("question");
    var question = q ? q.value.trim() : "";
    if (!question) {
      setStatus("Enter a question for Scout.", true);
      return;
    }
    setStatus("Scout is thinking...", false);
    try {
      var data = await postJSON("/api/ask", {question: question});
      renderAnswer(data);
      setStatus("Done.", false);
    } catch (err) {
      setStatus("Scout request failed: " + err.message, true);
      console.error(err);
    }
  }

  async function saveCredentials() {
    var league = $("league_secret") || $("fantrax_league_secret") || $("leagueSecret");
    var cookie = $("cookie_header") || $("fantrax_cookie") || $("cookieHeader");
    setStatus("Saving credentials...", false);
    try {
      var data = await postJSON("/api/credentials", {
        league_secret: league ? league.value : "",
        cookie_header: cookie ? cookie.value : ""
      });
      setStatus("Credentials saved. Cookie count: " + (data.fantrax_cookie_count || 0), false);
    } catch (err) {
      setStatus("Credential save failed: " + err.message, true);
      console.error(err);
    }
  }

  function bind() {
    var askBtn = $("ask-button") || $("askBtn") || $("submit-question") || $("submit");
    if (askBtn) askBtn.addEventListener("click", function (e) { e.preventDefault(); askScout(); });

    var form = $("question-form") || $("ask-form") || ( $("question") ? $("question").closest("form") : null );
    if (form) form.addEventListener("submit", function (e) { e.preventDefault(); askScout(); });

    var q = $("question");
    if (q) q.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        askScout();
      }
    });

    var saveBtn = $("save-credentials") || $("saveCredentials") || $("save-auth") || $("saveAuth");
    if (saveBtn) saveBtn.addEventListener("click", function (e) { e.preventDefault(); saveCredentials(); });

    window.ScoutUIRepair = {
      askScout: askScout,
      saveCredentials: saveCredentials,
      bound: true
    };
    console.log("Scout UI Action Repair bound.");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();

import sys, tempfile, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import Scout.app as app
with tempfile.TemporaryDirectory() as td:
    app.SESSION_JOURNAL=Path(td)/"journal.jsonl"
    app.PROJECT_ROOT=Path(td)
    app.SESSION_TRANSCRIPT.clear()
    assert app._write_session_log()["ok"] is False
    n=app._record_session_turn("Question?", "fantasy", {"title":"Test", "observed_facts":["schema available"]})
    assert app._record_user_visible_turn(n,"Rendered answer")
    app.SESSION_TRANSCRIPT.clear()  # simulated server-memory loss
    result=app._write_session_log()
    assert result["ok"] and result["turn_count"]==1, result
    assert "Rendered answer" in Path(result["text_path"]).read_text()
    assert "schema available" in Path(result["text_path"]).read_text()
    assert "scout_session_log_" in result["text_download_url"]
    assert result["text_path"] != app._write_session_log()["text_path"]
print("[PASS] durable session export, empty rejection, unique filenames")

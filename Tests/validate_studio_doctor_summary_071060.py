"""D6: startup Doctor reports actions accurately and never applies cleanup."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from Tools.repository_safe_cleanup import CleanupCandidate, CleanupReport, run_cleanup
from Tools.studio_doctor_summary import format_doctor_summary


def check(ok, label):
    assert ok, label
    print("[PASS]", label)


def report(applied=False):
    return CleanupReport("0.7.10.6.0", "now", "repo", applied,
        [CleanupCandidate("cache", "runtime_dir", "cache"), CleanupCandidate("legacy", "legacy_patch", "review", "review")],
        ["cache"] if applied else [], [],
        ["review-only candidates remain"], ["locked.tmp"] if applied else [], "report.json")

obs = format_doctor_summary(report())
check(any("Reviewed: 2" in x and "Review-only: 1" in x for x in obs), "candidate_counts")
check(any("Removed: 0" in x for x in obs) and any("No files changed" in x for x in obs), "observation_not_misreported_as_cleanup")
check(any("[REVIEW] legacy" in x for x in obs), "review_items_listed")
applied = format_doctor_summary(report(True))
check(any("[REMOVED] cache" in x for x in applied) and any("[SKIPPED] locked.tmp" in x for x in applied), "actual_actions_reported")
check(any("Result: WARN" in x for x in applied), "locked_files_warning")
with TemporaryDirectory() as d:
    root = Path(d)
    (root / "Core").mkdir()
    (root / "Core/version.py").write_text("ATHENA_VERSION='0.7.10.6.0'\n")
    (root / "old.patch").write_text("do not remove")
    with patch("Tools.repository_safe_cleanup._current_version", return_value="0.7.10.6.0"):
        observed = run_cleanup(root, apply=False)
    check((root / "old.patch").exists() and not observed.applied and not observed.removed, "startup_doctor_does_not_mutate")
    check(any("old.patch" in x for x in format_doctor_summary(observed)), "real_doctor_observation_visible")
source = (ROOT / "Tools/athena_studio.py").read_text(encoding="utf-8")
start = source.split("    def _startup_cleanup_observation(self)",1)[1].split("    def restart_studio(self)",1)[0]
check("format_doctor_summary(report)" in start and "run_cleanup(PROJECT_ROOT, apply=False)" in start, "studio_startup_wiring")
print("Overall status: PASS")

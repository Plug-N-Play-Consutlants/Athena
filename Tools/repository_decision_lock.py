"""Repository cleanup decision lock for AthenaEngine.

This module is intentionally read-only. It consumes the shim/duplicate review
report, locks the safe near-term repository cleanup decision, and writes a
Claude/auditor-ready consensus brief without removing, renaming, or rewriting
repository files.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_DECISION_LOCK_VERSION = "0.5.6.2.5"


@dataclass(frozen=True)
class ShimDecision:
    path: str
    target_module: str
    review_classification: str
    reference_count: int
    decision: str
    rationale: str
    next_action: str


@dataclass(frozen=True)
class DuplicateDecision:
    basename: str
    owners: list[str]
    location_count: int
    review_classification: str
    decision: str
    rationale: str
    next_action: str


@dataclass(frozen=True)
class RepositoryDecisionLockReport:
    version: str
    generated_at: str
    project_root: str
    status: str
    source_review_report: str
    summary: dict[str, Any]
    shim_decisions: list[ShimDecision] = field(default_factory=list)
    duplicate_decisions: list[DuplicateDecision] = field(default_factory=list)
    auditor_brief: str = ""
    report_paths: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["shim_decisions"] = [asdict(item) for item in self.shim_decisions]
        payload["duplicate_decisions"] = [asdict(item) for item in self.duplicate_decisions]
        return payload


def project_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_or_create_review(root: Path) -> tuple[dict[str, Any], Path]:
    latest = root / "Reports" / "repository_review" / "repository_review_latest.json"
    if not latest.exists():
        from Tools.repository_review import write_repository_review_reports
        write_repository_review_reports(root)
    if not latest.exists():
        raise FileNotFoundError(f"Repository review report not found: {latest}")
    return json.loads(latest.read_text(encoding="utf-8")), latest


def _shim_decision(item: dict[str, Any]) -> ShimDecision:
    refs = item.get("referenced_by") or []
    review_classification = str(item.get("classification", "unknown"))
    path = str(item.get("path", "unknown"))
    target = str(item.get("target_module", "unknown"))
    if refs or review_classification == "keep":
        return ShimDecision(
            path=path,
            target_module=target,
            review_classification=review_classification,
            reference_count=len(refs),
            decision="accepted keep",
            rationale="The shim is still referenced by repository code, so removal would create avoidable import risk.",
            next_action="Migrate callers to the canonical Athena package first; do not delete this shim in the cleanup pass.",
        )
    if review_classification == "archive candidate":
        return ShimDecision(
            path=path,
            target_module=target,
            review_classification=review_classification,
            reference_count=len(refs),
            decision="defer archive",
            rationale="The review found no active references, but compatibility shims should survive one decision cycle before removal.",
            next_action="Archive only after a follow-up import scan confirms no external or internal callers depend on the shim.",
        )
    return ShimDecision(
        path=path,
        target_module=target,
        review_classification=review_classification,
        reference_count=len(refs),
        decision="manual review required",
        rationale="The review could not prove this shim is safe or unsafe.",
        next_action="Inspect imports and runtime entrypoints before any repository mutation.",
    )


def _duplicate_decision(item: dict[str, Any]) -> DuplicateDecision:
    classification = str(item.get("classification", "unknown"))
    basename = str(item.get("basename", "unknown"))
    owners = list(item.get("package_owners") or [])
    locations = list(item.get("locations") or [])
    if classification == "intentional domain-local":
        decision = "accepted intentional"
        rationale = "The duplicate basename is a normal Python/domain-local convention and should not be renamed."
        next_action = "Document as an accepted repository warning."
    elif classification == "cleanup candidate":
        decision = "candidate for targeted review"
        rationale = "The duplicate is contained enough to review for stale or superseded files, but this build does not mutate files."
        next_action = "Open the listed locations, confirm ownership, then decide whether to consolidate, rename, or document as intentional."
    elif classification == "ambiguous":
        decision = "investigation required"
        rationale = "The duplicate crosses package boundaries or could confuse imports, so automated cleanup is unsafe."
        next_action = "Perform import-owner review and classify as accepted, rename candidate, or stale artifact before any rename/removal."
    else:
        decision = "manual review required"
        rationale = "The review classification is unknown."
        next_action = "Inspect manually before deciding."
    return DuplicateDecision(
        basename=basename,
        owners=owners,
        location_count=len(locations),
        review_classification=classification,
        decision=decision,
        rationale=rationale,
        next_action=next_action,
    )


def _counts(items: list[Any], attr: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[getattr(item, attr)] += 1
    return dict(sorted(counts.items()))


def _render_markdown(report: RepositoryDecisionLockReport) -> str:
    lines = [
        "# AthenaEngine Repository Decision Lock",
        "",
        f"Version: {report.version}",
        f"Generated: {report.generated_at}",
        f"Status: {report.status.upper()}",
        f"Source review: `{report.source_review_report}`",
        "",
        "## Locked Decisions",
        "",
        f"- Root shims reviewed: {report.summary.get('shim_count')}",
        f"- Shim decisions: {report.summary.get('shim_decisions')}",
        f"- Duplicate basename groups reviewed: {report.summary.get('duplicate_count')}",
        f"- Duplicate decisions: {report.summary.get('duplicate_decisions')}",
        "",
        "## Shim Decisions",
        "",
        "| Shim | Target | References | Decision | Next Action |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for item in report.shim_decisions:
        lines.append(f"| `{item.path}` | `{item.target_module}` | {item.reference_count} | {item.decision} | {item.next_action} |")
    lines.extend(["", "## Duplicate Basename Decisions", "", "| Basename | Owners | Count | Review | Decision | Next Action |", "| --- | --- | ---: | --- | --- | --- |"])
    for item in report.duplicate_decisions:
        owners = ", ".join(item.owners)
        lines.append(f"| `{item.basename}` | {owners} | {item.location_count} | {item.review_classification} | {item.decision} | {item.next_action} |")
    lines.extend(["", "## Auditor Brief", "", report.auditor_brief, ""])
    return "\n".join(lines)


def _render_auditor_brief(report: RepositoryDecisionLockReport, review: dict[str, Any]) -> str:
    cleanup_candidates = [d for d in report.duplicate_decisions if d.review_classification == "cleanup candidate"]
    ambiguous = [d for d in report.duplicate_decisions if d.review_classification == "ambiguous"]
    return "\n".join([
        "AthenaEngine repository cleanup consensus brief:",
        "",
        "1. All root-level compatibility shims are currently locked as accepted keep because the review found active repository references. Do not recommend deleting shims until imports are migrated to canonical package paths.",
        f"2. Duplicate basename groups total {report.summary.get('duplicate_count')}. The decision lock separates accepted domain-local duplicates from cleanup candidates and ambiguous cross-package names.",
        f"3. Cleanup candidates for human review: {', '.join(d.basename for d in cleanup_candidates) or 'none'}.",
        f"4. Ambiguous duplicate basenames requiring import-owner review: {', '.join(d.basename for d in ambiguous) or 'none'}.",
        "5. This lock is intentionally read-only: no removals, renames, import rewrites, or Scout behavior changes were performed.",
        "",
        "Recommended external audit task: independently inspect the shim references and duplicate basename groups, then classify each as accepted, stale cleanup, or safe rename. Return only actions that preserve the Studio-first workflow and avoid runtime behavior changes.",
    ])


def build_repository_decision_lock(project_root: Path | str | None = None) -> RepositoryDecisionLockReport:
    root = Path(project_root or project_root_from_here()).resolve()
    review, source = _load_or_create_review(root)
    shim_decisions = [_shim_decision(item) for item in review.get("shims", [])]
    duplicate_decisions = [_duplicate_decision(item) for item in review.get("duplicates", [])]
    summary = {
        "shim_count": len(shim_decisions),
        "duplicate_count": len(duplicate_decisions),
        "shim_decisions": _counts(shim_decisions, "decision"),
        "duplicate_decisions": _counts(duplicate_decisions, "decision"),
        "safe_shim_removals": [item.path for item in shim_decisions if item.decision not in {"accepted keep", "defer archive"}],
        "cleanup_candidate_duplicates": [item.basename for item in duplicate_decisions if item.review_classification == "cleanup candidate"],
        "ambiguous_duplicates": [item.basename for item in duplicate_decisions if item.review_classification == "ambiguous"],
    }
    report = RepositoryDecisionLockReport(
        version=REPOSITORY_DECISION_LOCK_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        project_root=str(root),
        status="pass",
        source_review_report=str(source),
        summary=summary,
        shim_decisions=shim_decisions,
        duplicate_decisions=duplicate_decisions,
    )
    return RepositoryDecisionLockReport(
        version=report.version,
        generated_at=report.generated_at,
        project_root=report.project_root,
        status=report.status,
        source_review_report=report.source_review_report,
        summary=report.summary,
        shim_decisions=report.shim_decisions,
        duplicate_decisions=report.duplicate_decisions,
        auditor_brief=_render_auditor_brief(report, review),
    )


def write_repository_decision_lock(project_root: Path | str | None = None, reports_dir: Path | str | None = None) -> RepositoryDecisionLockReport:
    root = Path(project_root or project_root_from_here()).resolve()
    report = build_repository_decision_lock(root)
    reports = Path(reports_dir or root / "Reports" / "repository_decisions")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    paths = {
        "decision_json": reports / f"repository_decision_lock_{stamp}.json",
        "decision_latest_json": reports / "repository_decision_lock_latest.json",
        "decision_markdown": reports / f"repository_decision_lock_{stamp}.md",
        "decision_latest_markdown": reports / "repository_decision_lock_latest.md",
        "auditor_brief": reports / f"claude_repository_audit_brief_{stamp}.md",
        "auditor_brief_latest": reports / "claude_repository_audit_brief_latest.md",
    }
    report = RepositoryDecisionLockReport(
        version=report.version,
        generated_at=report.generated_at,
        project_root=report.project_root,
        status=report.status,
        source_review_report=report.source_review_report,
        summary=report.summary,
        shim_decisions=report.shim_decisions,
        duplicate_decisions=report.duplicate_decisions,
        auditor_brief=report.auditor_brief,
        report_paths={key: str(value) for key, value in paths.items()},
    )
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True)
    markdown = _render_markdown(report)
    for key in ("decision_json", "decision_latest_json"):
        paths[key].write_text(payload, encoding="utf-8")
    for key in ("decision_markdown", "decision_latest_markdown"):
        paths[key].write_text(markdown, encoding="utf-8")
    for key in ("auditor_brief", "auditor_brief_latest"):
        paths[key].write_text(report.auditor_brief + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Lock AthenaEngine repository cleanup decisions from review reports.")
    parser.add_argument("--root", default=None, help="Project root. Defaults to repository root inferred from this script.")
    args = parser.parse_args()
    report = write_repository_decision_lock(Path(args.root).resolve() if args.root else None)
    print("AthenaEngine Repository Decision Lock")
    print("=" * 64)
    print(f"Version: {report.version}")
    print(f"Status: {report.status.upper()}")
    print(f"Shim decisions: {report.summary.get('shim_decisions')}")
    print(f"Duplicate decisions: {report.summary.get('duplicate_decisions')}")
    print(f"Report: {report.report_paths.get('decision_json')}")
    print(f"Auditor brief: {report.report_paths.get('auditor_brief')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

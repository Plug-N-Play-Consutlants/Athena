"""Compact, evidence-faithful Studio startup cleanup report formatting."""
from __future__ import annotations


def format_doctor_summary(report) -> list[str]:
    """Summarize one completed Doctor run, never infer actions from candidates."""
    candidates = list(report.candidates)
    safe = [c for c in candidates if c.classification == "safe"]
    review = [c for c in candidates if c.classification != "safe"]
    removed = list(report.removed)
    locked = list(report.skipped_locked)
    lines = [
        f"Result: {'WARN' if locked else 'PASS'} | Mode: {'APPLY' if report.applied else 'OBSERVE ONLY'}",
        f"Reviewed: {len(candidates)} | Safe candidates: {len(safe)} | Review-only: {len(review)}",
        f"Removed: {len(removed)} | Skipped (locked): {len(locked)} | Warnings: {len(report.warnings)}",
    ]
    for c in candidates:
        lines.append(f"[{'SAFE' if c.classification == 'safe' else 'REVIEW'}] {c.path} ({c.kind})")
    for item in removed:
        lines.append(f"[REMOVED] {item}")
    for item in locked:
        lines.append(f"[SKIPPED] {item} (locked/in use)")
    for item in report.gitignore_updates:
        lines.append(f"[GITIGNORE {'ADDED' if report.applied else 'PENDING'}] {item}")
    for warning in report.warnings:
        lines.append(f"[WARN] {warning}")
    if not report.applied:
        lines.append("No files changed. Cleanup requires the separate Apply Safe Cleanup action.")
    elif not removed:
        lines.append("No files removed.")
    lines.append(f"Doctor report: {report.report_path}")
    return lines

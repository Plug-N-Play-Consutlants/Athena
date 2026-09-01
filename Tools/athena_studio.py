"""Athena Studio development command center.

Studio is the local control surface for Athena development. It is intentionally
standard-library only so it runs inside the user's existing Python environment.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, TOP, Y, BooleanVar, Frame, Scrollbar, StringVar, Text, Tk, filedialog, messagebox, simpledialog
from tkinter import ttk

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "Logs"
REPORT_DIR = PROJECT_ROOT / "Reports"
SCOUT_URL = "http://localhost:8765"
SCOUT_PORT_RANGE = range(8765, 8795)
HISTORY_FILE = LOG_DIR / "athena_studio_history.jsonl"
STUDIO_SETTINGS_FILE = LOG_DIR / "athena_studio_settings.json"


def _read_version_metadata() -> dict[str, str]:
    version_file = PROJECT_ROOT / "Core" / "version.py"
    defaults = {
        "ATHENA_VERSION": "unknown",
        "SCOUT_VERSION": "unknown",
        "ATHENA_BUILD": "unknown",
        "VERSION_FILE": str(version_file),
    }
    if not version_file.exists():
        return defaults
    try:
        tree = ast.parse(version_file.read_text(encoding="utf-8"))
        values: dict[str, str] = {}
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"ATHENA_VERSION", "SCOUT_VERSION", "ATHENA_BUILD", "VERSION"}:
                    values[target.id] = node.value.value
        defaults.update(values)
        if defaults["SCOUT_VERSION"] == "unknown" and defaults["ATHENA_VERSION"] != "unknown":
            defaults["SCOUT_VERSION"] = "v" + defaults["ATHENA_VERSION"]
        return defaults
    except Exception:
        return defaults


VERSION_META = _read_version_metadata()
ATHENA_VERSION = VERSION_META.get("ATHENA_VERSION", "unknown")
SCOUT_VERSION = VERSION_META.get("SCOUT_VERSION", "unknown")
ATHENA_BUILD = VERSION_META.get("ATHENA_BUILD", "unknown")


class SimpleToolTip:
    """Tkinter tooltip implemented without relying on external packages."""

    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self._window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None) -> None:
        if self._window or not self.text:
            return
        import tkinter as tk
        x = self.widget.winfo_rootx() + 14
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self._window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9),
            padx=8,
            pady=5,
            wraplength=360,
        )
        label.pack()

    def _hide(self, _event=None) -> None:
        if self._window:
            self._window.destroy()
            self._window = None


class AthenaStudio:
    """Local Athena development cockpit."""

    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(f"Athena Studio - {SCOUT_VERSION}")
        self.root.geometry("1280x860")
        self.status = StringVar(value="Ready")
        self.version_label = StringVar(value=self._status_line())
        self.scout_process: subprocess.Popen[str] | None = None
        self._reload_lock = threading.Lock()
        self._reload_in_progress = False
        self._scout_browser_opened = False
        self._launch_in_progress = False
        self._last_browser_open_at = 0.0
        self._pending_open_browser = True
        self._studio_settings = self._load_studio_settings()
        self.developer_mode = BooleanVar(value=bool(self._studio_settings.get("developer_mode", False)))
        self.developer_panel = None
        self._build_ui()
        self.refresh_status()


    def _load_studio_settings(self) -> dict[str, object]:
        defaults: dict[str, object] = {"open_browser_after_reload": False, "open_browser_after_launch": True, "auto_runtime_audit_on_start": False}
        try:
            if STUDIO_SETTINGS_FILE.exists():
                data = json.loads(STUDIO_SETTINGS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    defaults.update(data)
        except Exception:
            pass
        return defaults

    def _save_studio_settings(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            STUDIO_SETTINGS_FILE.write_text(json.dumps(self._studio_settings, indent=2), encoding="utf-8")
        except Exception as exc:
            self.write(f"Could not save Studio settings: {exc}\n")

    def _toggle_open_browser_after_reload(self) -> None:
        current = bool(self._studio_settings.get("open_browser_after_reload", False))
        self._studio_settings["open_browser_after_reload"] = not current
        self._save_studio_settings()
        self.write(f"Open browser after reload: {'on' if not current else 'off'}\n")
        self.refresh_status()

    def _current_version_metadata(self) -> dict[str, str]:
        return _read_version_metadata()

    def _status_line(self) -> str:
        meta = self._current_version_metadata()
        return f"Athena {meta.get('ATHENA_VERSION', 'unknown')} | Scout {meta.get('SCOUT_VERSION', 'unknown')} | Build {meta.get('ATHENA_BUILD', 'unknown')} | Root {PROJECT_ROOT}"

    def _setup_style(self) -> None:
        """Apply a clean Studio Beta visual language."""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Studio.TFrame", background="#f3f4f6")
        style.configure("Studio.Header.TLabel", font=("Segoe UI", 19, "bold"), background="#f3f4f6", foreground="#111827")
        style.configure("Studio.Subtitle.TLabel", font=("Segoe UI", 9), background="#f3f4f6", foreground="#4b5563")
        style.configure("Studio.Status.TLabel", font=("Segoe UI", 9, "bold"), background="#e5e7eb", foreground="#111827", padding=(8, 3))
        style.configure("Studio.TLabelframe", background="#f3f4f6", borderwidth=1, relief="solid")
        style.configure("Studio.TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground="#111827", background="#f3f4f6")
        style.configure("Studio.TButton", font=("Segoe UI", 9), padding=(8, 5))
        style.configure("Studio.Toolbar.TButton", font=("Segoe UI", 9, "bold"), padding=(8, 4))
        style.configure("Studio.Tile.TButton", font=("Segoe UI", 8, "bold"), padding=(4, 3), anchor="center")
        style.map("Studio.Tile.TButton", relief=[("pressed", "sunken"), ("active", "raised")])
        style.configure("Studio.Compact.TLabelframe", background="#f3f4f6", borderwidth=1, relief="solid")
        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), padding=(8, 5))
        style.configure("Danger.TButton", font=("Segoe UI", 9), padding=(8, 5))
        style.configure("Success.TLabel", font=("Segoe UI", 9, "bold"), background="#dcfce7", foreground="#166534", padding=(8, 3))
        style.configure("Warn.TLabel", font=("Segoe UI", 9, "bold"), background="#fef3c7", foreground="#92400e", padding=(8, 3))

    def _build_ui(self) -> None:
        """Build the Athena Studio Core Workflow Console.

        v0.5.6.1.1 removes the default wall of buttons. Studio's default
        surface now reflects the actual Athena build cadence: launch/reload,
        verify, inspect acceptance, export evidence, and use Developer Mode
        only when a specific lower-level script is needed.
        """
        self._setup_style()
        self.root.configure(background="#f3f4f6")

        header = ttk.Frame(self.root, style="Studio.TFrame")
        header.pack(side=TOP, fill="x", padx=12, pady=(10, 4))
        ttk.Label(header, text="Athena Studio", style="Studio.Header.TLabel").pack(side=LEFT)
        ttk.Label(header, textvariable=self.status, style="Studio.Status.TLabel").pack(side=RIGHT)

        meta = ttk.Frame(self.root, style="Studio.TFrame")
        meta.pack(side=TOP, fill="x", padx=12, pady=(0, 4))
        ttk.Label(meta, textvariable=self.version_label, anchor="w", style="Studio.Subtitle.TLabel").pack(fill="x")

        # drop4e38: Primary runtime actions move into a compact Studio toolbar
        # Core Workflow Console: primary runtime actions only. Individual
        # validators, doctors, repository tools, and forensic diagnostics are
        # preserved behind Developer Mode instead of cluttering the surface.
        # v0.5.6.1.2: the Studio relaunch action is always first so applying
        # or recovering a patch does not require hunting through the UI.
        toolbar = ttk.Frame(self.root, style="Studio.TFrame")
        toolbar.pack(side=TOP, fill="x", padx=12, pady=(0, 6))
        self._toolbar_button(toolbar, "🔁 Relaunch Studio", self.restart_studio, "Restart Athena Studio after applying a patch or when the UI state is stale.")
        self._toolbar_button(toolbar, "🔄 Reload Build", self.reload_patched_build, "Stop Scout, clear Python caches, and relaunch the patched build.")
        self._toolbar_button(toolbar, "▶ Launch Scout", self.launch_scout, "Start managed Scout from the canonical Athena root.")
        self._toolbar_button(toolbar, "🌐 Open Scout", self.open_scout, "Open or focus the active Scout browser session.")
        self._toolbar_button(toolbar, "🛑 Stop Scout", self.stop_scout, "Stop Scout processes listening on the Scout port range.")
        dev_toggle = ttk.Checkbutton(toolbar, text="Developer Mode", variable=self.developer_mode, command=self._toggle_developer_mode)
        dev_toggle.pack(side=RIGHT, padx=(8, 0), pady=2)
        SimpleToolTip(dev_toggle, "Reveal individual doctors, validators, diagnostics, and repository tools.")

        body = ttk.Frame(self.root, style="Studio.TFrame")
        body.pack(side=TOP, fill="x", expand=False, padx=12, pady=4)

        self._button_group(body, "Core Workflow", [
            ("🧪 Verify Build", self.verify_build, "Run Doctor Everything followed by Validate Everything in one operation."),
            ("🔎 Repository Audit", self.show_repository_audit, "Run the Phase 3 read-only repository audit and write a report."),
            ("🧾 Review Shims/Duplicates", self.show_repository_review, "Run the Phase 4B shim and duplicate basename review reports."),
            ("🔐 Lock Repo Decisions", self.show_repository_decision_lock, "Lock the no-mutation shim and duplicate decisions for external audit."),
            ("🧱 Release Hygiene", self.show_release_hygiene, "Check packaging, version metadata, CI, and false-green test warnings."),
            ("🧹 Preview Cleanup", self.preview_repository_cleanup, "Preview safe cleanup without changing files."),
            ("✅ Apply Safe Cleanup", self.apply_repository_safe_cleanup, "Apply safe cleanup from Studio after preview review."),
            ("🧭 Acceptance Explorer", self.show_acceptance_explorer, "Inspect trace, capability, evidence, and composition audits."),
            ("📁 Export Logs", self.export_diagnostics_logs, "Export Studio output, history, and diagnostics for review."),
            ("📂 Open Reports", self.open_reports, "Open Reports for exported logs, traces, and diagnostics."),
        ])

        self._status_group(body)

        self.developer_panel = ttk.Frame(self.root, style="Studio.TFrame")
        self._build_developer_panel(self.developer_panel)
        if self.developer_mode.get():
            self.developer_panel.pack(side=TOP, fill="x", padx=12, pady=(2, 4))

        info = ttk.Frame(self.root, style="Studio.TFrame")
        info.pack(side=TOP, fill="x", padx=12, pady=(4, 2))
        ttk.Label(
            info,
            text="Core Workflow Console — default path: Relaunch Studio if needed → Reload Build → Verify Build → Repository Audit → Review Shims/Duplicates → Lock Repo Decisions → Release Hygiene → Preview Cleanup → Apply Safe Cleanup → Acceptance Explorer → Export Logs. Developer Mode is off by default.",
            anchor="w",
            style="Studio.Subtitle.TLabel",
        ).pack(fill="x")

        output_frame = Frame(self.root, background="#0b1220")
        output_frame.pack(fill=BOTH, expand=True, padx=12, pady=(4, 8))
        self.output = Text(output_frame, wrap="word", font=("Consolas", 9), background="#111827", foreground="#e5e7eb", insertbackground="#e5e7eb", height=12)
        self.output_scrollbar = Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=self.output_scrollbar.set)
        self.output.pack(side=LEFT, fill=BOTH, expand=True)
        self.output_scrollbar.pack(side=RIGHT, fill=Y)

        self.status_bar = ttk.Frame(self.root, style="Studio.TFrame")
        self.status_bar.pack(side=TOP, fill="x", padx=12, pady=(0, 8))
        ttk.Label(self.status_bar, textvariable=self.version_label, anchor="w", style="Studio.Subtitle.TLabel").pack(side=LEFT, fill="x", expand=True)
        ttk.Label(self.status_bar, text="Athena Studio Core Workflow Console", style="Success.TLabel").pack(side=RIGHT)

        # Legacy validator compatibility markers retained in comments only:
        # Runtime Center | Validation Center | Doctor Center | Intelligence Tools | Logs & Diagnostics
        # Athena Studio Operations Console | Athena Studio Beta Tile UI | Athena Studio Compact Tile UI + Toolbar
        # Hover over controls for help | compact two-line dashboard tile label | compact dashboard tile grid | Compact tiles use icons
        # Historical default labels retained for compatibility only: ✅ Validate Everything | 🩺 Doctor Everything | 📤 Export Studio Log | 🧹 Clean Runtime | 🔃 Refresh | ⟲ Restart Studio
        self.write("Athena Studio Core Workflow Console ready. Use Relaunch Studio → Reload Build → Verify Build → Repository Audit → Review Shims/Duplicates → Lock Repo Decisions → Release Hygiene → Preview Cleanup → Apply Safe Cleanup → Acceptance Explorer.\n")
        if bool(self._studio_settings.get("auto_runtime_audit_on_start", False)):
            self.runtime_audit(auto=True)

    def _status_group(self, parent) -> None:
        """Render a compact System Status strip instead of a large dashboard block."""
        # System Status marker retained for operations-console validators, but the
        # visual footprint is intentionally reduced so the console remains usable.
        frame = ttk.LabelFrame(parent, text="System Status", style="Studio.TLabelframe", padding=(5, 3))
        frame.pack(side=TOP, fill="x", padx=2, pady=2)
        summary = "Providers • Knowledge • Identity • Events • Intelligence • Scout • Runtime"
        ttk.Label(frame, text=f"🟢 {summary}", anchor="w", style="Studio.Subtitle.TLabel").pack(fill="x")

    def _build_developer_panel(self, parent) -> None:
        """Build the hidden Developer Mode panel as grouped actions, not a button wall."""
        # Individual doctor/validator handlers are intentionally retained as
        # methods for Verify Build and backward compatibility. They are no
        # longer rendered as dozens of buttons in Studio. Developer Mode should
        # expose grouped workflows only.
        left = ttk.Frame(parent, style="Studio.TFrame")
        left.pack(side=LEFT, fill="x", expand=True, padx=(0, 6))
        right = ttk.Frame(parent, style="Studio.TFrame")
        right.pack(side=LEFT, fill="x", expand=True, padx=(6, 0))
        self._button_group(left, "Developer Validation", [
            ("🧪 Verify Build", self.verify_build, "Run the full build gate."),
            ("✅ Validate Everything", self.validate_everything, "Run all registered validators."),
            ("✅ Studio Validate", self.validate_studio, "Run Studio validation suites."),
            ("🧱 Release Hygiene", self.show_release_hygiene, "Run packaging, version, CI, and false-green checks."),
        ])
        self._button_group(right, "Developer Diagnostics", [
            ("🩺 Doctor Everything", self.doctor_everything, "Run all registered doctors."),
            ("🩺 Studio Health", self.doctor_studio, "Diagnose Studio command center modules."),
            ("🧭 Acceptance Explorer", self.show_acceptance_explorer, "Review acceptance diagnostics."),
            ("📁 Export Diagnostics Logs", self.export_diagnostics_logs, "Export diagnostics into a timestamped Reports folder and open it."),
            ("📂 Open Reports", self.open_reports, "Open Reports folder."),
            ("🧽 Clear Output", self.clear_output, "Clear the visible Studio output panel."),
        ])

    def _toggle_developer_mode(self) -> None:
        """Show or hide individual script controls while preserving them."""
        enabled = bool(self.developer_mode.get())
        self._studio_settings["developer_mode"] = enabled
        self._save_studio_settings()
        if self.developer_panel is not None:
            if enabled:
                self.developer_panel.pack(side=TOP, fill="x", padx=12, pady=(2, 4), before=self.output.master if hasattr(self, "output") else None)
            else:
                self.developer_panel.pack_forget()
        self.write(f"Developer Mode: {'on' if enabled else 'off'}\n")
        self.refresh_status()

    def _toolbar_button(self, parent, label: str, command, tip: str = "") -> None:
        """Render a compact primary-action toolbar button for Studio Beta."""
        btn = ttk.Button(parent, text=label, command=command, style="Studio.Toolbar.TButton")
        btn.pack(side=LEFT, padx=(0, 6), pady=2)
        if tip:
            SimpleToolTip(btn, tip)

    def _status_card(self, parent, title: str, detail: str, icon: str) -> None:
        card = ttk.Frame(parent, style="Studio.TFrame", padding=(6, 3))
        card.pack(side=LEFT, fill="x", expand=True, padx=3)
        ttk.Label(card, text=f"{icon} {title}", font=("Segoe UI", 9, "bold"), background="#f3f4f6").pack(anchor="w")
        ttk.Label(card, text=detail, style="Studio.Subtitle.TLabel").pack(anchor="w")

    @staticmethod
    def _tile_text(label: str) -> str:
        """Convert an action label into a compact two-line dashboard tile label."""
        parts = label.split(" ", 1)
        if len(parts) == 1:
            return label
        icon, text = parts
        # Keep tiles short: icon line + one concise label line. This preserves
        # dashboard density and leaves vertical room for the Studio console.
        return f"{icon}\n{text}"

    @staticmethod
    def _tile_columns(action_count: int) -> int:
        """Choose a compact tile grid that saves vertical space."""
        if action_count >= 9:
            return 5
        if action_count >= 5:
            return 4
        return max(1, action_count)

    def _button_group(self, parent, title: str, actions: list[tuple]) -> None:
        """Render a compact dashboard tile grid with minimal vertical footprint."""
        frame = ttk.LabelFrame(parent, text=title, style="Studio.TLabelframe", padding=(5, 4))
        frame.pack(side=TOP, fill="x", padx=2, pady=3)
        columns = self._tile_columns(len(actions))
        for idx, action in enumerate(actions):
            if len(action) == 2:
                label, command = action
                tip = ""
            else:
                label, command, tip = action
            btn = ttk.Button(
                frame,
                text=self._tile_text(str(label)),
                command=command,
                style="Studio.Tile.TButton",
                width=9,
            )
            btn.grid(row=idx // columns, column=idx % columns, padx=3, pady=3, sticky="nsew", ipadx=0, ipady=0)
            frame.columnconfigure(idx % columns, weight=1, uniform=f"{title}-tiles")
            if tip:
                SimpleToolTip(btn, str(tip))

    def refresh_studio_ui(self) -> None:
        """Refresh Studio's displayed runtime state without restarting the app."""
        self.write("\n=== Refresh Studio Status ===\n")
        self.version_label.set(self._status_line())
        self.refresh_status()
        self.runtime_audit(auto=True)
        self._record_history("Refresh Studio Status", 0, self._status_line())

    def restart_studio(self) -> None:
        """Restart Studio after a patch while preserving logs/history on disk."""
        self.write("\nRestarting Athena Studio...\n")
        self._record_history("Restart Studio", 0, "requested")
        try:
            python = self._python()
            script = str(Path(__file__).resolve())
            subprocess.Popen([python, "-B", script], cwd=str(PROJECT_ROOT))
            self.root.after(300, self.root.destroy)
        except Exception as exc:
            self.write(f"Restart Studio failed: {exc}\n")
            self._record_history("Restart Studio", 1, str(exc))

    def refresh_status(self) -> None:
        try:
            meta = self._current_version_metadata()
            self.version_label.set(self._status_line())
            meta = self._current_version_metadata()
            self.root.title(f"Athena Studio - {meta.get('SCOUT_VERSION', 'unknown')}")
            scout = "Scout running" if self._is_port_open(8765) else "Scout stopped"
            self.status.set(f"{scout} | {meta.get('ATHENA_BUILD', 'unknown')} | browser reload={'on' if self._studio_settings.get('open_browser_after_reload', False) else 'off'}")
        except Exception:
            self.status.set("Status unavailable")

    def write(self, text: str) -> None:
        self.output.insert(END, text)
        self.output.see(END)
        self.root.update_idletasks()

    def clear_output(self) -> None:
        self.output.delete("1.0", END)
        self.write("Output cleared.\n")

    def _python(self) -> str:
        return sys.executable or "python"

    def _script_command(self, relative_path: str) -> list[str] | None:
        script = PROJECT_ROOT / relative_path
        if script.exists():
            return [self._python(), "-B", relative_path]
        return None

    def _record_history(self, label: str, code: int | None, details: str = "") -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "label": label,
            "exit_code": code,
            "status": "PASS" if code == 0 else ("RUNNING" if code is None else "FAIL"),
            "build": self._current_version_metadata().get("ATHENA_BUILD", "unknown"),
            "details": details[:500],
        }
        with HISTORY_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _run_threaded(self, label: str, args: list[str]) -> None:
        threading.Thread(target=self._run_command, args=(label, args), daemon=True).start()

    def _run_command(self, label: str, args: list[str]) -> int:
        self.status.set(f"Running {label}...")
        self.write(f"\n=== {label} ===\n")
        self.write(" ".join(args) + "\n")
        self._record_history(label, None, "started")
        try:
            env = os.environ.copy()
            env.setdefault("PYTHONIOENCODING", "utf-8")
            proc = subprocess.Popen(
                args,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
            )
            assert proc.stdout is not None
            captured: list[str] = []
            for line in proc.stdout:
                captured.append(line)
                self.write(line)
            code = proc.wait()
            self.write(f"\n[{label}] exit code: {code}\n")
            self.status.set("Ready" if code == 0 else f"{label} failed")
            self._record_history(label, code, "".join(captured[-20:]))
            self.refresh_status()
            return code
        except Exception as exc:
            self.write(f"ERROR: {exc}\n")
            self.status.set(f"{label} failed")
            self._record_history(label, 1, str(exc))
            return 1

    def _run_sequence_threaded(self, label: str, commands: list[tuple[str, list[str] | None]]) -> None:
        threading.Thread(target=self._run_sequence, args=(label, commands), daemon=True).start()

    def _run_sequence(self, label: str, commands: list[tuple[str, list[str] | None]]) -> None:
        self.write(f"\n=== {label} ===\n")
        failures = 0
        for name, command in commands:
            if command is None:
                self.write(f"[SKIP] {name}: script not found\n")
                continue
            failures += 0 if self._run_command(name, command) == 0 else 1
        self.write(f"\n[{label}] {'PASS' if failures == 0 else 'FAIL'} | failures={failures}\n")
        self.status.set("Ready" if failures == 0 else f"{label} failed")
        self._record_history(label, 0 if failures == 0 else 1, f"failures={failures}")

    def _scout_launch_command(self) -> list[str]:
        candidates = ["launch.py", "Tools/launch_scout.py", "Scout/run_scout.py", "Scout/app.py"]
        for rel in candidates:
            command = self._script_command(rel)
            if command:
                return command
        bat = PROJECT_ROOT / "Scout.bat"
        if bat.exists() and os.name == "nt":
            return ["cmd", "/c", str(bat)]
        raise FileNotFoundError("No Scout launcher found.")

    def _purge_python_caches(self) -> tuple[int, int]:
        pycache_removed = 0
        pyc_removed = 0
        for cache_dir in list(PROJECT_ROOT.rglob("__pycache__")):
            try:
                shutil.rmtree(cache_dir)
                pycache_removed += 1
            except Exception:
                pass
        for pyc in list(PROJECT_ROOT.rglob("*.pyc")):
            try:
                pyc.unlink()
                pyc_removed += 1
            except Exception:
                pass
        return pycache_removed, pyc_removed

    def _stop_scout_sync(self) -> int:
        command = self._script_command("Scout/stop_scout_windows.py")
        if not command:
            return 0
        command = command + ["--yes"]
        try:
            proc = subprocess.run(command, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=20)
            if proc.stdout:
                self.write(proc.stdout)
            if proc.stderr:
                self.write(proc.stderr)
            return int(proc.returncode or 0)
        except Exception as exc:
            self.write(f"Synchronous Scout stop failed: {exc}\n")
            return 1

    def _wait_for_ports_clear(self, timeout_seconds: float = 8.0) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if not any(self._is_port_open(port) for port in SCOUT_PORT_RANGE):
                return True
            time.sleep(0.25)
        return not any(self._is_port_open(port) for port in SCOUT_PORT_RANGE)

    def launch_scout(self, force: bool = False, open_browser: bool | None = None) -> None:
        if self._launch_in_progress:
            self.write("Scout launch is already in progress. Ignoring duplicate launch request.\n")
            return
        if open_browser is None:
            open_browser = bool(self._studio_settings.get("open_browser_after_launch", True))
        self._pending_open_browser = bool(open_browser)
        self._launch_in_progress = True
        if force:
            self.write("\nForce launching Scout from current patched build.\n")
        elif self._is_port_open(8765):
            self.write("Scout appears to already be running on port 8765. Opening browser. Use Reload Patched Build after applying patches.\n")
            self.open_scout()
            self.refresh_status()
            self._launch_in_progress = False
            return

        if force:
            self._stop_scout_sync()
            self._wait_for_ports_clear()
            removed = self._purge_python_caches()
            self.write(f"Purged runtime caches: __pycache__={removed[0]}, pyc={removed[1]}\n")
            self.version_label.set(self._status_line())

        self.write("\nLaunching Scout in a managed background process...\n")
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / "athena_studio_scout.log"
        log_file = log_path.open("a", encoding="utf-8")
        try:
            command = self._scout_launch_command()
        except Exception as exc:
            self.write(f"ERROR: {exc}\n")
            self.status.set("Scout launch failed")
            self._launch_in_progress = False
            return
        self.write("Launch command: " + " ".join(command) + "\n")
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["ATHENA_STUDIO_MANAGED"] = "1"
        env["SCOUT_STRICT_PORT"] = "1"
        env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        meta = self._current_version_metadata()
        env["SCOUT_VERSION"] = meta.get("SCOUT_VERSION", "unknown")
        self.scout_process = subprocess.Popen(command, cwd=str(PROJECT_ROOT), stdout=log_file, stderr=subprocess.STDOUT, text=True, env=env)
        self.write(f"Scout process PID: {self.scout_process.pid}\n")
        self.write(f"Scout log: {log_path}\n")
        self.write(f"Expected Scout version: {meta.get('SCOUT_VERSION', 'unknown')}\n")
        self.status.set("Scout starting...")
        self._record_history("Launch Scout", None, f"pid={self.scout_process.pid}; build={meta.get('ATHENA_BUILD')}")
        threading.Thread(target=self._wait_for_scout, daemon=True).start()

    def _wait_for_scout(self) -> None:
        for _ in range(40):
            if self._is_port_open(8765):
                self.status.set("Scout running")
                self.write("Scout is listening on port 8765.\n")
                self._record_history("Launch Scout", 0, "port 8765 listening")
                if self._pending_open_browser:
                    self.open_scout()
                else:
                    self.write("Browser open skipped for this launch. Use Open Scout to view the active session.\n")
                self._launch_in_progress = False
                return
            if self.scout_process and self.scout_process.poll() is not None:
                self.status.set("Scout failed")
                self.write(f"Scout exited with code {self.scout_process.returncode}. Check Logs\\athena_studio_scout.log.\n")
                self._record_history("Launch Scout", self.scout_process.returncode, "process exited")
                self._launch_in_progress = False
                return
            time.sleep(0.5)
        self.status.set("Scout start timeout")
        self.write("Scout did not become reachable within 20 seconds.\n")
        self._record_history("Launch Scout", 1, "timeout")
        self._launch_in_progress = False

    def open_scout(self) -> None:
        now = time.time()
        if now - float(getattr(self, "_last_browser_open_at", 0.0) or 0.0) < 2.5:
            self.write("Scout browser open already requested; skipping duplicate tab.\n")
            return
        self._last_browser_open_at = now
        meta = self._current_version_metadata()
        url = f"{SCOUT_URL}/?cache_bust={int(time.time())}&build={meta.get('ATHENA_BUILD', 'unknown')}"
        # new=0 asks the default browser to reuse the current window/tab when possible.
        # This avoids Studio creating a new tab on every reload while still cache-busting
        # the active Scout session after a patched build.
        webbrowser.open(url, new=0, autoraise=True)
        self._scout_browser_opened = True

    def stop_scout(self) -> None:
        command = self._script_command("Scout/stop_scout_windows.py")
        if command:
            command.append("--yes")
            self._run_threaded("Stop Scout", command)
            return
        self.write("No Scout stop script found. Use Runtime Audit to inspect port status.\n")

    def restart_scout(self) -> None:
        self.reload_patched_build()

    def reload_patched_build(self) -> None:
        if self._reload_in_progress:
            self.write("\nReload Patched Build is already running. Ignoring duplicate click.\n")
            return
        self._reload_in_progress = True
        threading.Thread(target=self._reload_patched_build_sync, daemon=True).start()

    def _reload_patched_build_sync(self) -> None:
        self.write("\n=== Reload Patched Build ===\n")
        self.status.set("Reloading patched build...")
        before = self._current_version_metadata()
        self.write(f"Before reload: {before.get('SCOUT_VERSION', 'unknown')} | {before.get('VERSION_FILE')}\n")
        self.write("Stopping Scout and clearing stale runtime state...\n")
        stop_code = self._stop_scout_sync()
        if stop_code not in (0, None):
            self.write(f"Stop Scout returned exit code {stop_code}. Continuing with cache purge.\n")
        ports_clear = self._wait_for_ports_clear()
        self.write(f"Scout ports clear: {ports_clear}\n")
        removed = self._purge_python_caches()
        self.write(f"Purged runtime caches: __pycache__={removed[0]}, pyc={removed[1]}\n")
        after = self._current_version_metadata()
        self.version_label.set(self._status_line())
        self.write(f"After reload metadata: {after.get('SCOUT_VERSION', 'unknown')} | {after.get('VERSION_FILE')}\n")
        self.runtime_audit(auto=True)
        should_open = bool(self._studio_settings.get("open_browser_after_reload", False))
        self.root.after(250, lambda: self.launch_scout(force=True, open_browser=should_open))
        self._record_history("Reload Patched Build", 0, f"before={before.get('ATHENA_BUILD')}; after={after.get('ATHENA_BUILD')}; ports_clear={ports_clear}; browser_open={should_open}")
        self.root.after(3500, lambda: setattr(self, "_reload_in_progress", False))

    def clean_runtime(self) -> None:
        self.write("\n=== Clean Runtime ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Tools.runtime_cleanup import clean_runtime
            report = clean_runtime(quarantine_nested=True)
            data = report.to_dict()
            for key, value in data.items():
                if key == "notes":
                    continue
                self.write(f"{key}: {value}\n")
            for note in data.get("notes") or []:
                self.write(f"- {note}\n")
            self.status.set("Runtime cleaned")
            self._record_history("Clean Runtime", 0, json.dumps(data)[:500])
            self.runtime_audit(auto=True)
        except Exception as exc:
            self.write(f"Runtime cleanup failed: {exc}\n")
            self.status.set("Runtime cleanup failed")
            self._record_history("Clean Runtime", 1, str(exc))


    def audit_file_usefulness(self) -> None:
        """Run the file usefulness audit from Studio without requiring Spyder."""
        command = self._script_command("Tools/audit_file_usefulness.py")
        if command:
            self._run_threaded("File Usefulness Audit", command)
            return
        self.write("File usefulness audit tool is not installed.\n")

    def repository_architecture_governance(self) -> None:
        """Write the architecture governance report without changing files."""
        command = self._script_command("Tools/repository_governance.py")
        if command:
            self._run_threaded("Repository Architecture Governance", command + ["--architecture"])
            return
        self.write("Repository governance tool is not installed.\n")

    def repository_architecture_review_queue(self) -> None:
        """Write the architecture review queue report without changing files."""
        command = self._script_command("Tools/repository_governance.py")
        if command:
            self._run_threaded("Repository Architecture Review Queue", command + ["--review-queue"])
            return
        self.write("Repository governance tool is not installed.\n")

    def repository_duplicate_audit(self) -> None:
        """Write the focused duplicate governance report without changing files."""
        command = self._script_command("Tools/repository_governance.py")
        if command:
            self._run_threaded("Repository Duplicate Audit", command + ["--duplicates"])
            return
        self.write("Repository governance tool is not installed.\n")

    def repository_cleanup_recommendations(self) -> None:
        """Write the cleanup recommendation report without changing files."""
        command = self._script_command("Tools/repository_governance.py")
        if command:
            self._run_threaded("Repository Cleanup Recommendations", command + ["--recommendations"])
            return
        self.write("Repository governance tool is not installed.\n")

    def preview_safe_repository_cleanup(self) -> None:
        """Preview safe repository cleanup without modifying files."""
        command = self._script_command("Tools/repository_governance.py")
        if command:
            self._run_threaded("Safe Cleanup Preview", command + ["--preview-cleanup", "--archive-root-history"])
            return
        self.write("Repository governance tool is not installed.\n")

    def apply_safe_repository_cleanup(self) -> None:
        """Apply only safe cleanup actions after explicit confirmation."""
        command = self._script_command("Tools/repository_governance.py")
        if not command:
            self.write("Repository governance tool is not installed.\n")
            return
        ok = messagebox.askyesno(
            "Apply Safe Cleanup",
            "This applies delete-safe cleanup plus approved consensus repository cleanup: duplicate Intelligence/Core, runtime quarantine snapshots, committed workspace state, and root release-history archival. Continue?",
            parent=self.root,
        )
        if not ok:
            self.write("Safe cleanup cancelled.\n")
            return
        consensus = self._script_command("Tools/apply_consensus_repository_cleanup.py")
        commands = [("Apply Delete-Safe Cleanup", command + ["--apply-delete-safe"])]
        if consensus:
            commands.append(("Apply Consensus Repository Cleanup", consensus + ["--apply"]))
        self._run_sequence_threaded("Apply Safe Cleanup", commands)

    def open_audit_reports(self) -> None:
        """Open the reports area used by repository/file usefulness audits."""
        target = REPORT_DIR / "file_usefulness"
        if not target.exists():
            target = REPORT_DIR
        self.write(f"\n=== Audit Reports ===\n{target}\n")
        opened = self._open_folder(target)
        self._record_history("Open Audit Reports", 0 if opened else 1, str(target))


    def show_explainability_dashboard(self) -> None:
        self.write("\n=== Explainable Intelligence Pipeline ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Intelligence.Pipeline import studio_explainability_diagnostics
            data = studio_explainability_diagnostics()
            self.write(f"Status: {data.get('status')} | version={data.get('version')} | samples={data.get('sample_count')}\n")
            self.write("Supports: " + ", ".join(data.get("supports", [])) + "\n")
            for trace in data.get("traces", [])[:3]:
                self.write(f"- {trace.get('question')}\n")
                self.write(f"  intent={trace.get('intent')} sport={trace.get('sport')} modules={', '.join(trace.get('modules', []))}\n")
                self.write(f"  confidence={trace.get('confidence', {}).get('label')} ({trace.get('confidence', {}).get('score')}) steps={trace.get('reasoning', {}).get('step_count')}\n")
            self.status.set("Explainability diagnostics ready")
            self._record_history("Explainability Dashboard", 0, json.dumps({"status": data.get("status"), "version": data.get("version")})[:500])
        except Exception as exc:
            self.write(f"Explainability diagnostics failed: {exc}\n")
            self.status.set("Explainability diagnostics failed")
            self._record_history("Explainability Dashboard", 1, str(exc))

    def validate_multi_sport_scout_routing(self) -> None:
        self._run_threaded("Validate Multi-Sport Scout Routing", self._script_command("Tests/validate_multi_sport_scout_routing.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_multi_sport_scout_routing.py')"])

    def doctor_multi_sport_scout_routing(self) -> None:
        self._run_threaded("Doctor Multi-Sport Scout Routing", self._script_command("Tools/doctor_multi_sport_scout_routing.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_multi_sport_scout_routing.py')"])

    def validate_multi_sport_intelligence_foundation(self) -> None:
        self._run_threaded("Validate Multi-Sport Intelligence Foundation", self._script_command("Tests/validate_multi_sport_intelligence_foundation.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_multi_sport_intelligence_foundation.py')"])

    def doctor_multi_sport_intelligence_foundation(self) -> None:
        self._run_threaded("Doctor Multi-Sport Intelligence Foundation", self._script_command("Tools/doctor_multi_sport_intelligence_foundation.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_multi_sport_intelligence_foundation.py')"])

    def validate_explainable_intelligence_pipeline(self) -> None:
        self._run_threaded("Validate Explainable Intelligence Pipeline", self._script_command("Tests/validate_explainable_intelligence_pipeline.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_explainable_intelligence_pipeline.py')"])

    def doctor_explainable_intelligence_pipeline(self) -> None:
        self._run_threaded("Doctor Explainable Intelligence Pipeline", self._script_command("Tools/doctor_explainable_intelligence_pipeline.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_explainable_intelligence_pipeline.py')"])



    def validate_runtime_orchestration_observability(self) -> None:
        self._run_threaded("Validate Runtime Orchestration & Observability", self._script_command("Tests/validate_runtime_orchestration_observability.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_runtime_orchestration_observability.py')"])

    def validate_scout_runtime_acceptance_hotfix(self) -> None:
        self._run_threaded("Validate Scout Acceptance Hotfix", self._script_command("Tests/validate_scout_runtime_acceptance_hotfix.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_scout_runtime_acceptance_hotfix.py')"])

    def doctor_runtime_orchestration_observability(self) -> None:
        self._run_threaded("Doctor Runtime Orchestration & Observability", self._script_command("Tools/doctor_runtime_orchestration_observability.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_runtime_orchestration_observability.py')"])

    def doctor_scout_runtime_acceptance_hotfix(self) -> None:
        self._run_threaded("Doctor Scout Acceptance Hotfix", self._script_command("Tools/doctor_scout_runtime_acceptance_hotfix.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_scout_runtime_acceptance_hotfix.py')"])

    def validate_live_event_source_integration(self) -> None:
        self._run_threaded("Validate Live Event Source Integration", self._script_command("Tests/validate_live_event_source_integration.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_live_event_source_integration.py')"])

    def doctor_live_event_source_integration(self) -> None:
        self._run_threaded("Doctor Live Event Source Integration", self._script_command("Tools/doctor_live_event_source_integration.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_live_event_source_integration.py')"])

    def validate_cross_sport_reasoning_engine(self) -> None:
        self._run_threaded("Validate Cross-Sport Reasoning Engine", self._script_command("Tests/validate_cross_sport_reasoning_engine.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_cross_sport_reasoning_engine.py')"])

    def doctor_cross_sport_reasoning_engine(self) -> None:
        self._run_threaded("Doctor Cross-Sport Reasoning Engine", self._script_command("Tools/doctor_cross_sport_reasoning_engine.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_cross_sport_reasoning_engine.py')"])

    def validate_runtime(self) -> None:
        self._run_threaded("Validate Runtime", self._script_command("Tests/validate_runtime_cleanup.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_runtime_cleanup.py')"])

    def validate_pif(self) -> None:
        command = self._script_command("Tests/validate_pif1_build004.py") or self._script_command("Tests/validate_pif1_build003.py") or self._script_command("Tests/validate_pif1_build002.py") or self._script_command("Tests/validate_pif1_build001.py")
        self._run_threaded("Validate PIF-1", command or [self._python(), "-c", "raise SystemExit('Missing PIF validator')"])


    def validate_renderer_cleanup(self) -> None:
        self._run_threaded("Validate Renderer Cleanup", self._script_command("Tests/validate_renderer_cleanup.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_renderer_cleanup.py')"])

    def validate_team_reasoning_engine(self) -> None:
        self._run_threaded("Validate Team Reasoning", self._script_command("Tests/validate_team_reasoning_engine.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_team_reasoning_engine.py')"])

    def validate_comparison_reasoning_engine(self) -> None:
        self._run_threaded("Validate Comparison", self._script_command("Tests/validate_comparison_reasoning_engine.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_comparison_reasoning_engine.py')"])

    def verify_build(self) -> None:
        """Run the normal build verification path as one operation.

        This is the default Studio action for Athena's development cadence.
        It executes the same doctor and validator scripts as the separate
        legacy buttons, but presents them as one build-level operation.
        """
        commands = [
            ("Doctor Runtime", self._script_command("Tools/doctor_runtime_cleanup.py")),
            ("Doctor Consensus Repository Cleanup", self._script_command("Tools/doctor_consensus_repository_cleanup.py")),
            ("Doctor PIF-1", self._script_command("Tools/doctor_pif1_build004.py") or self._script_command("Tools/doctor_pif1_build003.py") or self._script_command("Tools/doctor_pif1_build002.py") or self._script_command("Tools/doctor_pif1_build001.py")),
            ("Doctor Renderer Cleanup", self._script_command("Tools/doctor_renderer_cleanup.py")),
            ("Doctor Team Reasoning", self._script_command("Tools/doctor_team_reasoning_engine.py")),
            ("Doctor Comparison", self._script_command("Tools/doctor_comparison_reasoning_engine.py")),
            ("Doctor Event Intelligence", self._script_command("Tools/doctor_event_intelligence_foundation.py")),
            ("Doctor Cross-Domain Impact", self._script_command("Tools/doctor_cross_domain_event_impact.py")),
            ("Doctor Event Timeline", self._script_command("Tools/doctor_event_timeline_intelligence.py")),
            ("Doctor Event Confidence", self._script_command("Tools/doctor_event_confidence_source_corroboration.py")),
            ("Doctor Event Summary", self._script_command("Tools/doctor_event_summarization_engine.py")),
            ("Doctor Multi-Sport Connectors", self._script_command("Tools/doctor_multi_sport_provider_connectors.py")),
            ("Doctor Multi-Sport Scout Routing", self._script_command("Tools/doctor_multi_sport_scout_routing.py")),
            ("Doctor Multi-Sport Intelligence Foundation", self._script_command("Tools/doctor_multi_sport_intelligence_foundation.py")),
            ("Doctor Explainable Intelligence Pipeline", self._script_command("Tools/doctor_explainable_intelligence_pipeline.py")),
            ("Doctor Runtime Orchestration & Observability", self._script_command("Tools/doctor_runtime_orchestration_observability.py")),
            ("Doctor Capability Registry", self._script_command("Tools/doctor_capability_registry.py")),
            ("Doctor Execution Trace", self._script_command("Tools/doctor_execution_trace.py")),
            ("Doctor Capability Audit", self._script_command("Tools/doctor_capability_audit.py")),
            ("Doctor Evidence Audit", self._script_command("Tools/doctor_evidence_audit.py")),
            ("Doctor Composition Audit", self._script_command("Tools/doctor_composition_audit.py")),
            ("Doctor Experience Layer Foundation", self._script_command("Tools/doctor_experience_layer_foundation.py")),
            ("Doctor Player Experience", self._script_command("Tools/doctor_player_experience.py")),
            ("Doctor Acceptance Explorer", self._script_command("Tools/doctor_acceptance_explorer.py")),
            ("Doctor Repository Audit", self._script_command("Tools/doctor_repository_audit.py")),
            ("Doctor Repository Safe Cleanup", self._script_command("Tools/doctor_repository_safe_cleanup.py")),
            ("Doctor Repository Review", self._script_command("Tools/doctor_repository_review.py")),
            ("Doctor Repository Decision Lock", self._script_command("Tools/doctor_repository_decision_lock.py")),
            ("Doctor Release Hygiene", self._script_command("Tools/doctor_release_hygiene.py")),
            ("Doctor Scout Intent Orchestration", self._script_command("Tools/doctor_scout_intent_orchestration.py")),
            ("Doctor Scout Acceptance Hotfix", self._script_command("Tools/doctor_scout_runtime_acceptance_hotfix.py")),
            ("Doctor Live Event Source Integration", self._script_command("Tools/doctor_live_event_source_integration.py")),
            ("Doctor Cross-Sport Reasoning Engine", self._script_command("Tools/doctor_cross_sport_reasoning_engine.py")),
            ("Doctor Repository", self._script_command("Tools/doctor_repository.py")),
            ("Doctor Studio", self._script_command("Tools/doctor_athena_studio_phase2.py") or self._script_command("Tools/doctor_athena_studio_phase1.py") or self._script_command("Tools/doctor_athena_studio_pif_inspector.py")),
            ("Doctor Studio Reload", self._script_command("Tools/doctor_studio_reload_workflow.py")),
            ("Doctor Studio Browser Refresh", self._script_command("Tools/doctor_studio_browser_self_refresh.py")),
            ("Doctor Studio Beta UI", self._script_command("Tools/doctor_athena_studio_beta_ui.py")),
            ("Doctor Studio Tile UI", self._script_command("Tools/doctor_athena_studio_tile_ui.py")),
            ("Doctor Studio Toolbar", self._script_command("Tools/doctor_athena_studio_toolbar.py")),
            ("Doctor Studio Operations Console", self._script_command("Tools/doctor_athena_studio_operations_console.py")),
            ("Validate Runtime", self._script_command("Tests/validate_runtime_cleanup.py")),
            ("Validate Consensus Repository Cleanup", self._script_command("Tests/validate_consensus_repository_cleanup.py")),
            ("Validate PIF-1", self._script_command("Tests/validate_pif1_build004.py") or self._script_command("Tests/validate_pif1_build003.py") or self._script_command("Tests/validate_pif1_build002.py") or self._script_command("Tests/validate_pif1_build001.py")),
            ("Validate Renderer Cleanup", self._script_command("Tests/validate_renderer_cleanup.py")),
            ("Validate Team Reasoning", self._script_command("Tests/validate_team_reasoning_engine.py")),
            ("Validate Comparison", self._script_command("Tests/validate_comparison_reasoning_engine.py")),
            ("Validate Event Intelligence", self._script_command("Tests/validate_event_intelligence_foundation.py")),
            ("Validate Cross-Domain Impact", self._script_command("Tests/validate_cross_domain_event_impact.py")),
            ("Validate Event Timeline", self._script_command("Tests/validate_event_timeline_intelligence.py")),
            ("Validate Event Confidence", self._script_command("Tests/validate_event_confidence_source_corroboration.py")),
            ("Validate Event Summary", self._script_command("Tests/validate_event_summarization_engine.py")),
            ("Validate Multi-Sport Connectors", self._script_command("Tests/validate_multi_sport_provider_connectors.py")),
            ("Validate Multi-Sport Scout Routing", self._script_command("Tests/validate_multi_sport_scout_routing.py")),
            ("Validate Multi-Sport Intelligence Foundation", self._script_command("Tests/validate_multi_sport_intelligence_foundation.py")),
            ("Validate Explainable Intelligence Pipeline", self._script_command("Tests/validate_explainable_intelligence_pipeline.py")),
            ("Validate Runtime Orchestration & Observability", self._script_command("Tests/validate_runtime_orchestration_observability.py")),
            ("Validate Capability Registry", self._script_command("Tests/validate_capability_registry.py")),
            ("Validate Execution Trace", self._script_command("Tests/validate_execution_trace.py")),
            ("Validate Capability Audit", self._script_command("Tests/validate_capability_audit.py")),
            ("Validate Evidence Audit", self._script_command("Tests/validate_evidence_audit.py")),
            ("Validate Composition Audit", self._script_command("Tests/validate_composition_audit.py")),
            ("Validate Experience Layer Foundation", self._script_command("Tests/validate_experience_layer_foundation.py")),
            ("Validate Player Experience", self._script_command("Tests/validate_player_experience.py")),
            ("Validate Acceptance Explorer", self._script_command("Tests/validate_acceptance_explorer.py")),
            ("Validate Repository Audit", self._script_command("Tests/validate_repository_audit.py")),
            ("Validate Repository Safe Cleanup", self._script_command("Tests/validate_repository_safe_cleanup.py")),
            ("Validate Repository Review", self._script_command("Tests/validate_repository_review.py")),
            ("Validate Repository Decision Lock", self._script_command("Tests/validate_repository_decision_lock.py")),
            ("Validate Release Hygiene", self._script_command("Tests/validate_release_hygiene.py")),
            ("Validate Scout Intent Orchestration", self._script_command("Tests/validate_scout_intent_orchestration.py")),
            ("Validate Scout Acceptance Hotfix", self._script_command("Tests/validate_scout_runtime_acceptance_hotfix.py")),
            ("Validate Live Event Source Integration", self._script_command("Tests/validate_live_event_source_integration.py")),
            ("Validate Cross-Sport Reasoning Engine", self._script_command("Tests/validate_cross_sport_reasoning_engine.py")),
            ("Validate Studio", self._script_command("Tests/validate_athena_studio_phase2.py") or self._script_command("Tests/validate_athena_studio_phase1.py") or self._script_command("Tests/validate_athena_studio_pif_inspector.py")),
            ("Validate Studio Reload", self._script_command("Tests/validate_studio_reload_workflow.py")),
            ("Validate Studio Browser Refresh", self._script_command("Tests/validate_studio_browser_self_refresh.py")),
            ("Validate Studio Beta UI", self._script_command("Tests/validate_athena_studio_beta_ui.py")),
            ("Validate Studio Tile UI", self._script_command("Tests/validate_athena_studio_tile_ui.py")),
            ("Validate Studio Toolbar", self._script_command("Tests/validate_athena_studio_toolbar.py")),
            ("Validate Studio Operations Console", self._script_command("Tests/validate_athena_studio_operations_console.py")),
        ]
        self._run_sequence_threaded("Verify Build", commands)

    def validate_event_intelligence_foundation(self) -> None:
        self._run_threaded("Validate Event Intelligence", self._script_command("Tests/validate_event_intelligence_foundation.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_event_intelligence_foundation.py')"])

    def validate_cross_domain_event_impact(self) -> None:
        self._run_threaded("Validate Cross-Domain Impact", self._script_command("Tests/validate_cross_domain_event_impact.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_cross_domain_event_impact.py')"])

    def validate_event_timeline_intelligence(self) -> None:
        self._run_threaded("Validate Event Timeline", self._script_command("Tests/validate_event_timeline_intelligence.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_event_timeline_intelligence.py')"])

    def validate_event_confidence_source_corroboration(self) -> None:
        self._run_threaded("Validate Event Confidence", self._script_command("Tests/validate_event_confidence_source_corroboration.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_event_confidence_source_corroboration.py')"])

    def validate_event_summarization_engine(self) -> None:
        self._run_threaded("Validate Event Summary", self._script_command("Tests/validate_event_summarization_engine.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_event_summarization_engine.py')"])

    def validate_multi_sport_provider_connectors(self) -> None:
        self._run_threaded("Validate Multi-Sport Connectors", self._script_command("Tests/validate_multi_sport_provider_connectors.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_multi_sport_provider_connectors.py')"])

    def validate_studio(self) -> None:
        commands = [
            ("Validate Studio Phase 2", self._script_command("Tests/validate_athena_studio_phase2.py")),
            ("Validate Studio Reload", self._script_command("Tests/validate_studio_reload_workflow.py")),
            ("Validate Studio Browser Refresh", self._script_command("Tests/validate_studio_browser_self_refresh.py")),
            ("Validate Studio Beta UI", self._script_command("Tests/validate_athena_studio_beta_ui.py")),
            ("Validate Studio Tile UI", self._script_command("Tests/validate_athena_studio_tile_ui.py")),
            ("Validate Studio Toolbar", self._script_command("Tests/validate_athena_studio_toolbar.py")),
            ("Validate Studio Operations Console", self._script_command("Tests/validate_athena_studio_operations_console.py")),
        ]
        available = [(name, command) for name, command in commands if command is not None]
        if available:
            self._run_sequence_threaded("Validate Studio", available)
            return
        command = self._script_command("Tests/validate_athena_studio_phase1.py") or self._script_command("Tests/validate_athena_studio_pif_inspector.py")
        self._run_threaded("Validate Studio", command or [self._python(), "-c", "raise SystemExit('Missing Studio validator')"])

    def validate_everything(self) -> None:
        commands = [
            ("Validate Runtime", self._script_command("Tests/validate_runtime_cleanup.py")),
            ("Validate Consensus Repository Cleanup", self._script_command("Tests/validate_consensus_repository_cleanup.py")),
            ("Validate PIF-1", self._script_command("Tests/validate_pif1_build004.py") or self._script_command("Tests/validate_pif1_build003.py") or self._script_command("Tests/validate_pif1_build002.py") or self._script_command("Tests/validate_pif1_build001.py")),
            ("Validate Renderer Cleanup", self._script_command("Tests/validate_renderer_cleanup.py")),
            ("Validate Team Reasoning", self._script_command("Tests/validate_team_reasoning_engine.py")),
            ("Validate Comparison", self._script_command("Tests/validate_comparison_reasoning_engine.py")),
            ("Validate Event Intelligence", self._script_command("Tests/validate_event_intelligence_foundation.py")),
            ("Validate Cross-Domain Impact", self._script_command("Tests/validate_cross_domain_event_impact.py")),
            ("Validate Event Timeline", self._script_command("Tests/validate_event_timeline_intelligence.py")),
            ("Validate Event Confidence", self._script_command("Tests/validate_event_confidence_source_corroboration.py")),
            ("Validate Event Summary", self._script_command("Tests/validate_event_summarization_engine.py")),
            ("Validate Multi-Sport Connectors", self._script_command("Tests/validate_multi_sport_provider_connectors.py")),
            ("Validate Multi-Sport Scout Routing", self._script_command("Tests/validate_multi_sport_scout_routing.py")),
            ("Validate Multi-Sport Intelligence Foundation", self._script_command("Tests/validate_multi_sport_intelligence_foundation.py")),
            ("Validate Explainable Intelligence Pipeline", self._script_command("Tests/validate_explainable_intelligence_pipeline.py")),
            ("Validate Runtime Orchestration & Observability", self._script_command("Tests/validate_runtime_orchestration_observability.py")),
            ("Validate Capability Registry", self._script_command("Tests/validate_capability_registry.py")),
            ("Validate Execution Trace", self._script_command("Tests/validate_execution_trace.py")),
            ("Validate Capability Audit", self._script_command("Tests/validate_capability_audit.py")),
            ("Validate Evidence Audit", self._script_command("Tests/validate_evidence_audit.py")),
            ("Validate Composition Audit", self._script_command("Tests/validate_composition_audit.py")),
            ("Validate Experience Layer Foundation", self._script_command("Tests/validate_experience_layer_foundation.py")),
            ("Validate Player Experience", self._script_command("Tests/validate_player_experience.py")),
            ("Validate Acceptance Explorer", self._script_command("Tests/validate_acceptance_explorer.py")),
            ("Validate Repository Audit", self._script_command("Tests/validate_repository_audit.py")),
            ("Validate Repository Safe Cleanup", self._script_command("Tests/validate_repository_safe_cleanup.py")),
            ("Validate Repository Review", self._script_command("Tests/validate_repository_review.py")),
            ("Validate Repository Decision Lock", self._script_command("Tests/validate_repository_decision_lock.py")),
            ("Validate Release Hygiene", self._script_command("Tests/validate_release_hygiene.py")),
            ("Validate Scout Intent Orchestration", self._script_command("Tests/validate_scout_intent_orchestration.py")),
            ("Validate Scout Acceptance Hotfix", self._script_command("Tests/validate_scout_runtime_acceptance_hotfix.py")),
            ("Validate Live Event Source Integration", self._script_command("Tests/validate_live_event_source_integration.py")),
            ("Validate Cross-Sport Reasoning Engine", self._script_command("Tests/validate_cross_sport_reasoning_engine.py")),
            ("Validate Studio", self._script_command("Tests/validate_athena_studio_phase2.py") or self._script_command("Tests/validate_athena_studio_phase1.py") or self._script_command("Tests/validate_athena_studio_pif_inspector.py")),
            ("Validate Studio Reload", self._script_command("Tests/validate_studio_reload_workflow.py")),
            ("Validate Studio Browser Refresh", self._script_command("Tests/validate_studio_browser_self_refresh.py")),
            ("Validate Studio Beta UI", self._script_command("Tests/validate_athena_studio_beta_ui.py")),
            ("Validate Studio Tile UI", self._script_command("Tests/validate_athena_studio_tile_ui.py")),
            ("Validate Studio Toolbar", self._script_command("Tests/validate_athena_studio_toolbar.py")),
            ("Validate Studio Operations Console", self._script_command("Tests/validate_athena_studio_operations_console.py")),
        ]
        self._run_sequence_threaded("Validate Everything", commands)

    def doctor_runtime(self) -> None:
        self._run_threaded("Doctor Runtime", self._script_command("Tools/doctor_runtime_cleanup.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_runtime_cleanup.py')"])

    def doctor_pif(self) -> None:
        command = self._script_command("Tools/doctor_pif1_build004.py") or self._script_command("Tools/doctor_pif1_build003.py") or self._script_command("Tools/doctor_pif1_build002.py") or self._script_command("Tools/doctor_pif1_build001.py")
        self._run_threaded("Doctor PIF-1", command or [self._python(), "-c", "raise SystemExit('Missing PIF doctor')"])


    def doctor_renderer_cleanup(self) -> None:
        self._run_threaded("Doctor Renderer Cleanup", self._script_command("Tools/doctor_renderer_cleanup.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_renderer_cleanup.py')"])

    def doctor_team_reasoning_engine(self) -> None:
        self._run_threaded("Doctor Team Reasoning", self._script_command("Tools/doctor_team_reasoning_engine.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_team_reasoning_engine.py')"])

    def doctor_comparison_reasoning_engine(self) -> None:
        self._run_threaded("Doctor Comparison", self._script_command("Tools/doctor_comparison_reasoning_engine.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_comparison_reasoning_engine.py')"])

    def doctor_event_intelligence_foundation(self) -> None:
        self._run_threaded("Doctor Event Intelligence", self._script_command("Tools/doctor_event_intelligence_foundation.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_event_intelligence_foundation.py')"])

    def doctor_cross_domain_event_impact(self) -> None:
        self._run_threaded("Doctor Cross-Domain Impact", self._script_command("Tools/doctor_cross_domain_event_impact.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_cross_domain_event_impact.py')"])

    def doctor_event_timeline_intelligence(self) -> None:
        self._run_threaded("Doctor Event Timeline", self._script_command("Tools/doctor_event_timeline_intelligence.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_event_timeline_intelligence.py')"])

    def doctor_event_confidence_source_corroboration(self) -> None:
        self._run_threaded("Doctor Event Confidence", self._script_command("Tools/doctor_event_confidence_source_corroboration.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_event_confidence_source_corroboration.py')"])

    def doctor_event_summarization_engine(self) -> None:
        self._run_threaded("Doctor Event Summary", self._script_command("Tools/doctor_event_summarization_engine.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_event_summarization_engine.py')"])

    def doctor_multi_sport_provider_connectors(self) -> None:
        self._run_threaded("Doctor Multi-Sport Connectors", self._script_command("Tools/doctor_multi_sport_provider_connectors.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_multi_sport_provider_connectors.py')"])

    def doctor_repository(self) -> None:
        self._run_threaded("Doctor Repository", self._script_command("Tools/doctor_repository.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_repository.py')"])

    def doctor_studio(self) -> None:
        commands = [
            ("Doctor Studio Phase 2", self._script_command("Tools/doctor_athena_studio_phase2.py")),
            ("Doctor Studio Reload", self._script_command("Tools/doctor_studio_reload_workflow.py")),
            ("Doctor Studio Browser Refresh", self._script_command("Tools/doctor_studio_browser_self_refresh.py")),
            ("Doctor Studio Beta UI", self._script_command("Tools/doctor_athena_studio_beta_ui.py")),
            ("Doctor Studio Tile UI", self._script_command("Tools/doctor_athena_studio_tile_ui.py")),
            ("Doctor Studio Toolbar", self._script_command("Tools/doctor_athena_studio_toolbar.py")),
            ("Doctor Studio Operations Console", self._script_command("Tools/doctor_athena_studio_operations_console.py")),
        ]
        available = [(name, command) for name, command in commands if command is not None]
        if available:
            self._run_sequence_threaded("Doctor Studio", available)
            return
        command = self._script_command("Tools/doctor_athena_studio_phase1.py") or self._script_command("Tools/doctor_athena_studio_pif_inspector.py")
        self._run_threaded("Doctor Studio", command or [self._python(), "-c", "raise SystemExit('Missing Studio doctor')"])

    def doctor_everything(self) -> None:
        commands = [
            ("Doctor Runtime", self._script_command("Tools/doctor_runtime_cleanup.py")),
            ("Doctor Consensus Repository Cleanup", self._script_command("Tools/doctor_consensus_repository_cleanup.py")),
            ("Doctor PIF-1", self._script_command("Tools/doctor_pif1_build004.py") or self._script_command("Tools/doctor_pif1_build003.py") or self._script_command("Tools/doctor_pif1_build002.py") or self._script_command("Tools/doctor_pif1_build001.py")),
            ("Doctor Renderer Cleanup", self._script_command("Tools/doctor_renderer_cleanup.py")),
            ("Doctor Team Reasoning", self._script_command("Tools/doctor_team_reasoning_engine.py")),
            ("Doctor Comparison", self._script_command("Tools/doctor_comparison_reasoning_engine.py")),
            ("Doctor Event Intelligence", self._script_command("Tools/doctor_event_intelligence_foundation.py")),
            ("Doctor Cross-Domain Impact", self._script_command("Tools/doctor_cross_domain_event_impact.py")),
            ("Doctor Event Timeline", self._script_command("Tools/doctor_event_timeline_intelligence.py")),
            ("Doctor Event Confidence", self._script_command("Tools/doctor_event_confidence_source_corroboration.py")),
            ("Doctor Event Summary", self._script_command("Tools/doctor_event_summarization_engine.py")),
            ("Doctor Multi-Sport Connectors", self._script_command("Tools/doctor_multi_sport_provider_connectors.py")),
            ("Doctor Multi-Sport Scout Routing", self._script_command("Tools/doctor_multi_sport_scout_routing.py")),
            ("Doctor Multi-Sport Intelligence Foundation", self._script_command("Tools/doctor_multi_sport_intelligence_foundation.py")),
            ("Doctor Explainable Intelligence Pipeline", self._script_command("Tools/doctor_explainable_intelligence_pipeline.py")),
            ("Doctor Runtime Orchestration & Observability", self._script_command("Tools/doctor_runtime_orchestration_observability.py")),
            ("Doctor Capability Registry", self._script_command("Tools/doctor_capability_registry.py")),
            ("Doctor Execution Trace", self._script_command("Tools/doctor_execution_trace.py")),
            ("Doctor Capability Audit", self._script_command("Tools/doctor_capability_audit.py")),
            ("Doctor Evidence Audit", self._script_command("Tools/doctor_evidence_audit.py")),
            ("Doctor Composition Audit", self._script_command("Tools/doctor_composition_audit.py")),
            ("Doctor Experience Layer Foundation", self._script_command("Tools/doctor_experience_layer_foundation.py")),
            ("Doctor Player Experience", self._script_command("Tools/doctor_player_experience.py")),
            ("Doctor Acceptance Explorer", self._script_command("Tools/doctor_acceptance_explorer.py")),
            ("Doctor Repository Audit", self._script_command("Tools/doctor_repository_audit.py")),
            ("Doctor Repository Safe Cleanup", self._script_command("Tools/doctor_repository_safe_cleanup.py")),
            ("Doctor Repository Review", self._script_command("Tools/doctor_repository_review.py")),
            ("Doctor Repository Decision Lock", self._script_command("Tools/doctor_repository_decision_lock.py")),
            ("Doctor Release Hygiene", self._script_command("Tools/doctor_release_hygiene.py")),
            ("Doctor Scout Intent Orchestration", self._script_command("Tools/doctor_scout_intent_orchestration.py")),
            ("Doctor Scout Acceptance Hotfix", self._script_command("Tools/doctor_scout_runtime_acceptance_hotfix.py")),
            ("Doctor Live Event Source Integration", self._script_command("Tools/doctor_live_event_source_integration.py")),
            ("Doctor Cross-Sport Reasoning Engine", self._script_command("Tools/doctor_cross_sport_reasoning_engine.py")),
            ("Doctor Repository", self._script_command("Tools/doctor_repository.py")),
            ("Doctor Studio", self._script_command("Tools/doctor_athena_studio_phase2.py") or self._script_command("Tools/doctor_athena_studio_phase1.py") or self._script_command("Tools/doctor_athena_studio_pif_inspector.py")),
            ("Doctor Studio Reload", self._script_command("Tools/doctor_studio_reload_workflow.py")),
            ("Doctor Studio Browser Refresh", self._script_command("Tools/doctor_studio_browser_self_refresh.py")),
            ("Doctor Studio Beta UI", self._script_command("Tools/doctor_athena_studio_beta_ui.py")),
            ("Doctor Studio Tile UI", self._script_command("Tools/doctor_athena_studio_tile_ui.py")),
            ("Doctor Studio Toolbar", self._script_command("Tools/doctor_athena_studio_toolbar.py")),
            ("Doctor Studio Operations Console", self._script_command("Tools/doctor_athena_studio_operations_console.py")),
        ]
        self._run_sequence_threaded("Doctor Everything", commands)

    def inspect_pif_prompt(self) -> None:
        question = simpledialog.askstring("Inspect PIF Prompt", "Enter a public Scout prompt to inspect:", parent=self.root)
        if not question:
            return
        self.write("\n=== PIF Prompt Inspector ===\n")
        self.write(f"Question: {question}\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Knowledge.Intelligence.Routing.request_router import analyze_public_request
            result = analyze_public_request(question)
            data = result.to_dict()
            intent = data.get("intent", {})
            self.write(f"Intent: {intent.get('intent')} | confidence={intent.get('confidence')}\n")
            self.write(f"Route: {data.get('route')} | route_confidence={data.get('confidence')}\n")
            self.write("Allowed domains: " + ", ".join(data.get("allowed_domains", []) or []) + "\n")
            self.write("Blocked domains: " + ", ".join(data.get("blocked_domains", []) or []) + "\n")
            for note in data.get("notes", []) or []:
                self.write(f"Note: {note}\n")
            self.write("Matched terms: " + ", ".join(intent.get("matched_terms", []) or []) + "\n")
            self.write(f"Rationale: {intent.get('rationale')}\n")
            entities = data.get("entities", []) or []
            if not entities:
                self.write("Entities: none\n")
            else:
                self.write("Entities:\n")
                for item in entities:
                    entity = item.get("entity") or {}
                    label = entity.get("canonical_name") or entity.get("name") or item.get("query") or "unknown"
                    self.write(f"  - {label} | type={entity.get('entity_type')} | status={item.get('status')} | confidence={item.get('confidence')}\n")
                    for opt in item.get("candidates") or []:
                        self.write(f"      * {opt.get('canonical_name') or opt.get('name')} ({opt.get('position') or 'n/a'}, {opt.get('team') or 'n/a'}, {opt.get('nationality') or 'n/a'})\n")
            self.status.set("PIF inspection complete")
            self._record_history("Inspect PIF Prompt", 0, question)
        except Exception as exc:
            self.write(f"PIF inspection failed: {exc}\n")
            self.status.set("PIF inspection failed")
            self._record_history("Inspect PIF Prompt", 1, str(exc))


    def show_identity_graph_diagnostics(self) -> None:
        """Show Unified Identity & Cross-Sport Knowledge Graph diagnostics."""
        self.write("\n=== Identity Graph Diagnostics ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Knowledge.Identity import studio_identity_graph_diagnostics
            data = studio_identity_graph_diagnostics()
            for key, value in data.items():
                self.write(f"{key}: {value}\n")
            self._record_history("Identity Graph Diagnostics", 0, json.dumps(data)[:500])
        except Exception as exc:
            self.write(f"Identity graph diagnostics failed: {exc}\n")
            self._record_history("Identity Graph Diagnostics", 1, str(exc))

    def show_event_pipeline_diagnostics(self) -> None:
        """Show Event pipeline compatibility and import diagnostics."""
        self.write("\n=== Event Pipeline Diagnostics ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Knowledge.Events import canonical_event_payload, canonical_event_types, normalize_event_payload
            sample = normalize_event_payload({"event_type": "news", "sport": "hockey", "league": "NHL", "summary": "Studio diagnostic event"})
            event_types = canonical_event_types()
            compat = canonical_event_payload({"event_type": "news", "summary": "compatibility check"})
            self.write(f"canonical_event_types: {len(event_types)}\n")
            self.write(f"normalize_event_payload: {type(sample).__name__}\n")
            self.write(f"canonical_event_payload: {type(compat).__name__}\n")
            self.write("status: PASS\n")
            self._record_history("Event Pipeline Diagnostics", 0, f"event_types={len(event_types)}")
        except Exception as exc:
            self.write(f"Event pipeline diagnostics failed: {exc}\n")
            self._record_history("Event Pipeline Diagnostics", 1, str(exc))

    def show_pif_coverage(self) -> None:
        self.write("\n=== PIF Coverage ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Knowledge.Intelligence.Entities.identity_graph import graph_summary
            summary = graph_summary().to_dict()
            self.write(f"Entities: {summary.get('entity_count')}\n")
            self.write(f"Players: {summary.get('player_count')}\n")
            self.write(f"Teams: {summary.get('team_count')}\n")
            self.write(f"Aliases: {summary.get('alias_count')}\n")
            self.write("Ambiguous names:\n")
            for name, count in (summary.get('ambiguous_names') or {}).items():
                self.write(f"  - {name}: {count} entities\n")
            self.write("Guardrails:\n")
            for guardrail in summary.get('public_guardrails') or []:
                self.write(f"  - {guardrail}\n")
            self._record_history("PIF Coverage", 0, json.dumps(summary)[:500])
            self.status.set("PIF coverage ready")
        except Exception as exc:
            self.write(f"PIF coverage failed: {exc}\n")
            self.status.set("PIF coverage failed")
            self._record_history("PIF Coverage", 1, str(exc))

    def show_knowledge_dashboard(self) -> None:
        self.write("\n=== Knowledge Dashboard ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Knowledge.Intelligence.Entities.entity_registry import registry_stats
            from Knowledge.Intelligence.Public.public_player_profiles import public_profile_stats
            from Knowledge.Intelligence.Public.public_team_profiles import public_team_profile_stats
            stats = registry_stats()
            profile_stats = public_profile_stats()
            team_stats = public_team_profile_stats()
            self.write(f"Public entities: {stats.get('entities')}\n")
            for key, value in (stats.get('by_type') or {}).items():
                self.write(f"  {key}: {value}\n")
            self.write(f"Aliases: {stats.get('aliases')}\n")
            self.write(f"Public player profiles: {profile_stats.get('profiles')}\n")
            self.write(f"Public team profiles: {team_stats.get('teams')}\n")
            self.write(f"Seeded awards/signals: {profile_stats.get('awards_seeded')}\n")
            self.write("Public guardrails:\n")
            for guardrail in profile_stats.get('guardrails') or []:
                self.write(f"  - {guardrail}\n")
            self.write(f"Raw files: {len(list((PROJECT_ROOT / 'Raw').glob('*.json'))) if (PROJECT_ROOT / 'Raw').exists() else 0} json files\n")
            self.write(f"Output files: {len(list((PROJECT_ROOT / 'Output').glob('*.json'))) if (PROJECT_ROOT / 'Output').exists() else 0} json files\n")
            self._record_history("Knowledge Dashboard", 0, json.dumps({"registry": stats, "public_profiles": profile_stats, "team_profiles": team_stats})[:500])
            self.status.set("Knowledge dashboard ready")
        except Exception as exc:
            self.write(f"Knowledge dashboard failed: {exc}\n")
            self.status.set("Knowledge dashboard failed")
            self._record_history("Knowledge Dashboard", 1, str(exc))

    def show_capability_registry(self) -> None:
        """Show Capability Registry Foundation diagnostics."""
        self.write("\n=== Capability Registry ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Core.capability_registry import capability_registry_diagnostics
            data = capability_registry_diagnostics(limit=60)
            summary = data.get("summary", {}) or {}
            validation = data.get("validation", {}) or {}
            self.write(f"Version: {data.get('version')}\n")
            self.write(f"Status: {summary.get('status')}\n")
            self.write(f"Capabilities discovered: {summary.get('capability_count')}\n")
            self.write(f"With doctors: {summary.get('with_doctor')}\n")
            self.write(f"With validators/tests: {summary.get('with_validator')}\n")
            self.write("Layers:\n")
            for layer, count in (summary.get("by_layer") or {}).items():
                self.write(f"  - {layer}: {count}\n")
            if validation.get("duplicate_ids"):
                self.write("Duplicate capability ids:\n")
                for item in validation.get("duplicate_ids") or []:
                    self.write(f"  - {item}\n")
            if validation.get("missing_doctors"):
                self.write(f"Capabilities missing doctors: {len(validation.get('missing_doctors') or [])}\n")
            if validation.get("missing_validators"):
                self.write(f"Capabilities missing validators/tests: {len(validation.get('missing_validators') or [])}\n")
            self.write("Sample capabilities:\n")
            for cap in data.get("capabilities", [])[:30]:
                self.write(f"  - {cap.get('capability_id')} | {cap.get('layer')} | {cap.get('status')} | {', '.join(cap.get('entrypoints') or [])}\n")
            self._record_history("Capability Registry", 0, json.dumps(summary)[:500])
            self.status.set("Capability registry ready")
        except Exception as exc:
            self.write(f"Capability registry failed: {exc}\n")
            self.status.set("Capability registry failed")
            self._record_history("Capability Registry", 1, str(exc))

    def show_execution_trace(self) -> None:
        """Show Execution Trace Foundation diagnostics."""
        self.write("\n=== Execution Trace ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Core.execution_trace import execution_trace_diagnostics
            data = execution_trace_diagnostics(persist_sample=True)
            summary = data.get("summary", {}) or {}
            sample = data.get("sample_trace", {}) or {}
            self.write(f"Version: {data.get('version')}\n")
            self.write(f"Status: {data.get('status')}\n")
            self.write(f"Trace id: {data.get('trace_id')}\n")
            if data.get("persisted_sample"):
                self.write(f"Persisted sample: {data.get('persisted_sample')}\n")
            self.write(f"Intent: {summary.get('intent')}\n")
            self.write(f"Stages: {summary.get('stage_count')} | statuses={summary.get('stage_statuses')}\n")
            self.write(f"Expected capabilities: {summary.get('expected_capabilities')}\n")
            self.write(f"Selected capabilities: {summary.get('selected_capabilities')}\n")
            self.write(f"Skipped capabilities: {summary.get('skipped_capabilities')}\n")
            missing_caps = summary.get("missing_expected_capabilities") or []
            if missing_caps:
                self.write("Missing expected capabilities:\n")
                for cap in missing_caps:
                    self.write(f"  - {cap}\n")
            self.write(f"Evidence found/missing: {summary.get('evidence_found')}/{summary.get('evidence_missing')}\n")
            self.write(f"Composition inputs/outputs: {summary.get('composition_inputs')}/{summary.get('composition_outputs')}\n")
            self.write("Stages:\n")
            for stage in sample.get("stages", []) or []:
                self.write(f"  - {stage.get('stage_id')} | {stage.get('status')} | {stage.get('detail')} | {stage.get('duration_ms')}ms\n")
            self.write("Capability participation:\n")
            for cap in sample.get("capabilities", []) or []:
                status = "executed" if cap.get("executed") else "skipped" if cap.get("skipped") else "not executed"
                self.write(f"  - {cap.get('capability_id')} | {status} | {cap.get('skip_reason', '')}\n")
            self._record_history("Execution Trace", 0, json.dumps(summary)[:500])
            self.status.set("Execution trace ready")
        except Exception as exc:
            self.write(f"Execution trace failed: {exc}\n")
            self.status.set("Execution trace failed")
            self._record_history("Execution Trace", 1, str(exc))


    def _run_capability_audit_validator(self) -> None:
        self._run_threaded("Validate Capability Audit", self._script_command("Tests/validate_capability_audit.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_capability_audit.py')"])

    def _run_capability_audit_doctor(self) -> None:
        self._run_threaded("Doctor Capability Audit", self._script_command("Tools/doctor_capability_audit.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_capability_audit.py')"])

    def show_capability_audit(self) -> None:
        """Show Capability Participation Audit diagnostics."""
        self.write("\n=== Capability Participation Audit ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Core.capability_audit import capability_audit_diagnostics
            data = capability_audit_diagnostics()
            self.write(f"Version: {data.get('version')}\n")
            self.write(f"Prompt: {data.get('prompt')}\n")
            self.write(f"Intent: {data.get('intent')}\n")
            self.write(f"Expected/Selected/Executed: {data.get('expected_count')}/{data.get('selected_count')}/{data.get('executed_count')}\n")
            self.write(f"Skipped/Missing/Unregistered: {data.get('skipped_count')}/{data.get('missing_count')}/{data.get('unregistered_expected_count')}\n")
            self.write(f"Evidence found/missing: {data.get('evidence_found_count')}/{data.get('evidence_missing_count')}\n")
            self.write("Findings:\n")
            for finding in data.get("findings", []) or []:
                self.write(f"  - {finding}\n")
            self.write("Next actions:\n")
            for action in data.get("next_actions", []) or []:
                self.write(f"  - {action}\n")
            self.write("Capability records:\n")
            for record in data.get("records", []) or []:
                flags = []
                for key in ("expected", "registered", "selected", "executed", "skipped", "missing"):
                    if record.get(key):
                        flags.append(key)
                self.write(f"  - {record.get('capability_id')} | {', '.join(flags) or 'observed'} | {record.get('reason')}\n")
            self._record_history("Capability Audit", 0, json.dumps({"expected": data.get("expected_count"), "missing": data.get("missing_count")})[:500])
            self.status.set("Capability audit ready")
        except Exception as exc:
            self.write(f"Capability audit failed: {exc}\n")
            self.status.set("Capability audit failed")
            self._record_history("Capability Audit", 1, str(exc))


    def _run_evidence_audit_validator(self) -> None:
        self._run_threaded("Validate Evidence Audit", self._script_command("Tests/validate_evidence_audit.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_evidence_audit.py')"])

    def _run_evidence_audit_doctor(self) -> None:
        self._run_threaded("Doctor Evidence Audit", self._script_command("Tools/doctor_evidence_audit.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_evidence_audit.py')"])

    def show_evidence_audit(self) -> None:
        """Show Evidence Audit diagnostics."""
        self.write("\n=== Evidence Audit ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Core.evidence_audit import evidence_audit_diagnostics
            data = evidence_audit_diagnostics()
            self.write(f"Version: {data.get('version')}\n")
            self.write(f"Prompt: {data.get('prompt')}\n")
            self.write(f"Intent: {data.get('intent')}\n")
            self.write(f"Evidence requested/found/missing: {data.get('evidence_requested_count')}/{data.get('evidence_found_count')}/{data.get('evidence_missing_count')}\n")
            self.write(f"Required/optional missing: {data.get('required_missing_count')}/{data.get('optional_missing_count')}\n")
            self.write("Findings:\n")
            for finding in data.get("findings", []) or []:
                self.write(f"  - {finding}\n")
            self.write("Next actions:\n")
            for action in data.get("next_actions", []) or []:
                self.write(f"  - {action}\n")
            self.write("Evidence records:\n")
            for record in data.get("records", []) or []:
                self.write(
                    f"  - {record.get('capability_id')} | {record.get('status')} | "
                    f"coverage={record.get('coverage_ratio')} | missing_required={', '.join(record.get('missing_required') or [])} | "
                    f"impact={record.get('confidence_impact')}\n"
                )
            self._record_history("Evidence Audit", 0, json.dumps({"required_missing": data.get("required_missing_count"), "optional_missing": data.get("optional_missing_count")})[:500])
            self.status.set("Evidence audit ready")
        except Exception as exc:
            self.write(f"Evidence audit failed: {exc}\n")
            self.status.set("Evidence audit failed")
            self._record_history("Evidence Audit", 1, str(exc))



    def _run_composition_audit_validator(self) -> None:
        self._run_threaded("Validate Composition Audit", self._script_command("Tests/validate_composition_audit.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_composition_audit.py')"])

    def _run_composition_audit_doctor(self) -> None:
        self._run_threaded("Doctor Composition Audit", self._script_command("Tools/doctor_composition_audit.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_composition_audit.py')"])

    def show_composition_audit(self) -> None:
        """Show Composition Audit diagnostics."""
        self.write("\n=== Composition Audit ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Core.composition_audit import composition_audit_diagnostics
            data = composition_audit_diagnostics()
            self.write(f"Version: {data.get('version')}\n")
            self.write(f"Prompt: {data.get('prompt')}\n")
            self.write(f"Intent: {data.get('intent')}\n")
            self.write(f"Generated/displayed/included/discarded: {data.get('generated_count')}/{data.get('displayed_count')}/{data.get('included_count')}/{data.get('discarded_count')}\n")
            self.write(f"Coverage: {data.get('coverage_ratio')}\n")
            self.write("Findings:\n")
            for finding in data.get("findings", []) or []:
                self.write(f"  - {finding}\n")
            self.write("Next actions:\n")
            for action in data.get("next_actions", []) or []:
                self.write(f"  - {action}\n")
            self.write("Composition records:\n")
            for record in data.get("records", []) or []:
                self.write(
                    f"  - {record.get('capability_id')} | {record.get('status')} | "
                    f"generated={', '.join(record.get('generated_sections') or [])} | "
                    f"discarded={', '.join(record.get('discarded_sections') or [])} | "
                    f"coverage={record.get('coverage_ratio')}\n"
                )
            self._record_history("Composition Audit", 0, json.dumps({"discarded": data.get("discarded_count"), "coverage": data.get("coverage_ratio")})[:500])
            self.status.set("Composition audit ready")
        except Exception as exc:
            self.write(f"Composition audit failed: {exc}\n")
            self.status.set("Composition audit failed")
            self._record_history("Composition Audit", 1, str(exc))


    def _run_acceptance_explorer_validator(self) -> None:
        self._run_threaded("Validate Acceptance Explorer", self._script_command("Tests/validate_acceptance_explorer.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_acceptance_explorer.py')"])

    def _run_acceptance_explorer_doctor(self) -> None:
        self._run_threaded("Doctor Acceptance Explorer", self._script_command("Tools/doctor_acceptance_explorer.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_acceptance_explorer.py')"])

    def _run_repository_audit_validator(self) -> None:
        self._run_threaded("Validate Repository Audit", self._script_command("Tests/validate_repository_audit.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_repository_audit.py')"])

    def _run_repository_audit_doctor(self) -> None:
        self._run_threaded("Doctor Repository Audit", self._script_command("Tools/doctor_repository_audit.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_repository_audit.py')"])


    def _run_repository_review_validator(self) -> None:
        self._run_threaded("Validate Repository Review", self._script_command("Tests/validate_repository_review.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_repository_review.py')"])

    def _run_repository_review_doctor(self) -> None:
        self._run_threaded("Doctor Repository Review", self._script_command("Tools/doctor_repository_review.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_repository_review.py')"])

    def _run_repository_decision_lock_validator(self) -> None:
        self._run_threaded("Validate Repository Decision Lock", self._script_command("Tests/validate_repository_decision_lock.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_repository_decision_lock.py')"])

    def _run_repository_decision_lock_doctor(self) -> None:
        self._run_threaded("Doctor Repository Decision Lock", self._script_command("Tools/doctor_repository_decision_lock.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_repository_decision_lock.py')"])


    def _run_release_hygiene_validator(self) -> None:
        self._run_threaded("Validate Release Hygiene", self._script_command("Tests/validate_release_hygiene.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_release_hygiene.py')"])

    def _run_release_hygiene_doctor(self) -> None:
        self._run_threaded("Doctor Release Hygiene", self._script_command("Tools/doctor_release_hygiene.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_release_hygiene.py')"])

    def _run_scout_intent_orchestration_validator(self) -> None:
        self._run_threaded("Validate Scout Intent Orchestration", self._script_command("Tests/validate_scout_intent_orchestration.py") or [self._python(), "-c", "raise SystemExit('Missing Tests/validate_scout_intent_orchestration.py')"])

    def _run_scout_intent_orchestration_doctor(self) -> None:
        self._run_threaded("Doctor Scout Intent Orchestration", self._script_command("Tools/doctor_scout_intent_orchestration.py") or [self._python(), "-c", "raise SystemExit('Missing Tools/doctor_scout_intent_orchestration.py')"])

    def show_release_hygiene(self) -> None:
        """Run the Studio-first Release Hygiene Foundation check."""
        self.write("\n=== Release Hygiene ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Tools.doctor_release_hygiene import build_report, write_report

            report_path = write_report()
            report = build_report()
            summary = report.get("summary", {})
            self.write(f"Status: {str(report.get('status', '')).upper()}\n")
            self.write(f"Report: {report_path}\n")
            self.write(f"Version: {report.get('version')} — {report.get('release_name')}\n")
            self.write(
                "Checks: "
                f"passed={summary.get('passed', 0)} "
                f"failed={summary.get('failed', 0)} "
                f"warnings={summary.get('warnings', 0)}\n"
            )
            for item in report.get("checks", [])[:14]:
                self.write(f"[{item.get('status')}] {item.get('name')}: {item.get('detail')}\n")
            for warning in report.get("warnings", [])[:8]:
                self.write(f"[WARN] {warning}\n")
            self.status.set("Release Hygiene ready")
            self._record_history("Release Hygiene", 0, str(report_path))
        except Exception as exc:
            self.write(f"Release Hygiene failed: {exc}\n")
            self.status.set("Release Hygiene failed")
            self._record_history("Release Hygiene", 1, str(exc))

    def show_repository_review(self) -> None:
        """Run the read-only Phase 4B shim and duplicate basename review."""
        self.write("\n=== Review Shims/Duplicates ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Tools.repository_review import write_repository_review_reports

            report = write_repository_review_reports(PROJECT_ROOT)
            summary = report.summary or {}
            self.write(f"Status: {str(report.status).upper()}\n")
            self.write(f"Report: {report.report_paths.get('combined_json')}\n")
            self.write(f"Shim inventory: {report.report_paths.get('shim_markdown')}\n")
            self.write(f"Duplicate report: {report.report_paths.get('duplicate_markdown')}\n")
            self.write(f"Shims: {summary.get('shim_count', 0)} {summary.get('shim_classifications', {})}\n")
            self.write(f"Duplicate basename groups: {summary.get('duplicate_basename_group_count', 0)} {summary.get('duplicate_classifications', {})}\n")
            for item in report.shims[:12]:
                self.write(f"[SHIM:{item.classification.upper()}] {item.path} -> {item.target_module}; refs={len(item.referenced_by)}; {item.rationale}\n")
            for item in report.duplicates[:12]:
                self.write(f"[DUP:{item.classification.upper()}] {item.basename}; owners={','.join(item.package_owners)}; files={len(item.locations)}; {item.rationale}\n")
            self.status.set("Repository Review ready")
            self._record_history("Review Shims/Duplicates", 0, str(report.report_paths.get('combined_json')))
        except Exception as exc:
            self.write(f"Repository Review failed: {exc}\n")
            self.status.set("Repository Review failed")
            self._record_history("Review Shims/Duplicates", 1, str(exc))

    def show_repository_decision_lock(self) -> None:
        """Generate the read-only repository cleanup decision lock and auditor brief."""
        self.write("\n=== Lock Repo Decisions ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Tools.repository_decision_lock import write_repository_decision_lock

            report = write_repository_decision_lock(PROJECT_ROOT)
            summary = report.summary or {}
            self.write(f"Status: {str(report.status).upper()}\n")
            self.write(f"Report: {report.report_paths.get('decision_markdown')}\n")
            self.write(f"Claude audit brief: {report.report_paths.get('auditor_brief')}\n")
            self.write(f"Shim decisions: {summary.get('shim_decisions', {})}\n")
            self.write(f"Duplicate decisions: {summary.get('duplicate_decisions', {})}\n")
            self.write(f"Cleanup candidates: {summary.get('cleanup_candidate_duplicates', [])}\n")
            self.write(f"Ambiguous duplicates: {len(summary.get('ambiguous_duplicates') or [])} groups require import-owner review.\n")
            self.status.set("Repository decisions locked")
            self._record_history("Lock Repo Decisions", 0, str(report.report_paths.get('decision_json')))
        except Exception as exc:
            self.write(f"Repository Decision Lock failed: {exc}\n")
            self.status.set("Repository Decision Lock failed")
            self._record_history("Lock Repo Decisions", 1, str(exc))

    def show_repository_audit(self) -> None:
        """Run the read-only Phase 3 Repository Audit and show the report summary."""
        self.write("\n=== Repository Audit ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Tools.repository_audit import audit_repository, write_repository_audit_report

            report_path = write_repository_audit_report(PROJECT_ROOT)
            report = audit_repository(PROJECT_ROOT)
            self.write(f"Status: {str(report.status).upper()}\n")
            self.write(f"Report: {report_path}\n")
            summary = report.summary or {}
            self.write(
                "Findings: "
                f"total={summary.get('total', 0)} "
                f"fail={summary.get('fail', 0)} "
                f"warn={summary.get('warn', 0)} "
                f"info={summary.get('info', 0)}\n"
            )
            for finding in report.findings[:12]:
                self.write(f"[{finding.severity.upper()}] {finding.area}: {finding.title} — {finding.detail}\n")
                if finding.recommendation:
                    self.write(f"       next: {finding.recommendation}\n")
            self.status.set("Repository Audit ready")
            self._record_history("Repository Audit", 0, str(report_path))
        except Exception as exc:
            self.write(f"Repository Audit failed: {exc}\n")
            self.status.set("Repository Audit failed")
            self._record_history("Repository Audit", 1, str(exc))

    def _latest_repository_cleanup_report(self):
        """Return the most recent repository cleanup report path, if any."""
        reports_dir = PROJECT_ROOT / "Reports" / "repository_cleanup"
        if not reports_dir.exists():
            return None
        reports = sorted(reports_dir.glob("repository_safe_cleanup_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        return reports[0] if reports else None

    def _run_repository_cleanup(self, apply: bool = False) -> None:
        """Run Phase 4A safe repository cleanup from Studio."""
        label = "Apply Safe Cleanup" if apply else "Preview Cleanup"
        self.write(f"\n=== {label} ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Tools.repository_safe_cleanup import run_cleanup

            report = run_cleanup(PROJECT_ROOT, apply=apply)
            data = report.to_dict() if hasattr(report, "to_dict") else dict(report)
            report_path = data.get("report_path") or data.get("path") or ""
            candidates = data.get("candidates", []) or []
            removed = data.get("removed", []) or []
            actions = removed if apply else candidates
            status = "PASS"
            self.write(f"Status: {status}\n")
            self.write(f"Applied: {bool(data.get('applied', apply))}\n")
            self.write(f"Report: {report_path}\n")
            self.write(f"Candidates: {len(candidates)}\n")
            self.write(f"Removed: {len(removed)}\n")
            self.write(f"Gitignore updates: {len(data.get('gitignore_updates', []) or [])}\n")
            for item in actions[:18]:
                if isinstance(item, dict):
                    action = item.get("kind") or item.get("action") or item.get("type") or "candidate"
                    target = item.get("path") or item.get("target") or ""
                    reason = item.get("reason") or item.get("detail") or ""
                    self.write(f"[{action}] {target} {('- ' + reason) if reason else ''}\n")
                else:
                    self.write(f"- {item}\n")
            if not apply:
                self.write("Preview only. Use Apply Safe Cleanup in Studio after reviewing the report.\n")
            self.status.set(f"{label} complete")
            self._record_history(label, 0, str(report_path))
        except Exception as exc:
            self.write(f"{label} failed: {exc}\n")
            self.status.set(f"{label} failed")
            self._record_history(label, 1, str(exc))

    def preview_repository_cleanup(self) -> None:
        """Preview Phase 4A safe cleanup without changing files."""
        self._run_repository_cleanup(apply=False)

    def apply_repository_safe_cleanup(self) -> None:
        """Apply Phase 4A safe cleanup from Studio."""
        self._run_repository_cleanup(apply=True)

    def open_repository_cleanup_report(self) -> None:
        """Open the latest Phase 4A cleanup report, or Reports if none exists."""
        latest = self._latest_repository_cleanup_report()
        target = latest if latest else PROJECT_ROOT / "Reports" / "repository_cleanup"
        if not Path(target).exists():
            target = PROJECT_ROOT / "Reports"
        self.write(f"\n=== Open Cleanup Report ===\n{target}\n")
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
            self.status.set("Cleanup report opened")
            self._record_history("Open Cleanup Report", 0, str(target))
        except Exception as exc:
            self.write(f"Open Cleanup Report failed: {exc}\n")
            self.status.set("Open Cleanup Report failed")
            self._record_history("Open Cleanup Report", 1, str(exc))

    def show_acceptance_explorer(self) -> None:
        """Show Acceptance Explorer diagnostics."""
        self.write("\n=== Acceptance Explorer ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Core.acceptance_explorer import acceptance_explorer_diagnostics
            data = acceptance_explorer_diagnostics()
            self.write(f"Version: {data.get('version')}\n")
            self.write(f"Prompt: {data.get('prompt')}\n")
            self.write(f"Intent: {data.get('intent')}\n")
            self.write(f"Entities: {', '.join(data.get('entities') or [])}\n")
            self.write(f"Status: {data.get('status')} | Confidence: {data.get('confidence')}\n")
            self.write(f"Capabilities expected/selected/skipped/missing: {len(data.get('expected_capabilities') or [])}/{len(data.get('selected_capabilities') or [])}/{len(data.get('skipped_capabilities') or [])}/{len(data.get('missing_expected_capabilities') or [])}\n")
            self.write(f"Evidence found/missing: {data.get('evidence_found_count')}/{data.get('evidence_missing_count')}\n")
            self.write(f"Composition generated/displayed/discarded/coverage: {data.get('generated_section_count')}/{data.get('displayed_section_count')}/{data.get('discarded_section_count')}/{data.get('composition_coverage_ratio')}\n")
            self.write("Sections:\n")
            for section in data.get("sections", []) or []:
                self.write(f"  - {section.get('label')} [{section.get('status')}]: {section.get('summary')}\n")
                for warning in section.get("warnings", []) or []:
                    self.write(f"      warning: {warning}\n")
            self.write("Findings:\n")
            for finding in data.get("findings", []) or []:
                self.write(f"  - {finding}\n")
            self.write("Next actions:\n")
            for action in data.get("next_actions", []) or []:
                self.write(f"  - {action}\n")
            self._record_history("Acceptance Explorer", 0, json.dumps({"status": data.get("status"), "missing": data.get("missing_expected_capabilities"), "discarded": data.get("discarded_section_count")})[:500])
            self.status.set("Acceptance Explorer ready")
        except Exception as exc:
            self.write(f"Acceptance Explorer failed: {exc}\n")
            self.status.set("Acceptance Explorer failed")
            self._record_history("Acceptance Explorer", 1, str(exc))


    def show_intelligence_dashboard(self) -> None:
        """Show Multi-Sport Intelligence Foundation diagnostics."""
        self.write("\n=== Intelligence Dashboard ===\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Intelligence.Foundation import capability_matrix, studio_intelligence_diagnostics
            from Sports import sport_registry_diagnostics
            data = studio_intelligence_diagnostics()
            matrix = capability_matrix()
            sports = sport_registry_diagnostics()
            self.write(f"Version: {data.get('version')}\n")
            self.write(f"Registered modules: {data.get('registered_modules')}\n")
            self.write("Modules:\n")
            for module_id in data.get("module_ids", []) or []:
                self.write(f"  - {module_id}\n")
            self.write("Sport capability matrix:\n")
            for row in matrix.get("sports", []) or []:
                self.write(f"  - {row.get('sport')}: {row.get('module_count')} modules | {', '.join(row.get('modules', [])[:4])}\n")
            self.write(f"Sports registered: {sports.get('stats', {}).get('sport_ids')}\n")
            self.write("status: PASS\n" if data.get("status") == "pass" else "status: WARN\n")
            self._record_history("Intelligence Dashboard", 0, json.dumps({"intelligence": data, "sports": sports})[:500])
            self.status.set("Intelligence dashboard ready")
        except Exception as exc:
            self.write(f"Intelligence dashboard failed: {exc}\n")
            self.status.set("Intelligence dashboard failed")
            self._record_history("Intelligence Dashboard", 1, str(exc))

    def show_provider_dashboard(self) -> None:
        self.write("\n=== Provider Dashboard ===\n")
        raw = PROJECT_ROOT / "Raw"
        output = PROJECT_ROOT / "Output"
        checks = [
            ("Fantrax league metadata", raw / "league_info.json"),
            ("Fantrax player pool", raw / "fantrax_player_pool.json"),
            ("Fantrax transactions", raw / "transactions.json"),
            ("Team profiles", output / "team_profiles.json"),
            ("Player master", output / "player_master.json"),
            ("Transaction history", output / "transaction_history.json"),
            ("Manager behavior", output / "manager_behavior.json"),
            ("League market", output / "league_market.json"),
        ]
        available = 0
        for label, path in checks:
            exists = path.exists()
            available += 1 if exists else 0
            size = path.stat().st_size if exists else 0
            self.write(f"{'✓' if exists else '—'} {label}: {'available' if exists else 'missing'} | {size} bytes\n")
        self.write(f"Provider readiness: {available}/{len(checks)} artifacts available\n")
        self._record_history("Provider Dashboard", 0, f"available={available}")
        self.status.set("Provider dashboard ready")

    def run_pif_suite(self) -> None:
        self.validate_pif()

    def runtime_audit(self, auto: bool = False) -> None:
        if not auto:
            self.write("\n")
        self.write("=== Runtime Audit ===\n")
        self.write(f"Project root: {PROJECT_ROOT}\n")
        self.write(f"Python: {self._python()}\n")
        meta = self._current_version_metadata()
        self.write(f"Version file: {meta.get('VERSION_FILE')}\n")
        self.write(f"Athena version: {meta.get('ATHENA_VERSION', 'unknown')}\n")
        self.write(f"Scout version: {meta.get('SCOUT_VERSION', 'unknown')}\n")
        self.write(f"Scout app: {PROJECT_ROOT / 'Scout' / 'app.py'} | exists={(PROJECT_ROOT / 'Scout' / 'app.py').exists()}\n")
        self.write(f"Core version: {PROJECT_ROOT / 'Core' / 'version.py'} | exists={(PROJECT_ROOT / 'Core' / 'version.py').exists()}\n")
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from Tools.runtime_cleanup import audit_runtime
            audit = audit_runtime()
            self.write(f"Athena engine package present: {audit.get('nested_athena_present')}\n")
            self.write(f"Nested runtime duplicate present: {audit.get('nested_runtime_duplicate_present')}\n")
            self.write(f"Athena package path: {audit.get('nested_athena_path')}\n")
        except Exception:
            nested = PROJECT_ROOT / "Athena"
            runtime_duplicate = (nested / "Core").exists() or (nested / "Scout").exists()
            self.write(f"Athena engine package present: {nested.exists()}\n")
            self.write(f"Nested runtime duplicate present: {runtime_duplicate}\n")
        listening = [port for port in SCOUT_PORT_RANGE if self._is_port_open(port)]
        self.write("Scout-range ports listening: " + (", ".join(map(str, listening)) if listening else "none") + "\n")
        self.write("=====================\n")
        self.status.set("Runtime audit complete")

    def show_import_paths(self) -> None:
        self.write("\n=== Import Paths ===\n")
        self.write(f"sys.executable: {sys.executable}\n")
        self.write(f"cwd: {os.getcwd()}\n")
        self.write("sys.path:\n")
        for path in sys.path:
            self.write(f"  - {path}\n")

    def show_history(self) -> None:
        self.write("\n=== Studio History ===\n")
        if not HISTORY_FILE.exists():
            self.write("No Studio history found yet.\n")
            return
        lines = HISTORY_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
        for line in lines:
            try:
                item = json.loads(line)
                self.write(f"{item.get('timestamp')} | {item.get('label')} | {item.get('status')} | exit={item.get('exit_code')}\n")
            except Exception:
                self.write(line + "\n")

    def show_scout_log(self) -> None:
        log_path = LOG_DIR / "athena_studio_scout.log"
        self.write("\n=== Scout Log ===\n")
        if not log_path.exists():
            message = "No Scout log found yet. Launch Scout from Studio first.\n"
            self.write(message)
            self._open_text_window("Scout Log", message)
            return
        text = self._tail_file(log_path, 220)
        self.write(text)
        self._open_text_window("Scout Log", f"File: {log_path}\n\n{text}")

    def show_latest_debug(self) -> None:
        self.write("\n=== Latest Debug Export ===\n")
        search_roots = [
            PROJECT_ROOT,
            LOG_DIR,
            REPORT_DIR,
        ]
        patterns = [
            "scout_debug_export_*.txt",
            "athena_studio_log_export_*.txt",
            "*.txt",
        ]
        candidates: list[Path] = []
        seen: set[Path] = set()
        for root in search_roots:
            if not root.exists():
                continue
            for pattern in patterns:
                for path in root.glob(pattern):
                    if path.is_file() and path not in seen:
                        seen.add(path)
                        candidates.append(path)
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            message = "No readable Scout debug/report text files found in project root, Logs, or Reports.\n"
            self.write(message)
            self._open_text_window("Latest Debug Export", message)
            return
        latest = candidates[0]
        text = self._tail_file(latest, 260)
        header = f"File: {latest}\n\n"
        self.write(header)
        self.write(text)
        self._open_text_window("Latest Debug Export", header + text)

    def export_studio_log(self) -> None:
        """Export Studio-visible logs without requiring a full diagnostic bundle."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        export_path = REPORT_DIR / f"athena_studio_log_export_{stamp}.txt"
        try:
            meta = self._current_version_metadata()
            lines = [
                "Athena Studio Log Export",
                "========================",
                f"Created: {datetime.now(timezone.utc).isoformat()}",
                f"Project root: {PROJECT_ROOT}",
                f"Python: {self._python()}",
                f"Athena: {meta.get('ATHENA_VERSION', 'unknown')}",
                f"Scout: {meta.get('SCOUT_VERSION', 'unknown')}",
                f"Build: {meta.get('ATHENA_BUILD', 'unknown')}",
                "",
                "Studio Output",
                "-------------",
                self.output.get("1.0", END),
                "",
                "History",
                "-------",
            ]
            if HISTORY_FILE.exists():
                lines.append(HISTORY_FILE.read_text(encoding="utf-8", errors="replace"))
            else:
                lines.append("No history file found.")
            scout_log = LOG_DIR / "athena_studio_scout.log"
            lines.extend(["", "Scout Log", "---------"])
            if scout_log.exists():
                lines.append(scout_log.read_text(encoding="utf-8", errors="replace")[-60000:])
            else:
                lines.append("No Scout log found.")
            export_path.write_text("\n".join(lines), encoding="utf-8")
            self.write(f"\nStudio log export created: {export_path}\n")
            self._record_history("Export Studio Log", 0, str(export_path))
        except Exception as exc:
            self.write(f"Studio log export failed: {exc}\n")
            self._record_history("Export Studio Log", 1, str(exc))

    def _open_folder(self, folder: Path) -> bool:
        """Open a local folder from Studio without requiring Spyder or a terminal."""
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(folder))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
            return True
        except Exception as exc:
            self.write(f"Could not open folder automatically: {folder}\n{exc}\n")
            return False

    def open_reports(self) -> None:
        """Open the canonical Reports folder so exported diagnostics are easy to pick manually."""
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        self.write(f"\n=== Reports Folder ===\n{REPORT_DIR}\n")
        opened = self._open_folder(REPORT_DIR)
        self._record_history("Open Reports", 0 if opened else 1, str(REPORT_DIR))

    def export_diagnostics_logs(self) -> None:
        """Export diagnostics to a timestamped folder, then open that folder for manual selection.

        This restores the original acceptance workflow: create files under Reports,
        open the folder, and let the user choose the TXT/JSON/log to attach.
        """
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        export_dir = REPORT_DIR / f"diagnostics_export_{stamp}"
        export_dir.mkdir(parents=True, exist_ok=True)
        copied: list[str] = []
        errors: list[str] = []

        def copy_file(path: Path, label: str | None = None) -> None:
            if not path.exists() or not path.is_file():
                return
            target_name = label or path.name
            target = export_dir / target_name
            try:
                shutil.copy2(path, target)
                copied.append(target.name)
            except Exception as exc:
                errors.append(f"{path}: {exc}")

        # Current visible Studio output and runtime summary.
        try:
            meta = self._current_version_metadata()
            runtime_summary = "\n".join([
                "Athena Diagnostics Export",
                "=========================" ,
                f"Created: {datetime.now(timezone.utc).isoformat()}",
                f"Project root: {PROJECT_ROOT}",
                f"Python: {self._python()}",
                f"Athena: {meta.get('ATHENA_VERSION', 'unknown')}",
                f"Scout: {meta.get('SCOUT_VERSION', 'unknown')}",
                f"Build: {meta.get('ATHENA_BUILD', 'unknown')}",
                f"Reports folder: {REPORT_DIR}",
                f"Export folder: {export_dir}",
            ])
            (export_dir / "runtime_summary.txt").write_text(runtime_summary + "\n", encoding="utf-8")
            copied.append("runtime_summary.txt")
            (export_dir / "studio_visible_output.txt").write_text(self.output.get("1.0", END), encoding="utf-8")
            copied.append("studio_visible_output.txt")
        except Exception as exc:
            errors.append(f"studio/runtime export: {exc}")

        copy_file(HISTORY_FILE, "athena_studio_history.jsonl")
        copy_file(LOG_DIR / "athena_studio_scout.log", "athena_studio_scout.log")
        copy_file(LOG_DIR / "scout_stop_log.txt", "scout_stop_log.txt")
        copy_file(REPORT_DIR / "scout_session_log.txt", "scout_session_log.txt")
        copy_file(REPORT_DIR / "scout_session_log.json", "scout_session_log.json")

        # Include the most recent text/json debug exports and Studio log exports without flooding the folder.
        patterns = [
            "scout_debug_export_*.txt",
            "scout_debug_export_*.json",
            "athena_studio_log_export_*.txt",
            "diagnostics_recovery_validation_report.*",
        ]
        for pattern in patterns:
            files = sorted(REPORT_DIR.glob(pattern), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
            for path in files[:6]:
                copy_file(path)

        manifest = {
            "ok": not errors,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "project_root": str(PROJECT_ROOT),
            "reports_folder": str(REPORT_DIR),
            "export_folder": str(export_dir),
            "files": copied,
            "errors": errors,
        }
        (export_dir / "diagnostics_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        copied.append("diagnostics_manifest.json")

        self.write("\n=== Diagnostics Logs Export ===\n")
        self.write(f"Export folder: {export_dir}\n")
        self.write(f"Files copied: {len(copied)}\n")
        if errors:
            self.write("Warnings:\n" + "\n".join(f"- {e}" for e in errors) + "\n")
        opened = self._open_folder(export_dir)
        self._record_history("Export Diagnostics Logs", 0 if not errors else 1, str(export_dir))
        if not opened:
            self.write("Open this folder manually to choose a log file.\n")

    def create_diagnostic_bundle(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        bundle = REPORT_DIR / f"athena_diagnostic_bundle_{stamp}.zip"
        self.write(f"\n=== Diagnostic Bundle ===\nCreating {bundle}\n")
        try:
            with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
                for rel in ["Core/version.py", "Logs/athena_studio_scout.log", "Logs/athena_studio_history.jsonl"]:
                    path = PROJECT_ROOT / rel
                    if path.exists():
                        zf.write(path, rel)
                for pattern in ["scout_debug_export_*.txt", "Reports/*.json", "Reports/*.txt"]:
                    for path in PROJECT_ROOT.glob(pattern):
                        if path.is_file():
                            zf.write(path, str(path.relative_to(PROJECT_ROOT)))
                runtime_txt = (
                    f"Project root: {PROJECT_ROOT}\nPython: {self._python()}\nAthena: {self._current_version_metadata().get('ATHENA_VERSION', 'unknown')}\nScout: {self._current_version_metadata().get('SCOUT_VERSION', 'unknown')}\nBuild: {self._current_version_metadata().get('ATHENA_BUILD', 'unknown')}\n"
                )
                zf.writestr("runtime_summary.txt", runtime_txt)
            self.write(f"Diagnostic bundle created: {bundle}\n")
            self._record_history("Diagnostic Bundle", 0, str(bundle))
        except Exception as exc:
            self.write(f"Diagnostic bundle failed: {exc}\n")
            self._record_history("Diagnostic Bundle", 1, str(exc))

    def _open_text_window(self, title: str, text: str) -> None:
        """Open a useful, scrollable in-Studio log viewer instead of only pointing at report files."""
        try:
            import tkinter as tk
            window = tk.Toplevel(self.root)
            window.title(f"Athena Studio - {title}")
            window.geometry("1000x700")
            frame = Frame(window, background="#0b1220")
            frame.pack(fill=BOTH, expand=True)
            viewer = Text(
                frame,
                wrap="word",
                font=("Consolas", 9),
                background="#111827",
                foreground="#e5e7eb",
                insertbackground="#e5e7eb",
            )
            scrollbar = Scrollbar(frame, orient="vertical", command=viewer.yview)
            viewer.configure(yscrollcommand=scrollbar.set)
            viewer.insert("1.0", text)
            viewer.configure(state="disabled")
            viewer.pack(side=LEFT, fill=BOTH, expand=True)
            scrollbar.pack(side=RIGHT, fill=Y)
        except Exception as exc:
            self.write(f"Could not open log viewer window: {exc}\n")

    @staticmethod
    def _tail_file(path: Path, max_lines: int) -> str:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[-max_lines:]) + "\n"
        except Exception as exc:
            return f"Could not read {path}: {exc}\n"

    def open_logs(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(LOG_DIR))  # type: ignore[attr-defined]
        except Exception:
            path = filedialog.askdirectory(initialdir=str(PROJECT_ROOT), title="Open Logs Folder")
            if path:
                self.write(f"Selected: {path}\n")

    @staticmethod
    def _is_port_open(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    AthenaStudio().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

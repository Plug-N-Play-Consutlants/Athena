"""Reload Build must force-close Scout and never auto-launch it."""
import ast
from pathlib import Path
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / "Tools" / "athena_studio.py"


def _reload_method():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_reload_patched_build_sync")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace[node.name]


def _studio(stop_code=0, ports_clear=True):
    self = Mock()
    self._current_version_metadata.return_value = {"SCOUT_VERSION": "v0.7.10.67.23", "VERSION_FILE": "Core/version.py", "ATHENA_BUILD": "0.7.10.67.23"}
    self._stop_scout_sync.return_value = stop_code
    self._wait_for_ports_clear.return_value = ports_clear
    self._purge_python_caches.return_value = (2, 3)
    return self


def test_successful_reload_stops_and_never_launches():
    studio = _studio()
    _reload_method()(studio)
    studio._stop_scout_sync.assert_called_once()
    studio._wait_for_ports_clear.assert_called_once()
    studio._purge_python_caches.assert_called_once()
    studio.launch_scout.assert_not_called()
    studio.root.after.assert_not_called()
    assert studio.scout_process is None
    assert studio._reload_in_progress is False
    studio.status.set.assert_any_call("Build reloaded; Scout stopped")


def test_reload_blocks_when_shutdown_fails():
    studio = _studio(stop_code=1)
    _reload_method()(studio)
    studio._purge_python_caches.assert_not_called()
    studio.launch_scout.assert_not_called()
    studio.root.after.assert_not_called()
    assert studio._reload_in_progress is False


def test_reload_blocks_when_ports_remain_occupied():
    studio = _studio(ports_clear=False)
    _reload_method()(studio)
    studio._purge_python_caches.assert_not_called()
    studio.launch_scout.assert_not_called()
    assert studio._reload_in_progress is False

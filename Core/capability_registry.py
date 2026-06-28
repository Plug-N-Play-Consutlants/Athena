"""Runtime capability registry for AthenaEngine.

v0.5.6.1.0 introduces a lightweight, repository-discovered capability
inventory. This is intentionally observability-only: it does not change Scout
routing or execute capabilities. Studio uses this layer to answer a practical
engineering question: which capabilities exist, where are they, and are their
supporting doctors/validators present?
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple
import importlib
import re

CAPABILITY_REGISTRY_VERSION = "0.5.6.1.0"

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LAYER_DIRS: Tuple[str, ...] = (
    "Knowledge",
    "Intelligence",
    "Reasoning",
    "Engine",
    "Providers",
    "Sports",
    "Scout",
)

_STOP_NAMES = {
    "__init__",
    "models",
    "model",
    "registry",
    "types",
    "utils",
    "helpers",
    "constants",
    "version",
}


@dataclass(frozen=True)
class CapabilityMetadata:
    """Normalized metadata for a repository capability."""

    capability_id: str
    name: str
    layer: str
    owner: str
    version: str = "unknown"
    status: str = "discovered"
    entrypoints: Tuple[str, ...] = field(default_factory=tuple)
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    doctors: Tuple[str, ...] = field(default_factory=tuple)
    validators: Tuple[str, ...] = field(default_factory=tuple)
    tests: Tuple[str, ...] = field(default_factory=tuple)
    public_api: Tuple[str, ...] = field(default_factory=tuple)
    source: str = "repository_scan"
    registered: bool = True
    notes: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def has_doctor(self) -> bool:
        return bool(self.doctors)

    @property
    def has_validator(self) -> bool:
        return bool(self.validators or self.tests)

    @property
    def health(self) -> str:
        if not self.entrypoints:
            return "warn"
        if self.status in {"missing", "error"}:
            return "fail"
        return "pass"


def _title(value: str) -> str:
    value = re.sub(r"[_\-]+", " ", value).strip()
    return " ".join(part.capitalize() for part in value.split()) or "Unknown"


def _safe_version() -> str:
    try:
        from Core.version import ATHENA_VERSION
        return str(ATHENA_VERSION)
    except Exception:
        return "unknown"


def _existing(paths: Iterable[Path]) -> Tuple[str, ...]:
    found = []
    for path in paths:
        if path.exists():
            found.append(path.relative_to(_REPO_ROOT).as_posix())
    return tuple(sorted(set(found)))


def _candidate_support_files(capability_id: str) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]:
    slug = capability_id.replace(".", "_").replace("-", "_")
    compact = slug
    variants = {compact}
    # Strip common layer prefixes to match existing doctor/test naming.
    for prefix in ("knowledge_", "intelligence_", "reasoning_", "engine_", "provider_", "providers_", "sports_", "scout_"):
        if compact.startswith(prefix):
            variants.add(compact[len(prefix):])
    doctor_paths = []
    validator_paths = []
    test_paths = []
    for variant in variants:
        doctor_paths.append(_REPO_ROOT / "Tools" / f"doctor_{variant}.py")
        validator_paths.append(_REPO_ROOT / "Tests" / f"validate_{variant}.py")
        test_paths.extend((_REPO_ROOT / "Tests" / f"test_{variant}.py", _REPO_ROOT / "Tests" / f"validate_{variant}.py"))
    return _existing(doctor_paths), _existing(validator_paths), _existing(test_paths)


def _module_to_capability(path: Path, layer: str) -> CapabilityMetadata | None:
    rel = path.relative_to(_REPO_ROOT)
    stem = path.stem
    if stem in _STOP_NAMES or stem.startswith("_"):
        return None
    # Avoid one-off scripts in Scout static/assets, caches, etc.
    parts = rel.parts
    if any(part in {"__pycache__", "static", "templates"} for part in parts):
        return None
    capability_slug = "_".join([layer.lower(), *[p.replace(".py", "") for p in parts[1:]]])
    capability_id = capability_slug.replace("__", "_")
    doctors, validators, tests = _candidate_support_files(capability_id)
    owner = layer
    return CapabilityMetadata(
        capability_id=capability_id,
        name=_title(stem),
        layer=layer,
        owner=owner,
        version=_safe_version(),
        status="discovered",
        entrypoints=(rel.as_posix(),),
        dependencies=(),
        doctors=doctors,
        validators=validators,
        tests=tests,
        public_api=(),
        source="repository_scan",
        registered=True,
        notes=(),
    )


def _discover_repository_modules() -> List[CapabilityMetadata]:
    capabilities: List[CapabilityMetadata] = []
    for layer in _LAYER_DIRS:
        base = _REPO_ROOT / layer
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            item = _module_to_capability(path, layer)
            if item:
                capabilities.append(item)
    return capabilities


def _discover_intelligence_foundation() -> List[CapabilityMetadata]:
    """Import the provider-neutral intelligence registry if available."""
    found: List[CapabilityMetadata] = []
    try:
        foundation = importlib.import_module("Intelligence.Foundation")
        registry = foundation.seed_intelligence_registry()
        for module in registry.all_modules():
            module_id = str(module.module_id)
            doctors, validators, tests = _candidate_support_files(module_id)
            found.append(CapabilityMetadata(
                capability_id=module_id,
                name=str(module.label),
                layer="Intelligence",
                owner="Intelligence.Foundation",
                version=str(getattr(foundation, "INTELLIGENCE_FOUNDATION_VERSION", _safe_version())),
                status=str(module.status),
                entrypoints=("Intelligence/Foundation/modules.py",),
                dependencies=tuple(str(x) for x in module.inputs),
                doctors=doctors,
                validators=validators,
                tests=tests,
                public_api=tuple(str(x) for x in module.outputs),
                source="Intelligence.Foundation",
                registered=True,
                notes=tuple(str(x) for x in module.evidence_sources),
            ))
    except Exception:
        pass
    return found


class CapabilityRegistry:
    """In-memory capability registry built from repository discovery."""

    def __init__(self, capabilities: Sequence[CapabilityMetadata] | None = None) -> None:
        self._capabilities: Tuple[CapabilityMetadata, ...] = tuple(capabilities or discover_capabilities())
        self._by_id: Dict[str, CapabilityMetadata] = {cap.capability_id: cap for cap in self._capabilities}

    def list(self) -> Tuple[CapabilityMetadata, ...]:
        return self._capabilities

    def get(self, capability_id: str) -> CapabilityMetadata | None:
        return self._by_id.get(str(capability_id or "").strip())

    def by_layer(self, layer: str) -> Tuple[CapabilityMetadata, ...]:
        key = str(layer or "").strip().lower()
        return tuple(cap for cap in self._capabilities if cap.layer.lower() == key)

    def dependency_graph(self) -> Dict[str, Tuple[str, ...]]:
        return {cap.capability_id: cap.dependencies for cap in self._capabilities}

    def validate_metadata(self) -> Dict[str, Any]:
        duplicate_ids: List[str] = []
        seen: set[str] = set()
        for cap in self._capabilities:
            if cap.capability_id in seen:
                duplicate_ids.append(cap.capability_id)
            seen.add(cap.capability_id)
        missing_entrypoints = [cap.capability_id for cap in self._capabilities if not cap.entrypoints]
        missing_doctors = [cap.capability_id for cap in self._capabilities if not cap.doctors]
        missing_validators = [cap.capability_id for cap in self._capabilities if not (cap.validators or cap.tests)]
        invalid_dependencies = []
        known = set(self._by_id)
        # Dependencies are often evidence names, not capabilities. Only flag explicit capability: deps.
        for cap in self._capabilities:
            for dep in cap.dependencies:
                if str(dep).startswith("capability:") and str(dep).split(":", 1)[1] not in known:
                    invalid_dependencies.append((cap.capability_id, dep))
        status = "fail" if duplicate_ids or missing_entrypoints or invalid_dependencies else "pass"
        if status == "pass" and (missing_doctors or missing_validators):
            status = "warn"
        return {
            "status": status,
            "capability_count": len(self._capabilities),
            "duplicate_ids": sorted(set(duplicate_ids)),
            "missing_entrypoints": missing_entrypoints,
            "missing_doctors": missing_doctors,
            "missing_validators": missing_validators,
            "invalid_dependencies": invalid_dependencies,
        }

    def summary(self) -> Dict[str, Any]:
        by_layer: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        with_doctor = 0
        with_validator = 0
        for cap in self._capabilities:
            by_layer[cap.layer] = by_layer.get(cap.layer, 0) + 1
            by_source[cap.source] = by_source.get(cap.source, 0) + 1
            with_doctor += 1 if cap.doctors else 0
            with_validator += 1 if (cap.validators or cap.tests) else 0
        validation = self.validate_metadata()
        return {
            "version": CAPABILITY_REGISTRY_VERSION,
            "status": validation["status"],
            "capability_count": len(self._capabilities),
            "by_layer": dict(sorted(by_layer.items())),
            "by_source": dict(sorted(by_source.items())),
            "with_doctor": with_doctor,
            "with_validator": with_validator,
            "warnings": len(validation["missing_doctors"]) + len(validation["missing_validators"]),
            "errors": len(validation["duplicate_ids"]) + len(validation["missing_entrypoints"]) + len(validation["invalid_dependencies"]),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": CAPABILITY_REGISTRY_VERSION,
            "summary": self.summary(),
            "validation": self.validate_metadata(),
            "capabilities": [cap.to_dict() for cap in self._capabilities],
        }


def discover_capabilities() -> Tuple[CapabilityMetadata, ...]:
    """Discover capabilities from explicit registries and repository modules."""
    merged: Dict[str, CapabilityMetadata] = {}
    for cap in _discover_repository_modules():
        merged[cap.capability_id] = cap
    # Explicit registries override generic repository scan for richer metadata.
    for cap in _discover_intelligence_foundation():
        merged[cap.capability_id] = cap
    return tuple(sorted(merged.values(), key=lambda cap: (cap.layer, cap.capability_id)))


def seed_capability_registry() -> CapabilityRegistry:
    return CapabilityRegistry(discover_capabilities())


def capability_registry_diagnostics(limit: int = 40) -> Dict[str, Any]:
    registry = seed_capability_registry()
    data = registry.to_dict()
    data["panel"] = "capability_registry"
    data["capabilities"] = data["capabilities"][: max(0, int(limit))]
    return data


__all__ = [
    "CAPABILITY_REGISTRY_VERSION",
    "CapabilityMetadata",
    "CapabilityRegistry",
    "discover_capabilities",
    "seed_capability_registry",
    "capability_registry_diagnostics",
]

"""Doctor checks for Athena foundational governance and module adaptivity."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
from Intelligence.Foundation import MODULE_CONTRACT_VERSION, module_contract_diagnostics

FOUNDATION_FILES = (
    "Athena_Constitution.md",
    "Athena_Manifesto.md",
    "Athena_Intelligence_Model.md",
    "Scout_Principles.md",
    "Engineering_Principles.md",
    "Product_Vision.md",
    "Roadmap.md",
    "Decision_Record_Template.md",
)


def report(label: str, passed: bool, detail: object) -> dict[str, object]:
    return {"label": label, "status": "pass" if passed else "fail", "detail": detail}


def run() -> dict[str, object]:
    foundations_dir = PROJECT_ROOT / "Foundations"
    checks: list[dict[str, object]] = []
    checks.append(report("version", ATHENA_VERSION >= "0.6.3.0.0", ATHENA_VERSION))
    checks.append(report("release_name", RELEASE_NAME in {"Foundational Governance and Module Adaptivity", "Foundational Governance Cleanup Tolerance Hotfix", "Adaptive Investigation Strategy Foundation", "Adaptive Investigation Runtime Integration"}, RELEASE_NAME))
    checks.append(report("version_schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    checks.append(report("foundations_dir", foundations_dir.exists(), str(foundations_dir)))

    for filename in FOUNDATION_FILES:
        path = foundations_dir / filename
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        checks.append(report(f"foundation_file:{filename}", path.exists() and len(text.strip()) > 100, filename))

    engineering = (foundations_dir / "Engineering_Principles.md").read_text(encoding="utf-8") if foundations_dir.exists() else ""
    checks.append(report("module_adaptive_principle", "module-adaptive" in engineering and "Registries over imports" in engineering, "Engineering_Principles.md"))
    checks.append(report("canonical_pipeline", "Providers → Fetch → Build → Knowledge" in engineering, "pipeline present"))

    diagnostics = module_contract_diagnostics()
    checks.append(report("module_contract_version", MODULE_CONTRACT_VERSION >= "0.6.3.0.0", MODULE_CONTRACT_VERSION))
    checks.append(report("module_contracts_discoverable", diagnostics.get("all_discoverable") is True, diagnostics))
    checks.append(report("future_decision_contract", "decision_intelligence" in diagnostics.get("module_ids", []), diagnostics.get("module_ids")))

    passed = all(check["status"] == "pass" for check in checks)
    return {
        "doctor": "foundational_governance",
        "status": "pass" if passed else "fail",
        "checks": checks,
    }


def main() -> int:
    result = run()
    print("Athena Foundational Governance Doctor")
    print("=" * 64)
    for check in result["checks"]:
        print(f"[{str(check['status']).upper()}] {check['label']}: {check['detail']}")
    print("-" * 64)
    print(f"Overall status: {str(result['status']).upper()}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

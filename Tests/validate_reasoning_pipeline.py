"""
Athena 4E Reasoning Pipeline Validation
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Reasoning.reasoning_engine import ReasoningEngine


def main():
    engine = ReasoningEngine()
    result = engine.reason_about_asset([])
    assert "summary" in result
    assert "key_findings" in result
    assert "overall_confidence" in result
    print("Reasoning Pipeline Validation PASS")


if __name__ == "__main__":
    main()

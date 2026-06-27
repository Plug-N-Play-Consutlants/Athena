"""
Athena 4E Reasoning Pipeline Doctor
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Reasoning.reasoning_engine import ReasoningEngine
from Reasoning.reasoning_registry import ReasoningRegistry


def main():
    engine = ReasoningEngine()
    registry = ReasoningRegistry()

    print("Reasoning Pipeline Doctor")
    print("========================")
    print("Project Root:", PROJECT_ROOT)
    print("Engine:", engine.__class__.__name__)
    print("Asset assessor:", engine.asset_assessor.__class__.__name__)
    print("Player assessor:", engine.player_assessor.__class__.__name__)
    print("Registered reasoning types:", ", ".join(registry.keys()))
    print("STATUS: PASS")


if __name__ == "__main__":
    main()

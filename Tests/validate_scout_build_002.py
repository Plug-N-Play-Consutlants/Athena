from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from Intelligence.Player.player_intelligence import evaluate_player
from Reasoning.adapters.player_evidence_adapter import build_player_profile_from_evaluation
from Reasoning.reasoning_engine import ReasoningEngine
from Reasoning.composition.executive_brief import ExecutiveBriefComposer

ev=evaluate_player("Analyze Auston Matthews",mode="fantasy",project_root=root)
a=ReasoningEngine().reason_about_player(build_player_profile_from_evaluation(ev),ev)
b=ExecutiveBriefComposer().build_player_brief(a,ev)
assert "keeper" in b["fantasy_impact"].lower()
assert "strategically important asset" in b["natural_language_response"].lower()
print("SCOUT BUILD 002 VALIDATION PASS")

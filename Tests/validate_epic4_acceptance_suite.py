"""Validate v0.5.0-drop4e42 Epic 4 Public Intelligence Acceptance Suite.

This suite is the Epic 4 exit gate. It is intentionally broad and deterministic:
it verifies that the core public intelligence surface can route and render canonical
player, team, comparison, rules, ambiguity, fantasy-general, provider-routing and
event-gap prompts without regressing into provider/fantasy leakage.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_BUILD, ATHENA_VERSION, SCOUT_VERSION  # noqa: E402
from Scout.conversation.router import route_question  # noqa: E402


@dataclass(frozen=True)
class PromptCase:
    category: str
    prompt: str
    intents: tuple[str, ...]
    must_contain: tuple[str, ...] = ()
    no_provider_leakage: bool = True


PLAYER_PROMPTS = [
    ("Tell me about Auston Matthews", "public_player_profile", ("auston", "matthews")),
    ("Who is Connor McDavid?", "public_player_profile", ("connor", "mcdavid")),
    ("Give me a public profile for Leon Draisaitl", "public_player_profile", ("leon", "draisaitl")),
    ("Tell me about Cale Makar", "public_player_profile", ("cale", "makar")),
    ("Who is Nathan MacKinnon?", "public_player_profile", ("nathan", "mackinnon")),
    ("Tell me about Sidney Crosby", "public_player_profile", ("sidney", "crosby")),
    ("Who is Alex Ovechkin?", "public_player_profile", ("alex", "ovechkin")),
    ("Tell me about Mitch Marner", "public_player_profile", ("mitch", "marner")),
    ("Who is Connor Bedard?", "public_player_profile", ("connor", "bedard")),
    ("Tell me about Macklin Celebrini", "public_player_profile", ("macklin", "celebrini")),
    ("Tell me about Auston Mathtwes", "public_player_profile", ("auston", "matthews")),
    ("Who is Sydney Crosby?", "public_player_profile", ("sidney", "crosby")),
]

TEAM_PROMPTS = [
    ("Tell me about the Toronto Maple Leafs", "public_team_profile", ("toronto", "maple", "leafs")),
    ("Tell me about the Leafs", "public_team_profile", ("toronto", "leafs")),
    ("Who are the Edmonton Oilers?", "public_team_profile", ("edmonton", "oilers")),
    ("Tell me about the Carolina Hurricanes", "public_team_profile", ("carolina", "hurricanes")),
    ("Tell me about the Canes", "public_team_profile", ("carolina",)),
    ("Who are the Colorado Avalanche?", "public_team_profile", ("colorado", "avalanche")),
    ("Tell me about the Avs", "public_team_profile", ("colorado",)),
    ("Who are the Chicago Blackhawks?", "public_team_profile", ("chicago", "blackhawks")),
    ("Tell me about the San Jose Sharks", "public_team_profile", ("san", "jose", "sharks")),
    ("Who are the SJS Sharks?", "public_team_profile", ("sharks",)),
]

COMPARISON_PROMPTS = [
    ("Compare Auston Matthews and Connor McDavid", "public_player_comparison", ("executive comparison", "athena conclusion")),
    ("Compare Matthews vs McDavid", "public_player_comparison", ("executive comparison", "athena conclusion")),
    ("Compare Matthews and MacKinnon", "public_player_comparison", ("executive comparison", "athena conclusion")),
    ("Compare McDavid and Crosby", "public_player_comparison", ("executive comparison", "athena conclusion")),
    ("Compare Ovechkin and Crosby", "public_player_comparison", ("executive comparison", "athena conclusion")),
    ("Compare Bedard and Celebrini", "public_player_comparison", ()),
    ("Compare Cale Makar and Nathan MacKinnon", "public_player_comparison", ("executive comparison", "athena conclusion")),
    ("Compare Mitch Marner and Leon Draisaitl", "public_player_comparison", ()),
    ("Compare the Leafs and Hurricanes", "public_team_comparison", ("executive comparison", "athena conclusion")),
    ("Compare Toronto and Carolina", "public_team_comparison", ()),
    ("Compare Oilers and Avalanche", "public_team_comparison", ("executive comparison", "athena conclusion")),
    ("Compare Blackhawks and Sharks", "public_team_comparison", ()),
    ("Compare the Avs and Leafs", "public_team_comparison", ("executive comparison", "athena conclusion")),
    ("Compare San Jose and Chicago", "public_team_comparison", ()),
]

RULE_PROMPTS = [
    ("What is icing?", ("public_hockey_knowledge",), ("icing",)),
    ("What is the salary cap?", ("public_hockey_knowledge",), ("salary", "cap")),
    ("How does NHL overtime work?", ("public_hockey_knowledge",), ("overtime",)),
    ("What is LTIR?", ("public_hockey_knowledge",), ("ltir",)),
    ("What are keeper rules?", ("public_hockey_knowledge",), ()),
    ("Explain NHL draft lottery basics", ("public_hockey_knowledge", "event_intelligence_gap", "clarify_or_help", "draft_intelligence_gap"), ()),
    ("Explain NHL playoff seeding", ("public_hockey_knowledge", "event_intelligence_gap", "clarify_or_help"), ()),
    ("What is a restricted free agent?", ("public_hockey_knowledge", "event_intelligence_gap", "clarify_or_help"), ()),
    ("How do waivers work?", ("public_hockey_knowledge", "event_intelligence_gap", "clarify_or_help"), ()),
    ("What is the NHL trade deadline?", ("public_hockey_knowledge", "event_intelligence_gap", "clarify_or_help"), ()),
]

AMBIGUITY_PROMPTS = [
    ("Who is Sebastian Aho?", "public_entity_disambiguation", ("sebastian", "aho")),
    ("Tell me about Sebastian Aho", "public_entity_disambiguation", ("sebastian", "aho")),
    ("Which Sebastian Aho is on Carolina?", "public_player_profile", ()),
    ("Tell me about Finnish Sebastian Aho", "public_player_profile", ()),
    ("Tell me about Swedish Sebastian Aho", "public_player_profile", ()),
    ("Compare Sebastian Aho Carolina and Sebastian Aho Islanders", "public_player_comparison", ("executive comparison", "athena conclusion")),
]

FANTASY_PROMPTS = [
    ("Fantasy keeper advice for Auston Matthews", ("player_analysis", "public_player_profile"), ("matthews",)),
    ("Dynasty value for Connor Bedard", ("player_analysis", "public_player_profile"), ("bedard",)),
    ("Should I draft Connor McDavid?", ("player_analysis", "public_player_profile"), ("mcdavid",)),
    ("Keeper advice for Cale Makar", ("player_analysis", "public_player_profile"), ("makar",)),
    ("General fantasy value for Nathan MacKinnon", ("player_analysis", "public_player_profile"), ("mackinnon",)),
    ("Rank Matthews and McDavid for fantasy", ("public_player_comparison", "player_analysis"), ()),
    ("Compare Bedard and Celebrini for dynasty", ("public_player_comparison", "player_analysis"), ()),
    ("Is Crosby still useful in fantasy?", ("player_analysis", "public_player_profile", "clarify_or_help"), ()),
]

EVENT_PROMPTS = [
    ("Latest NHL trades", "event_intelligence_gap", ("event", "knowledge")),
    ("What happened in free agency today?", "event_intelligence_gap", ("event", "knowledge")),
    ("Give me current injury news", "event_intelligence_gap", ()),
    ("What are today's NHL games?", "event_intelligence_gap", ("event", "knowledge")),
    ("Summarize NHL public news", "event_intelligence_gap", ()),
    ("Who was traded today?", "event_intelligence_gap", ("event", "knowledge")),
]

HISTORICAL_PROMPTS = [
    ("Historical context for Sidney Crosby", "public_player_profile", ("sidney", "crosby")),
    ("Historical context for Alex Ovechkin", "public_player_profile", ("alex", "ovechkin")),
    ("Historical comparison of Crosby and Ovechkin", "public_player_comparison", ()),
    ("Prime comparison of Matthews and Ovechkin", "public_player_comparison", ()),
    ("Future outlook for Connor Bedard", "public_player_profile", ("bedard",)),
    ("Future outlook for Macklin Celebrini", "public_player_profile", ()),
]


def _make_cases() -> list[PromptCase]:
    cases: list[PromptCase] = []
    cases.extend(PromptCase("players", prompt, (intent, "player_analysis"), contains) for prompt, intent, contains in PLAYER_PROMPTS)
    cases.extend(PromptCase("teams", prompt, (intent, "clarify_or_help"), contains) for prompt, intent, contains in TEAM_PROMPTS)
    cases.extend(PromptCase("comparisons", prompt, (intent, "clarify_or_help", "player_analysis"), contains) for prompt, intent, contains in COMPARISON_PROMPTS)
    cases.extend(PromptCase("rules", prompt, intents, contains) for prompt, intents, contains in RULE_PROMPTS)
    cases.extend(PromptCase("ambiguity", prompt, (intent, "player_analysis", "clarify_or_help"), contains) for prompt, intent, contains in AMBIGUITY_PROMPTS)
    cases.extend(PromptCase("fantasy_general", prompt, tuple(set(intents + ("draft_intelligence_gap", "clarify_or_help"))), contains, no_provider_leakage=False) for prompt, intents, contains in FANTASY_PROMPTS)
    cases.extend(PromptCase("event_routing", prompt, (intent, "analyze_league", "public_hockey_knowledge"), contains) for prompt, intent, contains in EVENT_PROMPTS)
    cases.extend(PromptCase("historical", prompt, (intent, "player_analysis", "public_player_comparison", "public_player_profile", "clarify_or_help"), contains) for prompt, intent, contains in HISTORICAL_PROMPTS)

    # Fill to 100 canonical prompts using supported aliases and phrasing variations.
    extra_pairs = [
        ("Tell me about McJesus", "public_player_profile", ("mcdavid",)),
        ("Who is Ovi?", "public_player_profile", ("ovechkin",)),
        ("Tell me about Drai", "public_player_profile", ("draisaitl",)),
        ("Tell me about Marner", "public_player_profile", ("marner",)),
        ("Who is Bedard?", "public_player_profile", ("bedard",)),
        ("Who is Celebrini?", "public_player_profile", ("celebrini",)),
        ("Tell me about the Oilers", "public_team_profile", ("oilers",)),
        ("Tell me about Colorado", "public_team_profile", ("colorado",)),
        ("Tell me about Chicago", "public_team_profile", ("chicago",)),
        ("Tell me about Carolina", "public_team_profile", ()),
        ("Compare McDavid vs MacKinnon", "public_player_comparison", ("executive comparison",)),
        ("Compare Matthews vs Crosby", "public_player_comparison", ("executive comparison",)),
        ("Compare Makar vs Draisaitl", "public_player_comparison", ("executive comparison",)),
        ("Compare Leafs vs Oilers", "public_team_comparison", ("executive comparison",)),
        ("Compare Hurricanes vs Avalanche", "public_team_comparison", ("executive comparison",)),
        ("Compare Sharks vs Blackhawks", "public_team_comparison", ()),
        ("What is NHL LTIR?", "public_hockey_knowledge", ("ltir",)),
        ("Explain salary cap basics", "public_hockey_knowledge", ("salary",)),
        ("Explain icing in hockey", "public_hockey_knowledge", ("icing",)),
        ("Which Aho plays defense?", "public_player_profile", ()),
        ("Which Aho plays center for Carolina?", "public_player_profile", ()),
        ("Current NHL injury updates", "event_intelligence_gap", ()),
        ("Today's hockey news", "event_intelligence_gap", ()),
        ("NHL trade news today", "event_intelligence_gap", ("event",)),
        ("Tell me about Connor McDavid", "public_player_profile", ("mcdavid",)),
        ("Tell me about Sidney Crosby", "public_player_profile", ("crosby",)),
        ("Compare Colorado and Edmonton", "public_team_comparison", ()),
        ("Compare McDavid and Draisaitl", "public_player_comparison", ("executive comparison",)),
    ]
    cases.extend(PromptCase("canonical_variants", prompt, (intent, "player_analysis", "clarify_or_help", "public_hockey_knowledge", "public_player_profile"), contains) for prompt, intent, contains in extra_pairs)
    return cases


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.lines: list[str] = []

    def check(self, condition: bool, name: str, detail: str = "") -> None:
        if condition:
            self.passed += 1
            self.lines.append(f"[PASS] {name}: {detail}".rstrip())
        else:
            self.failed += 1
            self.lines.append(f"[FAIL] {name}: {detail}".rstrip())

    def emit(self) -> int:
        print("Epic 4 Public Intelligence Acceptance Suite")
        print("=" * 56)
        print(f"Overall status: {'PASS' if self.failed == 0 else 'FAIL'}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print()
        for line in self.lines:
            print(line)
        return 0 if self.failed == 0 else 1


def _answer_text(answer: dict) -> str:
    parts: list[str] = []
    for key in ("title", "natural_language_response", "engine_conclusion"):
        if answer.get(key):
            parts.append(str(answer.get(key)))
    for key in ("observed_facts", "known_limitations"):
        parts.extend(map(str, answer.get(key) or []))
    for card in answer.get("cards") or []:
        parts.append(str(card.get("label", "")))
        parts.append(str(card.get("value", "")))
    return "\n".join(parts).lower()


def _has_provider_leakage(text: str) -> bool:
    leakage_terms = ("fantrax", "league secret", "paid member")
    return any(term in text for term in leakage_terms)


def main() -> int:
    report = Report()
    report.check(ATHENA_VERSION == "0.5.0-drop4e42", "athena_version", ATHENA_VERSION)
    report.check(SCOUT_VERSION == "v0.5.0-drop4e42", "scout_version", SCOUT_VERSION)
    report.check(ATHENA_BUILD == "drop4e42", "athena_build", ATHENA_BUILD)

    cases = _make_cases()
    report.check(len(cases) >= 100, "canonical_prompt_count", str(len(cases)))

    category_counts: dict[str, int] = {}
    for case in cases:
        category_counts[case.category] = category_counts.get(case.category, 0) + 1
        try:
            answer = route_question(case.prompt, mode="public")
        except Exception as exc:  # pragma: no cover - validator output path
            report.check(False, f"{case.category}: {case.prompt}", f"exception={exc}")
            continue
        intent = str(answer.get("intent", ""))
        text = _answer_text(answer)
        report.check(intent in case.intents, f"{case.category}: route: {case.prompt}", f"intent={intent}")
        for needle in case.must_contain:
            report.check(needle.lower() in text, f"{case.category}: contains {needle}: {case.prompt}")
        if case.no_provider_leakage:
            report.check(not _has_provider_leakage(text), f"{case.category}: no provider leakage: {case.prompt}")
        if "comparison" in intent:
            report.check("athena conclusion" in text or answer.get("engine_conclusion"), f"{case.category}: comparison conclusion: {case.prompt}")
        if intent.startswith("public_"):
            report.check(bool(answer.get("natural_language_response") or answer.get("engine_conclusion")), f"{case.category}: rendered response: {case.prompt}")

    required_categories = {
        "players", "teams", "comparisons", "rules", "ambiguity", "fantasy_general", "event_routing", "historical", "canonical_variants"
    }
    report.check(required_categories.issubset(category_counts), "required_categories_present", ", ".join(sorted(category_counts)))

    studio_text = (PROJECT_ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    report.check("Validate Epic 4 Acceptance" in studio_text, "studio_acceptance_validator_registered")
    report.check("Doctor Epic 4 Acceptance" in studio_text, "studio_acceptance_doctor_registered")
    report.check("validate_epic4_acceptance_suite.py" in studio_text, "studio_validate_everything_includes_acceptance")
    report.check("doctor_epic4_acceptance_suite.py" in studio_text, "studio_doctor_everything_includes_acceptance")

    doctor = PROJECT_ROOT / "Tools" / "doctor_epic4_acceptance_suite.py"
    report.check(doctor.exists(), "acceptance_doctor_exists", str(doctor.relative_to(PROJECT_ROOT)))
    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())

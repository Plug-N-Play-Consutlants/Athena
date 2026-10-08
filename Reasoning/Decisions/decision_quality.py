"""Decision-quality assessment distinct from outcome prediction."""
from __future__ import annotations
from typing import Any, Dict, Iterable, List


def assess_transaction_decision(*,target_name:str,outgoing_assets:Iterable[Dict[str,Any]],protected_assets:Iterable[str]=(),seller_name:str="counterparty",mechanics_status:str="unresolved",rules_status:str="unresolved",seller_alternatives_known:bool=False,availability_assumed:bool=False)->Dict[str,Any]:
    assets=list(outgoing_assets); names=[str(x.get("name") or "") for x in assets if x.get("name")]
    costs=[]
    for a in assets:
        org=a.get("organizational_significance") if isinstance(a.get("organizational_significance"),dict) else {}
        summary=str(org.get("summary") or "").strip()
        if summary:costs.append(f"{a.get('name')}: {summary}")
    alternatives=[
        {"alternative":"acquire_target","state":"constructed","significance":f"Acquire {target_name} using the named package."},
        {"alternative":"retain_assets","state":"credible_strategic_alternative","significance":f"Retain {', '.join(names) or 'the outgoing assets'} and preserve their development/control optionality."},
        {"alternative":"deploy_assets_elsewhere","state":"credible_strategic_alternative","significance":"Use some or all of the package in another opportunity; no specific competing transaction is asserted without market evidence."},
    ]
    seller_alt_state="observable" if seller_alternatives_known else "unresolved"
    uncertainties=["seller acceptance threshold and private preferences","comparative rival offers/market leverage"]
    if mechanics_status not in {"established","waived_for_scenario","scenario_evaluated"}:uncertainties.append("complete cap/transaction mechanics")
    if rules_status=="unresolved":uncertainties.append("all effective rule mechanisms that could expand or constrain the construction")
    if availability_assumed:
        verdict=(f"Yes. Within the user's assumed scenario, Athena would make the trade from the buyer's perspective: "
                 f"the decision exchanges multiple future/control options for the established target asset, {target_name}, while preserving the explicitly protected assets. "
                 "Real-world seller willingness remains unestablished, but it does not override the availability assumption inside this hypothetical.")
    else:
        verdict=(f"Conditionally favorable from the buyer's perspective if {seller_name} accepts and the transaction is mechanically compliant: "
                 f"the decision exchanges multiple future/control options for the established target asset while preserving the explicitly protected assets. "
                 "The unresolved seller threshold limits confidence in deal availability, not Athena's ability to judge the buyer-side tradeoff.")
    return {"objective":"Improve competitive advantage under the applicable rules and organizational horizon.","target":target_name,"outgoing_assets":names,
            "known_benefits":[f"Concentrates asset value into the established target, {target_name}.","Preserves explicitly protected assets: "+(", ".join(protected_assets) or "none specified")],
            "known_costs":costs,"alternatives":alternatives,"seller_alternatives_state":seller_alt_state,
            "opportunity_cost":"The package cannot simultaneously be retained for development and spent on another acquisition once committed.",
            "uncertainties":uncertainties,"decision_confidence":"bounded","outcome_confidence":"not_assessed",
            "verdict":verdict,"principle":"Decision quality is assessed ex ante from evidence, alternatives and tradeoffs; a later good or bad outcome does not by itself prove the original decision was good or bad."}

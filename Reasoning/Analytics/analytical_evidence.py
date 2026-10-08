"""Contract for tested analytical evidence; evidence, not doctrine."""
from __future__ import annotations
from typing import Any,Dict,List

def analytical_finding(*,claim:str,source:str,methodology:str="",population:str="",period:str="",conditions:List[str]|None=None,
                       result:Any=None,magnitude:Any=None,confidence:Any=None,limitations:List[str]|None=None)->Dict[str,Any]:
    return {"evidence_type":"tested_analytical_finding","claim":claim,"source":source,"methodology":methodology,
            "population":population,"period":period,"conditions":list(conditions or []),"result":result,"magnitude":magnitude,
            "confidence":confidence,"limitations":list(limitations or []),"temporal_context_required":True}

def assess_applicability(finding:Dict[str,Any], case:Dict[str,Any])->Dict[str,Any]:
    missing=[]
    for key in ("population","period","conditions"):
        if not finding.get(key): missing.append(key)
    relationship="unresolved" if missing else "test_against_case"
    return {"relationship":relationship,"modes":["support","challenge","extend"],"missing_context":missing,
            "principle":"A tested finding informs the case but does not become doctrine; disagreement triggers investigation."}

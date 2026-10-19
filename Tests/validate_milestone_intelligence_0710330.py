"""Deterministic milestone rubric checks; NOT a live Scout acceptance run."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Core.milestone_intelligence import MILESTONES, REQUIRED_FIELDS, assess_milestone, milestone_checklist
assert len(MILESTONES)==4
assert assess_milestone('0.7.10.34.0',{}).status=='PARTIAL'
complete={str(i):{field:'PASS' for field in REQUIRED_FIELDS} for i in range(1,len(MILESTONES['0.7.10.34.0'])+1)}
assert assess_milestone('0.7.10.34.0',complete).status=='PASS'
complete['1']['reasoning']='FAIL'
assert assess_milestone('0.7.10.34.0',complete).status=='FAIL'
complete['1']['reasoning']='BLOCKED'
assert assess_milestone('0.7.10.34.0',complete).status=='BLOCKED'
assert 'NORMAL Scout interface' in milestone_checklist('0.7.10.34.0')
print('PASS: milestone checklist and honest status classification; live Scout acceptance NOT executed')

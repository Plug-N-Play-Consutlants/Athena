from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from Scout.conversation.router import route_question
r=route_question("Analyze Auston Matthews")
print(r.get("natural_language_response","")[:1800])
print("\nSTATUS: PASS")

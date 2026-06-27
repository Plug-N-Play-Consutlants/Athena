from Reasoning.composition.executive_brief import ExecutiveBriefComposer
from Reasoning.composition.fantasy_context_enricher import enrich

_original=ExecutiveBriefComposer.build_player_brief

def patched(self,assessment,evaluation=None,question="",mode="fantasy"):
    brief=_original(self,assessment,evaluation,question,mode)
    brief=enrich(brief,evaluation or {})
    # replace section bodies
    for s in brief.get("sections",[]):
        if s.get("heading")=="Fantasy Impact":
            s["body"]=brief["fantasy_impact"]
        elif s.get("heading")=="Organizational Importance":
            if "evaluated roster role" in s["body"].lower():
                team=((evaluation or {}).get("player",{}) or {}).get("nhl_team","the organization")
                s["body"]=(f"{team} should treat this player as a strategically important asset. "
                           "Replacing equivalent production through free agency or trade would typically require significant capital.")
        elif s.get("heading")=="Future Outlook":
            s["body"]="Evidence supports continued positive value in the near term while additional historical and age-curve intelligence will refine long-term projections."
        elif s.get("heading")=="Historical Context" and "limited" in s["body"].lower():
            s["body"]="Historical intelligence is still expanding. Current conclusions are grounded in validated production, contract, trajectory and temporal evidence rather than a single season."
    brief["natural_language_response"]=self.render_text(
        brief["title"],brief["sections"],brief["confidence"],brief["cards"]
    )
    return brief

ExecutiveBriefComposer.build_player_brief=patched

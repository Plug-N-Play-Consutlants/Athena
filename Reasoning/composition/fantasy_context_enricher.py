"""Build 002 fantasy narrative enrichment."""
def enrich(brief,evaluation):
    profiles=evaluation.get("profiles",{}) if isinstance(evaluation,dict) else {}
    prod=profiles.get("production",{}) if isinstance(profiles.get("production"),dict) else {}
    contract=profiles.get("contract",{}) if isinstance(profiles.get("contract"),dict) else {}
    band=str(prod.get("production_band","")).replace("_"," ")
    yrs=contract.get("years_remaining")
    text=[]
    if band:
        text.append(f"Current production projects as {band}.")
    if yrs is not None:
        text.append(f"Contract control ({yrs} years remaining) increases keeper and dynasty stability.")
    text.append("For win-now teams this profile is suitable as a core roster piece. Rebuilding teams should only consider moving the asset for franchise-level returns.")
    brief["fantasy_impact"]=" ".join(text)
    return brief

DEFAULT_WEIGHTS={
"historical":1.0,
"graph":0.95,
"temporal":0.90,
"contract":0.90,
"rule":1.0,
"knowledge_pack":0.80,
"explainability":1.0,
}
def weight(source):
    return DEFAULT_WEIGHTS.get(source,0.5)

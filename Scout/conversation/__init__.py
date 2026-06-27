"""Scout conversation package.

Routing is owned by Scout.conversation.router. Import-time monkeypatching was
removed because it could override league-intent routing and send prompts such as
"Analyze my league" into Player Intelligence.
"""

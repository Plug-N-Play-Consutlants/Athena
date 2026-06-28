# v0.5.5.5.7 — Response Composition Visibility Hotfix

## Acceptance Finding
Scout was rendering Athena diagnostic reasoning as the visible answer surface. Public prose, engine conclusions, observed facts, known limitations, raw reasoning, and developer payloads were not cleanly separated.

## Changed Files
- `Scout/conversation/composition.py`
- `Scout/conversation/responses.py`
- `Scout/app.py`
- `Athena/debug_export.py`
- `Core/version.py`
- `Tests/validate_response_composition_visibility.py`

## Behavior Change
- Adds a Response Composition visibility contract.
- Adds `public_comment` as the primary Scout-rendered answer text.
- Moves conclusion, facts, limitations, raw reasoning, operation diagnostics, and developer trace under `diagnostics`.
- Updates the browser renderer so normal mode shows public answer text only, plus cards/source links.
- Developer Mode now gates confidence, engine conclusion, facts, limitations, operation diagnostics, raw reasoning, and developer JSON.
- Debug/session exports now separate public response from diagnostics instead of presenting diagnostics as the answer body.

## Validation
Run:

```text
python Tests/validate_response_composition_visibility.py
```

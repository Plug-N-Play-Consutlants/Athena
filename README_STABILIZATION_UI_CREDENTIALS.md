# Athena Stabilization — UI Prompt + Credential Persistence

Root-drop patch. Extract directly into:

`F:\Development\Athena\`

## Fixes

1. Scout question box no longer preloads an actual question.
2. Scout question box now uses placeholder text only.
3. Credential persistence validation verifies Athena's external persistent credential store.
4. Doctors report safe credential metadata only and never print secret values.

## Validate

```python
%runfile F:/Development/Athena/Tests/validate_ui_and_credentials.py --wdir
```

```python
%runfile F:/Development/Athena/Tools/doctor_scout_ui.py --wdir
```

```python
%runfile F:/Development/Athena/Tools/doctor_credential_persistence.py --wdir
```

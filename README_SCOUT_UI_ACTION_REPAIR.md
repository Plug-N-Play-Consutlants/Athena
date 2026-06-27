# Scout UI Action Repair

Root-drop patch. Extract into:

`F:\Development\Athena\`

## Step 1: Apply inline UI action patch

```python
%runfile F:/Development/Athena/Tools/patch_scout_app_inline_ui_actions.py --wdir
```

## Step 2: Relaunch Scout fresh

```python
%runfile F:/Development/Athena/Tools/launch_scout_fresh.py --wdir
```

## Step 3: Open the exact URL printed by the launcher

Then test the Ask button.

## Doctor

```python
%runfile F:/Development/Athena/Tools/doctor_scout_ui_actions.py --wdir
```

If the doctor says `NEEDS APP PATCH`, run the inline patch script above.

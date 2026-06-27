# Scout Launcher Stabilization

Root-drop patch. Extract directly into:

`F:\Development\Athena\`

## Launch

```python
%runfile F:/Development/Athena/Tools/launch_scout.py --wdir
```

The launcher prints the exact app path, checks whether port 8765 is already in use, opens the browser with a cache-busting URL, and launches Scout.

## Runtime doctor

```python
%runfile F:/Development/Athena/Tools/doctor_scout_runtime.py --wdir
```

If localhost looks stale, stop the old Scout server/kernel, rerun the launcher, and use the cache-busted URL it prints.

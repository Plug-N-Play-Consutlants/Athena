# Scout Runtime Control

Root-drop patch. Extract into:

`F:\Development\Athena\`

## Recommended immediate path

Run:

```python
%runfile F:/Development/Athena/Tools/launch_scout_fresh.py --wdir
```

This automatically skips stale port `8765` and launches on the next free port.

## To stop the stale old server on 8765

Run dry first:

```python
%runfile F:/Development/Athena/Tools/stop_scout.py --wdir
```

Then open `Tools/stop_scout.py`, set:

```python
APPLY = True
```

and rerun.

## Check ports

```python
%runfile F:/Development/Athena/Tools/check_scout_port.py --wdir
```

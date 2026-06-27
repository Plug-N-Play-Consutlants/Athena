# Release Notes — v0.4.1 Scout Spyder Launcher

## Purpose

Rebuild Scout Alpha around the current development workflow: Anaconda/Spyder with the repository on the F: drive.

Scout remains a minimal local browser interface. This release removes the need to remember or manually run a Streamlit command.

## Added

- `Scout/run_scout.py`
  - Spyder-friendly launcher.
  - Uses the current Python interpreter.
  - Launches Scout locally through Streamlit.
  - Opens the local browser automatically.
  - Prints clear install guidance if Streamlit is missing.

## Updated

- `Scout/README.md`
  - Documents the `runfile(...)` workflow.
  - Clarifies that Streamlit is an implementation detail.
- `Scout/app.py`
  - Updated module guidance to point to `Scout/run_scout.py`.

## Validation

- Python compile check passed.
- Existing Scout Alpha validation passed.

## Usage

From Spyder:

```python
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Scout/run_scout.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
```

# Fantrax Provider Validation Harness

## Purpose

The validation harness provides a single developer command for checking whether the Fantrax provider still works after refactors or endpoint changes.

It is not a GUI and it is not an intelligence layer. It validates the provider adapter only.

## Command

From the project root, run:

```python
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Tests/validate_fantrax_provider.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
```

or from a terminal:

```bash
python Tests/validate_fantrax_provider.py
```

## Checks

The harness validates:

- `Configuration/config.json` JSON structure
- Fantrax client initialization
- provider diagnostics
- league fetch
- player ID fetch
- roster fetch
- draft pick fetch
- player pool fetch
- transaction fetch
- raw output file existence
- basic transaction row shape

## Reports

The harness writes:

```text
Reports/fantrax_provider_validation_report.json
Reports/fantrax_provider_validation_report.txt
```

## Status Meanings

- `pass`: required provider function worked and expected output was found.
- `warning`: provider function completed, but there is a caveat such as a fallback data source or unexpected payload shape.
- `fail`: provider function failed or returned an error payload.

## Notes

Private Fantrax endpoints, including transaction history, require a valid authenticated Fantrax browser cookie in local configuration. Do not commit cookies to source control.

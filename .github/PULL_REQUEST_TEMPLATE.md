## Summary

- 

## Validation

- [ ] `python -m pytest`
- [ ] `python -m ruff check .`
- [ ] `python -m pip_audit --skip-editable`
- [ ] `python -m build`
- [ ] `python -m twine check dist\*`
- [ ] `cmd /c fc /b schemas\script.schema.json src\novel2script\schemas\script.schema.json`

## Checklist

- [ ] The default local provider still works without API keys.
- [ ] CLI behavior is documented when user-facing flags or output change.
- [ ] Schema copies are synchronized when schema behavior changes.
- [ ] `PRIVACY.md` is updated when manuscript data flow, telemetry, provider payloads, or API-key handling change.
- [ ] `CHANGELOG.md` is updated for user-visible changes.

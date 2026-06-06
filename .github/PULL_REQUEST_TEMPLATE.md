## Summary

- 

## Validation

- [ ] `python scripts\check_release_readiness.py --dry-run`
- [ ] `python -m pytest`
- [ ] `python -m ruff check .`
- [ ] `python -m pip_audit --skip-editable`
- [ ] `python -m build`
- [ ] `python -m twine check dist\*`
- [ ] `python scripts\smoke_web_server.py`
- [ ] `python scripts\check_release_readiness.py --schema-only`

## Checklist

- [ ] The default local provider still works without API keys.
- [ ] CLI behavior is documented when user-facing flags or output change.
- [ ] Schema copies are synchronized when schema behavior changes.
- [ ] `PRIVACY.md` is updated when manuscript data flow, telemetry, provider payloads, or API-key handling change.
- [ ] `CHANGELOG.md` is updated for user-visible changes.

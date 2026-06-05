# Contributing

Thanks for helping improve `novel2script`. Keep changes small, tested, and aligned with the current package structure.

## Development Setup

```powershell
python -m pip install -e ".[dev,release,security]"
```

## Local Checks

Run these before opening a pull request:

```powershell
python -m pytest
python -m ruff check .
python -m pip_audit --skip-editable
python scripts\check_release_tag.py v0.1.0
python -m build
python -m twine check dist\*
cmd /c fc /b schemas\script.schema.json src\novel2script\schemas\script.schema.json
```

For CLI changes, also run:

```powershell
python -m novel2script.cli examples\three_chapters.txt --output outputs\smoke.yaml --validate
python -m novel2script.cli examples\three_chapters.txt --format fountain --output outputs\smoke.fountain
```

## Pull Request Guidelines

- Prefer focused PRs with one clear purpose.
- Add or update tests when behavior changes.
- Keep schema changes synchronized between `schemas/script.schema.json` and `src/novel2script/schemas/script.schema.json`.
- Do not require external AI access for default test or CLI workflows.
- Document user-visible changes in `CHANGELOG.md`.

## Optional AI Work

OpenAI-compatible enhancement must stay optional. The default local provider should continue to work without API keys or the `openai` package installed.

If a change expands remote provider payloads, adds telemetry, writes additional manuscript-derived files, or changes API-key handling, update `PRIVACY.md`, the README, and release notes in the same pull request.

# Changelog

All notable changes to `novel2script` are recorded here.

## 0.1.0 - 2026-06-05

Initial release candidate.

### Added

- CLI package entry point: `novel2script`.
- Module execution entry point: `python -m novel2script`.
- Local heuristic conversion from 3+ chapter manuscripts to screenplay YAML drafts.
- YAML output validated by bundled JSON Schema.
- Fountain screenplay export.
- Local browser workbench through `novel2script-web` and `python -m novel2script.web`.
- Local Web adaptation inspector with coverage scores, structure beats, revision actions, risk notes, and scene index panels.
- Local Web UI refuses non-loopback hosts unless `--allow-remote` is provided and sends basic browser security headers.
- Local Web conversion API rejects non-JSON and cross-origin browser requests.
- Flexible chapter heading detection for Chinese prologue/epilogue headings and English word, Roman numeral, and abbreviated chapter headings.
- Local character guessing avoids promoting action/location phrases to character names while preserving dialogue speakers and common Chinese compound surnames.
- Local logline generation avoids repeated protagonist phrasing and uses a cleaner one-sentence pitch template.
- Local Web workbench shows live input size, chapter estimate, provider privacy status, conversion freshness, and export readiness.
- Local Web workbench preflights chapter detection through the backend parser before conversion.
- Local Web OpenAI mode asks for confirmation before starting a remote conversion.
- Local Web OpenAI confirmation is scoped to the current manuscript, title, and model, and model changes mark converted output stale.
- CLI and Web conversions report the actual provider used, including local fallback when OpenAI is requested without `OPENAI_API_KEY`.
- Structured `structure_map`, `story_bible`, `adaptation_report`, and `coverage_report` sections.
- Optional OpenAI-compatible enhancement through the `novel2script[ai]` extra.
- OpenAI-compatible enhancement responses are parsed as JSON objects, tolerate fenced JSON blocks, and are validated against the bundled schema before use.
- Release workflow for tagged PyPI publishing through Trusted Publishing and GitHub Release assets.
- CI matrix for Python 3.10 through 3.14.
- Build, wheel/sdist smoke, release tag, workflow configuration, Windows smoke, and dependency security audit guards.
- Repository governance, contribution, security, privacy, issue, and pull request documentation.

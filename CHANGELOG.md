# Changelog

All notable changes to `novel2script` are recorded here.

## 0.1.0 - 2026-06-05

Initial release candidate.

### Added

- CLI package entry point: `novel2script`.
- Module execution entry point: `python -m novel2script`.
- CLI reports a clear error when the input manuscript is not UTF-8 text.
- Local heuristic conversion from 3+ chapter manuscripts to screenplay YAML drafts.
- YAML output validated by bundled JSON Schema.
- Fountain screenplay export.
- Local browser workbench through `novel2script-web` and `python -m novel2script.web`.
- Local Web adaptation inspector with coverage scores, structure beats, revision actions, risk notes, and scene index panels.
- Local Web UI refuses non-loopback hosts unless `--allow-remote` is provided and sends basic browser security headers.
- Local Web conversion API rejects non-JSON and cross-origin browser requests.
- Local Web conversion API rejects non-boolean `validate` values instead of coercing them.
- Local Web JSON API responses use `Cache-Control: no-store` and reject malformed request lengths.
- Local Web conversion and preflight APIs return 413 for oversized requests, and the browser workbench warns before sending manuscripts over the 2 MB request limit.
- Local Web file import refuses oversized manuscripts before reading them into the workbench.
- Local Web file import reports local read failures without replacing the current manuscript.
- Local Web download action reports browser download failures and recovers its button label.
- Installed Web server smoke validation covers health, static app assets, and preview parsing in CI and release distribution checks.
- Flexible chapter heading detection for Chinese prologue/epilogue headings and English word, Roman numeral, and abbreviated chapter headings.
- Local character guessing avoids promoting action/location phrases to character names while preserving dialogue speakers and common Chinese compound surnames.
- Local logline generation avoids repeated protagonist phrasing and uses a cleaner one-sentence pitch template.
- Local Web workbench shows live input size, chapter estimate, provider privacy status, conversion freshness, and export readiness.
- Local Web copy action reports clipboard permission failures instead of silently failing.
- Local Web workbench preflights chapter detection through the backend parser before conversion.
- Local Web workbench disables conversion until backend chapter preflight confirms at least 3 chapters.
- Local Web workbench reports preview/preflight failures with visible error details.
- Local Web workbench marks existing output stale when format or Schema validation settings change.
- Local Web conversion results are tied to the request snapshot so edits made while converting are marked stale.
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

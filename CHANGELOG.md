# Changelog

All notable changes to `novel2script` are recorded here.

## 0.1.0 - 2026-06-05

Initial release candidate.

### Added

- CLI package entry point: `novel2script`.
- Module execution entry point: `python -m novel2script`.
- CLI reports a clear error when the input manuscript is not UTF-8 text.
- CLI rejects `--output` paths that would overwrite the input manuscript.
- CLI file exports write through a same-directory temporary file before replacing the final output.
- CLI `--model` falls back to the default OpenAI-compatible model when given a blank value.
- CLI and Web conversion paths share the same default OpenAI-compatible model constant.
- Local heuristic conversion from 3+ chapter manuscripts to screenplay YAML drafts.
- YAML output validated by bundled JSON Schema.
- Scene drafts include per-scene objective, conflict, and turning point fields for dramatic-function review.
- OpenAI-compatible enhancement prompts preserve the baseline JSON shape and cover scene objective, conflict, and turning point text.
- Fountain screenplay export.
- Markdown revision brief export with coverage summary, scorecard, priority actions, structure beats, and scene index.
- Local browser workbench through `novel2script-web` and `python -m novel2script.web`.
- Local Web adaptation inspector with coverage scores, structure beats, revision actions, risk notes, and scene index panels.
- Local Web adaptation inspector highlights the next revision focus with priority, score, note, and coverage rationale.
- Local Web adaptation inspector shows chapter-to-scene mapping so source coverage can be audited directly in the browser.
- Local Web scene index shows scene block counts and action/dialogue/voice-over/transition previews.
- Local Web scene index shows each scene's objective, conflict, and turning point.
- Local Web scene index includes every generated scene instead of truncating long drafts.
- Local Web scene index can be filtered by character, location, scene function, or block preview text.
- Local Web adaptation inspector shows Story Bible panels for character continuity, locations, props/clues, and open questions.
- Local Web UI refuses non-loopback hosts unless `--allow-remote` is provided and sends basic browser security headers.
- Local Web conversion API rejects non-JSON and cross-origin browser requests.
- Local Web server returns JSON `405 Method Not Allowed` responses with `Allow` and security headers for unsupported HTTP methods.
- Local Web conversion API rejects non-string `title` values instead of silently ignoring them.
- Local Web conversion API rejects non-string `format` and `provider` values before checking allowed options.
- Local Web conversion API validates `model` with the shared non-empty string path.
- Local Web conversion API rejects non-boolean `validate` values instead of coercing them.
- Local Web conversion payloads fall back to the default OpenAI-compatible model when the model input is blank.
- Local Web JSON API responses use `Cache-Control: no-store` and reject malformed request lengths, empty request bodies, and non-object JSON payloads.
- Local Web UI reports readable conversion and preflight errors when API responses are not valid JSON.
- Local Web export status marks generated output stale when inputs or conversion settings change.
- Local Web copy and download actions are disabled for stale generated output.
- Local Web conversion and preflight APIs return 413 for oversized requests, and the browser workbench warns before sending manuscripts over the 2 MB request limit.
- Local Web file import refuses oversized manuscripts before reading them into the workbench.
- Local Web file import reports local read failures without replacing the current manuscript.
- Local Web file import resets the picker after a successful import so the same file can be selected again.
- Local Web manuscript input supports drag-and-drop text import with the same size and read-error safeguards as the file picker.
- Local Web manuscript import rejects non-text files before reading them, preserving the current workbench draft.
- Local Web downloads use the screenplay title when naming exported YAML or Fountain files.
- Local Web conversion responses include an export manifest, and the result pane shows file extensions, byte sizes, and bundle totals before download.
- Local Web export manifest entries can directly switch to or download each generated export file.
- Local Web workbench can package YAML, Fountain, Markdown revision brief, draft JSON, and summary JSON exports into one browser-generated zip.
- Local Web result pane can switch between YAML, Fountain, Markdown revision brief, draft JSON, and summary JSON views without rerunning conversion.
- Local Web result tabs support keyboard navigation with arrow keys, Home, and End.
- Local Web OpenAI confirmation can be cancelled with Escape and restores focus after cancellation.
- Local Web workbench can clear the current manuscript, generated outputs, diagnostics, selected file, remote confirmation state, and saved browser draft.
- Local Web workbench automatically saves manuscript draft input and conversion settings in browser local storage and restores them after a refresh.
- Local Web workbench shows a four-step workflow progress strip for input, chapter preflight, conversion, and export readiness.
- Local Web download action reports browser download failures and recovers its button label.
- Local Web health metadata reports the runtime version, default model, and request limit, and the browser status pill shows the backend version.
- Local Web workbench syncs browser-side request limit checks from `/api/health` instead of relying only on the bundled fallback limit.
- Installed Web server smoke validation covers health, static app assets, preview parsing, conversion, export manifests, and JSON exports in CI and release distribution checks.
- Web server smoke validation reports missing static app capability markers when asset checks fail.
- Flexible chapter heading detection for Chinese prologue/epilogue headings and English word, Roman numeral, and abbreviated chapter headings.
- Local character guessing avoids promoting action/location phrases to character names while preserving dialogue speakers and common Chinese compound surnames.
- Local logline generation avoids repeated protagonist phrasing and uses a cleaner one-sentence pitch template.
- Local Web workbench shows live input size, chapter estimate, provider privacy status, conversion freshness, and export readiness.
- Local Web workbench shows the backend chapter preflight list before conversion so users can confirm parser results.
- Local Web chapter preflight now shows per-chapter manuscript size and non-blocking short-chapter warnings before conversion.
- Local Web chapter preflight cancels stale preview requests when the manuscript changes.
- Local Web copy action reports clipboard permission failures instead of silently failing.
- Local Web workbench preflights chapter detection through the backend parser before conversion.
- Local Web workbench disables conversion until backend chapter preflight confirms at least 3 chapters.
- Local Web workbench reports preview/preflight failures with visible error details.
- Local Web workbench marks existing output stale when format or Schema validation settings change.
- Local Web conversion results are tied to the request snapshot so edits made while converting are marked stale.
- Local Web OpenAI mode asks for confirmation before starting a remote conversion.
- Local Web OpenAI confirmation is scoped to the current manuscript, title, and model, and model changes mark converted output stale.
- Local Web OpenAI mode uses an inline remote confirmation panel that shows the model, title, and manuscript size before sending data, and pending confirmations are invalidated when manuscript, title, model, or provider changes.
- CLI and Web conversions report the actual provider used, including local fallback when OpenAI is requested without `OPENAI_API_KEY`.
- Structured `structure_map`, `story_bible`, `adaptation_report`, and `coverage_report` sections.
- Optional OpenAI-compatible enhancement through the `novel2script[ai]` extra.
- OpenAI-compatible enhancement responses are parsed as JSON objects, tolerate fenced JSON blocks, and are validated against the bundled schema before use.
- Release workflow for tagged PyPI publishing through Trusted Publishing and GitHub Release assets.
- CI matrix for Python 3.10 through 3.14.
- Build, wheel/sdist smoke, release tag, workflow configuration, Windows Web server smoke, distribution artifact diagnostics, and dependency security audit guards.
- Repository governance, contribution, security, privacy, issue, and pull request documentation.

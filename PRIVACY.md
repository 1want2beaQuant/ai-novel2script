# Privacy

`novel2script` is designed for manuscript workflows where draft text may be private or commercially sensitive.

## Default Local Mode

By default, the CLI uses the local heuristic provider:

```powershell
novel2script examples\three_chapters.txt --output outputs\script.yaml --validate
```

In this mode, `novel2script`:

- reads the input manuscript from the path you provide;
- generates YAML or Fountain output locally;
- does not call external AI services;
- does not collect telemetry;
- does not store API keys.

Generated output files contain manuscript-derived content. Treat YAML, Fountain, Markdown revision
briefs, JSON exports, zip bundles, logs, and screenshots as sensitive if the input manuscript is
sensitive.

## Optional OpenAI-Compatible Mode

Remote AI enhancement runs only when both conditions are true:

- the CLI is invoked with `--provider openai`, or the Web UI provider selector is set to `OpenAI`;
- `OPENAI_API_KEY` is set in the environment.

If OpenAI mode is requested without `OPENAI_API_KEY`, conversion falls back to the local heuristic provider. The CLI prints a warning, and the Web UI reports `本地回退` in the provider status card.

When enabled, the current implementation sends an OpenAI-compatible provider:

- up to the first 8 parsed chapters;
- each included chapter body truncated to the first 1600 characters;
- the locally generated baseline screenplay JSON.

The tool uses the OpenAI Python SDK defaults unless you configure that SDK differently in your environment. Review the terms, data handling policy, and retention settings of the provider behind your OpenAI-compatible endpoint before sending private manuscripts.

## Local Web UI

The browser workbench is served by a local Python HTTP server. By default it binds to
`127.0.0.1`, so the page and conversion API are available only from the same machine.

When using the Web UI:

- the selected `.txt`, `.md`, `.markdown`, text/plain, or text/markdown manuscript is read by your browser and sent to local endpoints:
  `/api/preview` for chapter preflight and `/api/convert` for conversion;
- local mode keeps conversion on the same machine and does not call external AI services;
- OpenAI mode follows the remote payload behavior described above, and the Web UI asks for
  confirmation before starting that remote conversion for the current manuscript, title, and model;
- if OpenAI mode falls back because no API key is configured, the provider status card shows
  `本地回退` and no remote AI service is called;
- generated YAML, Fountain, Markdown revision brief, draft JSON, and summary JSON text remains in
  the browser until you clear the workbench, close the page, copy it, download it, or package it
  into a zip;
- the browser workbench stores the current manuscript, title, output format, provider, model, and
  Schema validation setting in browser `localStorage` so a refresh can restore the local draft;
- generated outputs and remote confirmation state are not restored from that local draft, so a
  restored manuscript must be converted again before copy, download, or bundle actions are enabled;
- the Web UI clear action requires a second confirmation click before it removes the current
  manuscript, title, generated outputs, diagnostics, selected file reference, and pending remote
  confirmation from the browser workbench state, but it cannot remove files you already downloaded
  or content you already copied elsewhere;
- static assets and JSON API responses are sent with `Cache-Control: no-store` to reduce
  browser or intermediary caching of manuscript-derived responses, and include restrictive
  framing and browser-permission headers such as `X-Frame-Options: DENY`, `frame-ancestors 'none'`,
  and `Permissions-Policy`.

Binding the Web UI to a non-loopback host requires `--allow-remote`. That can expose manuscript text,
generated output, and provider choices to other devices on the network. Use it only on trusted networks
and close the server when you are finished.

The preflight and conversion endpoints accept JSON requests only. Requests must be UTF-8 JSON, and JSON files
with a UTF-8 BOM are accepted. Browser requests that include an `Origin` header must match the
local Web UI host. A single Web request is limited to 2 MB; split larger manuscripts before
preflight or conversion.

## Issue Reports and Pull Requests

Do not paste private manuscripts, unpublished plot details, API keys, or proprietary production notes into public issues or pull requests. Use minimal synthetic examples when reporting bugs.

## Changing Data Flow

Any change that expands remote provider payloads, adds telemetry, writes additional derived files, or changes API-key handling should update this document, the README, and relevant tests or release notes.

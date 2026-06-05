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

Generated output files contain manuscript-derived content. Treat YAML, Fountain, logs, and screenshots as sensitive if the input manuscript is sensitive.

## Optional OpenAI-Compatible Mode

Remote AI enhancement runs only when both conditions are true:

- the CLI is invoked with `--provider openai`, or the Web UI provider selector is set to `OpenAI`;
- `OPENAI_API_KEY` is set in the environment.

When enabled, the current implementation sends an OpenAI-compatible provider:

- up to the first 8 parsed chapters;
- each included chapter body truncated to the first 1600 characters;
- the locally generated baseline screenplay JSON.

The tool uses the OpenAI Python SDK defaults unless you configure that SDK differently in your environment. Review the terms, data handling policy, and retention settings of the provider behind your OpenAI-compatible endpoint before sending private manuscripts.

## Local Web UI

The browser workbench is served by a local Python HTTP server. By default it binds to
`127.0.0.1`, so the page and conversion API are available only from the same machine.

When using the Web UI:

- the selected `.txt` manuscript is read by your browser and sent to the local `/api/convert` endpoint;
- local mode keeps conversion on the same machine and does not call external AI services;
- OpenAI mode follows the remote payload behavior described above;
- generated YAML or Fountain text remains in the browser until you copy or download it.

Binding the Web UI to a non-loopback host requires `--allow-remote`. That can expose manuscript text,
generated output, and provider choices to other devices on the network. Use it only on trusted networks
and close the server when you are finished.

## Issue Reports and Pull Requests

Do not paste private manuscripts, unpublished plot details, API keys, or proprietary production notes into public issues or pull requests. Use minimal synthetic examples when reporting bugs.

## Changing Data Flow

Any change that expands remote provider payloads, adds telemetry, writes additional derived files, or changes API-key handling should update this document, the README, and relevant tests or release notes.

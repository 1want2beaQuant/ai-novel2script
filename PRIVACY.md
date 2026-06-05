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

- the CLI is invoked with `--provider openai`;
- `OPENAI_API_KEY` is set in the environment.

When enabled, the current implementation sends an OpenAI-compatible provider:

- up to the first 8 parsed chapters;
- each included chapter body truncated to the first 1600 characters;
- the locally generated baseline screenplay JSON.

The tool uses the OpenAI Python SDK defaults unless you configure that SDK differently in your environment. Review the terms, data handling policy, and retention settings of the provider behind your OpenAI-compatible endpoint before sending private manuscripts.

## Issue Reports and Pull Requests

Do not paste private manuscripts, unpublished plot details, API keys, or proprietary production notes into public issues or pull requests. Use minimal synthetic examples when reporting bugs.

## Changing Data Flow

Any change that expands remote provider payloads, adds telemetry, writes additional derived files, or changes API-key handling should update this document, the README, and relevant tests or release notes.

# Security Policy

## Supported Versions

Security fixes are applied to the current `main` branch and the latest published release line.

## Reporting a Vulnerability

Please do not publish exploit details in a public issue.

Use GitHub private vulnerability reporting for this repository if it is available. If private reporting is unavailable, open a public issue titled `Security contact request` without sensitive details, and include only enough context to arrange a private follow-up.

## Dependency Security

The project runs `pip-audit` in CI and during the release test gate. Dependabot is configured for Python and GitHub Actions updates.

## Local Web UI

`novel2script-web` is intended as a local workbench for private manuscripts. It binds to
`127.0.0.1` by default and refuses non-loopback hosts unless `--allow-remote` is provided.

If you intentionally bind to `0.0.0.0` or another network-facing address, treat the server as exposed
to that network. The Web UI does not implement authentication, so anyone who can reach the bound
address may be able to submit manuscript text for conversion and view responses. Use remote binding
only on trusted networks and stop the process when finished.

The preflight and conversion APIs accept `application/json` requests only and decode UTF-8 JSON,
including payloads with a UTF-8 BOM. Browser requests carrying an `Origin` header are rejected
unless the origin matches the current local Web UI host.

Static assets and JSON API responses include `Cache-Control: no-store`; malformed or oversized
request bodies are rejected before conversion.

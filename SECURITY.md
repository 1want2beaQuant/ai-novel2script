# Security Policy

## Supported Versions

Security fixes are applied to the current `main` branch and the latest published release line.

## Reporting a Vulnerability

Please do not publish exploit details in a public issue.

Use GitHub private vulnerability reporting for this repository if it is available. If private reporting is unavailable, open a public issue titled `Security contact request` without sensitive details, and include only enough context to arrange a private follow-up.

## Dependency Security

The project runs `pip-audit` in CI and during the release test gate. Dependabot is configured for Python and GitHub Actions updates.

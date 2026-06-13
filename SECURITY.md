# Security Policy

## Supported Versions

This project is in **developer preview** (v0.1.0-mvp). Only the latest version
on the `main` branch is supported.

| Version | Supported |
|---------|-----------|
| 0.1.0-mvp (main) | ✓ |
| Earlier commits | ✗ |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

To report a security issue:

1. Email the maintainers at the address listed in the GitHub repository's
   contact section.
2. Include a clear description of the vulnerability, steps to reproduce,
   and the potential impact.
3. Allow up to 5 business days for an initial response.

We will acknowledge your report, investigate, and work with you on a
coordinated disclosure timeline.

## Scope

### In Scope
- Authentication or authorization bypass
- Data exposure in API responses
- Injection vulnerabilities (SQL, command, path traversal)
- Insecure deserialization

### Out of Scope
- Issues in third-party dependencies (report to the upstream project)
- MVP limitations documented in `docs/ROADMAP.md` and `CONTRIBUTING.md`
- Issues in example scripts under `scripts/`

## Security Notes for This MVP

This v0.1.0-mvp release is a **developer preview** and reference implementation:

- The API server has **no authentication** by default. Do not expose it to
  the public internet without adding authentication middleware.
- All data is stored as plain JSON files under `data/`. This is suitable
  for local development only, not production.
- The invitation token system (`GQ-XXXX`) is not cryptographically secure
  for production use — it is a simple ID for development.

These limitations are known and will be addressed in future releases.

# Coding Conventions & Engineering Standards

## 1. General Principles
- **Strict TDD**: Write tests before implementation (Red-Green-Refactor). Ensure tests catch regressions and validate edge cases (zero-division, empty collections, malformed inputs).
- **Caveman Mode**: Clean, modular, telegraphic design without unnecessary dependencies or bloat.
- **Fail Fast & Explicit**: Validate inputs at boundary entrypoints (regex, type assertions, schema checks).

## 2. Python Standards
- **Version**: Python 3.10+ compatible.
- **Style**: Follow PEP 8 guidelines. Explicit variable and function naming.
- **Encoding**: All file read/write operations must explicitly declare `encoding="utf-8"`.
- **Defensive Programming**:
  - Guard against `ZeroDivisionError` on empty collections (`total / count if count else 0`).
  - Guard array slicing and indexing with bounds checks before computing statistics or aggregations.
  - Safe HTML escaping for user-supplied or external content via `html.escape()`.
- **Network Requests**:
  - Always specify realistic `User-Agent` headers.
  - Mandatory timeout settings on all HTTP calls (`timeout=30` minimum/recommended).
  - Eliminate untrusted third-party service dependencies (no unofficial scrapers or third-party SVG proxies).

## 3. Security & Validation Standards
- **Username Validation**: Strict regex matching GitHub handle format:
  `^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$`
  Reject command injection characters, directory traversal attempts (`..`, `/`, `\`), and shell delimiters (`;`, `&`, `|`).
- **Dynamic Configuration**:
  - Dynamic user resolution hierarchy: CLI argument -> Environment variable `GH_PROFILE_USER` -> Default `JuniorCorzo`.

## 4. CI/CD & Workflow Hardening
- **Pinned Action SHAs**: All GitHub Actions must be pinned to full immutable 40-character commit SHAs with semantic version comments.
  - `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2`
  - `actions/setup-python@0b93645e9fea7318edeed27965017192518e0b4a # v5.3.0`
  - `stefanzweifel/git-auto-commit-action@e348103e9026cc0eee72ae06630dbe30c8088f38 # v5.1.0`
- **Least Privilege Principle**:
  - Explicit job-level permissions rather than overly permissive top-level permissions.
  - Dedicated jobs requesting only `contents: write` where commits are generated.

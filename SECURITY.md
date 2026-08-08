# Security

## Reporting a vulnerability

Please report security vulnerabilities privately through GitHub's
built-in mechanism rather than a public issue: open this repository's
**Security** tab and use **"Report a vulnerability"** (GitHub Private
Vulnerability Reporting). This sends the report only to the repository
maintainers, not the public issue tracker, and lets us coordinate a fix
before any public disclosure.

If that option is not visible, it means the repository owner has not
yet enabled Private Vulnerability Reporting in this repository's
Security settings — in that case, do not post the details publicly;
wait until it is enabled, or check this file again for an updated
process.

We do not currently offer a bug bounty, and no certifications or
compliance guarantees are claimed for this project.

## Secrets and credentials

- Never commit real credentials. `.env`, `.env.*` (except `*.example`),
  and `.auth/*.json` are gitignored — see `.gitignore`.
- Every config value that could be secret (`database.*.password`,
  `clickhouse.*.password`, `ai.*.api_key`, `api.*.client_secret`, ...) is
  sourced via `${VAR:-default}` substitution in
  `config/environments/*.yaml`, never a literal in a tracked file — see
  FRAMEWORK_MAINTENANCE_GUIDE.md.
- `framework.database.utilities.secrets.CredentialResolver` supports
  Fernet-encrypted passwords (`encrypted_password`, safe to commit as
  ciphertext) as an alternative to plaintext env vars.

## Optional capabilities — specific considerations

- **`framework.discovery`**: UI discovery is passive (look-don't-touch) —
  never submits a form or attempts login/credential guessing. Only run it
  against an application you are authorized to test.
- **`framework.sync`**: repository analysis is read-only static
  text-scanning — it never executes code found in the analyzed
  repository. `ZipArchiveSource` rejects path-traversal/absolute-path
  archive members (zip-slip protected). `RepositoryAnalyzer` excludes
  symlinks when collecting files, so a malicious cloned/extracted
  repository can't cause it to read a file outside the analyzed root.
  `GitRepositorySource` never requests, stores, or logs a credential — it
  relies entirely on the caller's own already-configured git credentials.
  Findings (hardcoded credentials/URLs) report only file + line +
  category, never the matched secret value.
- **`framework.ai`**: disabled by default (`DisabledProvider`, zero
  network calls). `redact_secrets()` strips anything that looks like a
  password/API key/token/cookie/Authorization header from a prompt before
  it reaches an AI provider — see `framework/ai/redaction.py` for the
  exact patterns. AI output is always a labeled recommendation
  (`RecommendationConfidence`), never something the framework acts on
  automatically. A misbehaving or unreachable provider degrades to a
  fallback recommendation (`framework.ai.safe_suggest`) rather than
  crashing or corrupting framework state.

## Reporting a bug vs. a vulnerability

Functional bugs: use the public issue tracker. Security-sensitive
findings (e.g. a redaction bypass, a zip-slip variant not covered by
the current tests, credential leakage) should go through the private
"Report a vulnerability" flow described above instead — do not open a
public issue for those.

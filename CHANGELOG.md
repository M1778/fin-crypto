# Changelog — fin-crypto

## [0.1.1] — 2026-10-20
### Fixed
- REAL bug, caught by first execution (finc 0.4.0): the SHA-256 message
  schedule used wrong tap indices (`s0` over `w[i]`, `s1` over `w[i+7]`,
  middle term `w[i+7]`). Correct per FIPS 180-4: `s0` over `w[i+1]`,
  `s1` over `w[i+14]`, middle term `w[i+9]`. Day-1's vectors were
  code-review-only; they now pass at runtime (FIPS 180-4 + RFC 4231).

## [0.1.0] — 2026-10-19

All notable changes to this library. Format follows [Keep a Changelog](https://keepachangelog.com/),
versioning follows [SemVer](https://semver.org/).

## [0.1.0] — 2026-10-19

### Added
- `sha256_hex` / `sha256_bytes_hex` — pure-Fin SHA-256 (FIPS 180-4), no
  overflow-wrapping assumptions (add32 via 16-bit halves), bitwise ops via
  `bits::std` (Fin grammar has no `& | ^`).
- `hmac_sha256_hex` / `hmac_sha256_bytes_hex` — HMAC-SHA256 (RFC 2104).
- `random_bytes` / `random_hex` — OS CSPRNG via `/dev/urandom` (Linux-only).
- `const_time_eq` / `const_time_eq_bytes` — constant-time comparison.
- Test suite with FIPS 180-4 and RFC 4231 vectors, runnable example, GitHub
  Actions CI, real `finn.toml` manifest format (see `finn/` repo).
- `exports.fin` using finn's real re-export syntax (`export * from "src/crypto";`).

### Notes
- UNVERIFIED: no `finc` binary was available; nothing type-checked or executed yet.
- Manifest uses the real finn format (`finn.toml`, `[project]`/`[packages]`/`[scripts]`),
  not the provisional `fin.toml` — see workspace NOTES.md.
- SHA-512/SHA-1 deferred to 0.2.0.

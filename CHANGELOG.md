# Changelog - fin-crypto

Format follows [Keep a Changelog](https://keepachangelog.com/); versioning
follows [SemVer](https://semver.org/).

## [Unreleased]

### Added
- `tests/vectors.fin`: published-vector proof in one place. FIPS 180-4 empty,
  `abc`, 448-bit, 896-bit and one-million-`a` messages; non-ASCII UTF-8 input;
  every padding boundary from 55 to 129 bytes; all 256 byte values; and RFC 4231
  HMAC cases 1-7, with case 5 asserted at full length rather than truncated.
- `tests/test_native_bits.fin` now pins the runtime behaviour (not constant
  folding) of signed casts, logical shift, XOR/OR/AND and wrapping 32-bit
  addition, including rotate-by-31. If `finc` changes these, the test fails
  before a digest does.
- `tests/test_crypto.fin`: hex and raw outputs cross-checked through
  `encoding::std`'s independent encoder; NUL truncation; non-aliasing of two
  results; every mismatch position; and two random draws required to differ.
- `FINC_VERSION` pins the verified compiler, and CI installs that published
  release with a sha256 check.
- CI now runs Linux (x86-64, ARM64), macOS (x86-64, ARM64) and Windows (x86-64),
  compiling and executing the whole suite at `-O0` and `-O2`. The Windows lane
  is where the `rand_s` branch actually executes.

### Changed
- `tests/run_tests.py` is stricter: it checks every program's success line,
  requires 600 differential cases plus a 1,000,000-byte message per
  optimisation level, requires each invalid input to abort with `SIGABRT` and a
  `blame` diagnostic, and fails if `finc` does not report contract 3.
- The differential and invalid-input programs now report that they need the
  runner when their harness variables are absent, instead of failing. This makes
  `finn test` run all five test files as programs.
- `finn.toml` drops the misleading `entrypoint = "crypto.fin"` (this is a
  library, so there is nothing to build) and the `test` script now runs the real
  runner. `exports.fin` is removed: `export * from` is not Fin syntax and `finc`
  rejects the file, so keeping it advertised a feature that does not exist.
- Every source file carries the project header via `scripts/fin_header.py`,
  which is committed so the rule is reproducible (`--check` is idempotent).

### Fixed
- **Withdrew a false upstream-blocker claim.** The README, `src/crypto.fin` and
  the changelog stated that Fin `1f7afd97` lacks `FIN_TARGET_WINDOWS` and that
  Windows support was therefore blocked by the compiler. That was true of
  `1f7afd97ab5ad520b78db3140d4f930aaeb74d1b` and false of the shipped compiler:
  commit `cc7f1663` ("fix: prepare v1 production candidate") added the target
  predefines, and `finc 1.0.0` reports `FIN_TARGET_WINDOWS`, `FIN_TARGET_DARWIN`,
  `FIN_TARGET_LINUX`, `FIN_TARGET_X86_64` and `FIN_TARGET_ARM64`. The guard
  spelling `#c_ifdef` was already correct. Telling users Windows was blocked was
  worse than saying nothing.
- Recorded the implementation limits as limits: the hash and MAC are
  hand-written rather than backed by OpenSSL/libsodium, and `const_time_eq` has
  no timing proof. Both are now in the README's first paragraph and in the
  source header instead of a footnote.

### Removed
- Stale verification claims: the README's "verified 2026-10-21 with finc 0.4.0"
  block, the broken `fin-sdk` run link, and the microbenchmark table whose
  numbers were machine-local and unrelated to correctness.
- `examples/run_benchmark.py` and `examples/benchmark.fin`. A microbenchmark
  comparing a revision to itself is not evidence of anything a user needs, and
  its numbers were already stale.

## [0.1.1] - 2026-10-20
### Fixed
- SHA-256 message schedule used wrong tap indices (`s0` over `w[i]`, `s1` over
  `w[i+7]`, middle term `w[i+7]`). Correct per FIPS 180-4: `s0` over `w[i+1]`,
  `s1` over `w[i+14]`, middle term `w[i+9]`. Vectors now pass at runtime.

## [0.1.0] - 2026-10-19
### Added
- `sha256_hex` / `sha256_bytes_hex`, pure-Fin SHA-256 (FIPS 180-4).
- `hmac_sha256_hex` / `hmac_sha256_bytes_hex`, HMAC-SHA256 (RFC 2104).
- `random_bytes` / `random_hex`, OS CSPRNG via `/dev/urandom`, later `rand_s`.
- `const_time_eq` / `const_time_eq_bytes`.
- FIPS 180-4 and RFC 4231 vectors, runnable example, GitHub Actions CI.

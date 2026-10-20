# fin-crypto

Cryptographic primitives for [Fin](https://github.com/M1778/Fin): SHA-256, HMAC-SHA256, OS secure random bytes, and full-scan equality helpers.

## Verification status

**Functionally tested 2026-10-21** with finc 0.4.0 (contract 3), on Linux x86-64,
at both `-O0` and `-O2`. SHA/HMAC vectors, 231 independent Python differential
cases per optimization level, and 25 invalid-input subprocess checks pass.
These are correctness checks, **not a cryptographic audit or proof of constant-time
execution**. The current changes are unreleased source, not a published version.
The earlier first execution caught a SHA-256 schedule bug (see CHANGELOG).

## Install

With [finn](https://github.com/M1778/finn) (once the registry resolves bare names):

```sh
finn add M1778/fin-crypto
```

Manual (today):

```sh
git clone https://github.com/M1778/fin-crypto
# then compile with -I fin-crypto/src
finc myapp.fin -I fin-crypto/src -o myapp
```

## Quick example

```fin
import { sha256_hex, hmac_sha256_hex, random_hex, const_time_eq } from crypto::fin;
import { free_str } from strings::std;

fun main() <noret> {
    let digest <string> = sha256_hex("hello fin");
    printf("%s\n", digest);

    let mac <string> = hmac_sha256_hex("s3cr3t", "transfer $100");
    let again <string> = hmac_sha256_hex("s3cr3t", "transfer $100");
    if (const_time_eq(mac, again)) {
        printf("MAC verified\n");
    }

    let token <string> = random_hex(32);   // 64 hex chars, OS CSPRNG
    printf("token=%s\n", token);
    free_str(digest);
    free_str(mac);
    free_str(again);
    free_str(token);
}
```

## API reference

All functions live in `namespace fin` inside module `crypto` — import with
`import { ... } from crypto::fin;` and call them **by name** (module-qualified
calls like `crypto.sha256_hex(...)` are refused by the Fin backend; see
`docs/guide/10-modules-and-imports.md`).

| Function | Description |
|---|---|
| `sha256_hex(data: string) <string>` | SHA-256 of a string as lowercase hex. Hashes bytes up to the first NUL. |
| `sha256_bytes_hex(data: [char], len: int) <string>` | SHA-256 of the first `len` bytes of an array as lowercase hex. |
| `hmac_sha256_hex(key: string, message: string) <string>` | HMAC-SHA256 (RFC 2104) as lowercase hex. |
| `hmac_sha256_bytes_hex(key: [char], key_len: int, message: [char], msg_len: int) <string>` | HMAC-SHA256 over byte arrays. |
| `sha256_bytes(data: [char], len: int) <[char]>` | Raw digest of the first `len` bytes: exactly 32 owned bytes, no sentinel. |
| `hmac_sha256_bytes(key: [char], key_len: int, message: [char], msg_len: int) <[char]>` | Raw HMAC: exactly 32 owned bytes, no sentinel. |
| `random_bytes(count: int) <[char]>` | `count` OS random bytes plus a zero sentinel: array length is **count + 1**, including when count is zero. Caller deletes. |
| `random_hex(count: int) <string>` | `count` random bytes as `2*count` lowercase hex chars. |
| `const_time_eq(a: string, b: string) <bool>` | Full-scan equality, intended for public-length tokens; length mismatch returns `false`. No timing guarantee. |
| `const_time_eq_bytes(a: [char], b: [char], len: int) <bool>` | Full-scan equality of the first `len` bytes. No timing guarantee. |

Ownership: every function returning `string` or `[char]` hands you fresh memory —
free strings with `free_str` (from `strings::std`) and arrays with `delete`.
Inputs remain owned by the caller and are not mutated. All byte lengths must be
nonnegative and no greater than the corresponding array length; invalid input
aborts via `blame`, before cryptographic work. Prefix lengths are supported.
HMAC messages must be at most 2,147,483,583 bytes; random counts at most
2,147,483,646, and random-hex counts at most 1,073,741,823. These are arithmetic
limits, **not recommended allocation budgets**; callers must enforce practical
resource limits. String inputs must be valid NUL-terminated storage (embedded
NULs require a byte API). Auth consumers adopting raw HMAC must account for the
32-byte output instead of a decoded-hex array's 33-byte sentinel convention.

## Dependencies

- **Fin standard library**: `strings::std` (`to_chars`/`from_chars`); native int bitwise expressions and uint shifts/addition implement the compression and comparison paths.
- **Base64/hex**: use `base64_encode`/`hex_encode` from `encoding::std` when needed.
- **libc**: `strlen` for string-size checks; `fopen`/`fread`/`fclose` for `/dev/urandom` (Linux-only).
- No Fin package dependencies (`finn.toml` `[packages]` is empty).

## Security and implementation limits

- Pure-Fin SHA/HMAC are **unaudited**. Native 32-bit casts, logical shifts and
  modular addition are tested on the pinned finc 0.4.0 toolchain at O0/O2;
  revalidate when changing compiler or target. SHA keeps a per-call schedule
  and 128-byte tail instead of copying/allocating the padded message or blocks.
  HMAC still allocates a message-sized inner buffer.
- Equality accumulates native XOR/OR over all requested bytes. It removes the
  old arithmetic bit helpers' data-dependent branches, but source-level scans
  and output vectors do not prove timing properties. Optimizers, targets,
  string-length scans and allocation behavior matter; lengths are public.
- No guaranteed secret zeroization is provided. `delete`/`free_str` release
  memory without a guaranteed secure erase. Untrusted array handles/pointers
  cannot be validated beyond their declared length; Fin has no borrow checker.
- `random_bytes` uses only `/dev/urandom`, preserves its trailing zero sentinel,
  and aborts on open failure or short read. It has no weak fallback, recoverable
  errors, cross-platform backend, or early-boot entropy-readiness guarantee.
  Shape tests do not establish entropy quality.
- SHA-256 alone is **not** suitable for password storage; use an appropriate,
  reviewed password KDF. Validate untrusted lengths before calling these APIs:
  `blame` aborts the process and cannot be caught.

## Testing

```sh
python3 -I tests/run_tests.py
```

Both runners accept `--finc` / `--fin-libs`, then respect `FINC` / `FIN_LIBS`.
Otherwise they autodetect `../.toolchain/bin/finc` / `../.toolchain/lib/std` when
available, falling back to `finc` on PATH and its bundled standard library.
The test runner builds/runs at O0 and O2 in temporary
folders, disables core dumps, and requires explicit assertion aborts rather than
segmentation faults for invalid inputs. Coverage includes FIPS empty/abc/448-bit
and million-'a' SHA vectors, RFC 4231 cases 1/2/3/4/6/7, raw/hex agreement against
Python `hashlib`/`hmac`, padding boundaries, binary inputs, keys crossing 64 bytes,
input preservation, all-byte/mismatch-position equality, and random sentinels.

Existing simple command remains supported:

```sh
finc tests/test_crypto.fin -I src -o test_crypto && ./test_crypto
```

## Local microbenchmark

```sh
python3 -I examples/run_benchmark.py --baseline dc286330c8c9dd7393d9a92ae197e62eb6864b22 --runs 5
```

The runner compiles the **same** `examples/benchmark.fin` against baseline and
working source, consuming a checksum of hex outputs and freeing results.
Workload per process: SHA-256 **16 × 65,536 bytes** (repeating bytes 0..255), plus
HMAC-SHA256 **1,000 × 32 bytes** with the 13-byte key `benchmark-key`.
On this Linux x86-64 machine, finc 0.4.0 (contract 3), pinned `.toolchain/lib/std`,
`-O0`/`-O2`, five wall-clock runs including startup, median seconds were:

| Flags | Baseline | Working source | Local ratio |
|---|---:|---:|---:|
| `-O0` | 4.347984 | 0.069019 | 63.00× |
| `-O2` | 0.369865 | 0.005221 | 70.85× |

These are machine-local microbenchmark measurements, not general throughput
claims or security evidence. The runner prints every sample, compiler version,
flags, revision and checksum for reproduction.

## Roadmap

- `v0.2.0`: SHA-512 (via `uint`-pair 64-bit words), SHA-1 (needed by
  `fin-websocket`'s RFC 6455 handshake), `/dev/urandom` fallback for
  macOS (`getentropy`) and Windows (`BCryptGenRandom`).
- License review: Fin itself is GPL-3.0 and `finn` is GPL-3.0-only; this repo
  ships MIT pending Eleanor's decision on ecosystem licensing.

## License

MIT — see [LICENSE](LICENSE).

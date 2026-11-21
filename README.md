# fin-crypto

SHA-256, HMAC-SHA256, OS-backed random bytes and byte comparison for the
[Fin programming language](https://github.com/M1778/Fin).

> **Read this first.** SHA-256 and HMAC-SHA256 here are *hand-written in Fin*.
> They are not wrappers around OpenSSL or libsodium, and they have not been
> audited. They match the published NIST and RFC vectors exactly, which proves
> they compute the right function for the inputs tested; it does not prove they
> are safe against a local attacker who can time them. Randomness *is* delegated
> to the operating system. There is no encryption, signing, key exchange or
> password hashing in this library, and it should not be used as a password
> store.

Broken values are reported, never returned: every rejected input aborts with a
diagnostic through `blame` instead of producing a wrong digest or weak bytes.

## Status

Verified with `finc 1.0.0 (contract 3)`. The compiler version is pinned in
[`FINC_VERSION`](FINC_VERSION); CI installs exactly that published release,
verifies its SHA-256 and refuses anything that does not report contract 3.

CI compiles **and executes** the full suite on Linux (x86-64, ARM64), macOS
(x86-64, ARM64) and Windows (x86-64) at `-O0` and `-O2`. Windows runs the real
`rand_s` branch, selected by `#c_ifdef FIN_TARGET_WINDOWS`.

This project was previously documented as blocked on Windows by a missing
compiler macro. An earlier compiler revision (Fin `1f7afd97`) did lack it; the
current compiler (`cc7f166` and later, including the 1.0.0 release) predefines
`FIN_TARGET_WINDOWS`, `FIN_TARGET_DARWIN`, `FIN_TARGET_LINUX`,
`FIN_TARGET_X86_64` and `FIN_TARGET_ARM64`. The claim was measured against the
stale revision and has been withdrawn.

## What this does not do

- **No constant-time guarantee.** `const_time_eq` and `const_time_eq_bytes` scan
  every byte and contain no early exit, but that is a property of the source.
  No timing measurement has been made, on any CPU, under any optimizer. A
  compiler is free to transform the loop; the tests would not notice. Treat the
  comparison as "not obviously timing-vulnerable", not as verified constant time.
- **No secure zeroization.** `delete` and `free_str` release memory. They do not
  scrub it, so key material may survive in freed heap memory.
- **No encryption, signatures, key exchange, or KDF.** SHA-256 alone is not a
  password hash; use a reviewed password KDF outside this library.
- **No length hiding.** Array lengths are public to this API. If the length of a
  secret is sensitive, that is the caller's problem to solve.
- **No entropy-quality test.** The random tests check length and sentinel bytes.
  They cannot and do not measure the quality of the OS entropy source.
- **No audit.** Nobody qualified has reviewed this code for correctness or side
  channels, and no formal verification exists.

## Install

Manual, today:

```sh
git clone https://github.com/M1778/fin-crypto
finc myapp.fin -I fin-crypto/src -o myapp
```

With the [`finn`](https://github.com/M1778/finn) package manager:

```sh
finn add M1778/fin-crypto
```

`finn add` installs the package, but Fin's import resolution does not yet map an
installed package to a module name, so a consumer must also pass
`-I .finn/packages/fin-crypto/src` to reach `import ... from crypto::fin`. The
repository has a `finn.toml` that `finn healthcheck` and `finn test` accept; it
is a library, so there is no entrypoint and `finn build` is not applicable.

## Use

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

## API

All names live in `namespace fin` in module `crypto`. Import them by name;
module-qualified calls such as `crypto.sha256_hex(...)` are refused by the
backend.

| Function | Result |
|---|---|
| `sha256_hex(data: string) <string>` | Lowercase hex SHA-256. Hashes up to the first NUL byte. |
| `sha256_bytes_hex(data: [char], len: int) <string>` | Lowercase hex SHA-256 of the first `len` bytes. |
| `hmac_sha256_hex(key: string, message: string) <string>` | Lowercase hex HMAC-SHA256. |
| `hmac_sha256_bytes_hex(key: [char], key_len: int, message: [char], msg_len: int) <string>` | HMAC-SHA256 over byte arrays. |
| `sha256_bytes(data: [char], len: int) <[char]>` | Raw digest: exactly 32 owned bytes, no sentinel. |
| `hmac_sha256_bytes(key: [char], key_len: int, message: [char], msg_len: int) <[char]>` | Raw MAC: exactly 32 owned bytes, no sentinel. |
| `random_bytes(count: int) <[char]>` | `count` OS random bytes plus a zero sentinel, so the array length is `count + 1` (including `count == 0`). |
| `random_hex(count: int) <string>` | `count` random bytes as `2*count` lowercase hex characters. |
| `const_time_eq(a: string, b: string) <bool>` | Full-scan comparison; length mismatch is `false`. No timing guarantee. |
| `const_time_eq_bytes(a: [char], b: [char], len: int) <bool>` | Full-scan comparison of the first `len` bytes. No timing guarantee. |

**Ownership.** Every `string` or `[char]` result is fresh memory: free strings
with `free_str` (from `strings::std`) and arrays with `delete`, exactly once.
Inputs stay owned by the caller and are not modified.

**Lengths.** Every byte length must be `>= 0` and `<=` the array's length;
anything else aborts before cryptographic work. HMAC messages are limited to
2,147,483,583 bytes, `random_bytes` to 2,147,483,646 and `random_hex` to
1,073,741,823. These are arithmetic limits that keep internal size sums inside
`int`, **not** allocation budgets - enforce your own practical limits first.

**Strings are NUL-terminated.** `sha256_hex` and `hmac_sha256_hex` hash bytes up
to the first NUL. A string that embeds `\0` hashes only its prefix; use the byte
API when that matters.

## Platform support

| Platform | SHA/HMAC | Randomness | Verified |
|---|---|---|---|
| Linux | yes | `/dev/urandom` | CI executes |
| macOS | yes | `/dev/urandom` | CI executes |
| Windows | yes | UCRT `rand_s` | CI executes |

The hash and MAC are portable: they use only integer arithmetic, casts and
shifts, and `tests/test_native_bits.fin` pins the 32-bit semantics they rely on
at run time, so a compiler change breaks that test before it breaks a digest.
Randomness is the only platform split and it is selected by `#c_ifdef
FIN_TARGET_WINDOWS`.

`rand_s` is documented by Microsoft to draw from the OS cryptographic
randomness provider. A failure aborts; there is no `rand()` fallback and no
recoverable error API. On Linux and macOS, a failure to open `/dev/urandom` or a
short read also aborts. There is no early-boot entropy-readiness check: this
library does not verify that the OS pool is initialized.

## Testing

```sh
python3 -I tests/run_tests.py --finc /path/to/finc
```

The runner builds every test at `-O0` and `-O2`, executes each one, and checks
the following:

- `tests/vectors.fin` - exact hex against published vectors: FIPS 180-4
  (empty, `abc`, the 448-bit and 896-bit messages, one million `a`), non-ASCII
  UTF-8 input, the padding boundaries at 55/56/57, 63/64/65 and
  119/120/127/128/129 bytes, all 256 byte values, and RFC 4231 HMAC cases 1-7
  (case 5 asserted at full length, not truncated).
  A deliberately corrupted round constant makes this file fail, which is how the
  assertions are known to be load-bearing.
- `tests/test_crypto.fin` - API contract: sentinels, raw 32-byte outputs, hex and
  raw agreement through `encoding::std`, non-aliasing, NUL truncation, every
  mismatch position, and random shapes.
- `tests/test_differential.fin` - Python `hashlib`/`hmac` agreement over 600
  length and key combinations plus a 1,000,000-byte message.
- `tests/test_invalid.fin` - 25 rejected inputs, each in its own process,
  required to abort with a `blame` diagnostic. Removing the length guard makes
  this file report heap corruption instead, so the guard is proven necessary.
- `tests/test_native_bits.fin` - the cast, shift, XOR/OR/AND and wrapping-add
  behaviour the hash depends on.

The same files run under `finn test`; the harness-driven ones report that they
need the runner instead of crashing.

## Dependencies

- Fin standard library: `strings::std` (`to_chars`, `from_chars`).
- libc/UCRT: `strlen`, and `fopen`/`fread`/`fclose` on Linux and macOS, or
  `rand_s` on Windows. No external crypto library, no Fin package dependencies.

## License

MIT - see [LICENSE](LICENSE).

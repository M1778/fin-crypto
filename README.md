# fin-crypto

Cryptographic primitives for [Fin](https://github.com/M1778/Fin): SHA-256, HMAC-SHA256, OS-seeded secure random bytes, and constant-time comparison.

## Verification status

> **UNVERIFIED.** This library is written against `docs/agent-guide.md` (Fin v0.4.0)
> but no `finc` binary was available when it was written, so it has not been
> type-checked or executed yet. Do not use for real secrets until the test suite
> below passes on a real toolchain. See [test vectors](#testing).

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
| `random_bytes(count: int) <[char]>` | `count` bytes from the OS CSPRNG (`/dev/urandom`). Caller deletes. |
| `random_hex(count: int) <string>` | `count` random bytes as `2*count` lowercase hex chars. |
| `const_time_eq(a: string, b: string) <bool>` | Constant-time string equality (no early exit). Length mismatch returns `false`. |
| `const_time_eq_bytes(a: [char], b: [char], len: int) <bool>` | Constant-time equality of `len` bytes. |

Ownership: every function returning `string` or `[char]` hands you fresh memory —
free strings with `free_str` (from `strings::std`) and arrays with `delete`.

## Dependencies

- **Fin standard library only**: `bits::std` (`bit_and`/`bit_or`/`bit_xor`/`bit_not`/`rotate_right` — the Fin grammar has no `& | ^` operators), `strings::std` (`to_chars`/`from_chars`).
- **Base64/hex**: not duplicated here — use `base64_encode`/`hex_encode` from `encoding::std`.
- **libc** (`fopen`/`fread`/`fclose` via `@define`): only for the `/dev/urandom` random source. Linux-only in v0.1.0.
- No Fin package dependencies (`finn.toml` `[packages]` is empty).

## Design notes

- SHA-256 is pure Fin. Its 32-bit additions are implemented as `add32` via
  16-bit halves so **no overflow-wrapping assumption** is needed (Fin's `uint`
  wrapping behavior is unconfirmed).
- `random_bytes` **aborts** (`blame`) if `/dev/urandom` cannot be opened or
  short-reads — Fin has no recoverable-error story for this yet.
- `const_time_eq` compares every byte even after a mismatch; only the length
  check short-circuits (length is not treated as secret).

## Testing

```sh
finc tests/test_crypto.fin -I src -o test_crypto && ./test_crypto
```

Vectors (all verified against Python `hashlib`/`hmac` while writing the tests):

- SHA-256: FIPS 180-4 `""`, `"abc"`, and the 448-bit `"abcdbcde...nopq"` vector.
- HMAC-SHA256: RFC 4231 test case 2 (`key="Jefe"`).
- `const_time_eq`: equal / differing / different-length / empty inputs.
- `random_bytes`/`random_hex`: output shape (values are nondeterministic).

## Roadmap

- `v0.2.0`: SHA-512 (via `uint`-pair 64-bit words), SHA-1 (needed by
  `fin-websocket`'s RFC 6455 handshake), `/dev/urandom` fallback for
  macOS (`getentropy`) and Windows (`BCryptGenRandom`).
- License review: Fin itself is GPL-3.0 and `finn` is GPL-3.0-only; this repo
  ships MIT pending Eleanor's decision on ecosystem licensing.

## License

MIT — see [LICENSE](LICENSE).

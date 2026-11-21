#!/usr/bin/env python3
# =============================================================================
# Fin Programming Language
#
# Made with ❤️ for someone special.
#
# This project is genuinely built on love and dedication, a way to express your love can be done through Fin.
# Fin is a semi-object-orientated programming language that specialized in control, giving so much control to the user while asking for the bare minimum.
# Fin is the name of the Angel from BlackNightmare-Stories not yet published.
# “Love is the reason this project exists”
# -----------------------------------------------------------------------------
# Author: M1778
# Repository: https://github.com/M1778/fin-crypto
# Profile: https://github.com/M1778M/
# -----------------------------------------------------------------------------
# Copyright (C) 2027 M1778
#
# This file is part of fin-crypto, a project for the Fin Programming Language.
#
# Licensed under the MIT License. See LICENSE in the repository root.
#
# SPDX-License-Identifier: MIT
# =============================================================================

"""Build and execute every fin-crypto test at -O0 and -O2.

What this proves, and what it does not:

  * vectors.fin      exact hex against FIPS 180-4 / RFC 4231 / Python hashlib.
  * test_crypto.fin  API contract, ownership, comparison behaviour.
  * test_differential.fin  Python hashlib/hmac agreement over many lengths.
  * test_invalid.fin every rejected input aborts with a diagnostic.
  * test_native_bits.fin  the 32-bit arithmetic SHA-256 relies on.

These are correctness checks. They are not a cryptographic audit, not a
side-channel measurement, and not proof of constant-time execution.

Exit status is nonzero if any binary fails to build, exits nonzero, or prints
something other than its expected success line.
"""
import argparse
import hashlib
import hmac
import os
from pathlib import Path
try:
    import resource
except ImportError:  # Unavailable on native Windows.
    resource = None
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "tests"
SRC = ROOT / "src"

# Files built and run once per optimisation level.
PROGRAMS = ("test_crypto", "vectors", "test_native_bits", "test_differential", "test_invalid")
EXPECTED = {
    "test_crypto": "all fin-crypto tests passed",
    "vectors": "vectors: FIPS 180-4, RFC 4231, padding and key-boundary cases passed",
    "test_native_bits": "native bit patterns and uint wrapping passed",
    "test_differential": "needs CRYPTO_LEN",
    "test_invalid": "needs CRYPTO_INVALID",
}

# Lengths chosen around every block and padding boundary, including 0.
LENGTHS = [0, 1, 2, 3, 7, 31, 32, 55, 56, 57, 63, 64, 65, 66,
           119, 120, 121, 127, 128, 129, 255, 256, 257, 1024, 4096]
KEY_LENGTHS = [0, 1, 20, 32, 55, 56, 63, 64, 65, 127, 128, 131]
INVALID_CASES = 25


def pattern(length):
    return bytes((i * 37 + i // 7) % 256 for i in range(length))


def key_pattern(length):
    return bytes((i * 19 + 128) % 256 for i in range(length))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    suffix = ".exe" if os.name == "nt" else ""
    parser.add_argument("--finc", default=os.environ.get("FINC") or "finc")
    parser.add_argument("--fin-libs", default=os.environ.get("FIN_LIBS") or None)
    args = parser.parse_args()
    libs_flags = ["--fin-libs", args.fin_libs] if args.fin_libs else []

    version = subprocess.check_output([args.finc, "--version"], text=True).strip()
    if "contract 3" not in version:
        sys.exit(f"finc must speak contract 3, got: {version}")
    print(f"compiler: {version}", flush=True)

    # Expected aborts must not leave POSIX core dumps behind.
    if resource is not None:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    with tempfile.TemporaryDirectory(prefix="crypto-tests-") as folder:
        for opt in ("O0", "O2"):
            binaries = {}
            for name in PROGRAMS:
                binary = Path(folder) / f"{name}_{opt}{suffix}"
                subprocess.run([args.finc, str(TEST_DIR / f"{name}.fin"),
                                "-I", str(SRC), *libs_flags,
                                f"-{opt}", "-o", str(binary)],
                               check=True, timeout=180)
                binaries[name] = binary

            # Every program runs once with no harness variables set. They must
            # exit 0 and say either their success line or that they need the
            # runner; a crash or a stray diagnostic is a failure.
            for name in PROGRAMS:
                run = subprocess.run([binaries[name]], capture_output=True,
                                     text=True, timeout=60)
                if run.returncode != 0:
                    sys.exit(f"{opt} {name}: exited {run.returncode}\n{run.stdout}{run.stderr}")
                if EXPECTED[name] not in run.stdout:
                    sys.exit(f"{opt} {name}: missing expected line\n{run.stdout}{run.stderr}")

            cases = 0
            for n in LENGTHS:
                for kn in KEY_LENGTHS:
                    for mode in (0, 1):
                        data = b"a" * n if mode else pattern(n)
                        key = key_pattern(kn)
                        want = [hashlib.sha256(data).hexdigest(),
                                hmac.new(key, data, hashlib.sha256).hexdigest()]
                        run = subprocess.run(
                            [binaries["test_differential"]], check=True,
                            capture_output=True, text=True, timeout=60,
                            env={**os.environ, "CRYPTO_LEN": str(n),
                                 "CRYPTO_KEY_LEN": str(kn), "CRYPTO_MODE": str(mode)})
                        got = run.stdout.splitlines()
                        if got != [*want, *want]:
                            sys.exit(f"{opt} differential n={n} key={kn} mode={mode}\n"
                                     f"  got  {got}\n  want {[*want, *want]}")
                        cases += 1

            # A single 1,000,000-byte message (FIPS long-message vector).
            data = b"a" * 1_000_000
            want = [hashlib.sha256(data).hexdigest(),
                    hmac.new(key_pattern(131), data, hashlib.sha256).hexdigest()]
            run = subprocess.run(
                [binaries["test_differential"]], check=True, capture_output=True,
                text=True, timeout=120,
                env={**os.environ, "CRYPTO_LEN": "1000000", "CRYPTO_KEY_LEN": "131",
                     "CRYPTO_MODE": "1"})
            if run.stdout.splitlines() != [*want, *want]:
                sys.exit(f"{opt} million-byte differential mismatch\n{run.stdout}")

            # Every invalid input must abort with a diagnostic, never return.
            clean_env = {k: v for k, v in os.environ.items() if k != "CRYPTO_ABSENT_NULL_TEST"}
            for case in range(INVALID_CASES):
                run = subprocess.run([binaries["test_invalid"]], capture_output=True,
                                     text=True, timeout=10,
                                     env={**clean_env, "CRYPTO_INVALID": str(case)})
                output = run.stdout + run.stderr
                if run.returncode == 0:
                    sys.exit(f"{opt} invalid case {case}: returned instead of aborting")
                if os.name != "nt" and run.returncode != -signal.SIGABRT:
                    sys.exit(f"{opt} invalid case {case}: expected SIGABRT, got {run.returncode}\n{output}")
                if "assertion failed:" not in output:
                    sys.exit(f"{opt} invalid case {case}: no blame diagnostic\n{output}")
                if "outside" not in output and "null string" not in output:
                    sys.exit(f"{opt} invalid case {case}: unexpected diagnostic\n{output}")
                if "ERROR: invalid input returned" in output:
                    sys.exit(f"{opt} invalid case {case}: rejection path fell through")

            print(f"{opt}: vectors, API contract, {cases} differential cases, "
                  f"1 long message, {INVALID_CASES} rejections passed", flush=True)

    print("all fin-crypto tests passed at -O0 and -O2")

    # The Windows RNG branch cannot be executed on a Linux or macOS runner, but
    # it must at least compile and select rand_s. This catches a rotted branch
    # before the Windows lane does.
    branch_check = [sys.executable, "-I", str(TEST_DIR / "check_platform_branch.py"),
                    "--finc", args.finc]
    if args.fin_libs:
        branch_check += ["--fin-libs", args.fin_libs]
    subprocess.run(branch_check, check=True, timeout=120)


if __name__ == "__main__":
    main()

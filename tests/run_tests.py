#!/usr/bin/env python3
"""Build and run crypto correctness, differential and rejection tests at O0/O2."""
import argparse
import hashlib
import hmac
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOOLCHAIN = ROOT.parent / ".toolchain"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    local_finc = DEFAULT_TOOLCHAIN / "bin/finc"
    local_libs = DEFAULT_TOOLCHAIN / "lib/std"
    parser.add_argument("--finc", default=os.environ.get("FINC") or
                        (str(local_finc) if local_finc.is_file() else "finc"))
    parser.add_argument("--fin-libs", default=os.environ.get("FIN_LIBS") if "FIN_LIBS" in os.environ else
                        (str(local_libs) if local_libs.is_dir() else None))
    args = parser.parse_args()
    libs_flags = ["--fin-libs", args.fin_libs] if args.fin_libs is not None else []
    # Expected blame aborts must not leave core dumps behind.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with tempfile.TemporaryDirectory(prefix="crypto-tests-") as folder:
        for opt in ("O0", "O2"):
            binaries = {}
            for name in ("test_crypto", "test_native_bits", "test_differential", "test_invalid"):
                binary = Path(folder) / f"{name}_{opt}"
                subprocess.run([args.finc, str(ROOT / "tests" / f"{name}.fin"),
                                "-I", str(ROOT / "src"), *libs_flags,
                                f"-{opt}", "-o", str(binary)], check=True, timeout=120)
                binaries[name] = binary
            subprocess.run([binaries["test_crypto"]], check=True, timeout=30)
            subprocess.run([binaries["test_native_bits"]], check=True, timeout=30,
                           env={**os.environ, "CRYPTO_HIGH": "-2147483648"})
            lengths = [0, 1, 2, 3, 7, 31, 32, 55, 56, 57, 63, 64, 65,
                       119, 120, 127, 128, 129, 255, 256, 257, 1024, 4096]
            key_lengths = [0, 1, 20, 32, 63, 64, 65, 127, 128, 131]
            cases = [(n, kn, 0) for n in lengths for kn in key_lengths]
            cases += [(1_000_000, 131, 1)]  # FIPS million-'a' SHA vector.
            for n, kn, mode in cases:
                data = b"a" * n if mode else bytes((i * 37 + i // 7) % 256 for i in range(n))
                key = bytes((i * 19 + 128) % 256 for i in range(kn))
                sh = hashlib.sha256(data).hexdigest()
                hm = hmac.new(key, data, hashlib.sha256).hexdigest()
                run = subprocess.run([binaries["test_differential"]], check=True,
                                     capture_output=True, text=True, timeout=30,
                                     env={**os.environ, "CRYPTO_LEN": str(n),
                                          "CRYPTO_KEY_LEN": str(kn), "CRYPTO_MODE": str(mode)})
                assert run.stdout.splitlines() == [sh, hm, sh, hm], (opt, n, kn, run.stdout)
            invalid_env = {key: value for key, value in os.environ.items()
                           if key != "CRYPTO_ABSENT_NULL_TEST"}
            for case in range(25):
                run = subprocess.run([binaries["test_invalid"]], capture_output=True,
                                     text=True, timeout=5,
                                     env={**invalid_env, "CRYPTO_INVALID": str(case)})
                output = run.stdout + run.stderr
                assert run.returncode == -signal.SIGABRT, (opt, case, run.returncode, output)
                assert ("outside" in output or "null string" in output), (opt, case, output)
                assert "ERROR: invalid input returned" not in output
            print(f"{opt}: vectors/native semantics, {len(cases)} differential cases, "
                  "25 explicit blame rejections passed", flush=True)


if __name__ == "__main__":
    main()

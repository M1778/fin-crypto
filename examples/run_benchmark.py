#!/usr/bin/env python3
"""Machine-local microbenchmark; compare current source against a git revision."""
import argparse
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = ROOT.parent / ".toolchain"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    local_finc = TOOLCHAIN / "bin/finc"
    local_libs = TOOLCHAIN / "lib/std"
    parser.add_argument("--finc", default=os.environ.get("FINC") or
                        (str(local_finc) if local_finc.is_file() else "finc"))
    parser.add_argument("--fin-libs", default=os.environ.get("FIN_LIBS") if "FIN_LIBS" in os.environ else
                        (str(local_libs) if local_libs.is_dir() else None))
    parser.add_argument("--baseline", default="HEAD", help="git revision holding pre-change crypto")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    libs_flags = ["--fin-libs", args.fin_libs] if args.fin_libs is not None else []
    if args.runs < 1:
        parser.error("--runs must be positive")
    print(subprocess.check_output([args.finc, "--version"], text=True).strip())
    print("Machine-local end-to-end microbenchmark (includes process startup).")
    print("Same source workload: SHA256 16 x 65536 bytes; HMAC 1000 x 32 bytes, "
          "13-byte key; hex outputs consumed and freed.")
    print(f"Flags: -O0/-O2 {libs_flags}; repeats: {args.runs}")
    baseline = subprocess.check_output(["git", "-C", str(ROOT), "show",
                                        f"{args.baseline}:src/crypto.fin"], text=True)
    revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", args.baseline], text=True).strip()
    print(f"Baseline revision: {revision}")
    with tempfile.TemporaryDirectory(prefix="crypto-benchmark-") as directory:
        folder = Path(directory)
        old = folder / "before"
        old.mkdir()
        (old / "crypto.fin").write_text(baseline)
        expected_output = None
        for opt in ("O0", "O2"):
            results = {}
            for label, source in (("before", old), ("after", ROOT / "src")):
                binary = folder / f"{label}_{opt}"
                subprocess.run([args.finc, str(ROOT / "examples/benchmark.fin"), "-I", str(source),
                                *libs_flags, f"-{opt}", "-o", str(binary)],
                               check=True, timeout=120)
                times = []
                for _ in range(args.runs):
                    start = time.perf_counter()
                    output = subprocess.check_output([binary], text=True, timeout=120)
                    times.append(time.perf_counter() - start)
                    if expected_output is None:
                        expected_output = output
                        print(output.strip())
                    assert output == expected_output, (label, opt, output)
                results[label] = statistics.median(times)
                print(f"{opt} {label}: samples {[round(t, 6) for t in times]} "
                      f"median {results[label]:.6f}s", flush=True)
            print(f"{opt} local ratio: {results['before'] / results['after']:.2f}x", flush=True)


if __name__ == "__main__":
    main()

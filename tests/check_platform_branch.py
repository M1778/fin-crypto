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

"""Prove the Windows randomness branch is compiled, without Windows hardware.

`random_bytes` selects its source with `#c_ifdef FIN_TARGET_WINDOWS`. CI on the
windows-x86_64 lane executes that branch for real, but a pull request cannot run
Windows locally, and a branch that no local build ever sees can rot silently
until the Windows lane goes red.

So this test forces the preprocessor down the Windows path by rewriting only the
guard's condition in a temporary copy of the source (the guard body itself is
untouched), compiles to an object file for the host, and inspects the emitted
symbols:

  * the Windows branch must reference `rand_s`;
  * it must not reference `fopen`/`fread`/`fclose` (the /dev/urandom path);
  * the unmodified source must do the opposite.

This is a compile-and-link-inspection check, not execution: it proves the right
code is selected and lowers, not that UCRT rand_s produces good random bytes on
a real Windows machine. The CI Windows lane is what executes it.

Usage: python3 -I tests/check_platform_branch.py --finc <finc> [--fin-libs DIR]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "crypto.fin"
PROBE = """import { random_bytes } from crypto::fin;
fun main() <noret> {
    let b <[char]> = random_bytes(9);
    printf("%d\\n", b.length);
    delete b;
}
"""


def symbols(object_file, tool):
    out = subprocess.run([tool, object_file], capture_output=True, text=True, check=True)
    return out.stdout


def build(finc, source_dir, work, libs_flags):
    probe = work / "probe.fin"
    probe.write_text(PROBE)
    obj = work / "probe.o"
    subprocess.run([finc, "-c", str(probe), "-I", str(source_dir), *libs_flags,
                    "-o", str(obj)], check=True, capture_output=True, text=True)
    return symbols(str(obj), shutil.which("nm") or "nm")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--finc", required=True)
    ap.add_argument("--fin-libs", default=os.environ.get("FIN_LIBS") or None)
    args = ap.parse_args()
    libs_flags = ["--fin-libs", args.fin_libs] if args.fin_libs else []

    if shutil.which("nm") is None:
        sys.exit("check_platform_branch: nm is required to inspect symbols")

    text = SRC.read_text(encoding="utf-8")
    if "#c_ifdef FIN_TARGET_WINDOWS" not in text:
        sys.exit("check_platform_branch: no FIN_TARGET_WINDOWS guard in src/crypto.fin")

    with tempfile.TemporaryDirectory(prefix="crypto-platform-") as tmp:
        work = Path(tmp)
        native_dir = work / "native"
        windows_dir = work / "windows"
        native_dir.mkdir()
        windows_dir.mkdir()
        shutil.copy(SRC, native_dir / "crypto.fin")
        # Only the guard condition changes; the Windows branch body is verbatim.
        windows = text.replace("#c_ifdef FIN_TARGET_WINDOWS",
                               "#c_ifdef FIN_TARGET_X86_64")
        (windows_dir / "crypto.fin").write_text(windows, encoding="utf-8")

        host = build(args.finc, native_dir, work, libs_flags)
        forced = build(args.finc, windows_dir, work, libs_flags)

    def has(syms, name):
        return re.search(rf"\b{name}\b", syms) is not None

    failures = []
    if not has(forced, "rand_s"):
        failures.append("forced Window branch does not reference rand_s")
    for libc_name in ("fopen", "fread", "fclose"):
        if has(forced, libc_name):
            failures.append(f"forced Windows branch still references {libc_name}")
    if has(host, "rand_s"):
        failures.append("host build references rand_s; the guard did not select the POSIX path")
    if not has(host, "fopen"):
        failures.append("host build does not reference fopen; the /dev/urandom path is missing")

    if failures:
        sys.exit("check_platform_branch failed:\n  " + "\n  ".join(failures))
    print("platform branch: Windows selects rand_s, host selects /dev/urandom, both lower")


if __name__ == "__main__":
    main()

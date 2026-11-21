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

# No single target macro is defined on every host: FIN_TARGET_LINUX on Linux,
# FIN_TARGET_DARWIN on macOS, FIN_TARGET_WINDOWS on Windows. Substituting a
# name that the current host does not define silently selects the POSIX branch,
# which is how an ARM64 runner reported a working guard as broken. The host
# macro is therefore discovered by asking the preprocessor, not assumed.
CANDIDATE_MACROS = ("FIN_TARGET_WINDOWS", "FIN_TARGET_LINUX",
                    "FIN_TARGET_DARWIN", "FIN_TARGET_X86_64", "FIN_TARGET_ARM64")


def defined_macro(finc, work, libs_flags):
    """Return one target macro the host compiler defines, or None."""
    for macro in CANDIDATE_MACROS:
        probe = work / f"probe_{macro}.fin"
        probe.write_text(
            "fun main() <noret> {\n"
            f"#c_ifdef {macro}\n"
            "    printf(\"defined\\n\");\n"
            "#c_else\n"
            "    printf(\"absent\\n\");\n"
            "#c_endif\n"
            "}\n")
        binary = work / f"probe_{macro}"
        subprocess.run([finc, str(probe), *libs_flags, "-o", str(binary)],
                       check=True, capture_output=True, text=True)
        out = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
        if out.stdout.strip() == "defined":
            return macro
    return None


def force_guard(text, host_macro):
    """Rewrite only the guard condition; the Windows branch body is verbatim."""
    return text.replace("#c_ifdef FIN_TARGET_WINDOWS", f"#c_ifdef {host_macro}")


def symbol_dump(object_file):
    """Symbols from the first available tool.

    `nm` exists on Linux and macOS. A Windows runner with the MSVC/x64 toolset
    has `llvm-nm` instead, and `dumpbin /symbols` as a last resort. A toolchain
    with none of the three cannot answer the question, and that is reported as
    skipped rather than as a pass.
    """
    if shutil.which("llvm-nm"):
        return subprocess.run(["llvm-nm", object_file], capture_output=True,
                              text=True, check=True).stdout
    if shutil.which("nm"):
        return subprocess.run(["nm", object_file], capture_output=True,
                              text=True, check=True).stdout
    dumpbin = shutil.which("dumpbin")
    if dumpbin:
        return subprocess.run([dumpbin, "/symbols", object_file], capture_output=True,
                              text=True, check=True).stdout
    return None


def build(finc, source_dir, work, libs_flags):
    probe = work / "probe.fin"
    probe.write_text(PROBE)
    obj = work / "probe.o"
    subprocess.run([finc, "-c", str(probe), "-I", str(source_dir), *libs_flags,
                    "-o", str(obj)], check=True, capture_output=True, text=True)
    return symbol_dump(str(obj))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--finc", required=True)
    ap.add_argument("--fin-libs", default=os.environ.get("FIN_LIBS") or None)
    args = ap.parse_args()
    libs_flags = ["--fin-libs", args.fin_libs] if args.fin_libs else []

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

        host_macro = defined_macro(args.finc, work, libs_flags)
        if host_macro is None:
            print("platform branch: skipped, the compiler predefines no target macro "
                  "this check can use")
            return
        (windows_dir / "crypto.fin").write_text(force_guard(text, host_macro),
                                                encoding="utf-8")

        host = build(args.finc, native_dir, work, libs_flags)
        forced = build(args.finc, windows_dir, work, libs_flags)

    if host is None or forced is None:
        print("platform branch: skipped, no symbol tool (llvm-nm, nm or dumpbin) on this runner")
        return

    def has(syms, name):
        # Mach-O prefixes external symbols with an underscore (_rand_s), ELF and
        # COFF do not, so the boundary must permit one. A bare word-boundary
        # pattern reported every macOS symbol as missing.
        return re.search(rf"(?<![A-Za-z0-9_])_?{name}(?![A-Za-z0-9_])", syms) is not None

    failures = []
    # The forced copy must always take the Windows path, on every runner.
    if not has(forced, "rand_s"):
        failures.append("forced Window branch does not reference rand_s")
    for libc_name in ("fopen", "fread", "fclose"):
        if has(forced, libc_name):
            failures.append(f"forced Windows branch still references {libc_name}")

    # The unmodified build must take whichever path its own platform selects.
    # A Windows runner's native build *is* the rand_s path, so asserting
    # /dev/urandom there would be asserting the wrong platform.
    if os.name == "nt":
        if not has(host, "rand_s"):
            failures.append("native Windows build does not reference rand_s")
        for libc_name in ("fopen", "fread", "fclose"):
            if has(host, libc_name):
                failures.append(f"native Windows build references {libc_name}")
        host_path = "rand_s"
    else:
        if has(host, "rand_s"):
            failures.append("host build references rand_s; the guard did not select the POSIX path")
        if not has(host, "fopen"):
            failures.append("host build does not reference fopen; the /dev/urandom path is missing")
        host_path = "/dev/urandom"

    if failures:
        sys.exit("check_platform_branch failed:\n  " + "\n  ".join(failures))
    print(f"platform branch: forced Windows selects rand_s, native host selects {host_path}")


if __name__ == "__main__":
    main()

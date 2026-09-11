"""Neutralize DGDcreateFB tamper gates so repackaged clones run.

Root cause of the "app keeps stopping" crash:
MainActivity.runSecurityGateOrBlock() and runIdentityGateOrBlock()
compare the runtime package id / app label / signing-cert SHA-256 /
dex CRC against baked-in EXPECTED_* values. Any repackaged clone (new
package id, badged label, new signature, patched dex) trips
securityBlock(), which posts a delayed NullPointerException crash on
the main looper a few seconds after launch.

Fix: replace the three method bodies with `return false` (0).
MainActivity.onCreate treats 0 as "proceed" (if-nez -> continue to
setContentView), so clones boot into the normal UI with no delayed
crash. Smali classes are deliberately NOT renamed, so the hardcoded
Class.forName("com.dgd.createfb.*") lookups keep resolving with a
manifest-only package rename.

Usage: python3 patch_gates.py <apktool-decode-dir>
Fails loudly if any gate method is not found (apktool version skew).
"""

import pathlib
import re
import sys

GATE_METHODS = (
    "runSecurityGateOrBlock()Z",
    "runIdentityGateOrBlock()Z",
    "securityBlock(Ljava/lang/String;)Z",
)

PATCHED_BODY = ".locals 1\n    const/4 v0, 0x0\n    return v0\n"


def patch_smali(smali: pathlib.Path) -> None:
    text = smali.read_text()
    for sig in GATE_METHODS:
        pat = re.compile(
            r"(\.method private " + re.escape(sig) + r"\n).*?(\.end method)",
            re.DOTALL,
        )
        m = pat.search(text)
        assert m, f"gate method not found (apktool skew?): {sig}"
        text = text[: m.start()] + m.group(1) + PATCHED_BODY + m.group(2) + text[m.end():]
    m_body = re.search(
        r"\.method private securityBlock\(Ljava/lang/String;\)Z\n(.*?).end method",
        text,
        re.DOTALL,
    )
    assert m_body, "securityBlock method lost after patch"
    body = m_body.group(1)
    assert "postDelayed" not in body, "securityBlock still schedules the crash runnable"
    smali.write_text(text)


def main(argv: list) -> int:
    root = pathlib.Path(argv[1])
    targets = sorted(root.rglob("MainActivity.smali"))
    assert targets, f"MainActivity.smali not found under {root}"
    for target in targets:
        patch_smali(target)
        print(f"patched gates: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

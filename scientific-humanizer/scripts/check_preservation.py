#!/usr/bin/env python3
"""Check that a rewrite kept every item a style edit must never touch.

    check_preservation.py ORIGINAL REWRITE [--format md|tex]

ORIGINAL and REWRITE are files (a manuscript before and after editing, or a passage saved
to two files). The script extracts, from each, the items whose exact text carries meaning:

  maths       $...$, $$...$$, \\(...\\), \\[...\\], and equation-like LaTeX environments
  citations   [@key], @key, \\cite{...} and its variants (each key counted separately)
  references  \\ref, \\eqref, \\cref, \\autoref, \\label, pandoc {#id} and @fig:/@sec:/@tbl:/@eq: ids
  numbers     digit strings outside maths (12, 3.5, 10^4, 95%), with their units if attached
  urls, code  http(s) links and `inline code`

and compares them as multisets. Anything missing from, or added to, the rewrite is printed,
and the exit status is 1. Moving an item is fine; changing, dropping or inventing one is not.
Order is not checked: style edits may legitimately reorder a sentence.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

MATH_ENVS = r"(?:equation|align|gather|multline|eqnarray|displaymath|math)\*?"
PATTERNS = {
    "maths": [
        rf"\\begin\{{{MATH_ENVS}\}}.*?\\end\{{{MATH_ENVS}\}}",
        r"\$\$.+?\$\$",
        r"\\\[.+?\\\]",
        r"\\\(.+?\\\)",
        r"(?<![\\$])\$(?!\$)(?:\\\$|[^$])+?\$",
    ],
}


def strip_comments(text, fmt):
    if fmt == "tex":
        return re.sub(r"(?<!\\)%.*", "", text)
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def extract(text, fmt):
    text = strip_comments(text, fmt)
    items = {k: Counter() for k in ("maths", "citations", "references", "numbers", "urls", "code")}
    rest = text
    for pat in PATTERNS["maths"]:
        for m in re.finditer(pat, rest, re.S):
            items["maths"][re.sub(r"\s+", " ", m.group(0)).strip()] += 1
        rest = re.sub(pat, " ", rest, flags=re.S)
    for m in re.finditer(r"`[^`\n]+`", rest):
        items["code"][m.group(0)] += 1
    rest = re.sub(r"`[^`\n]+`", " ", rest)
    for m in re.finditer(r"https?://[^\s)\]>}]+", rest):
        items["urls"][m.group(0).rstrip(".,;")] += 1
    rest = re.sub(r"https?://[^\s)\]>}]+", " ", rest)
    # LaTeX citations and references
    for m in re.finditer(r"\\[a-zA-Z]*cite[a-zA-Z]*\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}", rest):
        for key in m.group(1).split(","):
            items["citations"][key.strip()] += 1
    rest = re.sub(r"\\[a-zA-Z]*cite[a-zA-Z]*\*?(?:\[[^\]]*\]){0,2}\{[^}]*\}", " ", rest)
    for m in re.finditer(r"\\(ref|eqref|cref|Cref|autoref|pageref|label)\{([^}]*)\}", rest):
        items["references"][f"\\{m.group(1)}{{{m.group(2)}}}"] += 1
    rest = re.sub(r"\\(ref|eqref|cref|Cref|autoref|pageref|label)\{[^}]*\}", " ", rest)
    # pandoc: {#id} anchors, @fig:/@sec: cross-references, then citation keys
    for m in re.finditer(r"\{#([\w:.-]+)[^}]*\}", rest):
        items["references"][f"#{m.group(1)}"] += 1
    rest = re.sub(r"\{#[\w:.-]+[^}]*\}", " ", rest)
    for m in re.finditer(r"(?<![\w@])@((?:fig|sec|tbl|eq|lst):[\w:.-]+)", rest):
        items["references"][f"@{m.group(1)}"] += 1
    rest = re.sub(r"(?<![\w@])@(?:fig|sec|tbl|eq|lst):[\w:.-]+", " ", rest)
    for m in re.finditer(r"(?<![\w@.])@([A-Za-z0-9_][\w:.#$%&+?<>~/-]*\w)", rest):
        items["citations"][m.group(1)] += 1
    rest = re.sub(r"(?<![\w@.])@[A-Za-z0-9_][\w:.#$%&+?<>~/-]*\w", " ", rest)
    # numbers outside maths, with an attached unit or percent sign
    for m in re.finditer(r"(?<![\w.])[-−]?\d[\d,]*(?:\.\d+)?(?:[eE×x]\s?10\^?[-−]?\d+)?\s?(?:%|‰)?", rest):
        items["numbers"][m.group(0).replace(" ", "")] += 1
    return items


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original")
    ap.add_argument("rewrite")
    ap.add_argument("--format", choices=["md", "tex"], help="default: from the file extension (tex, else md)")
    args = ap.parse_args()
    a, b = Path(args.original), Path(args.rewrite)
    fmt = args.format or ("tex" if a.suffix == ".tex" else "md")
    before, after = extract(a.read_text(), fmt), extract(b.read_text(), fmt)
    problems = 0
    for kind in before:
        lost, gained = before[kind] - after[kind], after[kind] - before[kind]
        for item, n in lost.items():
            print(f"MISSING {kind}: {item}" + (f" (x{n})" if n > 1 else ""))
        for item, n in gained.items():
            print(f"ADDED   {kind}: {item}" + (f" (x{n})" if n > 1 else ""))
        problems += sum(lost.values()) + sum(gained.values())
    counts = ", ".join(f"{k} {sum(v.values())}" for k, v in before.items())
    print(f"checked {counts}: " + ("all preserved" if not problems else f"{problems} differences"))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()

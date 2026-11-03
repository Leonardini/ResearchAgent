#!/usr/bin/env python3
"""Check that a rewrite kept every item a style edit must never touch.

    check_preservation.py ORIGINAL REWRITE [--format md|tex]

ORIGINAL and REWRITE are files (a manuscript before and after editing, or a passage saved
to two files). The script extracts, from each, the items whose exact text carries meaning:

  maths       $...$, $$...$$, \\(...\\), \\[...\\], and equation-like LaTeX environments
  citations   [@key], @key, \\cite{...} and its variants (each key counted separately), and
              author-year citations typed as text: "Smith and Jones (2009)", "Smith et al. (2013a)",
              "(Smith, 2009; Jones et al., 2013)" (each author-year pair counted separately)
  references  \\ref, \\eqref, \\cref, \\autoref, \\label, pandoc {#id} and @fig:/@sec:/@tbl:/@eq: ids,
              and references typed by hand: "Section 3.4", "Appendix A.6", "Theorems 2.1 and 2.3"
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


# Author-year citations typed as plain text. A surname may carry a particle (van, de) and
# hyphens or apostrophes; a group is "A", "A and B", "A, B and C" or "A et al.".
_NAME = r"(?:(?:van|von|de|der|den|du|da|di|del|le|la|ter)\s+)*[A-Z][^\W\d_][\w'\u2019-]*"
_AUTHORS = rf"(?<![\w'\u2019-]){_NAME}(?:\s*,\s*{_NAME})*(?:,?\s+(?:and|&)\s+{_NAME})?(?:\s+et\s+al\.?)?"
_YEAR = r"(?:1[5-9]|20)\d\d[a-z]?"
NARRATIVE_CITE = re.compile(rf"({_AUTHORS})\s*\(\s*({_YEAR}(?:\s*[,;]\s*{_YEAR})*)\s*\)")
PAREN_CITE = re.compile(rf"\(((?:[^()]*?\b{_YEAR}\b[^()]*?))\)")
CITE_IN_PAREN = re.compile(rf"({_AUTHORS}),?\s+({_YEAR}(?:\s*,\s*{_YEAR})*)")
# Cross-references typed by hand, with lists and ranges: "Sections 2-5", "Theorems 2.1 and 2.3".
_TARGET = r"(?:[A-Z]?\d+(?:\.\d+)*[a-z]?|[A-Z](?:\.\d+)*|[IVX]+)\b"
HAND_REF = re.compile(
    r"\b(?:[Ss]ections?|[Aa]ppendi(?:x|ces)|[Tt]heorems?|[Ll]emmas?|[Pp]ropositions?|[Cc]orollar(?:y|ies)|"
    r"[Cc]onjectures?|[Dd]efinitions?|[Rr]emarks?|[Ee]xamples?|[Cc]ounterexamples?|[Tt]ables?|[Ff]igures?|"
    r"Figs?\.|[Aa]lgorithms?|[Ee]quations?|Eqs?\.|[Qq]uestions?|[Pp]ropert(?:y|ies)|[Cc]hapters?|[Pp]arts?|Steps?)"
    rf"\s+{_TARGET}(?:\s*(?:,|and|or|to|-|\u2013|\u2014)\s*{_TARGET})*")


def author_year(text):
    """Author-year citations as (normalised item, span) pairs, one item per author-year pair."""
    found = []
    def norm(authors, years):
        a = re.sub(r"\s+", " ", authors.replace("&", "and")).strip().rstrip(",")
        a = re.sub(r"\s+et al\.?$", " et al.", a)
        return [f"{a} {y}" for y in re.split(r"\s*[,;]\s*", years)]
    taken = []
    for m in NARRATIVE_CITE.finditer(text):
        found += norm(m.group(1), m.group(2))
        taken.append(m.span())
    for m in PAREN_CITE.finditer(text):
        if any(a <= m.start() < b for a, b in taken):
            continue
        hits = list(CITE_IN_PAREN.finditer(m.group(1)))
        if hits:
            for h in hits:
                found += norm(h.group(1), h.group(2))
            taken.append(m.span())
    return found, taken


def cut(text, spans):
    for a, b in sorted(spans, reverse=True):
        text = text[:a] + " " + text[b:]
    return text


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
    # author-year citations and hand-typed cross-references, which hold numbers of their own
    cites, spans = author_year(rest)
    for c in cites:
        items["citations"][c] += 1
    rest = cut(rest, spans)
    for m in HAND_REF.finditer(rest):
        ref = re.sub(r"\s*[\u2013\u2014]\s*", "-", re.sub(r"\s+", " ", m.group(0)))
        items["references"][ref] += 1
    rest = HAND_REF.sub(" ", rest)
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

#!/usr/bin/env python3
"""Formatter: mechanical layout and structure checks for a pandoc Markdown or LaTeX manuscript.

    formatter.py check DRAFT [--defaults FILE] [--out DIR] [--max-lines 12] [--hard-max-lines 15] [--min-trim-lines 5]
        Compile the paper privately (never touching the author's own PDF or build folder),
        run every mechanical check, and write to DIR (default: formatter/ next to the draft):
          issues.json      every finding, machine-readable
          report.md        findings grouped by kind, with page numbers and sections
          annotated.pdf    the compiled paper with each finding highlighted on its page
          paper.pdf, paper.log, paper.tex   the private build

    formatter.py annotate DRAFT [--out DIR] --extra REVIEW.json
        Re-render report.md and annotated.pdf with the agent's own review items added
        (a JSON list of {"check", "severity", "message", "find"?, "page"?, "section"?}).

Needs pandoc (>= 3), latexmk with pdflatex, and PyMuPDF (`pip install pymupdf`).
"""
import argparse
import json
import re
import unicodedata
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

SEVERITIES = ("fix", "propose", "review")  # mechanical fix / change wording / author judgement
SEVERITY_TEXT = {"fix": "Layout fix", "propose": "Proposed change", "review": "For review"}
COLOURS = {"fix": (0.85, 0.1, 0.1), "propose": (0.95, 0.55, 0.0), "review": (0.15, 0.35, 0.85)}
UNICODE_MATHS = set("≤≥≠≈≡×÷±∓∑∏∫∈∉⊂⊆⊃⊇∪∩∞→←↔⇒⇔∀∃∂∇√′″−αβγδεζηθκλμνξπρστφχψωΓΔΘΛΞΠΣΦΨΩ")
ACRONYM_ALLOW = {"NP", "PDF", "CPU", "GPU", "RAM", "URL", "DOI", "ID", "OK", "UK", "USA", "EU", "AI", "API",
                 "GB", "MB", "TB", "KB", "GHz", "IBM", "IEEE", "ISO", "ASCII", "HTML", "JSON", "CSV", "OS",
                 "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII"}
BACK_MATTER = re.compile(r"acknowledg|funding|declaration|competing|author contributions|credit authorship|data availability|references|bibliography", re.I)
ROADMAP = re.compile(r"rest of (?:this|the) (?:paper|article|manuscript) is organi[sz]ed as follows", re.I)


def run(cmd, cwd=None, stdin=None):
    return subprocess.run(cmd, cwd=cwd, input=stdin, check=True, capture_output=True, text=True).stdout


def issue(check, severity, message, page=None, find=None, rect=None, section=None):
    assert severity in SEVERITIES, severity
    return {"check": check, "severity": severity, "message": message, "page": page,
            "find": find, "rect": rect, "section": section}


# ---------------------------------------------------------------------------------------
# The paper and its private build.

class Paper:
    def __init__(self, draft, defaults=None, out=None, tex=None):
        self.draft = Path(draft).expanduser().resolve()
        self.root = self.draft.parent
        self.is_tex = self.draft.suffix.lower() == ".tex"
        self.defaults = self._find_defaults(defaults)
        self.out = Path(out).expanduser().resolve() if out else self.root / "formatter"
        self.author_tex, self.build_note = self._find_author_tex(tex)

    def _find_author_tex(self, given):
        """The .tex the author's own build produced, so the pages checked are the pages submitted.
        Given with --tex, or <stem>.tex beside a Markdown draft when it is at least as new as the
        draft. A stale one is not used (it would show an older text), and the note says so."""
        if self.is_tex:
            return None, "built from the LaTeX draft itself"
        if given:
            return Path(given).expanduser().resolve(), f"built from the author's {Path(given).name} (--tex)"
        cand = self.draft.with_suffix(".tex")
        scripts = sorted(p.name for p in self.root.iterdir() if p.is_file() and
                         (p.name == "Makefile" or re.match(r"(build|make|compile)\w*\.(py|sh)$", p.name)))
        hint = f" The folder has a build script ({', '.join(scripts)}): rerun it, or pass --tex." if scripts else ""
        if cand.exists() and cand.stat().st_mtime >= self.draft.stat().st_mtime:
            return cand, f"built from the author's {cand.name} (newer than the draft)"
        if cand.exists():
            return None, (f"WARNING: {cand.name} is older than the draft, so it was not used; the pages checked "
                          f"come from a default pandoc build and may differ from the author's.{hint}")
        if scripts and not self.defaults:
            return None, (f"WARNING: no generated .tex found; the pages checked come from a default pandoc build, "
                          f"not the author's.{hint}")
        return None, "built with pandoc" + (f" and {self.defaults.name}" if self.defaults else " defaults")

    def _find_defaults(self, given):
        if given:
            return Path(given).expanduser().resolve()
        mk = self.root / "Makefile"
        if mk.exists():
            m = re.search(r"--defaults[= ](\S+)", mk.read_text())
            if m and (self.root / m.group(1)).exists():
                return self.root / m.group(1)
        return None

    def build(self):
        """Compile into self.out. Returns (tex, pdf, log)."""
        self.out.mkdir(parents=True, exist_ok=True)
        gi = self.out / ".gitignore"
        if not gi.exists():
            gi.write_text("# Regenerated by formatter.py check.\n*\n")
        if self.is_tex or self.author_tex:
            tex = self.author_tex or self.draft
            job = ["-jobname=paper"]
        else:
            tex = self.out / "paper.tex"
            cmd = ["pandoc", str(self.draft), "-o", str(tex)]
            cmd += ["--defaults", str(self.defaults)] if self.defaults else ["--standalone", "--citeproc"]
            run(cmd, cwd=self.root)
            job = []
        src = tex.read_text(errors="replace")
        # pdflatex unless the file says otherwise: a magic comment, or fontspec/unicode-math loaded
        # outside an engine conditional (pandoc's template loads them only under \ifPDFTeX's else).
        conditional = re.search(r"\\if(PDFTeX|tutex|xetex|luatex)\b", src)
        magic = re.search(r"!TEX\s+(?:TS-)?program\s*=\s*(xelatex|lualatex)", src, re.I)
        engine = f"-{magic.group(1).lower()}" if magic else \
            "-xelatex" if not conditional and re.search(r"\\usepackage(\[[^\]]*\])?\{(fontspec|unicode-math)\}", src) else "-pdf"
        cmd = ["latexmk", engine, "-interaction=nonstopmode", "-halt-on-error", f"-outdir={self.out}"] + job + [str(tex)]
        r = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True)
        log = self.out / "paper.log"
        if r.returncode != 0:
            tail = log.read_text(errors="replace")[-3000:] if log.exists() else r.stdout[-3000:]
            sys.exit(f"compilation failed; end of the log:\n{tail}")
        return tex, self.out / "paper.pdf", log

    def ast(self):
        cmd = ["pandoc", str(self.draft), "-t", "json"]
        if self.defaults and not self.is_tex:
            m = re.search(r"(?m)^from:\s*(\S+)", self.defaults.read_text())
            if m:
                cmd += ["-f", m.group(1)]
        return json.loads(run(cmd, cwd=self.root))


# ---------------------------------------------------------------------------------------
# Pandoc AST helpers.

def stringify(x):
    if isinstance(x, list):
        return "".join(stringify(i) for i in x)
    if not isinstance(x, dict):
        return ""
    t, c = x.get("t"), x.get("c")
    if t == "Str":
        return c
    if t in ("Space", "SoftBreak", "LineBreak"):
        return " "
    if t == "Math":
        return "$" + c[1] + "$"
    if t == "Code":
        return c[1]
    if t in ("RawInline", "RawBlock", "Note"):
        return ""
    if t == "Cite":
        return stringify(c[1])
    if t in ("Link", "Image", "Span", "Quoted"):
        return stringify(c[1])
    return stringify(c)


def walk(x, fn):
    """Call fn on every dict node, depth first, in document order."""
    if isinstance(x, list):
        for i in x:
            walk(i, fn)
    elif isinstance(x, dict):
        fn(x)
        walk(x.get("c"), fn)


def header_title(h):
    return stringify(h["c"][2]).strip()


NUMBERING = re.compile(r"^(?:(?:Part|Appendix|Section|Chapter)\s+[A-Z0-9IVX]+(?:\.\d+)*\b\.?\s*[:—–-]?\s*"
                       r"|(?:\d+(?:\.\d+)*\.?|[A-Z](?:\.\d+)+\.?|[A-Z]\.)(?=\s|$)\s*[:—–-]?\s*)")


def strip_numbering(title):
    """'7.2 The compact solver' -> 'The compact solver'; '### 3.2' -> ''; 'Abstract' stays."""
    return NUMBERING.sub("", title.strip(), count=1).strip()


def sections(blocks):
    """Split top-level blocks into (header, body blocks) at every header."""
    out, cur = [], None
    for b in blocks:
        if b["t"] == "Header":
            cur = [b, []]
            out.append(cur)
        elif cur is not None:
            cur[1].append(b)
    return out


# ---------------------------------------------------------------------------------------
# Source checks (on the pandoc AST of the draft).

def check_headings(ast):
    found = []
    heads = [b for b in ast["blocks"] if b["t"] == "Header"]
    for h in heads:
        title = header_title(h)
        if not strip_numbering(title):
            found.append(issue("titles", "propose", f"Heading '{title}' has a number but no title.", find=title, section=title))
    secs = sections(ast["blocks"])
    levels = sorted({h["c"][0] for h in heads})
    for i, (h, body) in enumerate(secs):
        title, level = header_title(h), h["c"][0]
        nxt = secs[i + 1][0] if i + 1 < len(secs) else None
        has_children = nxt is not None and nxt["c"][0] > level
        if strip_numbering(title).lower() in ("abstract", "references", "bibliography", "acknowledgements",
                                              "acknowledgments") or level == levels[0] and len(levels) > 2:
            continue  # parts and front/back matter have no transition duty
        prose = [b for b in body if b["t"] in ("Para", "Plain")]
        if has_children and not prose:
            found.append(issue("transitions", "propose",
                               f"'{title}' goes straight into its first subsection: add 1-2 sentences saying what this section does.",
                               find=title, section=title))
    return found


EXEMPT_FLAT = re.compile(r"\b(introduction|conclusions?|discussion|concluding remarks|summary|outlook)\b", re.I)


def check_flat_sections(ast):
    """A main-text section with no subsections is a flag: it usually means an idea that belongs
    inside another section (his words, 2026-11-05: short sections "reflect poor organisation of
    the ideas"). Exempt: the introduction and the conclusion or discussion; front and back
    matter; unnumbered sections; and everything from the first appendix or the reference list
    on."""
    heads = [b for b in ast["blocks"] if b["t"] == "Header"]
    levels = sorted({h["c"][0] for h in heads})
    if len(levels) < 2:
        return []
    section_level = levels[1] if len(levels) > 2 else levels[0]
    found = []
    for i, h in enumerate(heads):
        level, (_, classes, _) = h["c"][0], h["c"][1]
        title = strip_numbering(header_title(h))
        if "appendix" in classes or re.match(r"(Appendix|Appendices)\b", header_title(h)) \
                or title.lower() in ("references", "bibliography"):
            break
        if level != section_level or "unnumbered" in classes or front_matter(h, ast) \
                or EXEMPT_FLAT.search(title) or BACK_MATTER.search(title):
            continue
        nxt = next((g for g in heads[i + 1:] if g["c"][0] <= level or g["c"][0] == level + 1), None)
        if nxt is None or nxt["c"][0] <= level:
            found.append(issue("flat-section", "propose",
                               f"Section '{title}' has no subsections. Outside the introduction and the "
                               "conclusion, a section without subsections usually means its idea belongs "
                               "inside another section: fold it into the section it serves, or give it the "
                               "subsections its content needs.", find=title[:60], section=header_title(h)))
    return found


def subsection_titles(ast):
    """(title, heading) for every subsection: a heading below the section level. The section
    level is the shallowest heading level, or the next one when the draft also has parts (three
    or more levels). Front and back matter (Abstract, References...) are not subsections."""
    heads = [b for b in ast["blocks"] if b["t"] == "Header"]
    levels = sorted({h["c"][0] for h in heads})
    if not levels:
        return []
    section_level = levels[1] if len(levels) > 2 else levels[0]
    return [(header_title(h), h) for h in heads if h["c"][0] > section_level]


AND_JOIN = re.compile(r"\band\b|,\s*(?:but|while|whereas)\b", re.I)


def check_subsection_titles(ast, layout):
    """A subsection title fits on one line and makes one point. Two checks:
    - it wraps onto a second line in the compiled PDF ("going over one line is a flag");
    - it contains "and" (or ", but"/", while"/", whereas"). When the conjunction joins two
      claims, each with its own verb ("X certifies ... and is mostly slower"), the subsection is
      really two and should be split; when it joins nouns ("Trees, splits and tree metrics",
      "NJ and FastME miss ...") it is fine. The script cannot tell the two apart, so it lists
      every candidate for the agent to judge."""
    def words(text):  # letters-only words, so maths renders the same in the source and the PDF
        return [w.lower() for w in re.findall(r"[^\W\d_]{2,}", unicodedata.normalize("NFKC", text))]

    found = []
    for title, _ in subsection_titles(ast):
        plain = strip_numbering(title)
        if AND_JOIN.search(plain):
            found.append(issue("subsection-titles", "review",
                               f"Subsection title '{plain}' contains '{AND_JOIN.search(plain).group(0).strip(', ')}'. "
                               "If it joins two claims (each with its own verb), split the subsection into two, "
                               "one claim per title; a list of nouns is fine.", find=plain[:60], section=title))
        tw = words(plain)
        if len(tw) < 2:
            continue
        # The title wraps when a heading row holds a proper prefix of its words and the row
        # just below holds the words that come next.
        for pno, p in enumerate(layout.pages):
            rows = [r for r in p["rows"] if r["kind"] != "footer"]
            for i, r in enumerate(rows[:-1]):
                rw, nxt = words(strip_numbering(r["text"])), rows[i + 1]
                if r["kind"] != "heading" or not rw or len(rw) >= len(tw) or tw[:len(rw)] != rw:
                    continue
                nw = words(nxt["text"])
                if nxt["kind"] == "heading" and nw and tw[len(rw):len(rw) + len(nw)] == nw \
                        and nxt["bbox"][1] - r["bbox"][3] < r["size"]:
                    found.append(issue("subsection-titles", "propose",
                                       f"Subsection title '{plain}' runs over one line in the PDF. Shorten it to "
                                       "one line, or split the subsection if the title states two things.",
                                       page=pno + 1, rect=[r["bbox"][0], r["bbox"][1], nxt["bbox"][2], nxt["bbox"][3]],
                                       section=title))
    return found


def section_ends(ast):
    """For each main-text section that has subsections or prose: its first and last sentence, so
    the agent can judge the opening and closing transitions. Appendices and everything after the
    reference list are left out: only the manuscript's sections must open and close with a
    transition (his ruling, 2026-11-06)."""
    secs = sections(ast["blocks"])
    out = []
    for i, (h, body) in enumerate(secs):
        classes = h["c"][1][1]
        if "appendix" in classes or re.match(r"(Appendix|Appendices)\b", header_title(h)) \
                or strip_numbering(header_title(h)).lower() in ("references", "bibliography"):
            break
        if front_matter(h, ast) or BACK_MATTER.search(strip_numbering(header_title(h))):
            continue
        paras = [stringify(b["c"]) for b in body if b["t"] in ("Para", "Plain")]
        if not paras:
            continue
        last_block = body[-1]["t"] if body else None
        out.append({"title": header_title(h), "level": h["c"][0], "first": paras[0][:300],
                    "last": paras[-1][-300:], "ends_with": last_block})
    return out


FRONT_MATTER = ("abstract", "highlights", "keywords", "key words", "graphical abstract", "summary")


def front_matter(h, ast):
    """A heading that is not the paper's first section: front matter (Abstract, Highlights...),
    or the title written as a heading, i.e. the first heading of the draft when it is the only
    heading at its level or is followed directly by the abstract."""
    if strip_numbering(header_title(h)).lower() in FRONT_MATTER:
        return True
    heads = [b for b in ast["blocks"] if b["t"] == "Header"]
    if not heads or h is not heads[0]:
        return False
    same_level = [x for x in heads if x["c"][0] == h["c"][0]]
    nxt = heads[1] if len(heads) > 1 else None
    return len(same_level) == 1 and len(heads) > 1 or \
        (nxt is not None and strip_numbering(header_title(nxt)).lower() in FRONT_MATTER)


def check_roadmap(ast):
    text_all = stringify(ast["blocks"])
    mathematical = bool(re.search(r"\b(Theorem|Lemma|Proposition|Corollary|Proof)\b", text_all))
    secs = sections(ast["blocks"])
    first = next(((h, b) for h, b in secs if not front_matter(h, ast)
                  and any(x["t"] == "Para" for x in b)), None)
    if first is None:
        return [], None
    h, body = first
    # the first section runs until the next header of the same or a higher level
    level, idx = h["c"][0], ast["blocks"].index(h)
    blocks = []
    for b in ast["blocks"][idx + 1:]:
        if b["t"] == "Header" and b["c"][0] <= level:
            break
        blocks.append(b)
    paras = [stringify(b["c"]) for b in blocks if b["t"] in ("Para", "Plain")]
    road = next((p for p in reversed(paras[-3:]) if ROADMAP.search(p)), None)
    if road is None:
        sev = "propose" if mathematical else "review"
        return [issue("roadmap", sev, f"The first section ('{header_title(h)}') does not end with "
                      "'The rest of this paper is organised as follows' naming every section and appendix.",
                      find=header_title(h), section=header_title(h))], None
    return [], road


def roadmap_coverage(ast, road):
    """Sections the roadmap paragraph does not mention. Appendices are left out of the roadmap
    (the author's preference, 2026-11-05: listing them makes the paragraph too long), so they
    are not required; check_roadmap_appendices flags a roadmap that lists them."""
    missing = []
    for h in [b for b in ast["blocks"] if b["t"] == "Header"]:
        title = header_title(h)
        m = re.match(r"^(\d+)\.\s", title)
        if not m:
            continue
        num = m.group(1)
        ok = re.search(rf"\bSections?\s+(?:\d+\s*(?:,|and|–|-)\s*)*{num}\b", road)
        if not ok:
            for m2 in re.finditer(r"\bSections?\s+(\d+)\s*[–-]\s*(\d+)", road):
                ok = ok or int(m2.group(1)) <= int(num) <= int(m2.group(2))
        if not ok and strip_numbering(title).lower() not in ("introduction",):
            missing.append(title)
    return missing


def check_roadmap_appendices(road):
    """The roadmap names the sections only; a list of appendices is proposed for cutting."""
    n = len(re.findall(r"\bAppendi(?:x|ces)\b", road))
    if n == 0:
        return []
    return [issue("roadmap", "propose", f"The roadmap paragraph lists appendices ({n} mention(s)). Cut them: "
                  "the roadmap names the sections only, and each appendix is reached from the text that uses it.",
                  find="rest of this paper is organised")]


def check_numbers(ast):
    found, seen = [], set()

    def sig_figs(tok):
        digits = tok.replace("{,}", "").replace(",", "")
        if "." in digits:
            return len(digits.replace(".", "").lstrip("0"))
        return len(digits.lstrip("0").rstrip("0")) or 1

    def scan(text, context):
        for m in re.finditer(r"(?<![\w.^_])\d{1,3}(?:(?:,|\{,\})\d{3})+(?:\.\d+)?(?![\w])|(?<![\w.^_])\d+(?:\.\d+)?(?![\w])", text):
            tok = m.group(0)
            plain = tok.replace("{,}", "").replace(",", "")
            if re.fullmatch(r"1[5-9]\d\d|20\d\d", plain):  # years
                continue
            n = sig_figs(tok)
            if n > 5 and (tok, context) not in seen:
                seen.add((tok, context))
                found.append(issue("numbers", "propose",
                                   f"{tok} has {n} significant figures: give at most 5, and round a large number "
                                   f"for readability unless its exact value matters. Context: \"{context[:120]}\"",
                                   find=plain if "." in plain else tok.replace("{,}", ",")))

    def visit(node):
        t = node.get("t")
        if t in ("Para", "Plain"):
            text = stringify(node["c"])
            scan(IDENTIFIER.sub(" ", text).replace("$", " "), text)
    walk(ast["blocks"], visit)
    return found


# Identifiers are exact by nature and never rounded: DOIs, ORCIDs, arXiv numbers, ISBNs, and
# any number inside a web address.
IDENTIFIER = re.compile(
    r"(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?\b10\.\d{4,9}/[^\s,;]+"            # DOI
    r"|\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b"                                         # ORCID
    r"|(?:arXiv:\s*)?\b\d{4}\.\d{4,5}(?:v\d+)?\b"                                  # arXiv
    r"|ISBN(?:-1[03])?[:\s]*[\d-]{9,17}[\dX]"                                      # ISBN
    r"|https?://\S+", re.I)


REF_KINDS = (r"Sections?|Secs?\.|§|Appendix|Appendices|Tables?|Figures?|Figs?\.|Theorems?|Thms?\.|"
             r"Propositions?|Props?\.|Lemmas?|Lemmata|Corollar(?:y|ies)|Conjectures?|Definitions?|"
             r"Algorithms?|Equations?|Eqs?\.")
HARD_REF = re.compile(rf"(?<![\w@#:])({REF_KINDS})[\s~]*\(?([A-Z]?\d+(?:\.\d+)*[a-z]?|[A-Z](?:\.\d+)*(?![\w']))")
# A bare capital needs "Appendix" or a following dot, so "A polynomial ..." is not read as a letter.
NUMBERED_HEADING = re.compile(r"^(?:Appendix\s+[A-Z](?:\.\d+)*\.?|[A-Z](?:\.\d+)+\.?|[A-Z]\.|\d+(?:\.\d+)*\.?)\s")


def check_hardcoded_refs(ast):
    """Cross-references must go through labels, so that reordering renumbers them automatically.

    Finds numbers written by hand: in prose ("Section 8.1", "Table E9", "Theorem 2",
    "Appendix J") and in headings ("## 8.1 Results"). One summary finding per kind, with
    examples, since a paper that numbers by hand usually does so everywhere."""
    refs, heads = defaultdict(list), []

    def visit(node):
        t = node.get("t")
        if t == "Header":
            title = stringify(node["c"][2])
            if NUMBERED_HEADING.match(title):
                heads.append(title)
        elif t in ("Para", "Plain"):
            text = stringify(node["c"])
            for m in HARD_REF.finditer(text):
                kind = re.sub(r"s$|ies$|\.$", "", m.group(1)).replace("Appendice", "Appendix")
                refs[kind].append(m.group(0))
    walk(ast["blocks"], visit)
    found = []
    for kind, hits in sorted(refs.items(), key=lambda kv: -len(kv[1])):
        examples = ", ".join(f'"{h}"' for h in list(dict.fromkeys(hits))[:4])
        found.append(issue("hardcoded-refs", "fix",
                           f"{len(hits)} hand-numbered reference(s) of the form \"{kind} N\" ({examples}). Give every "
                           f"numbered object a label and refer to it by label, so that moving it renumbers every "
                           f"reference automatically.", find=hits[0]))
    if heads:
        found.append(issue("hardcoded-refs", "fix",
                           f"{len(heads)} heading(s) carry hand-written numbers (e.g. \"{heads[0]}\"). Let the "
                           f"build number them, and give each a label.", find=heads[0]))
    return found


def check_unicode_maths(ast):
    found, seen = [], set()

    def visit(node):
        if node.get("t") in ("Para", "Plain"):
            for x in node["c"]:
                if x.get("t") == "Str" and (bad := sorted(set(x["c"]) & UNICODE_MATHS)):
                    ctx = stringify(node["c"])
                    i = ctx.find(x["c"])
                    if (x["c"], ctx[max(0, i - 60):i + 60]) in seen:
                        continue
                    seen.add((x["c"], ctx[max(0, i - 60):i + 60]))
                    found.append(issue("maths", "propose",
                                       f"Unicode maths '{x['c']}' in prose ({''.join(bad)}): write it as LaTeX maths "
                                       f"like the rest of the paper. Context: \"…{ctx[max(0, i - 60):i + 60]}…\"",
                                       find=" ".join(re.sub(r"\$[^$]*\$|\[@[^\]]*\]", " ", ctx[max(0, i - 25):i + 25]).split()[1:-1]) or None))
    walk(ast["blocks"], visit)
    return found


def maths_inventory(ast):
    """Candidates for inconsistent notation, for the agent to judge."""
    inline, display, prose_tokens = [], [], Counter()

    def visit(node):
        t = node.get("t")
        if t == "Math":
            (display if node["c"][0]["t"] == "DisplayMath" else inline).append(node["c"][1])
        elif t == "Str":
            for w in re.findall(r"(?<![\w$])([A-Za-z])(?![\w$])", node["c"]):
                prose_tokens[w] += 1
    walk(ast["blocks"], visit)
    single = Counter(m.strip() for m in inline if re.fullmatch(r"\s*[A-Za-z]\s*", m))
    letters_as_text = {w: prose_tokens[w] for w in single if w not in ("a", "A", "I") and prose_tokens[w]}
    named = Counter()
    for m in inline + display:
        for k in re.findall(r"\\(?:mathrm|operatorname|text|mathit)\{([A-Za-z]{2,})\}", m):
            named[k] += 1
    bare = {}
    for name in named:
        n = sum(len(re.findall(rf"(?<![\\{{A-Za-z]){name}(?![A-Za-z}}])", re.sub(r"\\(?:mathrm|operatorname|text|mathit)\{[^}]*\}", "", m)))
                for m in inline + display)
        if n:
            bare[name] = n
    fracs = {"\\frac (inline)": sum("\\frac" in m for m in inline), "\\tfrac (inline)": sum("\\tfrac" in m for m in inline),
             "\\dfrac (inline)": sum("\\dfrac" in m for m in inline)}
    return {"letters_also_in_plain_text": letters_as_text, "named_operators_also_bare": bare,
            "inline_fraction_commands": {k: v for k, v in fracs.items() if v}}


def check_acronyms(ast):
    """Acronyms first used in the main text before any '(ACRONYM)' definition. Front matter
    (title block, authors and affiliations, abstract, keywords, highlights) and back matter
    (funding, declarations, CRediT, acknowledgements, references) are exempt: affiliations
    (CNRS, MRC), identifiers (ORCID) and funder names are not terms the reader must learn."""
    found, order = [], []
    # everything before the first heading (title block, authors, affiliations) is front matter
    in_abstract = [True]

    def visit(node):
        if node.get("t") == "Header":
            title = strip_numbering(header_title(node))
            in_abstract[0] = front_matter(node, ast) or bool(BACK_MATTER.search(title))
        if node.get("t") in ("Para", "Plain", "Header"):
            inl = node["c"][2] if node["t"] == "Header" else node["c"]
            text = re.sub(r"\$[^$]*\$", " ", stringify(inl))  # symbols in maths are not acronyms
            order.append((in_abstract[0], text))
    walk(ast["blocks"], visit)
    defined, first_use = set(), {}
    for abstract, text in order:
        for m in re.finditer(r"\(([^()]{1,60})\)", text):
            if not abstract:
                defined.update(x.strip() for x in re.split(r"[,;]| or ", m.group(1)))
        for m in re.finditer(r"(?<![\w-])([A-Z][A-Z0-9]*[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)(?:s)?(?![\w])", text):
            a = m.group(1)
            if a in ACRONYM_ALLOW or abstract:
                continue
            if a not in first_use:
                around = re.sub(r"\[@[^\]]*\]", " ", text[max(0, m.start() - 40):m.end() + 25])
                words = re.findall(r"[\w’'-]+", around)
                k = next((i for i, w in enumerate(words) if a in w), 0)
                # defined here only if it is a whole item of a parenthesis: "(BME)", "(2K, CO)"
                first_use[a] = (a in defined or bool(re.search(rf"\((?:[^()]*[,;]\s*)?{re.escape(a)}(?:\s*[,;][^()]*)?\)", text)),
                                text[max(0, m.start() - 80):m.end() + 40], " ".join(words[max(0, k - 2):k + 2]))
    for a, (ok, ctx, near) in first_use.items():
        if not ok:
            found.append(issue("definitions", "review",
                               f"'{a}' is used before it is defined (no '(…{a})' in the main text before this point). "
                               f"First use: \"…{ctx.strip()}…\"", find=near or a))
    return found


def structure_notes(ast):
    """Formatter-owned structure conventions, for the agent to judge."""
    heads = [(b["c"][0], header_title(b)) for b in ast["blocks"] if b["t"] == "Header"]
    titles = [t.lower() for _, t in heads]
    notes = []
    exp = [t for _, t in heads if re.search(r"experiment|computational results|evaluation|benchmark", t, re.I)]
    setup = [t for _, t in heads if re.search(r"set-?up|experimental design|materials and methods", t, re.I)]
    if exp and not setup:
        notes.append(issue("structure", "review", "There are experiment sections but no separate experimental-setup section "
                           f"(hardware, software, instances, metrics). Experiment headings: {exp[:3]}"))
    return notes, [t for _, t in heads]


# ---------------------------------------------------------------------------------------
# PDF checks.

class Layout:
    """Rows of text on each page, the body text frame, and paragraphs reconstructed from rows."""

    def __init__(self, pdf):
        self.doc = pymupdf.open(pdf)
        sizes, lefts, rights = Counter(), Counter(), Counter()
        self.pages = []
        for pno, page in enumerate(self.doc):
            lines = []
            for b in page.get_text("dict")["blocks"]:
                if b["type"] != 0:
                    continue
                for l in b["lines"]:
                    text = "".join(s["text"] for s in l["spans"])
                    if not text.strip():
                        continue
                    size = max(s["size"] for s in l["spans"])
                    bold = all(s["flags"] & 16 or not s["text"].strip() for s in l["spans"])
                    lines.append({"bbox": list(l["bbox"]), "text": text, "size": size, "bold": bold})
                    for s in l["spans"]:
                        sizes[round(s["size"], 1)] += len(s["text"])
            self.pages.append({"lines": lines, "rect": page.rect})
        self.body_size = sizes.most_common(1)[0][0]
        for p in self.pages:
            for row in self._rows(p["lines"]):
                if abs(row["size"] - self.body_size) < 0.6 and len(row["text"]) > 40:
                    lefts[round(row["bbox"][0])] += 1
                    rights[round(row["bbox"][2])] += 1
        self.left = lefts.most_common(1)[0][0]
        self.right = max(r for r, c in rights.items() if c >= rights.most_common(1)[0][1] * 0.2)
        self.width = self.right - self.left
        for p in self.pages:
            p["rows"] = self._rows(p["lines"])
        gaps = [b["bbox"][1] - a["bbox"][1] for p in self.pages for a, b in zip(p["rows"], p["rows"][1:])
                if a["kind"] == b["kind"] == "body"]
        self.leading = statistics.median([g for g in gaps if g > 0]) if gaps else self.body_size * 1.2
        # Justified text: most body rows reach the right margin, so a short row ending a sentence
        # is the last line of a paragraph (the cue that separates paragraphs under parskip, where
        # there is no indent and the extra space can be smaller than a line).
        body_rows = [r for p in self.pages for r in p["rows"] if r["kind"] == "body"]
        full = sum(1 for r in body_rows if r["bbox"][2] >= self.right - 3)
        self.justified = bool(body_rows) and full >= 0.5 * len(body_rows)
        tops = [p["rows"][0]["bbox"][1] for p in self.pages if p["rows"]]
        bottoms = [max(r["bbox"][3] for r in p["rows"] if r["kind"] != "footer") for p in self.pages
                   if any(r["kind"] != "footer" for r in p["rows"])]
        self.top = statistics.median(tops) if tops else 72
        self.bottom = sorted(bottoms)[int(len(bottoms) * 0.9)] if bottoms else 720

    def _rows(self, lines):
        rows = []
        for l in sorted(lines, key=lambda l: ((l["bbox"][1] + l["bbox"][3]) / 2, l["bbox"][0])):
            yc = (l["bbox"][1] + l["bbox"][3]) / 2
            if rows and abs(rows[-1]["yc"] - yc) < 3.5:
                r = rows[-1]
                r["parts"].append(l)
                r["bbox"] = [min(r["bbox"][0], l["bbox"][0]), min(r["bbox"][1], l["bbox"][1]),
                             max(r["bbox"][2], l["bbox"][2]), max(r["bbox"][3], l["bbox"][3])]
                r["size"] = max(r["size"], l["size"])
                r["bold"] = r["bold"] and l["bold"]
            else:
                rows.append({"yc": yc, "parts": [l], "bbox": list(l["bbox"]), "size": l["size"], "bold": l["bold"]})
        for r in rows:
            r["parts"].sort(key=lambda l: l["bbox"][0])
            r["text"] = " ".join(l["text"].strip() for l in r["parts"])
        if hasattr(self, "left"):
            for r in rows:
                r["kind"] = self._kind(r)
        return rows

    def _kind(self, r):
        t = r["text"].strip()
        if re.fullmatch(r"\d{1,3}", t) and r["bbox"][1] > 700:
            return "footer"
        if r["size"] > self.body_size + 0.6 or (r["bold"] and len(t) < 90):
            return "heading"
        gaps = [b["bbox"][0] - a["bbox"][2] for a, b in zip(r["parts"], r["parts"][1:])]
        if any(g > 18 for g in gaps):
            return "table"
        if r["bbox"][0] > self.left + 25 and r["bbox"][2] < self.right - 25:
            return "display"
        return "body"

    para_starts = frozenset()  # the first words of every source paragraph (set from the AST)

    def starts_paragraph(self, text):
        """True if this row begins with the first words of a paragraph in the source: the only
        reliable cue under parskip, where the space between paragraphs can be smaller than the
        extra space inline maths adds inside one, and a last line can fill the width."""
        return bool(self.para_starts) and lead_words(text) in self.para_starts

    def paragraphs(self):
        """Body-text paragraphs as lists of (page, row); a paragraph may span pages."""
        paras, cur = [], []
        prev, display_after = None, None
        for pno, p in enumerate(self.pages):
            for r in p["rows"]:
                if r["kind"] == "footer":
                    continue
                if r["kind"] == "display" and cur:
                    display_after = r  # an equation inside the paragraph: keep going
                    continue
                if r["kind"] != "body" or CAPTION.match(r["text"]):
                    if cur:
                        paras.append(cur)
                    cur, prev, display_after = [], None, None
                    continue
                new = prev is None
                if prev is not None:
                    ppno, prow = prev
                    if ppno == pno:
                        anchor = display_after or prow
                        gap = r["bbox"][1] - anchor["bbox"][1]
                        new = gap > self.leading * (2.6 if display_after else 1.45) or r["bbox"][0] > self.left + 6 \
                            or (not display_after and self.starts_paragraph(r["text"])) \
                            or (self.justified and not display_after and prow["bbox"][2] < self.right - 0.08 * self.width
                                and SENTENCE_END.search(prow["text"].strip()) is not None)
                        if display_after and not new:
                            cur[-1] = (cur[-1][0], dict(cur[-1][1], before_display=True))
                    else:  # page break: continue only if the previous row ran to the margin
                        new = prow["bbox"][2] < self.right - 0.1 * self.width or r["bbox"][0] > self.left + 6
                if new and cur:
                    paras.append(cur)
                    cur = []
                cur.append((pno, r))
                prev, display_after = (pno, r), None
        if cur:
            paras.append(cur)
        return paras


def lead_words(text, n=4):
    """The first n words of plain text (letters only, maths and punctuation skipped), lower-case."""
    words = re.findall(r"[^\W\d_]{2,}", unicodedata.normalize("NFKC", text))
    return " ".join(w.lower() for w in words[:n]) if len(words) >= n else None


def paragraph_starts(ast):
    """lead_words of every paragraph of the draft, except openings shared by several paragraphs
    ("Proof. Let the"), which would mark false starts."""
    seen = Counter()
    def visit(node):
        if isinstance(node, dict):
            if node.get("t") == "Para":
                seen[lead_words(re.sub(r"\$[^$]*\$", " ", stringify(node["c"])))] += 1
            visit(node.get("c"))
        elif isinstance(node, list):
            for x in node:
                visit(x)
    visit(ast["blocks"])
    return frozenset(k for k, v in seen.items() if k and v == 1)


CAPTION = re.compile(r"^(Table|Figure|Fig\.|Algorithm|Listing)\s+(?:[A-Z]\.?)?\d+(?:\.\d+)*[.:]")


ALGO_LINE = re.compile(r"^(\d{1,3}:\s|Algorithm\s+[A-Z]?\d+\b)")
SENTENCE_END = re.compile(r"[.?!][)\]’”\"']*(\s*[□■∎])?$")


def check_paragraphs(layout, max_lines, hard_max_lines, min_trim_lines):
    """Long paragraphs and short last lines. A paragraph between max_lines and hard_max_lines is a
    review item (split it only if it holds more than one idea); one at hard_max_lines or more is a
    proposal. Short last lines are reported only for paragraphs of at least min_trim_lines lines
    (shorter ones are hard to trim), never inside an algorithm listing, and only when the line ends
    a sentence (otherwise it leads into a display or a list and is not a dangling line)."""
    found = []
    for para in layout.paragraphs():
        n = len(para)
        pno, first = para[0]
        if any(ALGO_LINE.match(r["text"].strip()) for _, r in para):
            continue
        # A paragraph that crosses a page is marked on the page holding most of its lines, and
        # the message names every page it covers: marking only the first page hid a 27-line
        # paragraph whose first 2 lines ended page 6 and whose other 25 filled page 7.
        pages = sorted({p for p, _ in para})
        main = Counter(p for p, _ in para).most_common(1)[0][0]
        where = f"page {pages[0] + 1}" if len(pages) == 1 else f"pages {pages[0] + 1}–{pages[-1] + 1}"
        if n >= hard_max_lines:
            found.append(issue("long-paragraph", "propose",
                               f"Paragraph of {n} lines on {where} (limit about {max_lines}): split it where the topic "
                               f"shifts. Starts: \"{first['text'][:70]}…\"", page=main + 1, rect=_span_rect(para, main)))
        elif n > max_lines:
            found.append(issue("long-paragraph", "review",
                               f"Paragraph of {n} lines on {where} (limit about {max_lines}): split it only if it holds "
                               f"more than one idea. Starts: \"{first['text'][:70]}…\"", page=main + 1,
                               rect=_span_rect(para, main)))
        lpno, last = para[-1]
        if n >= min_trim_lines and last["bbox"][2] - last["bbox"][0] < 0.2 * layout.width and len(last["text"]) < 40 \
                and not last.get("before_display") and SENTENCE_END.search(last["text"].strip()):
            found.append(issue("short-last-line", "propose",
                               f"The paragraph ends with a short line (\"{last['text']}\"): cutting about "
                               f"{len(last['text']) + 2} characters from the paragraph would save a line. Starts: "
                               f"\"{first['text'][:60]}…\"", page=lpno + 1, rect=last["bbox"]))
    return found


def _span_rect(para, pno=None):
    """The box around the paragraph's lines on page pno (default: its first page)."""
    pno = para[0][0] if pno is None else pno
    rows = [r for p, r in para if p == pno]
    return [min(r["bbox"][0] for r in rows), min(r["bbox"][1] for r in rows),
            max(r["bbox"][2] for r in rows), max(r["bbox"][3] for r in rows)]


def check_space(layout):
    """Large empty areas inside the text frame (not on the last page)."""
    found = []
    height = layout.bottom - layout.top
    threshold = max(6 * layout.leading, 0.1 * height)
    for pno, p in enumerate(layout.pages[:-1]):
        page = layout.doc[pno]
        boxes = [r["bbox"] for r in p["rows"] if r["kind"] != "footer"]
        boxes += [list(b) for b in (page.get_image_rects(x[0]) for x in page.get_images()) for b in b]
        boxes += [list(d["rect"]) for d in page.get_drawings() if d["rect"].height > 0.5 or d["rect"].width > 30]
        boxes = sorted((b for b in boxes if b[3] > layout.top - 5 and b[1] < layout.bottom + 5), key=lambda b: b[1])
        if not boxes:
            continue
        y = layout.top
        for b in boxes:
            if b[1] - y > threshold:
                found.append(issue("wasted-space", "fix", f"{(b[1] - y) / layout.leading:.0f} empty lines in the middle of "
                                   "the page: usually a float that did not fit, or a forced page break.",
                                   page=pno + 1, rect=[layout.left, y, layout.right, b[1]]))
            y = max(y, b[3])
        if layout.bottom - y > threshold:
            nxt = layout.pages[pno + 1]["rows"]
            nxt_kind = nxt[0]["kind"] if nxt else "?"
            found.append(issue("wasted-space", "fix", f"The page ends {(layout.bottom - y) / layout.leading:.0f} lines early"
                               + (" before a table or figure that did not fit" if nxt_kind in ("table", "display") else "")
                               + ".", page=pno + 1, rect=[layout.left, y, layout.right, layout.bottom]))
    return found


def normalise(s):
    s = re.sub(r"-\s*\n\s*", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def tex_plain(cell):
    cell = re.sub(r"\\\(.*?\\\)|\$[^$]*\$", " ", cell)
    cell = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", cell)
    cell = re.sub(r"[{}~\\]", " ", cell)
    return re.sub(r"\s+", " ", cell).strip()


def wrap_norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip().lower()


def cell_wraps(cell, rows_by_page, leading):
    """(page, first words) if this table cell's text runs over more than one row of the PDF,
    else None. Math is skipped (its PDF text differs from the source); a cell under six words
    or with no three-word run of plain text on either side is not judged."""
    segs = [wrap_norm(tex_plain(x)).split() for x in re.split(r"\\\(.*?\\\)|\$[^$]*\$", cell)]
    words = [w for seg in segs for w in seg]
    runs = [seg for seg in segs if len(seg) >= 3]
    if len(words) < 6 or not runs:
        return None
    first, last = " ".join(runs[0][:3]), " ".join(runs[-1][-3:])
    if first == last or any(sum(not w.isdigit() for w in snip.split()) < 2 for snip in (first, last)):
        return None  # numbers alone ("5 6 7") also occur in prose and other rows
    # Unwrapped if some table row holds the cell's first and last words in order (rows of one
    # table often start alike, so the first row matching the opening is not necessarily its own).
    for rows in rows_by_page:
        for _, text, kind in rows:
            if kind == "table" and first in text and last in text[text.index(first):]:
                return None
    for pno, rows in enumerate(rows_by_page):
        for i, (y, text, kind) in enumerate(rows):
            # The cell's first row must be a table row (cells set apart), not prose quoting it.
            if kind != "table" or first not in text:
                continue
            for y2, text2, _ in rows[i + 1:]:
                if y2 - y > 4 * leading:
                    break
                if last in text2:
                    return pno, " ".join(runs[0][:4])
    return None


def check_tables(layout, tex_text):
    """longtables that break across pages, and tables whose columns force cells to wrap."""
    found = []
    texts = [normalise(p.get_text()) for p in layout.doc]
    last_page = 0  # tables appear in document order
    for n, m in enumerate(re.finditer(r"\\begin\{longtable\}(\[[^\]]*\])?\{(.*?)\}\n(.*?)\\end\{longtable\}", tex_text, re.S), 1):
        spec, body = m.group(2), m.group(3)
        rows_part = body.split("\\endlastfoot")[-1] if "\\endlastfoot" in body else body.split("\\endhead")[-1]
        rows = [r for r in re.split(r"\\\\|\\tabularnewline", rows_part) if tex_plain(r.split("&")[0])]
        cap = re.search(r"\\caption\{(.*?)\}\s*(\\tabularnewline|\\\\)", body, re.S)
        name = tex_plain(cap.group(1))[:60] if cap else f"table {n}"

        def page_of(row, start, stop):
            words = [w for w in tex_plain(row.split("&")[0]).split() if len(w) > 2][:5]
            if len(words) < 2:
                words = tex_plain(row).split()[:5]
            snip = normalise(" ".join(words))
            return next((i for i in range(start, min(stop, len(texts))) if snip and snip in texts[i]), None)
        if rows:
            a = page_of(rows[0], last_page, len(texts))
            if cap and a is not None:
                c = page_of(cap.group(1), max(0, last_page - 1), a + 1)
                if c is not None and c != a:
                    found.append(issue("split-table", "fix", f"The caption of table '{name}' is on page {c + 1} but the table "
                                       f"starts on page {a + 1}: keep caption and table together.", page=c + 1,
                                       find=" ".join(tex_plain(cap.group(1)).split()[:4])))
            b = page_of(rows[-1], a, a + 3) if a is not None else None
            if a is not None:
                last_page = a
            if a is not None and b is not None and a != b:
                found.append(issue("split-table", "fix", f"Table '{name}' starts on page {a + 1} and ends on page {b + 1}.",
                                   page=a + 1, find=" ".join(tex_plain(rows[0].split('&')[0]).split()[:4])))
        if False:  # fixed-width columns are checked for every table type below
            found.append(issue("wrapped-rows", "fix", f"Table '{name}' has fixed-width columns ({spec[:60]}), so long "
                               "cells wrap onto a second line. Size the columns to their content (pandoc: set "
                               "`columns: 1000` in the defaults; LaTeX: l/c/r columns) and shrink the font if the table "
                               "is then too wide.", find=" ".join(tex_plain(rows[0].split('&')[0]).split()[:4]) if rows else None))
    # Fixed-width columns (p, m, b, X) wrap long cells. Report a table only when a cell actually
    # wraps in the PDF: its first and last words land on different rows a line or two apart.
    rows_by_page = [[(r["bbox"][1], wrap_norm(r["text"]), r["kind"]) for r in p["rows"]] for p in layout.pages]
    for m in re.finditer(r"\\begin\{(?:longtable|tabular\*?|tabularx)\}(?:\[[^\]]*\])?(?:\{[^}]*\})?\{((?:[^{}]|\{[^}]*\})*)\}(.*?)\\end\{(?:longtable|tabular\*?|tabularx)\}",
                         tex_text, re.S):
        spec, body = m.group(1), m.group(2)
        if not re.search(r"p\{|X|m\{|b\{", spec):
            continue
        body = re.sub(r"\\caption\{(?:[^{}]|\{[^}]*\})*\}", " ", body)
        for row in re.split(r"\\\\|\\tabularnewline", body):
            hit = next((w for w in (cell_wraps(c, rows_by_page, layout.leading) for c in row.split("&")) if w), None)
            if hit:
                pno, snip = hit
                found.append(issue("wrapped-rows", "fix", f"A table cell wraps onto a second line (\u201c{snip}\u2026\u201d): "
                                   f"size the columns to their content (pandoc: `columns: 1000` in the defaults, or l/c/r "
                                   f"columns), shorten the cell, or shrink the table's font.", page=pno + 1, find=snip))
                break
    return found


def check_citations(layout):
    """IEEE-style numbering: numbers increasing inside each bracket and by first citation;
    every reference in the list cited."""
    found = []
    body, refs, in_refs = [], {}, False
    for pno, p in enumerate(layout.pages):
        for r in p["rows"]:
            t = r["text"]
            if r["kind"] == "heading" and re.fullmatch(r"(\d+\.?\s*)?(References|Bibliography)", t.strip(), re.I):
                in_refs = True
                continue
            if in_refs:
                m = re.match(r"^\W*\[(\d+)\]", t)
                if m:
                    refs[int(m.group(1))] = (pno, t)
            else:
                body.append((pno, r))
    if not refs:
        return [issue("citations", "review", "No numbered reference list found; the citation-order checks were skipped.")], set()
    nmax = max(refs)
    order, cited = [], set()
    for pno, r in body:
        # a citation group: brackets of numbers, possibly several brackets joined by commas
        # a citation group: one or more adjacent brackets; each may end with a locator ("[24, Ch. 2]")
        for m in re.finditer(r"\[\d[^\[\]]{0,60}\](?:\s*,\s*\[\d[^\[\]]{0,60}\])*", r["text"]):
            nums = []
            for bracket in re.findall(r"\[([^\[\]]*)\]", m.group(0)):
                for part in re.split(r"\s*[,;]\s*", bracket):
                    if re.fullmatch(r"\d+\s*[–-]\s*\d+", part):
                        a, b = map(int, re.split(r"\s*[–-]\s*", part))
                        nums += list(range(a, b + 1))
                    elif re.fullmatch(r"\d+", part):
                        nums.append(int(part))
                    else:
                        break  # a locator: the rest of this bracket is not reference numbers
            if not nums or max(nums) > nmax or min(nums) < 1:
                continue  # an interval like [0, 1] in prose, not a citation
            if nums != sorted(nums):
                found.append(issue("citations", "fix", f"Citation numbers out of order in {m.group(0)}: list the keys so "
                                   f"the numbers increase ({sorted(nums)}).", page=pno + 1, find=m.group(0)))
            for x in nums:
                if x not in cited:
                    order.append((x, pno, m.group(0)))
                    cited.add(x)
    expected = 1
    for x, pno, s in order:
        if x != expected:
            found.append(issue("citations", "review", f"Reference [{x}] is cited before [{expected}]: with numbering by first "
                               "citation the numbers should first appear in order (check the bibliography style).",
                               page=pno + 1, find=s))
            break
        expected += 1
    for x in sorted(set(refs) - cited):
        pno, t = refs[x]
        found.append(issue("citations", "propose", f"Reference [{x}] is in the list but never cited: cite it or remove it.",
                           page=pno + 1, find=f"[{x}]"))
    sample = [t for _, t in list(refs.values())[:5]]
    if not any(re.match(r"^\s*[^\w\s\[]", t) for t in sample):
        found.append(issue("citations", "review", "The reference list has no topic symbols (e.g. ♠ ♣ ♦ ♥ before each number) "
                           "and legend, which the author's convention asks for.",
                           page=list(refs.values())[0][0] + 1))
    return found, cited


_PARTICLE = r"(?:(?:van|von|de|der|den|du|da|di|del|le|la|ter)\s+)*"
_SURNAME = _PARTICLE + r"[A-Z][^\W\d_][\w'\u2019-]*"
_YEAR = r"(?:1[5-9]|20)\d\d[a-z]?"
# A citation in the text: "Smith (2009)", "Smith and Jones (2009)", "Smith et al. (2013a)",
# "(Smith, 2009; Jones et al., 2013)". Only the first author's surname is kept.
_JOIN = r"(?:\s*,\s*|,?\s+(?:and|&)\s+|\s*[\u2013\u2014]\s*)"  # "A, B and C", "A & B", "A\u2013B"
_GROUP = rf"(?<![\w'\u2019-])({_SURNAME})(?:{_JOIN}{_SURNAME})*(?:\s+et\s+al\.?)?(?:['\u2019]s)?"
AY_NARRATIVE = re.compile(rf"{_GROUP}\s*\(\s*({_YEAR}(?:\s*[,;]\s*{_YEAR})*)\s*\)")
AY_PAREN = re.compile(rf"{_GROUP},?\s+({_YEAR}(?:\s*,\s*{_YEAR})*)")


def check_author_year(ast):
    """For an author-year paper (a reference list of entries "Surname X, ... (2009) Title" or
    "Surname, X. ... 2009."): entries never cited, and citations with no entry. None when the
    paper is not author-year, so the numbered checks apply instead."""
    blocks, refs, body = ast["blocks"], [], []
    i = next((k for k, b in enumerate(blocks) if b["t"] == "Header" and
              re.fullmatch(r"(\d+\.?\s*)?(References|Bibliography|Literature cited)", header_title(b), re.I)), None)
    if i is None:
        return None
    end = len(blocks)
    for k, b in enumerate(blocks[i + 1:], i + 1):
        if b["t"] == "Header":
            end = k
            break
        if b["t"] in ("Para", "Plain"):
            refs.append(stringify(b["c"]).strip())
        elif b["t"] == "Div":
            refs += [stringify(x["c"]).strip() for x in b["c"][1] if x["t"] in ("Para", "Plain")]
    entries = []
    for r in refs:
        m, y = re.match(rf"\s*({_SURNAME})", r), re.search(rf"\b({_YEAR})\b", r)
        if m and y and not re.match(r"\s*\[\d+\]", r):
            entries.append((m.group(1), y.group(1), r))
    if len(entries) < max(3, 0.6 * len(refs)):
        return None
    def visit(node):
        if isinstance(node, dict):
            if node.get("t") in ("Para", "Plain"):
                body.append(stringify(node["c"]))
            elif node.get("t") == "Table":
                body.append(stringify(node["c"]))
            else:
                visit(node.get("c"))
        elif isinstance(node, list):
            for x in node:
                visit(x)
    visit(blocks[:i] + blocks[end:])  # appendices often follow the reference list
    text = re.sub(r"\s+", " ", " ".join(body))
    found = []
    for surname, year, entry in entries:
        if not re.search(rf"\b{re.escape(surname)}\b[^)]{{0,80}}?\b{year}\b", text):
            named = re.search(rf"\b{re.escape(surname)}\b", text)
            why = (f"{surname} is named but never with the year {year}" if named
                   else f"{surname} {year} does not appear in the text")
            found.append(issue("citations", "propose", f"Reference \u201c{entry[:80]}\u2026\u201d is in the list but never "
                               f"cited ({why}): cite it or remove it.", find=entry[:40]))
    known = {(a.casefold(), y) for a, y, _ in entries}
    loose = {(a.casefold(), y[:4]) for a, y, _ in entries}
    missing = {}
    for pat in (AY_NARRATIVE, AY_PAREN):
        for m in pat.finditer(text):
            for y in re.split(r"\s*[,;]\s*", m.group(2)):
                # "Shepardson\u2013Tovey" names two authors; "Cruz-Filipe" is one hyphenated surname.
                first = re.sub(r"['\u2019]s$", "", re.split(r"[\u2013\u2014]", m.group(1))[0])
                key = (first.casefold(), y)
                if key not in known and (key[0], y[:4]) not in loose:
                    missing.setdefault(f"{first} {y}", m.group(0))
    for cite, ctx in missing.items():
        found.append(issue("citations", "propose", f"\u201c{ctx[:80]}\u201d cites {cite}, which has no entry in the "
                           "reference list: add the entry or correct the citation.", find=ctx[:40]))
    return found


def check_floats_cited(layout):
    found = []
    captions, mentions = {}, set()
    for pno, p in enumerate(layout.pages):
        for r in p["rows"]:
            t = r["text"].strip()
            cap = re.match(r"^(Table|Figure|Fig\.)\s+([A-Z]?\d+)\s*[.:]", t)
            if cap:
                kind = "Table" if cap.group(1) == "Table" else "Figure"
                captions.setdefault((kind, cap.group(2)), pno)
                t = t[cap.end():]
            for m in re.finditer(r"\b(Tables?|Figures?|Figs?\.)\s+((?:[A-Z]?\d+\s*(?:,|and|–|-|to)\s*)*[A-Z]?\d+)", t):
                kind = "Table" if m.group(1).startswith("Table") else "Figure"
                for part in re.findall(r"[A-Z]?\d+\s*[–-]\s*[A-Z]?\d+|[A-Z]?\d+", m.group(2)):
                    ends = re.split(r"\s*[–-]\s*", part)
                    if len(ends) == 2:
                        pre = re.match(r"[A-Z]?", ends[0]).group(0)
                        a, b = int(ends[0].lstrip(pre)), int(ends[1].lstrip(pre))
                        mentions.update((kind, f"{pre}{i}") for i in range(a, b + 1))
                    else:
                        mentions.add((kind, part))
    for (kind, n), pno in sorted(captions.items(), key=lambda kv: kv[1]):
        if (kind, n) not in mentions:
            found.append(issue("floats-cited", "propose", f"{kind} {n} is never referred to in the text.",
                               page=pno + 1, find=f"{kind} {n}"))
    return found


def check_stranded_captions(layout):
    """A table or figure caption that is the last thing on its page has been separated from
    its table (or broken across the page)."""
    found = []
    for pno, p in enumerate(layout.pages[:-1]):
        rows = [r for r in p["rows"] if r["kind"] != "footer"]
        tail = rows[-3:]
        for i, r in enumerate(tail):
            if CAPTION.match(r["text"]) and r["text"].startswith(("Table", "Algorithm")) and \
                    all(t["kind"] in ("body", "heading") for t in tail[i + 1:]):
                found.append(issue("split-table", "fix", f"'{r['text'][:50]}…' ends page {pno + 1} while its table is on "
                                   "the next page: keep the caption with its table.", page=pno + 1, rect=r["bbox"]))
    return found


def check_consistency(ast, layout):
    """Notation that should be uniform across the paper."""
    found = []
    text = stringify(ast["blocks"])
    enote = re.findall(r"(?<![\w])-?\d+(?:\.\d+)?e[+-]?\d+\b", text)
    if enote:
        ex = list(dict.fromkeys(enote))
        found.append(issue("numbers", "propose", f"{len(enote)} numbers in computer exponent notation ({', '.join(ex[:5])}…): "
                           "write them as $a\\times10^{n}$ with a true minus sign. If they come from a script that "
                           "generates the tables, fix it there.", find=ex[0]))
    pdf_text = "".join(p.get_text() for p in layout.doc)
    marks = {c: pdf_text.count(c) for c in "□■∎◻" if pdf_text.count(c)}
    if len(marks) > 1:
        found.append(issue("maths", "review", "End-of-proof marks are mixed: " + ", ".join(f"{c} ×{n}" for c, n in marks.items())
                           + ". Use one (or one per purpose, consistently)."))
    not_ise = ("wise", "rise", "rais", "noise", "prais", "premis", "promis", "precis", "concis", "exercis", "advis",
               "devis", "surpris", "compris", "compromis", "expertis", "disguis", "revis", "supervis", "televis", "improvis")
    # At least three letters before the -is-/-iz- (organ-ise, real-ize): shorter words are not
    # spelling variants ("rising", "arise", "size", "seize").
    ise = Counter(w.lower() for w in re.findall(r"\b\w{3,}is(?:e|es|ed|ing|ation|ations)\b", text)
                  if not any(x in w.lower() for x in not_ise))
    ize = Counter(w.lower() for w in re.findall(r"\b\w{3,}iz(?:e|es|ed|ing|ation|ations)\b", text))
    if ise and ize:
        found.append(issue("spelling", "review", f"Both -ise and -ize spellings: {sum(ise.values())} -ise "
                           f"({', '.join(list(ise)[:4])}) and {sum(ize.values())} -ize ({', '.join(list(ize)[:4])}). Pick one.",
                           find=next(iter(ise))))
    return found


def check_log(layout, log_path, tex_text):
    found = []
    log = log_path.read_text(errors="replace")
    tex_lines = tex_text.splitlines()
    page = 1
    for m in re.finditer(r"\[(\d+)(?=[\s\]{<])|Overfull \\hbox \(([\d.]+)pt too wide\) (?:in paragraph|detected) at lines? (\d+)(?:--(\d+))?"
                         r"|Missing character: There is no (\S+) in font|LaTeX Warning: (Reference|Citation) `([^']+)'", log):
        if m.group(1):
            page = int(m.group(1)) + 1
        elif m.group(2):
            pts = float(m.group(2))
            if pts < 1:
                continue
            a, b = int(m.group(3)), int(m.group(4) or m.group(3))
            src = tex_plain(" ".join(tex_lines[a - 1:b]))
            found.append(issue("maths" if "\\(" in " ".join(tex_lines[a - 1:b]) or "$" in " ".join(tex_lines[a - 1:b]) else "overfull",
                               "fix", f"A line sticks {pts:.1f}pt into the margin (TeX lines {a}-{b}): \"{src[:90]}\".",
                               page=min(page, len(layout.doc)), find=" ".join(src.split()[:4]) or None))
        elif m.group(5):
            found.append(issue("maths", "fix", f"The font has no glyph for '{m.group(5)}', so it is missing from the PDF: "
                               "write it as LaTeX maths.", page=min(page, len(layout.doc))))
        elif m.group(6):
            found.append(issue("citations" if m.group(6) == "Citation" else "references", "fix",
                               f"{m.group(6)} '{m.group(7)}' is undefined.", page=min(page, len(layout.doc))))
    for lab in sorted(set(re.findall(r"LaTeX Warning: Label `([^']+)' multiply defined", log))):
        found.append(issue("references", "fix", f"Label '{lab}' is defined more than once (for a longtable, a \\label in "
                           "the repeated header is the usual cause): cross-references to it may point to the wrong place."))
    if "There were undefined references" in log or "Label(s) may have changed" in log:
        found.append(issue("references", "review", "LaTeX reports undefined or changed references after the final run; "
                           "check the cross-references."))
    for i, p in enumerate(layout.doc):
        t = p.get_text()
        for bad in re.findall(r"(?<!\\)\$[^$\n]{1,40}\$|\\(?:frac|tfrac|mathrm|le|ge|sum|cdot|in)\b", t):
            found.append(issue("maths", "fix", f"Raw maths markup '{bad}' printed as text: the conversion to LaTeX failed here.",
                               page=i + 1, find=bad))
    return found


# ---------------------------------------------------------------------------------------
# Report and annotated PDF.

def locate(page, issue_):
    if issue_.get("rect"):
        return [pymupdf.Rect(issue_["rect"])]
    if issue_.get("find"):
        hits = page.search_for(issue_["find"])
        if not hits and len(issue_["find"]) > 25:
            hits = page.search_for(issue_["find"][:25])
        return hits[:1]
    return []


def search_variants(find):
    """The phrase, then shorter windows of it: PDF text breaks lines where the source does not."""
    words = find.split()
    yield find
    for size in (3, 2):
        for i in range(len(words) - size + 1):
            yield " ".join(words[i:i + size])


def place(doc, issues):
    """Give every issue a page where it can: by searching for its text when no page is known.
    The narrowed phrase that matched replaces `find`, so the annotation lands on it."""
    for x in issues:
        if x.get("page") or not x.get("find"):
            continue
        for variant in search_variants(x["find"]):
            if len(variant) < 6:
                continue
            hits = [i for i, p in enumerate(doc) if p.search_for(variant)]
            if len(hits) == 1 or (hits and variant == x["find"]):
                x["page"], x["find"] = hits[0] + 1, variant
                break


def annotate(pdf_path, issues, out_path):
    doc = pymupdf.open(pdf_path)
    place(doc, issues)
    for x in issues:
        if not x.get("page"):
            continue
        page = doc[x["page"] - 1]
        rects = locate(page, x) or [pymupdf.Rect(page.rect.width - 60, 40, page.rect.width - 40, 60)]
        for r in rects:
            a = page.add_rect_annot(r)
            a.set_colors(stroke=COLOURS[x["severity"]])
            a.set_border(width=1.2)
            a.set_info(title=f"{SEVERITY_TEXT[x['severity']]}: {x['check']}", content=x["message"])
            a.update(opacity=0.8)
        note = page.add_text_annot(pymupdf.Point(page.rect.width - 30, max(30, rects[0].y0)), x["message"])
        note.set_info(title=f"{SEVERITY_TEXT[x['severity']]}: {x['check']}")
        note.set_colors(stroke=COLOURS[x["severity"]])
        note.update()
    doc.save(out_path, garbage=3, deflate=True)


def write_report(paper, issues, extras, out_path):
    lines = [f"# Formatter report: {paper.draft.name}", ""]
    if extras and extras.get("build"):
        lines += [f"Pages: {extras.get('pages')}, {extras['build']}.", ""]
    counts = Counter(x["severity"] for x in issues)
    lines += ["Severity: **Layout fix** = mechanical, apply and re-check; **Proposed change** = changes wording or "
              "content, author decides; **For review** = needs judgement.", "",
              "Totals: " + ", ".join(f"{SEVERITY_TEXT[s]} {counts[s]}" for s in SEVERITIES), ""]
    by_check = defaultdict(list)
    for x in issues:
        by_check[x["check"]].append(x)
    for check in sorted(by_check, key=lambda c: min(SEVERITIES.index(x["severity"]) for x in by_check[c])):
        lines.append(f"## {check} ({len(by_check[check])})")
        for x in sorted(by_check[check], key=lambda x: (x.get("page") or 0)):
            where = f"p. {x['page']}" if x.get("page") else "no page"
            sec = f", {x['section']}" if x.get("section") else ""
            lines.append(f"- [{SEVERITY_TEXT[x['severity']]}] ({where}{sec}) {x['message']}")
        lines.append("")
    if extras:
        material = json.dumps(extras, indent=1, ensure_ascii=False)
        lines += ["## Material for the agent's review", ""]
        # Never cut the JSON part-way (a truncated block cannot be parsed): point to issues.json instead.
        lines += ["```json", material, "```"] if len(material) <= 20000 else \
            [f"Too long to show here ({len(material):,} characters): read `review_material` in "
             f"`{(paper.out / 'issues.json').name}`."]
    out_path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------------------

def cmd_check(args):
    paper = Paper(args.draft, args.defaults, args.out, args.tex)
    tex, pdf, log = paper.build()
    tex_text = tex.read_text(errors="replace")
    ast = paper.ast()
    layout = Layout(pdf)
    layout.para_starts = paragraph_starts(ast)
    issues = []
    issues += check_headings(ast)
    issues += check_subsection_titles(ast, layout)
    issues += check_flat_sections(ast)
    road_issue, road = check_roadmap(ast)
    issues += road_issue
    if road:
        missing = roadmap_coverage(ast, road)
        if missing:
            issues.append(issue("roadmap", "propose", "The roadmap paragraph does not mention: " + "; ".join(missing),
                                find="rest of this paper is organised"))
        issues += check_roadmap_appendices(road)
    issues += check_numbers(ast)
    issues += check_hardcoded_refs(ast)
    issues += check_unicode_maths(ast)
    issues += check_acronyms(ast)
    notes, headings = structure_notes(ast)
    issues += notes
    issues += check_paragraphs(layout, args.max_lines, args.hard_max_lines, args.min_trim_lines)
    issues += check_space(layout)
    issues += check_tables(layout, tex_text)
    cit, _ = check_citations(layout)
    author_year = check_author_year(ast)
    if author_year is not None:  # an author-year paper: the numbered-citation checks do not apply
        cit = [x for x in cit if not x["message"].startswith("No numbered reference list")] + author_year
    issues += cit
    issues += check_floats_cited(layout)
    issues += check_stranded_captions(layout)
    issues += check_consistency(ast, layout)
    issues += check_log(layout, log, tex_text)
    extras = {"section_openings_and_closings": section_ends(ast), "maths_inventory": maths_inventory(ast),
              "headings": headings, "pages": len(layout.doc), "build": paper.build_note}
    place(layout.doc, issues)
    (paper.out / "issues.json").write_text(json.dumps({"issues": issues, "review_material": extras}, indent=1, ensure_ascii=False))
    write_report(paper, issues, extras, paper.out / "report.md")
    annotate(pdf, issues, paper.out / "annotated.pdf")
    counts = Counter(x["check"] for x in issues)
    print(paper.build_note)
    print(f"{len(layout.doc)} pages; {len(issues)} findings: " + ", ".join(f"{k} {v}" for k, v in counts.most_common()))
    print(f"report: {paper.out / 'report.md'}\nannotated PDF: {paper.out / 'annotated.pdf'}")


def cmd_annotate(args):
    paper = Paper(args.draft, args.defaults, args.out)
    data = json.loads((paper.out / "issues.json").read_text())
    extra = json.loads(Path(args.extra).read_text())
    for x in extra:
        assert x.get("severity") in SEVERITIES and x.get("message") and x.get("check"), x
        x.setdefault("page", None), x.setdefault("find", None), x.setdefault("rect", None), x.setdefault("section", None)
    issues = data["issues"] + extra
    place(pymupdf.open(paper.out / "paper.pdf"), issues)
    write_report(paper, issues, data["review_material"], paper.out / "report.md")
    annotate(paper.out / "paper.pdf", issues, paper.out / "annotated.pdf")
    print(f"{len(issues)} findings ({len(extra)} from review) -> {paper.out / 'report.md'}, {paper.out / 'annotated.pdf'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "annotate"])
    ap.add_argument("draft")
    ap.add_argument("--defaults", help="pandoc defaults file (found from the Makefile if omitted)")
    ap.add_argument("--tex", help="the .tex the author's own build produced (default: <draft>.tex beside a "
                    "Markdown draft, if it is at least as new as the draft)")
    ap.add_argument("--out", help="output folder (default: formatter/ next to the draft)")
    ap.add_argument("--max-lines", type=int, default=12, help="longest acceptable paragraph, in lines")
    ap.add_argument("--hard-max-lines", type=int, default=15,
                    help="paragraphs this long are always proposed for splitting; shorter ones over --max-lines "
                         "only if they hold more than one idea")
    ap.add_argument("--min-trim-lines", type=int, default=5,
                    help="report a short last line only for paragraphs of at least this many lines")
    ap.add_argument("--extra", help="annotate: JSON list of the agent's review items")
    args = ap.parse_args()
    {"check": cmd_check, "annotate": cmd_annotate}[args.command](args)


if __name__ == "__main__":
    main()

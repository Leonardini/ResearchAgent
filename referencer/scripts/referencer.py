#!/usr/bin/env python3
"""Referencer: tie every citation in a draft to a verbatim passage of the cited work.

Subcommands (DRAFT is a pandoc Markdown or LaTeX file):
  init    DRAFT                 add the mode toggle (final) to the draft, create evidence/
  mode    DRAFT final|verification   set the toggle
  extract DRAFT                 list every citation instance -> evidence/citations.json
  fetch   DRAFT                 download open-access full texts -> evidence/fulltext/
  add     DRAFT KEY (--download URL | FILE --url U) --version V [--ocr] [--title T]
                                install a text found by other means (the script logs its hashes)
  locate  DRAFT KEY QUOTE       check a quote against KEY's text (also for works not yet cited)
  todo    DRAFT [--key K]       print the citation instances that still need an assessment
  find    DRAFT KEY TERM...     search one full text; print matching passages with locations
  record  DRAFT KEY ID --verdict V [--quote Q]... [--note N] [--secondary] [--doubt WHY]
                                check one assessment and write it to the ledger
  check   DRAFT                 match every ledger quote against the full text; report
  build   DRAFT                 verification mode: write evidence/html/; final: nothing
  worksheet DRAFT [--import]    citations the agent could not read, for the author to tick by hand
  terms   DRAFT ID TERM...      suggest search terms for one citation, for `assist`
  keyify  DRAFT BIB             author-year draft with a typed reference list: write DRAFT_keyed.md
                                with pandoc citations against BIB (the draft is only read)
  assist  DRAFT KEY --pdf FILE  FOR THE AUTHOR, in their own terminal: check KEY's citations
                                against their own copy; the agent never sees the text

Needs pandoc (>= 3) and pdftotext (poppler). Python standard library only.
"""
import argparse
from collections import Counter
import bisect
import datetime
import hashlib
import html
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import textwrap
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

MODES = ("final", "verification")
VERDICTS = ("supported", "partial", "unsupported", "contradicted", "not-a-claim")
# Statuses an instance can have, worst first; the order sets the colour legend and summary.
STATUSES = ("error", "contradicted", "unsupported", "partial", "unchecked",
            "no-fulltext", "not-a-claim", "abstract-only", "supported")
# The statuses share six colours, so the page stays readable at a glance:
# green (supported), amber (partial), red (unsupported or contradicted), grey (not yet
# verified: no text or not checked), blue (attribution only), purple (the evidence is broken).
COLOUR = {"supported": "ok", "abstract-only": "ok", "partial": "partial", "unsupported": "bad",
          "contradicted": "bad", "unchecked": "open", "no-fulltext": "open", "not-a-claim": "attr",
          "error": "error"}
# Crossref update types that withdraw or cast doubt on a work.
RETRACTION_TYPES = ("retraction", "withdrawal", "removal", "expression_of_concern")
# What a full text is. "abstract" texts can back a verdict, but it is shown as abstract-only.
VERSIONS = ("published", "accepted", "preprint", "third-party", "abstract", "unknown")
OPENALEX_VERSION = {"publishedVersion": "published", "acceptedVersion": "accepted",
                    "submittedVersion": "preprint"}
MIN_QUOTE_CHARS = 20     # a shorter "quote" cannot carry a claim on its own
MAX_ELLIPSIS_GAP = 3000  # characters allowed between fragments joined by [...]
UA = "Referencer/0.1 (citation verification for a research manuscript)"
SKILL_DIR = Path(__file__).resolve().parent.parent

MARK_OPEN, MARK_CLOSE = "\ue000", "\ue001"
MARK_RE = re.compile(MARK_OPEN + r"(\d+)" + MARK_CLOSE)
WRAPPERS = ("Emph", "Strong", "Underline", "Strikeout", "Superscript", "Subscript", "SmallCaps")
ABBREVIATIONS = {"e.g", "i.e", "al", "cf", "vs", "fig", "figs", "eq", "eqs", "ref", "refs",
                 "sec", "no", "approx", "resp", "dr", "prof", "vol", "pp", "ch", "thm", "lem",
                 "prop", "def", "cor", "app", "tab"}


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def run(cmd, cwd=None, stdin=None):
    return subprocess.run(cmd, cwd=cwd, input=stdin, check=True, capture_output=True,
                          text=True).stdout


# ---------------------------------------------------------------------------------------
# Text normalisation: what "the quote appears verbatim in the full text" means.
# Case, ligatures, dash and quote variants, soft hyphens, hyphens (including those split
# across a line break) and whitespace are ignored; every word and its order must match.

_TRANSLATE = str.maketrans({**dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-"),
                            **dict.fromkeys(map(ord, "\u2018\u2019\u201a\u201b\u2032"), "'"),
                            **dict.fromkeys(map(ord, "\u201c\u201d\u201e\u201f\u2033"), '"'),
                            0x00ad: None})


def dehyphenate(s):
    """Undo a hyphenation split across a line break: only a true hyphen (ASCII, U+2010 or a
    soft hyphen) directly after a letter. A dash at a line end (an em dash, an en dash in a
    range, a "-" table cell, a minus sign) is a real character and stays."""
    return re.sub(r"(?<=\w)[-\u2010\u00ad][ \t]*\n\s*", "", s)


def id_text(s):
    """The citing sentence as it enters a citation's ID. Frozen at the normalisation the IDs
    were first made with: changing it would re-key every recorded assessment, so quote matching
    (normalise) may improve without touching it."""
    s = unicodedata.normalize("NFKC", s).translate(_TRANSLATE)
    s = re.sub(r"-[ \t]*\n\s*", "", s)
    s = re.sub(r"(?<=\w)-(?=\w)", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.casefold().strip()


def normalise(s):
    s = dehyphenate(unicodedata.normalize("NFKC", s)).translate(_TRANSLATE)
    # Spacing around a dash varies between a PDF's text and a quote typed on one line.
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"(?<=\w)-(?=\w)", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.casefold().strip()


# ---------------------------------------------------------------------------------------
# The draft: parsing, the toggle, citation instances.

def pandoc_meta(yaml_text):
    """Parse a YAML mapping with pandoc itself, so no YAML library is needed."""
    doc = json.loads(run(["pandoc", "-f", "markdown", "-t", "json"],
                         stdin=f"---\n{yaml_text}\n---\n"))
    return {k: meta_value(v) for k, v in doc["meta"].items()}


def meta_value(m):
    t, c = m["t"], m.get("c")
    if t == "MetaString":
        return c
    if t == "MetaBool":
        return c
    if t == "MetaInlines":
        return flatten(c)
    if t == "MetaBlocks":
        return " ".join(flatten(b["c"]) for b in c if b["t"] in ("Para", "Plain"))
    if t == "MetaList":
        return [meta_value(x) for x in c]
    if t == "MetaMap":
        return {k: meta_value(v) for k, v in c.items()}
    return None


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def flatten(inlines, cites=None):
    """Plain text of an inline list. With `cites`, each Cite becomes a numbered marker and
    the Cite node itself is appended to `cites`. Footnote text is left out here; footnotes
    are visited as blocks of their own (see text_runs)."""
    out = []
    for x in inlines:
        t, c = x["t"], x.get("c")
        if t == "Str":
            out.append(c)
        elif t in ("Space", "SoftBreak", "LineBreak"):
            out.append(" ")
        elif t in WRAPPERS:
            out.append(flatten(c, cites))
        elif t in ("Span", "Link", "Image"):
            out.append(flatten(c[1], cites))
        elif t == "Quoted":
            q = "\u201c\u201d" if c[0]["t"] == "DoubleQuote" else "\u2018\u2019"
            out.append(q[0] + flatten(c[1], cites) + q[1])
        elif t == "Code":
            out.append(c[1])
        elif t == "Math":
            out.append("$" + c[1] + "$")
        elif t == "Cite":
            if cites is None:
                out.append(cite_label(c[0]))
            else:
                out.append(f"{MARK_OPEN}{len(cites)}{MARK_CLOSE}")
                cites.append(x)
    return "".join(out)


def cite_keys(cite_node):
    return [c["citationId"] for c in cite_node["c"][0]]


def cite_label(citations):
    return "[" + "; ".join("@" + c["citationId"] for c in citations) + "]"


def notes(inlines):
    for x in inlines:
        t, c = x["t"], x.get("c")
        if t == "Note":
            yield c
        elif t in WRAPPERS:
            yield from notes(c)
        elif t in ("Span", "Link", "Image", "Quoted"):
            yield from notes(c[1])


def table_rows(c):
    """Rows of a pandoc Table node, header first, each a list of cells' block lists."""
    _, caption, _, head, bodies, foot = c
    rows = list(head[1])
    for body in bodies:
        rows += body[2] + body[3]
    rows += foot[1]
    return caption, [[cell[4] for cell in row[1]] for row in rows]


def blocks_text(blocks):
    return " ".join(flatten(r) for _, r, _ in text_runs(blocks)).strip()


def text_runs(node, ctx=None):
    """Yield (block type, inline list, context) for every run of text in document order; the
    paragraphs of a footnote follow the paragraph that holds the footnote mark. A table cell's
    context is its whole row (and the header), since a cited cell alone ("[3]") says nothing."""
    if isinstance(node, list):
        for x in node:
            yield from text_runs(x, ctx)
        return
    if not isinstance(node, dict):
        return
    t = node.get("t")
    if t == "Table":
        caption, rows = table_rows(node["c"])
        yield from text_runs(caption[1], ctx)
        header = " | ".join(blocks_text(cell) for cell in rows[0]) if rows else ""
        for row in rows:
            row_text = " | ".join(blocks_text(cell) for cell in row)
            for cell in row:
                yield from text_runs(cell, f"Table row: {row_text} (columns: {header})")
        return
    if t in ("Para", "Plain"):
        runs = [node["c"]]
    elif t == "Header":
        runs = [node["c"][2]]
    elif t == "LineBlock":
        runs = node["c"]
    elif t in ("CodeBlock", "RawBlock", "HorizontalRule"):
        return
    else:
        yield from text_runs(node.get("c"), ctx)
        return
    for r in runs:
        yield t, r, ctx
        for note in notes(r):
            yield from text_runs(note)


def latex_captions(tex):
    """The text of every \\caption[...]{...} in a raw LaTeX block, braces matched."""
    out = []
    for m in re.finditer(r"\\caption\s*(?:\[[^\]]*\])?\s*\{", tex):
        depth, i = 1, m.end()
        while i < len(tex) and depth:
            depth += {"{": 1, "}": -1}.get(tex[i], 0) if tex[i - 1] != "\\" else 0
            i += 1
        if depth == 0:
            out.append(tex[m.end():i - 1])
    return out


def expand_raw_captions(blocks, paper):
    """After each raw LaTeX block holding a \\caption, insert the caption as a paragraph, parsed
    as Markdown (with \\cite{a,b} read as [@a; @b]), so its citations are instances like any
    other. A citation there is also a warning: in a Markdown draft citeproc never sees raw
    LaTeX, so `[@key]` prints literally and `\\cite{key}` stays unresolved in the final PDF."""
    out = []
    for b in blocks:
        if isinstance(b, dict) and b.get("t") == "Div":
            b["c"][1] = expand_raw_captions(b["c"][1], paper)
        out.append(b)
        if not (isinstance(b, dict) and b.get("t") == "RawBlock" and b["c"][0] in ("latex", "tex")):
            continue
        for cap in latex_captions(b["c"][1]):
            md = re.sub(r"\\cite[tp]?\*?\s*(?:\[[^\]]*\])*\{([^}]*)\}",
                        lambda m: "[" + "; ".join("@" + k.strip() for k in m.group(1).split(",")) + "]", cap)
            parsed = json.loads(run(["pandoc", "-f", "markdown", "-t", "json"], cwd=paper.root, stdin=md))
            inlines = [x for blk in parsed["blocks"] if blk["t"] in ("Para", "Plain") for x in blk["c"] + [{"t": "Space"}]]
            if not inlines:
                continue
            keys = [k for x in inlines if x.get("t") == "Cite" for k in cite_keys(x)]
            if keys:
                paper.raw_caption_warnings.append(
                    f"raw LaTeX caption cites {', '.join('@' + k for k in keys)}: checked here, but citeproc "
                    f"does not see raw LaTeX, so the final PDF will not resolve it (\"{cap[:60]}…\")")
            out.append({"t": "Para", "c": [{"t": "Span", "c": [["", ["raw-caption"], []],
                                                              [{"t": "Strong", "c": [{"t": "Str", "c": "Caption:"}]},
                                                               {"t": "Space"}] + inlines[:-1]]}]})
    return out


_BOUNDARY = re.compile(r"[.!?][\"\u201d\u2019)\]]*\s+")


def sentences(text):
    out, start = [], 0
    for m in _BOUNDARY.finditer(text):
        nxt = text[m.end():m.end() + 1]
        if not (nxt.isupper() or nxt.isdigit() or nxt in "\u201c\"\u2018([$" + MARK_OPEN):
            continue
        if text[m.start()] == ".":
            word = re.search(r"([\w.]+)$", text[start:m.start()])
            w = word.group(1).lower() if word else ""
            if w in ABBREVIATIONS or (len(w) == 1 and w.isalpha()):
                continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    if text[start:].strip():
        out.append(text[start:].strip())
    return out


def render_markers(s, cites, target=None):
    """Replace cite markers by "[@key]" labels; return the text and the target's span."""
    span, out = None, ""
    last = 0
    for m in MARK_RE.finditer(s):
        out += s[last:m.start()]
        label = cite_label(cites[int(m.group(1))]["c"][0])
        if target is not None and int(m.group(1)) == target:
            span = [len(out), len(out) + len(label)]
        out += label
        last = m.end()
    out += s[last:]
    return re.sub(r"\s+", " ", out), span


class Paper:
    def __init__(self, draft, defaults=None, evidence=None):
        self.draft = Path(draft).expanduser().resolve()
        self.root = self.draft.parent
        self.is_tex = self.draft.suffix.lower() == ".tex"
        self.defaults = self._find_defaults(defaults)
        self.ev = Path(evidence).resolve() if evidence else self.root / "evidence"
        self.fulltext = self.ev / "fulltext"
        self.ledger_dir = self.ev / "ledger"
        self.html_dir = self.ev / "html"
        cmd = ["pandoc", str(self.draft), "-t", "json"]
        if self.defaults.get("from") and not self.is_tex:
            cmd += ["-f", self.defaults["from"]]
        self.ast = json.loads(run(cmd, cwd=self.root))
        self.meta = {k: meta_value(v) for k, v in self.ast["meta"].items()}
        # Markdown drafts often carry figures as raw LaTeX, which pandoc leaves unparsed, so
        # the citations in their captions would be missed. Each caption becomes a visible
        # paragraph after its block (the HTML drops raw LaTeX anyway).
        self.raw_caption_warnings = []
        if not self.is_tex:
            self.ast["blocks"] = expand_raw_captions(self.ast["blocks"], self)

    def _find_defaults(self, given):
        """A pandoc defaults file supplies the reader options and the bibliography when the
        draft itself does not. Given explicitly, or the one a Makefile in the draft's folder
        passes with --defaults."""
        path = Path(given).expanduser().resolve() if given else None
        if path is None and (self.root / "Makefile").exists():
            m = re.search(r"--defaults[= ](\S+)", (self.root / "Makefile").read_text())
            if m and (self.root / m.group(1)).exists():
                path = self.root / m.group(1)
        if path is None:
            return {}
        return pandoc_meta(path.read_text())

    @property
    def mode(self):
        if self.is_tex:
            src = "\n".join(re.sub(r"(?<!\\)%.*", "", l) for l in self.draft.read_text().splitlines())
            found = re.findall(r"\\referencermode\{(\w+)\}", src)
            val = found[-1] if found else "final"
        else:
            val = str(self.meta.get("referencer", "final")).strip()
        if val not in MODES:
            sys.exit(f"Toggle value '{val}' is not one of {MODES}")
        return val

    @property
    def bibs(self):
        files = as_list(self.meta.get("bibliography")) or as_list(self.defaults.get("bibliography"))
        if self.is_tex and not files:
            src = self.draft.read_text()
            for grp in re.findall(r"\\(?:bibliography|addbibresource)\{([^}]+)\}", src):
                files += [f if f.endswith(".bib") else f + ".bib" for f in grp.split(",")]
        if not files:
            sys.exit("No bibliography found: set `bibliography:` in the draft or a defaults file")
        return [(self.root / f).resolve() for f in files]

    @property
    def csl(self):
        c = self.meta.get("csl") or self.defaults.get("csl")
        return (self.root / c).resolve() if c else None

    def instances(self):
        """Every citation instance in document order, each with its Cite node in the AST.
        The ID hashes the citing sentence and the keys, so it changes when the claim does."""
        out, seen, section = [], {}, ""
        for kind, inlines, ctx in text_runs(self.ast["blocks"]):
            cites = []
            text = flatten(inlines, cites)
            if kind == "Header":
                section = render_markers(text, cites)[0]
            if not cites:
                continue
            sents = sentences(text)
            for n, node in enumerate(cites):
                marker = f"{MARK_OPEN}{n}{MARK_CLOSE}"
                i = next(j for j, s in enumerate(sents) if marker in s)
                sentence, span = render_markers(sents[i], cites, target=n)
                keys = cite_keys(node)
                # Marking the target inside the sentence keeps two citations of one sentence
                # apart: deleting one never hands its assessment to the other.
                marked = sentence[:span[0]] + "⟦" + sentence[span[0]:span[1]] + "⟧" + sentence[span[1]:]
                base = hashlib.sha1(f"{id_text(marked)}|{','.join(keys)}".encode()).hexdigest()[:10]
                seen[base] = seen.get(base, 0) + 1
                iid = base if seen[base] == 1 else f"{base}-{seen[base]}"
                out.append({
                    "n": len(out) + 1, "id": iid, "keys": keys, "section": section,
                    "before": ctx or render_markers(" ".join(sents[max(0, i - 2):i]), cites)[0],
                    "sentence": sentence, "target": span,
                    "after": render_markers(sents[i + 1], cites)[0] if i + 1 < len(sents) else "",
                    "_node": node,
                })
        return out

    def bib_entries(self):
        entries = {}
        for bib in self.bibs:
            for e in json.loads(run(["pandoc", str(bib), "-f", "biblatex", "-t", "csljson"])):
                entries[e["id"]] = e
            raw = bib.read_text()
            for chunk in re.split(r"(?=@\w+\s*\{)", raw):
                m = re.match(r"@\w+\s*\{\s*([^,\s]+)\s*,", chunk)
                if not m or m.group(1) not in entries:
                    continue
                for field in ("eprint", "pmid", "pmcid"):
                    f = re.search(rf"\b{field}\s*=\s*[{{\"]([^}}\"]+)", chunk, re.I)
                    if f:
                        entries[m.group(1)].setdefault("_" + field, f.group(1).strip())
        return entries

    def ledger(self, key):
        p = self.ledger_dir / f"{key}.json"
        return json.loads(p.read_text()) if p.exists() else {}


def public(inst):
    return {k: v for k, v in inst.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------------------
# Full texts: one text file per key, page (or section) chunks separated by form feeds,
# with a sidecar listing each chunk's label.

class FullText:
    def __init__(self, paper, key):
        self.key = key
        self.txt = paper.fulltext / f"{key}.txt"
        meta = json.loads((paper.fulltext / f"{key}.json").read_text())
        self.is_pdf = meta["format"] == "pdf"
        self.version = meta.get("version", "unknown")
        self.source, self.url = meta.get("source"), meta.get("url")
        self.chunks = self.txt.read_text().split("\f")
        self.labels = meta["labels"]
        assert len(self.labels) == len(self.chunks), \
            f"{key}: {len(self.labels)} labels for {len(self.chunks)} chunks; rerun fetch --refresh"
        self._index()

    @classmethod
    def from_chunks(cls, key, chunks, labels):
        """A text held only in memory (the author's own copy in `assist`), never on disk."""
        ft = cls.__new__(cls)
        ft.key, ft.chunks, ft.labels, ft.txt, ft.is_pdf, ft.version = key, chunks, labels, None, True, "published"
        ft.source = ft.url = None
        ft._index()
        return ft

    def _index(self):
        normed = [normalise(c) for c in self.chunks]
        self.starts, pos = [], 0
        for c in normed:
            self.starts.append(pos)
            pos += len(c) + 1
        self.text = " ".join(normed)

    @staticmethod
    def available(paper, key):
        return (paper.fulltext / f"{key}.txt").exists() and (paper.fulltext / f"{key}.json").exists()

    def chunk_of(self, offset):
        return bisect.bisect_right(self.starts, offset) - 1

    def locate(self, quote):
        """Chunk index where the quote starts, or an error message. Fragments joined by
        [...] must appear in order, each within MAX_ELLIPSIS_GAP of the previous one."""
        frags = [normalise(f) for f in re.split(r"\s*\[(?:\.\.\.|\u2026)\]\s*", quote) if f.strip()]
        if not frags or sum(len(f) for f in frags) < MIN_QUOTE_CHARS:
            return None, f"quote shorter than {MIN_QUOTE_CHARS} characters"
        first, pos = None, 0
        for f in frags:
            i = self.text.find(f, pos)
            if i < 0 or (first is not None and i - pos > MAX_ELLIPSIS_GAP):
                return None, "quote not found in the full text"
            first = i if first is None else first
            pos = i + len(f)
        return self.chunk_of(first), None


def http_get(url, accept=None, timeout=30, retries=3):
    """GET with a back-off on HTTP 429 (rate limit); every other failure is raised."""
    headers = {"User-Agent": UA}
    if accept:
        headers["Accept"] = accept
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == retries:
                raise
            time.sleep(2 ** (attempt + 1))


def landing_pdf_url(page_bytes, base):
    """The PDF link an HTML landing page declares in its citation_pdf_url meta tag
    (HAL, DSpace, OJS, most publishers)."""
    m = re.search(rb"<meta[^>]+name=[\"']citation_pdf_url[\"'][^>]+content=[\"']([^\"']+)", page_bytes, re.I) \
        or re.search(rb"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+name=[\"']citation_pdf_url", page_bytes, re.I)
    return urllib.parse.urljoin(base, html.unescape(m.group(1).decode())) if m else None


def get_json(url):
    return json.loads(http_get(url, accept="application/json"))


NETWORK_ERRORS = (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError)


def arxiv_id(entry):
    for s in (entry.get("_eprint", ""), entry.get("DOI", ""), entry.get("URL", "")):
        m = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})", s)
        if m and ("arxiv" in s.lower() or s == entry.get("_eprint")):
            return m.group(1)
    return None


def candidates(entry, attempts):
    """Yield (source, kind, url, version), the version of record first, querying each
    index lazily."""
    aid = arxiv_id(entry)
    doi = entry.get("DOI")
    if not doi:
        if aid:
            yield "arXiv", "pdf", f"https://arxiv.org/pdf/{aid}", "preprint"
        if entry.get("title"):
            q = urllib.parse.quote(entry["title"])
            try:
                hits = get_json(f"https://api.openalex.org/works?search={q}&per-page=3")["results"]
            except NETWORK_ERRORS as e:
                attempts.append(f"OpenAlex title search: {e}")
                hits = []
            for h in hits:
                for loc in [h.get("best_oa_location")] + h.get("locations", []):
                    if loc and loc.get("pdf_url"):
                        yield ("OpenAlex (title search)", "pdf", loc["pdf_url"],
                               OPENALEX_VERSION.get(loc.get("version"), "unknown"))
        return
    qdoi = urllib.parse.quote(doi)
    later = []
    try:
        w = get_json(f"https://api.openalex.org/works/https://doi.org/{qdoi}")
        oa_url = (w.get("open_access") or {}).get("oa_url")
        if oa_url and oa_url.lower().endswith(".pdf"):
            later.append(("OpenAlex (open-access URL)", "pdf", oa_url, "unknown"))
        for loc in [w.get("best_oa_location")] + w.get("locations", []):
            if not loc:
                continue
            version = OPENALEX_VERSION.get(loc.get("version"), "unknown")
            landing = loc.get("landing_page_url") or ""
            if loc.get("pdf_url"):
                item = ("OpenAlex", "pdf", loc["pdf_url"], version)
                if version == "published":
                    yield item
                else:
                    later.append(item)
            if "arxiv.org/abs/" in landing:
                later.append(("arXiv (via OpenAlex)", "pdf", landing.replace("/abs/", "/pdf/"), "preprint"))
    except NETWORK_ERRORS as e:
        attempts.append(f"OpenAlex: {e}")
    email = os.environ.get("UNPAYWALL_EMAIL")  # set only by the user: it sends their address
    if email:
        try:
            u = get_json(f"https://api.unpaywall.org/v2/{qdoi}?email={urllib.parse.quote(email)}")
            for loc in u.get("oa_locations") or []:
                if loc.get("url_for_pdf"):
                    yield ("Unpaywall", "pdf", loc["url_for_pdf"],
                           OPENALEX_VERSION.get(loc.get("version"), "unknown"))
        except NETWORK_ERRORS as e:
            attempts.append(f"Unpaywall: {e}")
    pmcid = None
    try:
        r = get_json("https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json"
                     f"&resultType=core&query=DOI:%22{qdoi}%22")["resultList"]["result"]
        if r:
            pmcid = r[0].get("pmcid") if r[0].get("isOpenAccess") == "Y" else None
            for u in (r[0].get("fullTextUrlList") or {}).get("fullTextUrl", []):
                if u.get("documentStyle") == "pdf" and u.get("availabilityCode") in ("OA", "F"):
                    yield "Europe PMC", "pdf", u["url"], "published"
    except NETWORK_ERRORS as e:
        attempts.append(f"Europe PMC: {e}")
    if pmcid:
        yield ("Europe PMC (XML)", "xml",
               f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML", "published")
    yield "DOI landing page", "pdf", f"https://doi.org/{doi}", "published"
    yield from later
    if aid:
        yield "arXiv", "pdf", f"https://arxiv.org/pdf/{aid}", "preprint"
    try:
        time.sleep(1)
        s = get_json(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{qdoi}?fields=openAccessPdf,externalIds")
        ext = s.get("externalIds") or {}
        if ext.get("ArXiv") and not aid:
            yield "arXiv (via Semantic Scholar)", "pdf", f"https://arxiv.org/pdf/{ext['ArXiv']}", "preprint"
        if ext.get("PubMedCentral") and not pmcid:
            yield ("Europe PMC (XML, via Semantic Scholar)", "xml", "https://www.ebi.ac.uk/europepmc/webservices/"
                   f"rest/PMC{ext['PubMedCentral'].removeprefix('PMC')}/fullTextXML", "published")
        if (s.get("openAccessPdf") or {}).get("url"):
            yield "Semantic Scholar", "pdf", s["openAccessPdf"]["url"], "unknown"
    except NETWORK_ERRORS as e:
        attempts.append(f"Semantic Scholar: {e}")


def pdf_chunks(pdf):
    text = run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"])
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages, [f"p. {i + 1}" for i in range(len(pages))]


def xml_chunks(xml_bytes):
    root = ET.fromstring(xml_bytes)
    chunks, labels = [], []
    abstract = root.find(".//abstract")
    if abstract is not None:
        chunks.append(" ".join(abstract.itertext()))
        labels.append("Abstract")
    body = root.find(".//body")
    loose = [" ".join(c.itertext()) for c in (body if body is not None else []) if c.tag != "sec"]
    if any(t.strip() for t in loose):  # short articles often have no sections at all
        chunks.append(" ".join(loose))
        labels.append("Body")
    for sec in (body.findall("sec") if body is not None else []):
        title = sec.findtext("title") or "Section"
        chunks.append(" ".join(sec.itertext()))
        labels.append("\u00a7 " + " ".join(title.split()))
    return chunks, labels


def title_matches(title, text, strict=False):
    """Does the start of a full text show this title? `strict` (used for hits found by
    title search, which have no DOI to anchor them) demands the whole title verbatim."""
    head = normalise(text[:20000])
    if strict:
        return bool(title) and normalise(title) in head
    words = [w for w in re.findall(r"\w+", normalise(title or "")) if len(w) > 3]
    if not words:
        return True
    return sum(w in head for w in words) / len(words) >= 0.7


# ---------------------------------------------------------------------------------------
# Download log: every file that enters fulltext/ gets its MD5 and SHA-256 appended to
# evidence/hashes.log, and `check` recomputes them. The log is append-only on macOS (the
# user-append flag, which only an explicit `chflags nouappnd` lifts), and each line carries
# the SHA-256 of the line before it, so editing or deleting a line breaks the chain. A text
# altered after download, by anyone, then fails the check.

LOG_HEADER = ("# Referencer download log. Append-only: never edit, truncate or delete.\n"
              "# time\tkey\tfile\tmd5\tsha256\tsource\turl\tsha256 of the previous line\n")


def digests(path):
    data = path.read_bytes()
    return hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest()


def line_hash(line):
    return hashlib.sha256(line.encode()).hexdigest()


def protect(path):
    """Set the macOS user append-only flag (a no-op where chflags does not exist)."""
    if hasattr(os, "chflags"):
        flags = os.stat(path).st_flags
        if not flags & (stat.UF_APPEND | stat.SF_APPEND):
            os.chflags(path, flags | stat.UF_APPEND)


def log_files(paper, key, files, source, url, names=None):
    path = paper.ev / "hashes.log"
    if not path.exists():
        path.write_text(LOG_HEADER)
    prev = line_hash(path.read_text().splitlines()[-1])
    with open(path, "a") as f:  # O_APPEND: the only kind of write the flag allows
        for fp in files:
            md5, sha = digests(fp)
            line = "\t".join([datetime.datetime.now().isoformat(timespec="seconds"), key,
                              (names or {}).get(fp, fp.name),
                              md5, sha, source or "", url or "", prev])
            f.write(line + "\n")
            prev = line_hash(line)
    protect(path)


def read_log(paper):
    """Latest logged (md5, sha256) per file name, and any break in the chain."""
    path = paper.ev / "hashes.log"
    if not path.exists():
        return {}, [], None
    lines = path.read_text().splitlines()
    latest, problems = {}, []
    prev = None
    for n, line in enumerate(lines, 1):
        if line.startswith("#"):
            prev = line_hash(line)
            continue
        f = line.split("\t")
        if len(f) != 8 or f[7] != prev:
            problems.append(f"hashes.log line {n} does not chain to the line before it: the log was edited")
        else:
            latest[f[2]] = (f[3], f[4])
        prev = line_hash(line)
    flags = getattr(os.stat(path), "st_flags", 0)
    warning = None if flags & (stat.UF_APPEND | stat.SF_APPEND) else \
        "hashes.log is not append-only (its flag was lifted, or this system has no chflags)"
    return latest, problems, warning


def integrity(paper, key, logged):
    """Why KEY's stored text cannot be trusted, or None. A file with no extracted text beside it
    (a PDF waiting to be fetched, or one the licence check refused) has not been read, so there
    is nothing to distrust yet."""
    if not (paper.fulltext / f"{key}.txt").exists():
        return None
    for name in (f"{key}.txt", f"{key}.json", f"{key}.pdf", f"{key}.xml", f"{key}.scan.pdf",
                 f"{key}.download.txt"):
        fp = paper.fulltext / name
        if not fp.exists():
            continue
        if name not in logged:
            return f"{name} is not in hashes.log, so its origin is unknown"
        if digests(fp) != logged[name]:
            return f"{name} differs from the file logged when it was obtained (hashes.log)"
    return None


def save_text(paper, key, chunks, labels, fmt, source, url, version, original=None):
    """Store a text, its metadata, and log the hashes of both and of the original file."""
    assert version in VERSIONS, version
    (paper.fulltext / f"{key}.txt").write_text("\f".join(chunks))
    (paper.fulltext / f"{key}.json").write_text(json.dumps(
        {"format": fmt, "labels": labels, "source": source, "url": url, "version": version}, indent=1))
    files = ([original] if original else []) + [paper.fulltext / f"{key}.txt", paper.fulltext / f"{key}.json"]
    log_files(paper, key, files, source, url)


def licence_tool():
    """The papers plugin's `license-check`, if installed (on PATH while the plugin is loaded)."""
    found = shutil.which("license-check")
    if found:
        return found
    cands = sorted(Path.home().glob(".claude/plugins/cache/*/papers/*/bin/license-check"))
    return str(cands[-1]) if cands else None


def licence(target, doi=None):
    """What the licence of a PDF, DOI or arXiv ID allows, from `license-check`. Returns None when
    the tool is not installed; otherwise its JSON verdict plus "refused": True when no licence
    lets the full text go to an AI service (a subscription copy) and the user has not allowed it.
    The rule is the user's: such a text is never extracted for the agent to read."""
    tool = licence_tool()
    if not tool:
        return None
    r = subprocess.run([tool, "check", str(target), "--json"], capture_output=True, text=True, timeout=120)
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"refused": True, "why": f"license-check gave no verdict: {r.stderr.strip()[:200]}"}
    out["refused"] = r.returncode == 3
    # A PDF the check cannot identify ("silent": a repository cover page can hide the
    # publisher's marks) is judged by the work's DOI instead.
    if out.get("verdict") == "silent" and doi and str(target) != doi:
        return licence(doi)
    return out


def licence_recheck(paper, key, entry):
    """Check the licence of a text already held (fetched before the check existed, or by an
    older version). A refused text is withdrawn: its extracted text is deleted so no agent can
    read it, the original stays, and the citation goes back on the worksheet."""
    meta_path = paper.fulltext / f"{key}.json"
    if meta_path.exists() and json.loads(meta_path.read_text()).get("version") == "abstract":
        return {"licence": "abstract only (title, abstract and short quotes are always usable)"}
    pdf = paper.fulltext / f"{key}.pdf"
    target = pdf if pdf.exists() else entry.get("DOI")
    v = licence(target, entry.get("DOI")) if target else None
    if v is None:
        return {"licence": "not checked (license-check is not installed)" if target else "not checked (no PDF or DOI)"}
    if not v["refused"]:
        return {"licence": "allowed" + (f" ({v.get('rights')})" if v.get("rights") else "")}
    (paper.fulltext / f"{key}.txt").unlink(missing_ok=True)
    log(f"{key}: withdrawn after a licence check: {refusal_text(v)}")
    return {"status": "refused", "licence": "refused", "why": refusal_text(v)}


def refusal_text(v):
    """Why license-check refused a text, in its own terms: a subscription copy, or a manuscript
    under review (a referee copy, or a PDF without DOI or arXiv number in a refereeing folder)."""
    if v.get("class") == "review":
        return f"treated as a manuscript under review ({v.get('why') or 'review marker'}): confidential, not read"
    who = v.get("publisher_name") or "the publisher"
    return f"subscription copy ({who}): its licence does not allow the full text to be read by an AI service"


def fetch_one(paper, key, entry, refresh):
    attempts = []
    pdf = paper.fulltext / f"{key}.pdf"
    meta_path = paper.fulltext / f"{key}.json"
    if FullText.available(paper, key) and not refresh:
        return {"status": "ok", **json.loads(meta_path.read_text())}
    if refresh and meta_path.exists() and pdf.exists() and \
            json.loads(meta_path.read_text()).get("source") not in ("manual", "added by hand"):
        pdf.unlink()  # our own earlier download: fetch it again rather than treat it as a drop-in
    if pdf.exists():  # dropped in by hand, or downloaded earlier
        v = licence(pdf, entry.get("DOI"))
        if v and v["refused"]:
            return {"status": "refused", "why": refusal_text(v), "tried": [f"{pdf.name}: {refusal_text(v)}"],
                    "open_copies": v.get("copies", [])}
        chunks, labels = pdf_chunks(pdf)
        save_text(paper, key, chunks, labels, "pdf", "manual", None, "unknown", original=pdf)
        warn = None if title_matches(entry.get("title"), "".join(chunks[:2])) else \
            "title words not found on the first pages: check this is the right paper"
        return {"status": "ok", "source": "manual", "version": "unknown", "warning": warn}
    tried = set()
    for source, kind, url, version in candidates(entry, attempts):
        if url in tried:
            continue
        tried.add(url)
        try:
            data = http_get(url)
            if kind == "pdf" and not data.startswith(b"%PDF"):
                inner = landing_pdf_url(data, url)
                if inner and inner not in tried:
                    tried.add(inner)
                    url, data = inner, http_get(inner)
        except NETWORK_ERRORS as e:
            attempts.append(f"{source} {url}: {e}")
            continue
        if kind == "pdf":
            if not data.startswith(b"%PDF"):
                attempts.append(f"{source} {url}: not a PDF (landing page without a usable PDF link)")
                continue
            pdf.write_bytes(data)
            v = licence(pdf, entry.get("DOI"))
            if v and v["refused"]:
                pdf.unlink()
                attempts.append(f"{source} {url}: {refusal_text(v)}; deleted unread")
                continue
            chunks, labels = pdf_chunks(pdf)
            original = pdf
        else:
            original = paper.fulltext / f"{key}.xml"
            original.write_bytes(data)
            chunks, labels = xml_chunks(data)
        if not title_matches(entry.get("title"), "".join(chunks[:2]), strict="title search" in source):
            attempts.append(f"{source} {url}: downloaded file does not show this title")
            original.unlink(missing_ok=True)
            continue
        if "arxiv.org/" in url:  # indexes sometimes point at the arXiv copy as if it were published
            version = "preprint"
            source = source if source.startswith("arXiv") else f"arXiv (via {source})"
        save_text(paper, key, chunks, labels, kind, source, url, version, original=original)
        return {"status": "ok", "source": source, "url": url, "version": version, "tried": attempts}
    return {"status": "missing", "tried": attempts}


# ---------------------------------------------------------------------------------------
# Assessment: join instances, ledger and full texts into a status per instance.

def assess(paper, inst, texts, tainted, retracted=None, withdrawn=()):
    return assess_entry(paper, inst, texts, {k: paper.ledger(k).get(inst["id"]) for k in inst["keys"]},
                        tainted, retracted, withdrawn)


def assess_entry(paper, inst, texts, entries, tainted, retracted=None, withdrawn=()):
    per_key, problems, doubts = [], [], []
    for key in inst["keys"]:
        entry = entries.get(key)
        if key in withdrawn and entry and entry.get("checked_by") != "author":
            entry = None  # the agent's verdict rested on a text its licence did not allow it to read
        if key in tainted:
            problems.append(f"@{key}: {tainted[key]}")
        has_text = key in texts
        notice = (retracted or {}).get(key)
        if entry is None:
            per_key.append({"key": key, "verdict": "unchecked" if has_text else "no-fulltext",
                            "abstract": has_text and texts[key].version == "abstract", "retracted": notice})
            continue
        v = entry.get("verdict")
        res = {"key": key, "verdict": v, "note": entry.get("note", ""), "retracted": notice,
               "secondary": entry.get("secondary", False), "passages": [],
               "by_author": entry.get("checked_by") == "author"}
        if entry.get("doubt"):
            doubts.append(entry["doubt"])
        pinned = entry.get("text_sha256")
        if has_text and pinned and pinned != digests(texts[key].txt)[1]:
            problems.append(f"@{key}: the text was replaced after this assessment was recorded; re-check it")
        if has_text and texts[key].version == "abstract" and v in ("partial", "unsupported"):
            problems.append(f"@{key}: only the abstract was read, and an abstract cannot show that a claim is "
                            f"not (fully) supported; leave it unrecorded so it is listed for retrieval")
        if v == "supported" and has_text and texts[key].version == "abstract" and not res["by_author"]:
            res["verdict"] = "abstract-only"
        if v not in VERDICTS:
            problems.append(f"@{key}: verdict '{v}' is not one of {VERDICTS}")
        if v in ("supported", "partial", "contradicted") and not entry.get("passages") and not res["by_author"]:
            problems.append(f"@{key}: verdict '{v}' needs at least one passage")
        if v != "supported" and not entry.get("note") and not res["by_author"]:
            problems.append(f"@{key}: verdict '{v}' needs a note saying why")
        for p in entry.get("passages", []):
            if res["by_author"]:
                res["passages"].append({"quote": p["quote"], "label": f"{p.get('page', '')} of the author's copy"})
                continue
            if not has_text:
                problems.append(f"@{key}: passage given but there is no full text to check it against")
                res["passages"].append({"quote": p["quote"], "error": "no full text"})
                continue
            chunk, err = texts[key].locate(p["quote"])
            if err:
                problems.append(f"@{key}: {err}: \"{p['quote'][:80]}\"")
                res["passages"].append({"quote": p["quote"], "error": err})
            else:
                res["passages"].append({"quote": p["quote"], "chunk": chunk,
                                        "label": texts[key].labels[chunk]})
        per_key.append(res)
    verdicts = {r["verdict"] for r in per_key}
    if problems:
        status = "error"
    elif verdicts == {"supported"}:
        status = "supported"
    elif verdicts <= {"supported", "abstract-only"}:
        status = "abstract-only"
    elif "contradicted" in verdicts:
        status = "contradicted"
    elif "unchecked" in verdicts:
        status = "unchecked"
    elif verdicts <= {"not-a-claim"}:
        status = "not-a-claim"
    elif verdicts <= {"no-fulltext"}:
        status = "no-fulltext"
    elif verdicts & {"supported", "abstract-only", "partial"}:
        status = "partial"
    else:
        status = "unsupported"
    # Each key's own status, so that one weak citation in "[3, 5, 8]" is marked on its own.
    for r in per_key:
        r["status"] = "error" if any(p.startswith(f"@{r['key']}:") for p in problems) else \
            r["verdict"] if r["verdict"] in STATUSES else "error"
    return {"status": status, "per_key": per_key, "problems": problems, "doubts": doubts}


def sources_of(paper):
    p = paper.ev / "sources.json"
    return json.loads(p.read_text()) if p.exists() else {}


def evaluate(paper):
    insts = paper.instances()
    keys = sorted({k for i in insts for k in i["keys"]})
    logged, log_problems, log_warning = read_log(paper)
    tainted = {k: why for k in keys if (why := integrity(paper, k, logged))}
    # A text that fails its hash is never parsed or quoted from.
    texts = {k: FullText(paper, k) for k in keys if FullText.available(paper, k) and k not in tainted}
    sources = sources_of(paper)
    retracted = {k: notice_text(s["retraction"]) for k, s in sources.items()
                 if (s.get("retraction") or {}).get("retracted")}
    withdrawn = {k for k, s in sources.items() if s.get("status") == "refused"}
    results = {i["id"]: assess(paper, i, texts, tainted, retracted, withdrawn) for i in insts}
    live = {i["id"] for i in insts}
    stale = {k: sorted(set(paper.ledger(k)) - live) for k in keys}
    paper.log_report = (log_problems, log_warning)
    return insts, results, {k: v for k, v in stale.items() if v}


def to_retrieve(paper, insts, results, entries):
    """Works whose text is still needed, most important first: those with no text, and those
    read only as an abstract that did not settle every claim citing them. Importance is the
    number of claims (not attributions) resting on the work."""
    need = {}
    for i in insts:
        for r in results[i["id"]]["per_key"]:
            waiting = r["verdict"] == "no-fulltext" or (r.get("abstract") and r["verdict"] == "unchecked")
            if waiting:
                n = need.setdefault(r["key"], {"key": r["key"], "claims": 0, "first": i["section"],
                                               "abstract": bool(r.get("abstract")), "instances": []})
                n["claims"] += 1
                n["instances"].append(public(i))
    sources = sources_of(paper)
    for n in need.values():
        st = sources.get(n["key"], {})
        n["why"] = st.get("why") or ("only the abstract is open, and it does not settle the claim" if n["abstract"]
                                     else "no open copy found" if st.get("status") == "missing" else "not fetched yet")
    out = []
    for n in sorted(need.values(), key=lambda n: -n["claims"]):
        e = entries.get(n["key"], {})
        url = f"https://doi.org/{e['DOI']}" if e.get("DOI") else e.get("URL") or \
            "https://scholar.google.com/scholar?q=" + urllib.parse.quote(e.get("title", n["key"]))
        out.append(dict(n, title=e.get("title", "?"), url=url, ref=ref_text(e)))
    return out


# ---------------------------------------------------------------------------------------
# Commands.

def cmd_init(paper, args):
    paper.ev.mkdir(exist_ok=True)
    paper.ledger_dir.mkdir(exist_ok=True)
    gi = paper.ev / ".gitignore"
    if not gi.exists():
        gi.write_text("# Full texts are copyrighted and the HTML is rebuilt in seconds.\nfulltext/\nhtml/\n"
                      "# The download log must be tracked, even where the repository ignores *.log.\n!hashes.log\n")
    src = paper.draft.read_text()
    if paper.is_tex:
        sty = paper.root / "referencer.sty"
        if not sty.exists():
            shutil.copy(SKILL_DIR / "assets" / "referencer.sty", sty)
        if "\\referencermode" not in src:
            src = re.sub(r"(\\documentclass(\[[^\]]*\])?\{[^}]*\}\n)",
                         r"\1\\usepackage{referencer}\n\\referencermode{final}\n",
                         src, count=1)
            paper.draft.write_text(src)
            log("added \\usepackage{referencer} and \\referencermode{final} after \\documentclass")
    elif "referencer" not in paper.meta:
        line = "referencer: final\n"
        src = re.sub(r"\A---\n", "---\n" + line, src, count=1) if src.startswith("---\n") \
            else f"---\n{line}---\n\n{src}"
        paper.draft.write_text(src)
        log("added `referencer: final` to the YAML header")
    log(f"evidence folder: {paper.ev}")


def cmd_extract(paper, args):
    insts = paper.instances()
    paper.ev.mkdir(exist_ok=True)
    (paper.ev / "citations.json").write_text(json.dumps(
        {"draft": paper.draft.name, "instances": [public(i) for i in insts]}, indent=1, ensure_ascii=False))
    keys = {k for i in insts for k in i["keys"]}
    print(f"{len(insts)} citation instances of {len(keys)} works -> {paper.ev / 'citations.json'}")


def retraction(entry):
    """Has the work been retracted, withdrawn or given an expression of concern? Asks Crossref
    (whose `updated-by` includes the Retraction Watch database) and OpenAlex (`is_retracted`).
    Returns {"checked": date, "retracted": bool, "notices": [...], "errors": [...]}."""
    out = {"checked": datetime.date.today().isoformat(), "retracted": False, "notices": [], "errors": []}
    doi = entry.get("DOI")
    if not doi:
        out["errors"].append("no DOI in the bibliography entry, so not checked")
        return out
    qdoi = urllib.parse.quote(doi)
    try:
        msg = get_json(f"https://api.crossref.org/works/{qdoi}")["message"]
        for u in msg.get("updated-by", []):
            if u.get("type") in RETRACTION_TYPES:
                out["notices"].append({"type": u["type"], "doi": u.get("DOI"), "source": u.get("source", "crossref"),
                                       "date": "-".join(map(str, (u.get("updated") or {}).get("date-parts", [[""]])[0]))})
    except (*NETWORK_ERRORS, KeyError) as e:
        out["errors"].append(f"Crossref: {e}")
    try:
        if get_json(f"https://api.openalex.org/works/https://doi.org/{qdoi}").get("is_retracted"):
            if not out["notices"]:
                out["notices"].append({"type": "retraction", "doi": None, "source": "OpenAlex", "date": ""})
    except NETWORK_ERRORS as e:
        out["errors"].append(f"OpenAlex: {e}")
    out["retracted"] = bool(out["notices"])
    return out


def notice_text(r):
    kinds = sorted({n["type"].replace("_", " ") for n in r["notices"]})
    links = [f"https://doi.org/{n['doi']}" for n in r["notices"] if n.get("doi")]
    return " and ".join(kinds) + (f" ({', '.join(links)})" if links else "")


def cmd_fetch(paper, args):
    paper.fulltext.mkdir(parents=True, exist_ok=True)
    insts = paper.instances()
    entries = paper.bib_entries()
    keys = sorted({k for i in insts for k in i["keys"]})
    if args.key:
        keys = [k for k in keys if k in args.key]
    sources_path = paper.ev / "sources.json"
    sources = json.loads(sources_path.read_text()) if sources_path.exists() else {}
    for n, key in enumerate(keys, 1):
        if key not in entries:
            sources[key] = {"status": "missing", "tried": ["key not in the bibliography"]}
        else:
            had = sources.get(key, {})
            sources[key] = fetch_one(paper, key, entries[key], args.refresh)
            if sources[key]["status"] == "ok":
                sources[key]["licence"] = had.get("licence") if not args.refresh else None
                if not sources[key]["licence"]:
                    sources[key].update(licence_recheck(paper, key, entries[key]))
            # Checked on every fetch, even when the text is already here: a retraction can come later.
            sources[key]["retraction"] = retraction(entries[key])
        s = sources[key]
        log(f"{n}/{len(keys)} {key}: {s['status']}" + (f" ({s.get('source')})" if s["status"] == "ok" else "")
            + (f"; RETRACTION NOTICE: {notice_text(s['retraction'])}" if s.get("retraction", {}).get("retracted") else ""))
        sources_path.write_text(json.dumps(sources, indent=1))
    # missing.md lists every cited work still missing, also when only some keys were fetched.
    every = sorted({k for i in insts for k in i["keys"]})
    missing = [k for k in write_missing(paper, entries, every, sources) if k in keys]
    print(f"{len(keys) - len(missing)}/{len(keys)} full texts available; "
          f"{len(missing)} missing, listed in {paper.ev / 'missing.md'}")
    for k in keys:
        if sources[k].get("warning"):
            print(f"  warning {k}: {sources[k]['warning']}")


def cmd_todo(paper, args):
    insts, results, stale = evaluate(paper)
    out = []
    for i in insts:
        for r in results[i["id"]]["per_key"]:
            if r["verdict"] == "unchecked" and (not args.key or r["key"] in args.key):
                out.append({"key": r["key"], **public(i),
                            "stale_entries_for_key": stale.get(r["key"], [])})
    print(json.dumps(out, indent=1, ensure_ascii=False))


def cmd_find(paper, args):
    if not FullText.available(paper, args.key):
        sys.exit(f"@{args.key}: no full text in {paper.fulltext} (run fetch, or add one; a refused "
                 f"subscription copy stays on the worksheet)")
    ft = FullText(paper, args.key)
    for term in args.terms:
        words = re.findall(r"\w+", term)
        pat = re.compile(r"\W+".join(map(re.escape, words)), re.I)
        hits = 0
        for chunk, label in zip(ft.chunks, ft.labels):
            flat = re.sub(r"\s+", " ", dehyphenate(chunk))
            for m in pat.finditer(flat):
                a, b = max(0, m.start() - args.width), min(len(flat), m.end() + args.width)
                print(f"--- {label} | {term}\n{flat[a:b]}\n")
                hits += 1
                if hits >= args.max:
                    break
            if hits >= args.max:
                break
        if not hits:
            print(f"--- no match for '{term}'\n")


def cmd_mode(paper, args):
    """Set the toggle: `mode DRAFT final|verification`."""
    if len(args.rest) != 1 or args.rest[0] not in MODES:
        sys.exit(f"mode needs one of {MODES}")
    new, src = args.rest[0], paper.draft.read_text()
    if paper.is_tex:
        src, n = re.subn(r"\\referencermode\{\w+\}", lambda m: f"\\referencermode{{{new}}}", src)
    else:
        head = re.match(r"\A---\n.*?\n(---|\.\.\.)\n", src, re.S)
        n = 0
        if head:
            block, n = re.subn(r"(?m)^referencer:.*$", f"referencer: {new}", head.group(0))
            src = block + src[head.end():]
    if n != 1:
        sys.exit(f"found {n} toggle lines in {paper.draft.name}; run init first")
    paper.draft.write_text(src)
    print(f"{paper.draft.name}: mode {new}")


def sniff(data):
    """'pdf', 'xml', 'html' or 'text', from a file's first bytes."""
    head = data[:600].lstrip().lower()
    if data.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<html" in head[:300]:
        return "html"
    if head.startswith(b"<?xml") or head.startswith(b"<article") or head.startswith(b"<!doctype article"):
        return "xml"
    return "text"


def ocr_pdf(scan, out):
    """OCR a scanned PDF into a searchable copy (ocrmypdf, which uses tesseract)."""
    if not shutil.which("ocrmypdf"):
        sys.exit("this PDF has no text layer and ocrmypdf is not installed (brew install ocrmypdf)")
    subprocess.run(["ocrmypdf", "--skip-text", "--quiet", str(scan), str(out)], check=True)


def write_missing(paper, entries, keys, sources):
    missing = [k for k in keys if sources.get(k, {}).get("status") != "ok"]
    lines = ["# Full texts still missing", "",
             f"Save each as `{os.path.relpath(paper.fulltext, paper.root)}/<key>.pdf` and run `fetch` again.", ""]
    for k in missing:
        e = entries.get(k, {})
        doi = f" https://doi.org/{e['DOI']}" if e.get("DOI") else ""
        lines.append(f"- **{k}**: {e.get('title', '?')}{doi}")
        lines += [f"  - tried: {t}" for t in sources.get(k, {}).get("tried", [])]
    (paper.ev / "missing.md").write_text("\n".join(lines) + "\n")
    return missing


def cmd_add(paper, args):
    """Install a text obtained other than by `fetch`:
    `add DRAFT KEY (FILE | --download URL) --version V [--url URL] [--ocr] [--title T]`.
    With --download the script fetches the file itself, so the logged hash is that of the
    file as served; a FILE is logged as handed over. Plain text not fetched by the script is
    marked as supplied text on the evidence page."""
    if args.version not in VERSIONS:
        sys.exit(f"--version must be one of {VERSIONS}")
    if args.download:
        if len(args.rest) != 1:
            sys.exit("add --download needs KEY only")
        key, url = args.rest[0], args.download

        def download(u):
            # A failed download stops the command with the reason, and is recorded so the
            # worksheet and missing.md show it; nothing is installed.
            try:
                return http_get(u, timeout=90)
            except NETWORK_ERRORS as e:
                why = f"HTTP {e.code} {e.reason}" if isinstance(e, urllib.error.HTTPError) else str(getattr(e, "reason", e))
                sources_path = paper.ev / "sources.json"
                sources = json.loads(sources_path.read_text()) if sources_path.exists() else {}
                entry_s = sources.setdefault(key, {"status": "missing", "tried": []})
                entry_s.setdefault("tried", []).append(f"add --download {u}: {why}")
                paper.ev.mkdir(parents=True, exist_ok=True)
                sources_path.write_text(json.dumps(sources, indent=1))
                sys.exit(f"{key}: not added: downloading {u} failed ({why}). Check the address, or download the "
                         f"file another way and pass it as FILE.")
        data = download(url)
        kind = sniff(data)
        if kind == "html":
            inner = landing_pdf_url(data, url)
            if not inner:
                sys.exit(f"{url} is a web page with no declared PDF; download the file another way and pass it as FILE")
            url, data = inner, download(inner)
            kind = sniff(data)
        supplied = False
    else:
        if len(args.rest) != 2:
            sys.exit("add needs KEY and FILE (or --download URL)")
        key, src = args.rest[0], Path(args.rest[1]).expanduser().resolve()
        url, data = args.url, src.read_bytes()
        kind = "pdf" if data.startswith(b"%PDF") else "xml" if src.suffix.lower() == ".xml" else "text"
        supplied = kind == "text" and args.version != "abstract"
    entry = paper.bib_entries().get(key)
    if entry is None and not args.title:
        sys.exit(f"{key} is not in the bibliography; give --title to add a work it does not cite yet")
    title = (entry or {}).get("title") or args.title
    paper.fulltext.mkdir(parents=True, exist_ok=True)
    # The licence decides whether the agent may read this text at all; a file is checked as
    # itself, plain text by the work's DOI. Only the user's own words lift a refusal
    # (`license-check allow`), never the agent's.
    probe = None
    if kind == "pdf":
        probe = paper.fulltext / f"{key}.licence-check.pdf"
        probe.write_bytes(data)
    target = probe or (entry or {}).get("DOI")
    v = licence(target, (entry or {}).get("DOI")) if target else None
    if probe:
        probe.unlink()
    if v and v["refused"] and args.version != "abstract":
        # Record the refusal, so the worksheet says why the agent could not read this work
        # ("subscription copy ...") rather than "no open copy found". A text already held stays.
        sources_path = paper.ev / "sources.json"
        sources = json.loads(sources_path.read_text()) if sources_path.exists() else {}
        had = sources.get(key, {})
        tried = had.get("tried", []) + [f"add {url or args.rest[-1]}: {refusal_text(v)}"]
        if had.get("status") == "ok":
            had["tried"] = tried
        else:
            sources[key] = {"status": "refused", "why": refusal_text(v), "tried": tried}
        sources_path.write_text(json.dumps(sources, indent=1))
        insts = paper.instances()
        write_missing(paper, paper.bib_entries(), sorted({k for i in insts for k in i["keys"]}), sources)
        sys.exit(f"{key}: not added: {refusal_text(v)}. It stays on the worksheet for the author to check "
                 f"by hand (`referencer.py worksheet`). Only the author can lift this, in their own words "
                 f"(license-check allow).")
    extra, ocr = [], False
    if kind == "pdf":
        # Land under a temporary name, so a refused file never replaces a logged one.
        incoming = paper.fulltext / f"{key}.incoming.pdf"
        incoming.write_bytes(data)
        chunks, labels = pdf_chunks(incoming)
        original = paper.fulltext / f"{key}.pdf"
        if len("".join(chunks).strip()) < 20 * max(1, len(chunks)):  # under 20 characters a page: a scan
            if not args.ocr:
                incoming.unlink()
                sys.exit(f"{key}: the PDF has (almost) no text layer, so it is a scan: rerun with --ocr")
            scan = paper.fulltext / f"{key}.scan.pdf"
            incoming.rename(scan)
            ocr_pdf(scan, original)
            extra, ocr = [scan], True
            chunks, labels = pdf_chunks(original)
        else:
            incoming.rename(original)
        fmt = "pdf"
    elif kind == "xml":
        original = paper.fulltext / f"{key}.xml"
        original.write_bytes(data)
        chunks, labels = xml_chunks(data)
        fmt = "xml"
    else:
        chunks = data.decode("utf-8", errors="replace").split("\f")  # form feeds separate pages
        labels = ["Abstract"] if args.version == "abstract" and len(chunks) == 1 else \
            [f"part {i + 1}" for i in range(len(chunks))]
        fmt, original = "text", None
        if not supplied:  # fetched by the script: keep the bytes as served
            original = paper.fulltext / f"{key}.download.txt"
            original.write_bytes(data)
    source = "downloaded by add" if args.download else "added by hand"
    log_files(paper, key, extra, source, url) if extra else None
    save_text(paper, key, chunks, labels, fmt, source, url, args.version, original=original)
    meta_path = paper.fulltext / f"{key}.json"
    meta = json.loads(meta_path.read_text())
    meta.update({"supplied_text": supplied, "ocr": ocr})
    meta_path.write_text(json.dumps(meta, indent=1))
    log_files(paper, key, [meta_path], source, url)
    sources_path = paper.ev / "sources.json"
    sources = json.loads(sources_path.read_text()) if sources_path.exists() else {}
    sources[key] = {"status": "ok", "source": source, "url": url, "version": args.version,
                    "supplied_text": supplied, "ocr": ocr, "tried": sources.get(key, {}).get("tried", [])}
    sources_path.write_text(json.dumps(sources, indent=1))
    insts = paper.instances()
    write_missing(paper, paper.bib_entries(), sorted({k for i in insts for k in i["keys"]}), sources)
    ok = title_matches(title, "".join(chunks[:2]))
    print(f"{key}: {len(chunks)} chunks ({args.version}{', OCR' if ocr else ''}"
          f"{', supplied text' if supplied else ''})" +
          ("" if ok else "; WARNING: the title is not on the first pages, check this is the right work"))


def cmd_locate(paper, args):
    """Is this quote in KEY's text? `locate DRAFT KEY "quote"`; for works not yet cited too."""
    if len(args.rest) != 2:
        sys.exit("locate needs KEY and a quote")
    key, quote = args.rest
    logged, _, _ = read_log(paper)
    why = integrity(paper, key, logged)
    if why:
        sys.exit(f"@{key}: {why}")
    if not FullText.available(paper, key):
        sys.exit(f"@{key}: no full text in {paper.fulltext}")
    chunk, err = FullText(paper, key).locate(quote)
    if err:
        sys.exit(f"@{key}: {err}")
    print(f"@{key}: found ({FullText(paper, key).labels[chunk]})")


def cmd_record(paper, args):
    """Write one assessment after checking it:
    `record DRAFT KEY ID --verdict V [--quote Q ...] [--note N] [--secondary]`."""
    if len(args.rest) != 2:
        sys.exit("record needs KEY and instance ID")
    key, iid = args.rest
    inst = next((i for i in paper.instances() if i["id"] == iid), None)
    if inst is None or key not in inst["keys"]:
        sys.exit(f"no citation instance {iid} citing @{key}; see `todo`")
    entry = {"sentence": inst["sentence"], "verdict": args.verdict,
             "passages": [{"quote": q} for q in args.quote or []], "note": args.note or ""}
    if args.secondary:
        entry["secondary"] = True
    if args.doubt:
        entry["doubt"] = args.doubt
    logged, _, _ = read_log(paper)
    why = integrity(paper, key, logged)
    if why:
        sys.exit(f"not recorded: @{key}: {why}")
    texts = {key: FullText(paper, key)} if FullText.available(paper, key) else {}
    if texts:
        entry["text_sha256"] = digests(texts[key].txt)[1]
    single = dict(inst, keys=[key])
    result = assess_entry(paper, single, texts, {key: entry}, {key: why} if why else {})
    if result["problems"]:
        sys.exit("not recorded:\n  " + "\n  ".join(result["problems"]))
    paper.ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger = paper.ledger(key)
    ledger[iid] = entry
    (paper.ledger_dir / f"{key}.json").write_text(json.dumps(ledger, indent=1, ensure_ascii=False))
    where = ", ".join(p["label"] for p in result["per_key"][0]["passages"])
    print(f"recorded @{key} {iid}: {args.verdict}" + (f" ({where})" if where else ""))


def summarise(insts, results, stale, log_report=([], None), retrieve=()):
    counts = {s: 0 for s in STATUSES}
    for i in insts:
        counts[results[i["id"]]["status"]] += 1
    lines = [f"{len(insts)} citation instances: " + ", ".join(f"{s} {counts[s]}" for s in STATUSES if counts[s])]
    retracted = sorted({(r["key"], r["retracted"]) for i in insts for r in results[i["id"]]["per_key"] if r.get("retracted")})
    lines += [f"  RETRACTED @{k}: {why}" for k, why in retracted]
    for i in insts:
        for d in results[i["id"]]["doubts"]:
            lines.append(f"  DOUBTFUL CLAIM {i['id']} (#{i['n']}, {i['section']}): {d}")
    if retrieve:
        lines.append("  full texts to retrieve, most-cited first:")
        lines += [f"    {w['url']}  @{w['key']} ({w['claims']} claim{'s' if w['claims'] > 1 else ''}"
                  f"; {w['why']}): {w['title']}" for w in retrieve]
    for i in insts:
        r = results[i["id"]]
        if r["problems"]:
            lines.append(f"  ERROR {i['id']} (#{i['n']}, {i['section']}):")
            lines += [f"    {p}" for p in r["problems"]]
    for k, ids in stale.items():
        lines.append(f"  stale ledger entries for @{k} (claim edited or removed): {', '.join(ids)}")
    log_problems, log_warning = log_report
    lines += [f"  LOG ERROR: {p}" for p in log_problems]
    if log_warning:
        lines.append(f"  warning: {log_warning}")
    counts["error"] += len(log_problems)
    return counts, "\n".join(lines)


WORKSHEET_CHOICES = (("supported", "supported"), ("partly", "partial"), ("not supported", "unsupported"),
                     ("contradicted", "contradicted"))


def claim_html(inst):
    s, (a, b) = inst["sentence"], inst["target"]
    return html.escape(s[:a]) + "<b>" + html.escape(s[a:b]) + "</b>" + html.escape(s[b:])


def cited_claim(inst):
    """The clause the citation sits in, on both sides of it, bounded by ';' or ':' (which in
    these papers separate a cited statement from the authors' own gloss); other citation labels
    are dropped."""
    s, (a, b) = inst["sentence"], inst["target"]
    # Look for boundaries outside citation groups and mathematics only.
    masked = re.sub(r"\[@[^\]]*\]|\$[^$]*\$", lambda m: "x" * len(m.group(0)), s)
    start = max(masked.rfind(";", 0, a), masked.rfind(":", 0, a)) + 1
    ends = [i for i in (masked.find(";", b), masked.find(":", b)) if i != -1]
    claim = s[start:a] + " " + s[b:min(ends) if ends else len(s)]
    claim = re.sub(r"\s+", " ", re.sub(r"\s*\[@[^\]]*\]", "", claim))
    claim = re.sub(r" ([,.;:)])", r"\1", claim).strip(" ,.;:")
    return claim[:1].upper() + claim[1:]


def cmd_worksheet(paper, args):
    """Write evidence/worksheet.md: one entry per citation the agent could not read, for the
    author to check by hand (open the link, find the passage, tick one box). With --import,
    record the ticked entries in the ledger as checked by the author."""
    path = paper.ev / "worksheet.md"
    insts, results, _ = evaluate(paper)
    if args.import_:
        return import_worksheet(paper, path, insts)
    if path.exists():  # never overwrite ticks the author has not imported yet
        pending = []
        for block in re.split(r"^### ", path.read_text(), flags=re.M)[1:]:
            m = re.match(r"(\S+) · @(\S+)", block)
            if m and re.search(r"^- \[[xX]\]", block, re.M) and \
                    paper.ledger(m.group(2)).get(m.group(1), {}).get("checked_by") != "author":
                pending.append(m.group(1))
        if pending:
            sys.exit(f"{path} has ticked boxes not yet imported ({', '.join(pending[:5])}"
                     f"{'…' if len(pending) > 5 else ''}): run `worksheet {paper.draft.name} --import` first")
    entries = paper.bib_entries()
    todo = to_retrieve(paper, insts, results, entries)
    lines = ["# Citations to check by hand", "",
             "The agent could not read these works (no open copy, or a licence that keeps the full text "
             "from AI tools). For each citation: open the link, find the passage, tick one box with "
             "`[x]`, and add a note if it is not plainly supported. Then run "
             f"`referencer.py worksheet {paper.draft.name} --import`. Boxes left empty are ignored.", "",
             "If you have your own copy of a paper, `referencer.py assist "
             f"{paper.draft.name} <key> --pdf <your copy>`, run in your own terminal (not through Claude), "
             "searches it for each claim, shows you the best passages, and records your verdict with the "
             "passage you pick. The text of your copy is never saved and never reaches the agent.", ""]
    for n, w in enumerate(todo, 1):
        lines += [f"## {n}. {w['title']}", "", f"`@{w['key']}` · {w['url']} · {w['why']}", ""]
        for i in w["instances"]:
            s, (a, b) = i["sentence"], i["target"]
            lines += [f"### {i['id']} · @{w['key']} · {i['section']}", "",
                      f"> {s[:a]}**{s[a:b]}**{s[b:]}", ""]
            if len(s) - (b - a) < 20:
                lines += [f"Context: {i['before']}", ""]
            lines += [f"Claim to verify: *{cited_claim(i) or 'see the context'}*", ""]
            lines += [f"- [ ] {label}" for label, _ in WORKSHEET_CHOICES]
            lines += ["", "Note: ", ""]
    path.write_text("\n".join(lines) + "\n")
    print(f"{sum(len(w['instances']) for w in todo)} citations of {len(todo)} works -> {path}")


def import_worksheet(paper, path, insts):
    if not path.exists():
        sys.exit(f"no worksheet at {path}; run `worksheet` first")
    by_id = {i["id"]: i for i in insts}
    recorded, skipped = 0, []
    for block in re.split(r"^### ", path.read_text(), flags=re.M)[1:]:
        m = re.match(r"(\S+) · @(\S+)", block)
        if not m:
            continue
        iid, key = m.groups()
        ticked = [v for label, v in WORKSHEET_CHOICES if re.search(rf"^- \[[xX]\] {re.escape(label)}\s*$", block, re.M)]
        note = (re.search(r"^Note:[ \t]*(.*)$", block, re.M) or [None, ""])[1].strip()
        if not ticked:
            continue
        if len(ticked) > 1:
            skipped.append(f"{iid}: more than one box ticked")
            continue
        inst = by_id.get(iid)
        if inst is None or key not in inst["keys"]:
            skipped.append(f"{iid}: no such citation of @{key} any more (the sentence changed); check it again")
            continue
        ledger = paper.ledger(key)
        ledger[iid] = {"sentence": inst["sentence"], "verdict": ticked[0], "passages": [], "note": note,
                       "checked_by": "author", "checked_on": datetime.date.today().isoformat()}
        paper.ledger_dir.mkdir(parents=True, exist_ok=True)
        (paper.ledger_dir / f"{key}.json").write_text(json.dumps(ledger, indent=1, ensure_ascii=False))
        recorded += 1
    print(f"recorded {recorded} verdicts checked by the author" + "".join(f"\n  skipped {s}" for s in skipped))


# ---------------------------------------------------------------------------------------
# assist: the author checks a citation against their own copy of a paper the agent may not
# read. The PDF is searched in memory on the author's machine; only the author's verdict and
# the short passage they choose reach the ledger.

STOPWORDS = set("""a an and are as at be been being but by can could do does for from had has have
however if in into is it its may might more most no not of on or our over such than that the their
then there these they this those through to under was we were what when where which while who with
would also each every only one two both between within without whose using used use given show
shows shown""".split())
MAX_AUTHOR_QUOTE = 400  # a short quote, which the licence rule allows, not a page


def claim_terms(text):
    """Search terms from a claim: numbers, content words, and pairs of adjacent content words."""
    plain = re.sub(r"\$[^$]*\$|\[@[^\]]*\]|\(columns:[^)]*\)|^Table row:", " ", text)
    numbers = [n for n in re.findall(r"\d+(?:[.,]\d+)?", plain) if len(n) > 1 or "." in n]
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", plain)]
    content = [w for w in words if w not in STOPWORDS and len(w) >= 4]
    pairs = [f"{a} {b}" for a, b in zip(words, words[1:]) if a not in STOPWORDS and b not in STOPWORDS]
    seen, out = set(), []
    for t in numbers + pairs + content:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def passage_windows(chunks, labels):
    """Two-sentence windows over every page, with the page label. The reference list is left
    out: its years and page numbers match everything."""
    out = []
    refs = re.compile(r"^\s*(\d+\.?\s*)?(References|Bibliography|Literature cited)\s*$", re.I | re.M)
    for n, (chunk, label) in enumerate(zip(chunks, labels)):
        m = refs.search(chunk) if n >= len(chunks) // 2 else None
        if m:
            chunk = chunk[:m.start()]
        flat = re.sub(r"\s+", " ", dehyphenate(chunk)).strip()
        sents = [x for x in re.split(r"(?<=[.?!])\s+(?=[A-Z(\[])", flat) if x]
        for i in range(len(sents)):
            out.append((label, " ".join(sents[i:i + 2])))
        if m:
            break
    return out


def rank_passages(windows, terms, k=5):
    low = [w.lower() for _, w in windows]
    n = len(windows) or 1
    df = {t: sum(t in w for w in low) for t in terms}
    scored = []
    for (label, text), w in zip(windows, low):
        hits = [t for t in terms if t in w]
        if not hits:
            continue
        score = sum((3 if re.fullmatch(r"[\d.,]+", t) else 2 if " " in t else 1) * math.log(1 + n / (1 + df[t]))
                    for t in hits)
        scored.append((score, label, text, hits))
    scored.sort(key=lambda x: -x[0])
    best, used = [], set()
    for sc in scored:  # drop windows that overlap the previous pick (same opening sentence)
        if sc[2][:80] not in used:
            used.add(sc[2][:80])
            best.append(sc)
        if len(best) == k:
            break
    return best


def shade(text, hits):
    if not sys.stdout.isatty():
        return text
    for t in sorted(hits, key=len, reverse=True):
        text = re.sub(re.escape(t), lambda m: f"\033[1;33m{m.group(0)}\033[0m", text, flags=re.I)
    return text


def ask(prompt, allowed=None):
    while True:
        try:
            a = input(prompt).strip()
        except EOFError:
            sys.exit("\nstopped (end of input); verdicts given so far are recorded")
        if allowed is None or a in allowed or a.startswith("/"):
            return a
        print(f"  please answer one of: {', '.join(x or 'Enter' for x in allowed)}")


def cmd_terms(paper, args):
    """Add search terms for one citation (the agent's suggestions for `assist`):
    `terms DRAFT ID TERM...`; stored in evidence/search_terms.json."""
    if len(args.rest) < 2:
        sys.exit("terms needs a citation ID and at least one term")
    iid, terms = args.rest[0], args.rest[1:]
    if iid not in {i["id"] for i in paper.instances()}:
        sys.exit(f"no citation instance {iid}; see `worksheet`")
    path = paper.ev / "search_terms.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data[iid] = sorted(set(data.get(iid, [])) | {t.lower() for t in terms})
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"{iid}: {', '.join(data[iid])}")


def cmd_assist(paper, args):
    """For the AUTHOR, in their own terminal: check the citations of KEY against their own
    copy of the paper. `assist DRAFT KEY --pdf FILE [--all]`."""
    if os.environ.get("CLAUDECODE") or os.environ.get("AI_AGENT"):
        sys.exit("assist is for the author's own terminal: it shows passages of a paper the agent may "
                 "not read. Run it outside Claude Code (not with `!`, whose output enters the conversation).")
    if not sys.stdin.isatty():
        sys.exit("assist is interactive: run it in a terminal")
    if len(args.rest) != 1 or not args.pdf:
        sys.exit("assist needs KEY and --pdf FILE")
    key, pdf = args.rest[0], Path(args.pdf).expanduser().resolve()
    data = pdf.read_bytes()
    if not data.startswith(b"%PDF"):
        sys.exit(f"{pdf} is not a PDF")
    chunks, labels = pdf_chunks(pdf)  # in memory only: nothing of the text is written to disk
    entry = paper.bib_entries().get(key, {})
    if not title_matches(entry.get("title"), "".join(chunks[:2])):
        if ask(f"The title of @{key} is not on the first pages of {pdf.name}. Use it anyway? [y/N] ",
               ("y", "n", "")) != "y":
            return 1
    ft = FullText.from_chunks(key, chunks, labels)
    windows = passage_windows(chunks, labels)
    sha = digests(pdf)[1]
    insts, results, _ = evaluate(paper)
    extra = json.loads((paper.ev / "search_terms.json").read_text()) if (paper.ev / "search_terms.json").exists() else {}
    todo = [i for i in insts if key in i["keys"] and (args.all or next(
        r for r in results[i["id"]]["per_key"] if r["key"] == key)["verdict"] in ("no-fulltext", "unchecked"))]
    if not todo:
        print(f"No citation of @{key} is waiting for a check (use --all to redo them).")
        return 0
    choices = {"s": "supported", "p": "partial", "n": "unsupported", "c": "contradicted", "": None}
    done = 0
    for n, inst in enumerate(todo, 1):
        terms = claim_terms(cited_claim(inst))
        if len(terms) < 3:  # a bare citation ("[3]" in a table or a list): search its surroundings
            terms += claim_terms(inst["before"] + " " + inst["after"])
        terms = list(dict.fromkeys(extra.get(inst["id"], []) + terms))
        while True:
            print("\n" + "=" * 78)
            print(f"[{n}/{len(todo)}] @{key} · {inst['section']} · {inst['id']}")
            s, (a, b) = inst["sentence"], inst["target"]
            print(textwrap.fill(f"Sentence: {s[:a]}>>{s[a:b]}<<{s[b:]}", 100))
            print(textwrap.fill(f"Claim:    {cited_claim(inst) or '(no words of its own; see the surrounding text)'}", 100))
            if len(s) - (b - a) < 20:
                print(textwrap.fill(f"Context:  {inst['before']} … {inst['after']}", 100))
            print(f"Searching for: {', '.join(terms[:12])}{' …' if len(terms) > 12 else ''}")
            best = rank_passages(windows, terms)
            for j, (_, label, text, hits) in enumerate(best, 1):
                print(f"\n  {j}. {label}: " + shade(textwrap.shorten(text, 500, placeholder=' …'), hits))
            if not best:
                print("\n  No passage matches these terms.")
            a = ask("\nVerdict: [s]upported [p]artly [n]ot supported [c]ontradicted, /words to search for "
                    "other words, Enter to skip: ", set(choices))
            if a.startswith("/"):
                terms = [t.strip().lower() for t in a[1:].split(",") if t.strip()] or terms
                continue
            break
        verdict = choices[a]
        if verdict is None:
            continue
        passages = []
        while best:
            pick = ask(f"Passage to keep as evidence (1-{len(best)}), or Enter for none: ",
                       {str(j) for j in range(1, len(best) + 1)} | {""})
            if not pick:
                break
            quote = best[int(pick) - 1][2]
            if len(quote) > MAX_AUTHOR_QUOTE:
                quote = input(f"That passage is {len(quote)} characters; paste the part that matters "
                              f"(at most {MAX_AUTHOR_QUOTE}): ").strip()
            chunk, err = ft.locate(quote)
            if err or len(quote) > MAX_AUTHOR_QUOTE:
                print(f"  {err or 'still too long'}; try again")
                continue
            passages.append({"quote": quote, "page": labels[chunk]})
            break
        try:
            note = input("Note (Enter for none): ").strip()
        except EOFError:
            note = ""
        if not done:  # the copy's hash goes in the log with the first verdict that rests on it
            log_files(paper, key, [pdf], "author's own copy, searched locally by `assist`; never given to the agent",
                      None, names={pdf: f"{key}.author-copy.pdf"})
        ledger = paper.ledger(key)
        ledger[inst["id"]] = {"sentence": inst["sentence"], "verdict": verdict, "passages": passages,
                              "note": note, "checked_by": "author", "checked_on": datetime.date.today().isoformat(),
                              "author_copy_sha256": sha}
        paper.ledger_dir.mkdir(parents=True, exist_ok=True)
        (paper.ledger_dir / f"{key}.json").write_text(json.dumps(ledger, indent=1, ensure_ascii=False))
        done += 1
        print(f"  recorded: {verdict}" + (f", with the passage from {passages[0]['page']}" if passages else ""))
    print(f"\n{done} verdict(s) recorded for @{key}. The text of {pdf.name} was not saved anywhere; "
          f"its hash is in hashes.log.")
    return 0


def cmd_check(paper, args):
    insts, results, stale = evaluate(paper)
    retrieve = to_retrieve(paper, insts, results, paper.bib_entries())
    counts, text = summarise(insts, results, stale, paper.log_report, retrieve)
    print(text)
    for w in paper.raw_caption_warnings:
        print(f"  warning: {w}")
    return 1 if counts["error"] else 0


def cmd_build(paper, args):
    if paper.mode == "final":
        usual = "make" if (paper.root / "Makefile").exists() else \
            f"latexmk -pdf {paper.draft.name}" if paper.is_tex else f"pandoc {paper.draft.name} --citeproc -o ..."
        print(f"final mode: nothing to build here; the paper compiles as usual ({usual}). "
              f"For the evidence view: referencer.py mode {paper.draft.name} verification")
        return 0
    insts, results, stale = evaluate(paper)
    entries = paper.bib_entries()
    retrieve = to_retrieve(paper, insts, results, entries)
    counts, text = summarise(insts, results, stale, paper.log_report, retrieve)
    write_html(paper, insts, results, counts, entries, retrieve)
    print(text)
    print(f"verification view: {paper.html_dir / 'manuscript.html'}")
    return 1 if counts["error"] else 0


# ---------------------------------------------------------------------------------------
# HTML output.

VERSION_TEXT = {
    "published": "published version", "accepted": "accepted manuscript", "preprint": "preprint",
    "third-party": "third-party copy of the published version (e.g. a course page)",
    "abstract": "abstract only", "unknown": "copy of unknown version",
}

STATUS_TEXT = {
    "supported": "supported", "partial": "partly supported", "unsupported": "not supported",
    "contradicted": "contradicted", "no-fulltext": "full text not retrieved", "unchecked": "not yet checked",
    "not-a-claim": "attribution only", "error": "evidence does not check out",
    "abstract-only": "supported by the abstract",
}

_LIGHT = {"ok": "#1f7a3a", "partial": "#a86a00", "bad": "#b3261e", "open": "#6b6a65", "attr": "#3a5bb0",
          "error": "#8e24aa"}
_DARK = {"ok": "#5fc27e", "partial": "#e0a640", "bad": "#f07167", "open": "#a3a19a", "attr": "#9fb0e8",
         "error": "#d58cf0"}


def _vars(base, colours):
    return base + "".join(f"--{k}:{v};" for k, v in colours.items())


CSS = (":root{" + _vars("--bg:#fbfaf7;--fg:#1d1d1b;--muted:#6b6a65;--card:#ffffff;--line:#e3e1da;--mark:#fff1a8;", _LIGHT) + "}"
       "@media (prefers-color-scheme:dark){:root:not([data-theme=\"light\"]){"
       + _vars("--bg:#17181a;--fg:#e9e7e1;--muted:#a3a19a;--card:#202226;--line:#34363b;--mark:#5a4d00;", _DARK) + "}}"
       ":root[data-theme=\"dark\"]{"
       + _vars("--bg:#17181a;--fg:#e9e7e1;--muted:#a3a19a;--card:#202226;--line:#34363b;--mark:#5a4d00;", _DARK) + "}"
       + """
body{background:var(--bg);color:var(--fg);font:16px/1.55 Georgia,serif;max-width:60rem;margin:0 auto;padding:1.5rem 16px}
a{color:inherit}
a.referencer{text-decoration:none;border-bottom:2px solid;padding:0 .1em}
""" + "".join(f"a.referencer.{s}{{color:var(--{c});border-color:var(--{c})}}.badge.{s}{{background:var(--{c})}}"
              for s, c in COLOUR.items()) + """
a.referencer.unchecked,a.referencer.abstract-only{border-bottom-style:dashed}
a.referencer.doubt::after,a.referencer.retracted::after{content:"\\26A0";font-size:.75em;vertical-align:super;color:var(--error)}
.badge{color:var(--bg);font:600 .75rem/1 system-ui,sans-serif;padding:.3em .55em;border-radius:.3em;white-space:nowrap}
.banner{font:.9rem system-ui,sans-serif;border:1px solid var(--line);background:var(--card);padding:.6rem .8rem;border-radius:.4rem;margin-bottom:1.5rem}
.alert{font:.95rem system-ui,sans-serif;border:2px solid var(--error);border-radius:.4rem;padding:.5rem .8rem;margin:.8rem 0}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}
@media (max-width:760px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:.5rem;padding:1rem 1.2rem}
.card h2{font:600 .8rem system-ui,sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 .6rem}
.card h3{scroll-margin-top:1rem}
.card h3:target{outline:2px solid var(--mark);outline-offset:4px}
mark{background:var(--mark);color:inherit;padding:0 .1em}
.claim .ctx{color:var(--muted)}
blockquote{margin:.6rem 0;padding:.4rem .9rem;border-left:3px solid var(--line)}
blockquote.bad{border-left-color:var(--error)}
.loc{font:.85rem system-ui,sans-serif;color:var(--muted)}
.ref{font-size:.9rem;color:var(--muted);margin-bottom:.5rem}
.note{font-style:italic}
.problem{color:var(--error);font:.9rem system-ui,sans-serif}
.keys{font:.95rem system-ui,sans-serif;display:flex;flex-wrap:wrap;gap:.4rem .9rem;margin:.4rem 0 1rem}
table{border-collapse:collapse;width:100%;font:.9rem system-ui,sans-serif}
td,th{border-bottom:1px solid var(--line);padding:.35rem .5rem;text-align:left;vertical-align:top}
""")

# An evidence page opens in its own tab; "back" closes that tab, and falls back to following
# the link when the browser will not let a page close itself (e.g. it was opened directly).
BACK_JS = ("if(history.length<=1){window.close();var h=this.href;"
           "setTimeout(function(){location.href=h},300);return false}")


def ref_text(e):
    if not e:
        return ""
    authors = [a.get("family", a.get("literal", "")) for a in e.get("author", [])]
    who = authors[0] + (" et al." if len(authors) > 2 else (" and " + authors[1] if len(authors) == 2 else "")) \
        if authors else ""
    year = ((e.get("issued") or {}).get("date-parts") or [[""]])[0][0]
    where = e.get("container-title", "") or e.get("publisher", "")
    return f"{who} ({year}). {e.get('title', '')}. {where}".strip()


def page(title, body):
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style>"
            "<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']]}};</script>"
            "<script defer src='https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js'></script>"
            f"</head><body>{body}</body></html>")


def inline_text(x):
    """Plain text of rendered inlines (used for the labels citeproc produced)."""
    if isinstance(x, list):
        return "".join(inline_text(y) for y in x)
    if not isinstance(x, dict):
        return ""
    t, c = x.get("t"), x.get("c")
    if t == "Str":
        return c
    if t in ("Space", "SoftBreak", "LineBreak"):
        return " "
    if t in ("Span", "Link", "Quoted", "Cite"):
        return inline_text(c[1])
    if t in WRAPPERS:
        return inline_text(c)
    return ""


def find_spans(x, prefix, found):
    """Collect Spans whose id starts with prefix, keyed by id, with their parent list and index."""
    if isinstance(x, list):
        for n, y in enumerate(x):
            if isinstance(y, dict) and y.get("t") == "Span" and y["c"][0][0].startswith(prefix):
                found[y["c"][0][0]] = y
            find_spans(y, prefix, found)
    elif isinstance(x, dict):
        find_spans(x.get("c"), prefix, found)
    return found


def key_title(r):
    t = f"@{r['key']}: {STATUS_TEXT.get(r['status'], r['status'])}" + (" (checked by the author)" if r.get("by_author") else "")
    if r.get("note"):
        t += f". {r['note']}"
    if r.get("retracted"):
        t += f". RETRACTED: {r['retracted']}"
    return t


def cite_link(iid, inlines, classes, title, anchor=""):
    return {"t": "Link", "c": [["", ["referencer"] + classes, [["target", "_blank"], ["title", title]]],
                               inlines, [f"cite/{iid}.html{anchor}", ""]]}


def write_html(paper, insts, results, counts, entries, retrieve=()):
    cite_dir = paper.html_dir / "cite"
    cite_dir.mkdir(parents=True, exist_ok=True)
    groups = {}
    for s in STATUSES:
        if counts[s]:
            groups.setdefault(COLOUR[s], []).append(f"{counts[s]} {STATUS_TEXT[s]}")
    first = {c: next(s for s in STATUSES if COLOUR[s] == c) for c in groups}
    tally = " · ".join(f"<span class='badge {first[c]}'>{', '.join(v)}</span>" for c, v in groups.items())
    fetch_line = (f" <a href='index.html#retrieve'>{len(retrieve)} full text{'s' if len(retrieve) != 1 else ''} "
                  f"to retrieve</a>." if retrieve else "")
    banner = (f"<div class=banner><b>Verification mode</b>: {len(insts)} citations. {tally}. "
              f"Each citation opens its evidence in a new tab; in a group such as [3, 5], each number "
              f"is marked on its own.{fetch_line} <a href='index.html'>Summary table</a></div>")

    # Pass 1: let citeproc render every citation, and render each citation of a group alone
    # (probes at the end of the document; they add no new works, so numbering is unchanged).
    probes = []
    for i in insts:
        node = i["_node"]
        orig = {"t": node["t"], "c": node["c"]}
        node["t"], node["c"] = "Span", [[f"cite-{i['id']}", [], []], [orig]]
        if len(orig["c"][0]) > 1:
            for j, citation in enumerate(orig["c"][0]):
                probe = {"t": "Cite", "c": [[dict(citation, citationMode={"t": "NormalCitation"})],
                                           [{"t": "Str", "c": "?"}]]}
                probes += [{"t": "Span", "c": [[f"probe-{i['id']}-{j}", [], []], [probe]]}, {"t": "Space"}]
    doc = dict(paper.ast, blocks=paper.ast["blocks"] + ([{"t": "Para", "c": probes}] if probes else []))
    doc["meta"] = dict(doc["meta"], **{"link-citations": {"t": "MetaBool", "c": False}})
    cmd = ["pandoc", "-f", "json", "-t", "json", "--citeproc"]
    for b in paper.bibs:
        cmd += ["--bibliography", str(b)]
    if paper.csl:
        cmd += ["--csl", str(paper.csl)]
    doc = json.loads(run(cmd, cwd=paper.root, stdin=json.dumps(doc)))
    probe_spans = find_spans(doc["blocks"], "probe-", {})
    if probes:
        doc["blocks"] = [b for b in doc["blocks"] if not (b["t"] == "Para" and b["c"] and b["c"][0].get("t") == "Span"
                                                          and b["c"][0]["c"][0][0].startswith("probe-"))]
    rendered = find_spans(doc["blocks"], "cite-", {})

    for i in insts:
        r = results[i["id"]]
        (cite_dir / f"{i['id']}.html").write_text(evidence_page(paper, i, r, entries))
        span = rendered[f"cite-{i['id']}"]
        cite = span["c"][1][0]
        flags = (["doubt"] if r["doubts"] else [])
        if len(r["per_key"]) == 1:
            k = r["per_key"][0]
            title = key_title(k) + (f". Doubtful claim: {'; '.join(r['doubts'])}" if r["doubts"] else "")
            span["c"][1] = [cite_link(i["id"], cite["c"][1], [k["status"]] + flags +
                                      (["retracted"] if k.get("retracted") else []), title)]
            continue
        labels = []
        for j, k in enumerate(r["per_key"]):
            p = probe_spans.get(f"probe-{i['id']}-{j}")
            labels.append(inline_text(p["c"][1]).strip() if p else "@" + k["key"])
        opens, closes = labels[0][:1], labels[0][-1:]
        bracketed = opens in "[(" and closes in "])" and all(l[:1] == opens and l[-1:] == closes for l in labels)
        inner = [l[1:-1] if bracketed else l for l in labels]
        out = [{"t": "Str", "c": opens}] if bracketed else []
        for j, (k, lab) in enumerate(zip(r["per_key"], inner)):
            if j:
                out.append({"t": "Str", "c": ", "})
            title = key_title(k) + (f". Doubtful claim: {'; '.join(r['doubts'])}" if r["doubts"] and j == 0 else "")
            out.append(cite_link(i["id"], [{"t": "Str", "c": lab}],
                                 [k["status"]] + (flags if j == len(r["per_key"]) - 1 else []) +
                                 (["retracted"] if k.get("retracted") else []), title, f"#key-{k['key']}"))
        if bracketed:
            out.append({"t": "Str", "c": closes})
        span["c"][1] = out

    # Pass 2: the rendered document to HTML, without citeproc (it has already run).
    header = paper.html_dir / "_style.html"
    header.write_text(f"<style>{CSS}</style>")
    before = paper.html_dir / "_banner.html"
    before.write_text(banner)
    run(["pandoc", "-f", "json", "-t", "html5", "-s", "-o", str(paper.html_dir / "manuscript.html"),
         "--metadata", f"pagetitle={paper.draft.stem} (verification)", "-H", str(header), "-B", str(before),
         "--mathjax"], cwd=paper.root, stdin=json.dumps(doc))
    header.unlink()
    before.unlink()

    rows = "".join(
        f"<tr><td><a href='cite/{i['id']}.html' target=_blank>{i['n']}</a></td>"
        f"<td>{html.escape(i['section'])}</td><td>{html.escape(i['sentence'][:160])}</td>"
        f"<td>{' '.join(f'''<span class='badge {k['status']}' title='{html.escape(key_title(k), quote=True)}'>{html.escape(k['key'])}</span>''' for k in results[i['id']]['per_key'])}</td>"
        f"<td><span class='badge {results[i['id']]['status']}'>{STATUS_TEXT[results[i['id']]['status']]}</span>"
        f"{' <span class=problem>doubtful claim</span>' if results[i['id']]['doubts'] else ''}</td></tr>"
        for i in insts)
    fetch = ""
    if retrieve:
        items = "".join(
            f"<li><a href='{html.escape(w['url'], quote=True)}' target=_blank>{html.escape(w['title'])}</a> "
            f"<span class=loc>@{html.escape(w['key'])} · {w['claims']} claim{'s' if w['claims'] > 1 else ''} · "
            f"{html.escape(w['why'])}</span>"
            + "<ul>" + "".join(f"<li class=loc>{html.escape(i['section'])}: {claim_html(i)}</li>" for i in w["instances"]) + "</ul>"
            + "</li>" for w in retrieve)
        fetch = (f"<h2 id=retrieve>Citations to check by hand</h2><p class=loc>Works the agent could not read, "
                 f"most-cited first, each with the sentences that cite it (the cited clause in bold). Tick your "
                 f"verdicts in <code>evidence/worksheet.md</code> and import them with <code>referencer.py worksheet "
                 f"{html.escape(paper.draft.name)} --import</code>.</p><ol>{items}</ol>")
    (paper.html_dir / "index.html").write_text(page(
        f"{paper.draft.stem}: citation evidence",
        f"<h1>Citation evidence</h1><div class=banner>{tally}. "
        f"<a href='manuscript.html'>Manuscript in verification mode</a></div>{fetch}"
        f"<h2>All citations</h2><table><tr><th>#</th><th>Section</th><th>Citing sentence</th><th>Cites</th><th>Status</th></tr>{rows}</table>"))


def evidence_page(paper, inst, res, entries):
    s, (a, b) = inst["sentence"], inst["target"]
    claim = (f"<span class=ctx>{html.escape(inst['before'])}</span> "
             f"<mark>{html.escape(s[:a])}<b>{html.escape(s[a:b])}</b>{html.escape(s[b:])}</mark> "
             f"<span class=ctx>{html.escape(inst['after'])}</span>")
    blocks = []
    for r in res["per_key"]:
        key = r["key"]
        parts = [f"<h3 id='key-{html.escape(key, quote=True)}'>@{html.escape(key)} <span class='badge {r['status']}'>"
                 f"{STATUS_TEXT.get(r['status'], r['status'])}</span></h3>",
                 f"<div class=ref>{html.escape(ref_text(entries.get(key)))}</div>"]
        if r.get("retracted"):
            parts.append(f"<div class=alert><b>This work has a retraction notice:</b> {html.escape(r['retracted'])}. "
                         f"Cite it only to discuss the retraction.</div>")
        if r.get("by_author"):
            parts.append("<p class=loc>Checked by the author against their own copy" +
                         (", with the passage below found in it by `assist`" if r.get("passages") else
                          "; no passage was kept") + ". The agent did not read this copy.</p>")
        if r.get("note"):
            parts.append(f"<p class=note>{html.escape(r['note'])}</p>")
        if r.get("secondary"):
            parts.append("<p class=problem>The cited work attributes this point to another source.</p>")
        meta_path = paper.fulltext / f"{key}.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        is_pdf = meta.get("format") == "pdf"
        if meta:
            version = meta.get("version", "unknown")
            link = f" · <a href='{html.escape(meta['url'])}' target=_blank>source ↗</a>" if meta.get("url") else ""
            cls = "problem" if version in ("third-party", "abstract", "unknown") else "loc"
            src = f", from {html.escape(meta['source'])}" if meta.get("source") else ""
            parts.append(f"<div class={cls}>Text read: {html.escape(VERSION_TEXT[version])}{src}{link}</div>")
            if meta.get("supplied_text"):
                parts.append("<div class=problem>This text was supplied as plain text, not extracted by the "
                             "script from a logged original file, so its fidelity to the paper rests on whoever "
                             "supplied it.</div>")
            if meta.get("ocr"):
                parts.append("<div class=loc>Text from OCR of a scanned PDF; the scan is kept and logged.</div>")
        for p in r.get("passages", []):
            if p.get("error"):
                parts.append(f"<blockquote class=bad>{html.escape(p['quote'])}"
                             f"<div class=problem>{html.escape(p['error'])}</div></blockquote>")
                continue
            if "chunk" not in p:  # from the author's own copy: checked there, not stored here
                parts.append(f"<blockquote>{html.escape(p['quote'])}<div class=loc>{html.escape(p['label'])}, "
                             f"matched against it by `assist` (its hash is in hashes.log)</div></blockquote>")
                continue
            href = f"../../fulltext/{key}.pdf#page={p['chunk'] + 1}" if is_pdf else f"../../fulltext/{key}.txt"
            parts.append(f"<blockquote>{html.escape(p['quote'])}"
                         f"<div class=loc><a href='{href}' target=_blank>{html.escape(p['label'])} ↗</a></div></blockquote>")
        if r["verdict"] == "no-fulltext":
            e = entries.get(key, {})
            url = f"https://doi.org/{e['DOI']}" if e.get("DOI") else e.get("URL")
            get = f" <a href='{html.escape(url, quote=True)}' target=_blank>Retrieve it ↗</a>" if url else ""
            parts.append(f"<p class=problem>The full text was not retrieved, so this citation is not verified.{get}</p>")
        if r["verdict"] == "unchecked":
            parts.append("<p class=problem>" + ("Only the abstract is available, and no assessment is recorded yet."
                                                if r.get("abstract") else
                                                "The full text is available but no passage has been recorded yet.")
                         + "</p>")
        blocks.append("".join(parts))
    problems = "".join(f"<p class=problem>{html.escape(p)}</p>" for p in res["problems"])
    doubts = "".join(f"<div class=alert><b>The claim itself looks doubtful</b>, whatever the cited work says: "
                     f"{html.escape(d)}</div>" for d in res["doubts"])
    if len(res["per_key"]) > 1:
        head = "<div class=keys>" + "".join(
            f"<a href='#key-{html.escape(r['key'], quote=True)}'>@{html.escape(r['key'])}</a> "
            f"<span class='badge {r['status']}'>{STATUS_TEXT.get(r['status'], r['status'])}</span>"
            for r in res["per_key"]) + "</div>"
    else:
        head = f"<h1><span class='badge {res['status']}'>{STATUS_TEXT[res['status']]}</span></h1>"
    body = (f"<p class=loc><a href='../manuscript.html#cite-{inst['id']}' onclick='{BACK_JS}'>← back to the manuscript</a> · "
            f"citation {inst['n']} · {html.escape(inst['section'])}</p>"
            f"{head}{doubts}{problems}"
            f"<div class=grid><div class='card claim'><h2>What the manuscript claims</h2><p>{claim}</p></div>"
            f"<div class=card><h2>What the cited work says</h2>{''.join(blocks)}</div></div>")
    return page(f"Citation {inst['n']}", body)


# ---------------------------------------------------------------------------------------
# Author-year drafts: a keyed copy.

_AY_PARTICLE = r"(?:(?:van|von|de|der|den|du|da|di|del|le|la|ter)\s+)*"
_AY_SURNAME = _AY_PARTICLE + r"[A-Z][^\W\d_][\w'\u2019.-]*"
_AY_JOIN = r"(?:\s*,\s*|,?\s+(?:and|&)\s+|\s*[\u2013\u2014]\s*)"
_AY_GROUP = (rf"(?<![\w'\u2019@-])(?P<first>{_AY_SURNAME})(?:\s+Foundation\s+Inc\.)?(?:{_AY_JOIN}{_AY_SURNAME})*"
             r"(?:\s+et\s+al\.?)?(?:['\u2019]s)?")
_AY_YEAR = r"(?:1[5-9]|20)\d\d[a-z]?"
AY_NARR = re.compile(rf"{_AY_GROUP}\s*\(\s*(?P<years>{_AY_YEAR}(?:\s*[,;]\s*{_AY_YEAR})*)(?:,\s*(?P<loc>[^()]*?))?\s*\)")
AY_BARE = re.compile(rf"{_AY_GROUP},?\s+(?P<years>{_AY_YEAR})\b")
AY_PIECE = re.compile(rf"(?P<pre>[^;]*?){_AY_GROUP},?\s+(?P<years>{_AY_YEAR}(?:\s*,\s*{_AY_YEAR})*)(?:,\s*(?P<loc>.*))?$", re.S)


def ay_index(entries):
    """(surname, year) -> key, from the bibliography: the first author's family name (with its
    particle), or the first word of an institution. A year suffix is read from the key
    ("oeis2026a"), so suffixed works must carry it there."""
    idx = {}
    for key, e in entries.items():
        a = (e.get("author") or e.get("editor") or [{}])[0]
        particle = a.get("non-dropping-particle") or a.get("dropping-particle") or ""
        names = {a.get("family", ""), f"{particle} {a.get('family', '')}".strip(),
                 re.split(r"[\s,]+", (a.get("literal") or "").strip())[0]}
        year = str(((e.get("issued") or {}).get("date-parts") or [[""]])[0][0])
        m = re.search(rf"{year}([a-z])$", key) if year else None
        for n in filter(None, names):
            idx[(n.casefold(), year + (m.group(1) if m else ""))] = key
    return idx


def ay_keys(idx, first, years):
    first = re.sub(r"['\u2019]s$", "", re.split(r"[\u2013\u2014]", first)[0])
    keys = [idx.get((first.casefold(), y)) for y in re.split(r"\s*[,;]\s*", years)]
    return keys if all(keys) else None


def keyify_text(text, idx, unmapped):
    """Rewrite author-year citations outside maths and code as pandoc citations."""
    def narrative(m):
        keys = ay_keys(idx, m.group("first"), m.group("years"))
        if not keys:
            unmapped.append(m.group(0))
            return m.group(0)
        loc = f" [{m.group('loc')}]" if m.group("loc") else ""
        return f"@{keys[0]}{loc}" if len(keys) == 1 else "[" + "; ".join("@" + k for k in keys) + "]"

    def parenthetical(m):
        parts = []
        for piece in re.split(r";\s*", m.group(1)):
            pm = AY_PIECE.match(piece.strip())
            keys = pm and ay_keys(idx, pm.group("first"), pm.group("years"))
            if not keys:
                if re.search(_AY_YEAR, piece) and re.search(r"[A-Z][a-z]", piece):
                    unmapped.append(m.group(0))
                return m.group(0)
            pre = pm.group("pre").strip()
            loc = f", {pm.group('loc').strip()}" if pm.group("loc") else ""
            parts += [(f"{pre} " if pre and i == 0 else "") + "@" + k + (loc if i == len(keys) - 1 else "")
                      for i, k in enumerate(keys)]
        return "[" + "; ".join(parts) + "]"

    def bare(m):
        # "see Burnside 1911", or a group the parenthesis pass could not split ("(A 2019, B 2026)"):
        # converted only when the surname and year name a work in the bibliography.
        keys = ay_keys(idx, m.group("first"), m.group("years"))
        return "; ".join("@" + k for k in keys) if keys else m.group(0)

    out = []
    for seg in re.split(r"(\$\$.*?\$\$|\$[^$]*\$|`[^`]*`)", text, flags=re.S):
        if seg.startswith(("$", "`")):
            out.append(seg)
            continue
        seg = AY_NARR.sub(narrative, seg)
        seg = re.sub(r"\(([^()]*\b" + _AY_YEAR + r"\b[^()]*)\)", parenthetical, seg)
        seg = AY_BARE.sub(bare, seg)
        out.append(seg)
    return "".join(out)


def cmd_keyify(paper, args):
    """`keyify DRAFT BIB`: for a Markdown draft that cites author-year in plain text ("Smith and
    Jones (2009)", "(Smith 2009; Jones et al. 2013, Theorem 2)") with a typed reference list,
    write DRAFT_keyed.md, in which those citations are pandoc citations against BIB, and point
    its YAML header at BIB. The draft itself is only read; the typed reference list is copied
    unchanged. Run the skill on the keyed copy."""
    if paper.is_tex or len(args.rest) != 1:
        sys.exit("keyify needs a Markdown DRAFT and the BIB built from its reference list")
    bib = Path(args.rest[0]).expanduser().resolve()
    entries = {e["id"]: e for e in json.loads(run(["pandoc", str(bib), "-f", "biblatex", "-t", "csljson"]))}
    idx = ay_index(entries)
    text = paper.draft.read_text()
    m = re.search(r"(?m)^#+\s*(?:\d+\.?\s*)?(?:References|Bibliography)\s*$", text)
    nxt = re.search(r"(?m)^#", text[m.end():]) if m else None
    a, b = (m.start(), m.end() + nxt.start()) if nxt else (m.start(), len(text)) if m else (len(text), len(text))
    unmapped = []
    pre, post = keyify_text(text[:a], idx, unmapped), keyify_text(text[b:], idx, unmapped)
    unmapped = [u for u in unmapped if u in pre or u in post]  # still there after every pass
    body = pre + text[a:b] + post
    rel = os.path.relpath(bib, paper.root)
    body = body.replace("---\n", f"---\nbibliography: {rel}\n", 1) if body.startswith("---\n") else \
        f"---\nbibliography: {rel}\n---\n\n" + body
    out = paper.draft.with_name(paper.draft.stem + "_keyed.md")
    out.write_text(body)
    used = Counter(re.findall(r"@([\w:.-]*\w)", pre + post))
    print(f"{sum(used[k] for k in entries)} citations of {sum(1 for k in entries if used[k])}/{len(entries)} "
          f"works keyed -> {out}")
    for k in sorted(k for k in entries if not used[k]):
        print(f"  never cited: @{k}")
    # A bibliography surname with its year in brackets a few words later ("McKay's digraph
    # archive (2026)") is probably a citation too loose to convert safely: list it.
    loose = []
    for (name, year), key in idx.items():
        for m in re.finditer(rf"(?i)(?<![@\w]){re.escape(name)}\b[^@()\n]{{1,40}}\(\s*{year}\s*\)", pre + post):
            loose.append(f"@{key}?: {m.group(0)}")
    for u in dict.fromkeys(unmapped):
        print(f"  not mapped (key it by hand in the copy): {u[:100]}")
    for u in dict.fromkeys(loose):
        print(f"  possible citation, not converted (check by hand): {u[:100]}")
    return 1 if unmapped or loose else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["init", "mode", "extract", "fetch", "add", "todo", "find",
                                        "locate", "record", "check", "build", "worksheet", "assist", "terms", "keyify"])
    ap.add_argument("draft")
    ap.add_argument("rest", nargs="*",
                    help="mode: final|verification; add: KEY FILE; find: KEY TERM...; record: KEY ID")
    ap.add_argument("--defaults", help="pandoc defaults file (found from the Makefile if omitted)")
    ap.add_argument("--evidence", help="evidence folder (default: evidence/ next to the draft)")
    ap.add_argument("--key", action="append", help="restrict fetch/todo to these keys")
    ap.add_argument("--refresh", action="store_true", help="fetch: download again")
    ap.add_argument("--width", type=int, default=300, help="find: context characters")
    ap.add_argument("--max", type=int, default=8, help="find: maximum hits per term")
    ap.add_argument("--url", help="add: where the file came from")
    ap.add_argument("--download", help="add: URL for the script to fetch itself (preferred over FILE)")
    ap.add_argument("--ocr", action="store_true", help="add: OCR a scanned PDF (keeps and logs the scan)")
    ap.add_argument("--title", help="add: title of a work the bibliography does not cite yet")
    ap.add_argument("--version", default="unknown", help=f"add: one of {VERSIONS}")
    ap.add_argument("--verdict", choices=VERDICTS, help="record: the verdict")
    ap.add_argument("--quote", action="append", help="record: a verbatim passage (repeatable)")
    ap.add_argument("--note", help="record: why, for any verdict but supported")
    ap.add_argument("--secondary", action="store_true",
                    help="record: the passage reports another work's result")
    ap.add_argument("--pdf", help="assist: the author's own copy of the paper")
    ap.add_argument("--all", action="store_true", help="assist: also redo citations already decided")
    ap.add_argument("--import", dest="import_", action="store_true",
                    help="worksheet: record the boxes the author ticked")
    ap.add_argument("--doubt", help="record: the claim itself looks false, whatever the source says; why")
    args = ap.parse_args()
    paper = Paper(args.draft, args.defaults, args.evidence)
    if args.command == "find":
        if len(args.rest) < 2:
            ap.error("find needs KEY and at least one search term")
        args.key, args.terms = args.rest[0], args.rest[1:]
    if args.command == "record" and not args.verdict:
        ap.error("record needs --verdict")
    commands = {"init": cmd_init, "mode": cmd_mode, "extract": cmd_extract, "fetch": cmd_fetch,
                "add": cmd_add, "todo": cmd_todo, "find": cmd_find, "locate": cmd_locate, "record": cmd_record,
                "check": cmd_check, "build": cmd_build, "worksheet": cmd_worksheet,
                "assist": cmd_assist, "terms": cmd_terms, "keyify": cmd_keyify}
    sys.exit(commands[args.command](paper, args) or 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Score a HerdingChickens blog draft against rules.toml and print a Markdown checklist report.

    python3 check_post.py POST.md [--site-blog DIR] [--sources LEDGER.json] [--check-links] [--out REPORT.md]

--site-blog   the website's content/blog folder; enables the slug, keyword and related-link checks
--sources     the post's sources ledger (default: POST.sources.json beside the post)
--check-links fetch every external link and record its HTTP status

Each rule is reported as PASS, FAIL, WARN, MANUAL (a person answers it), SITE (a site-wide
property, checked once), or OFF (switched off in rules.toml; for automatic rules the report
still says what the result would have been). Exit status is 1 when any rule that is on FAILs.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blog  # noqa: E402

LINK_TIMEOUT_S = 20
USER_AGENT = "Mozilla/5.0 (compatible; hc-blog-writer link check)"
CTA_URL_RE = re.compile(r"t\.me/HerdingChickensBot|^/early-access|^/$|^https://herdingchickens\.com/?$")
CONTACT_URL_RE = re.compile(r"^(/contact|https://(www\.)?herdingchickens\.com/contact)\b")
AUTHOR_SLOT_RE = re.compile(r"\[AUTHOR:[^\]]*\]")


class Ctx:
    def __init__(self, path, rules, site_blog, ledger_path, check_links):
        self.path = Path(path)
        self.fm, self.body = blog.read_post(path)
        self.sec = blog.sections(self.body)
        self.rules = rules
        self.kw = str(self.fm.get("focus_keyword", "")).lower().strip()
        self.site = blog.site_posts(site_blog, self.fm.get("slug")) if site_blog else None
        self.all_links = blog.links(self.body)
        self.external = sorted({u for img, _, u in self.all_links if not img and not blog.is_internal(u)})
        # Citations: external links other than our own product links, which need no source.
        self.cited = [u for u in self.external if not CTA_URL_RE.search(u)]
        self.ledger_path = Path(ledger_path) if ledger_path else self.path.with_suffix(".sources.json")
        self.ledger = json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else None
        self.link_status = {u: fetch_status(u) for u in self.external} if check_links else None

    def body_words(self):
        return blog.words(self.sec["prose"])


PUBMED_RE = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)")
PMC_RE = re.compile(r"ncbi\.nlm\.nih\.gov/(?:pmc/)?articles/PMC(\d+)")
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db={db}&id={id}&retmode=json"


def ncbi_record(db, rid):
    """PubMed and PMC answer any ID with a JavaScript page (HTTP 200 or 203), so a made-up PMID looks
    alive to a plain fetch. Ask NCBI's E-utilities instead: returns 200 and the title, or 404."""
    with urllib.request.urlopen(ESUMMARY.format(db=db, id=rid), timeout=LINK_TIMEOUT_S) as r:
        rec = json.load(r).get("result", {}).get(rid, {})
    return (404, None) if not rec or "error" in rec else (200, rec.get("title"))


def fetch_status(url):
    """HTTP status of a link, or for PubMed/PMC links the existence of the record."""
    for rx, db in ((PUBMED_RE, "pubmed"), (PMC_RE, "pmc")):
        m = rx.search(url)
        if m:
            status, title = ncbi_record(db, m.group(1))
            return status if title is None else f"200 ({title})"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=LINK_TIMEOUT_S) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, TimeoutError) as e:
        return f"unreachable ({getattr(e, 'reason', e)})"


def count_phrase(text, phrase):
    return len(re.findall(rf"\b{re.escape(phrase)}\b", text, re.I))


# ---------------------------------------------------------------- the checks
# Each returns (status, detail). Status is PASS, FAIL or WARN.

def frontmatter_valid(c, r):
    missing = [k for k in r["required"] if k not in c.fm or c.fm[k] in (None, "")]
    bad = []
    if c.fm.get("cluster") not in r["clusters"]:
        bad.append(f"cluster '{c.fm.get('cluster')}' not in {r['clusters']}")
    if c.fm.get("tier") not in r["tiers"]:
        bad.append(f"tier '{c.fm.get('tier')}' not in {r['tiers']}")
    if missing or bad:
        return "FAIL", "; ".join(([f"missing: {', '.join(missing)}"] if missing else []) + bad)
    return "PASS", "all required fields present"


def unpublished(c, r):
    return ("PASS", "published: false") if c.fm.get("published") is False else ("FAIL", f"published: {c.fm.get('published')}")


def unique_focus_keyword(c, r):
    if c.site is None:
        return "WARN", "not checked: pass --site-blog"
    clash = [p["slug"] for p in c.site if str(p.get("focus_keyword", "")).lower().strip() == c.kw]
    return ("FAIL", f"already the focus keyword of: {', '.join(clash)}") if clash else ("PASS", f"'{c.kw}' unused as a focus keyword")


def unique_slug(c, r):
    if c.site is None:
        return "WARN", "not checked: pass --site-blog"
    clash = [p["file"] for p in c.site if p.get("slug") == c.fm.get("slug")]
    return ("FAIL", f"slug used by {', '.join(clash)}") if clash else ("PASS", "slug is new")


def related_exist(c, r):
    if c.site is None:
        return "WARN", "not checked: pass --site-blog"
    known = {p["slug"] for p in c.site if p.get("published") is True}  # a draft would 404
    wanted = set(c.fm.get("related") or [])
    wanted |= {u.split("/resources/")[1].split("#")[0].split("?")[0]
               for _, _, u in c.all_links if "/resources/" in u and "/resources/topics/" not in u}
    missing = sorted(wanted - known)
    return ("FAIL", f"no such post: {', '.join(missing)}") if missing else ("PASS", f"{len(wanted)} internal post links resolve")


def title_has_keyword(c, r):
    t = str(c.fm.get("title", ""))
    return ("PASS", t) if c.kw and c.kw in t.lower() else ("FAIL", f"'{c.kw}' not in title '{t}'")


def title_length(c, r):
    n = len(str(c.fm.get("title", "")))
    return ("PASS" if n <= r["max_chars"] else "FAIL"), f"{n} characters (cap {r['max_chars']})"


def slug_short_keyword(c, r):
    slug = str(c.fm.get("slug", ""))
    kw_words = [w for w in c.kw.split() if w]
    missing = [w for w in kw_words if w not in slug.split("-")]
    if len(slug) > r["max_chars"] or missing:
        return "FAIL", f"{len(slug)} characters (cap {r['max_chars']})" + (f"; keyword words missing: {missing}" if missing else "")
    return "PASS", f"/{slug} ({len(slug)} characters)"


def author_bio(c, r):
    a = c.fm.get("author")
    authors = c.rules["frontmatter_valid"]["authors"]
    return ("PASS", f"author: {a}") if a in authors else ("FAIL", f"author '{a}' has no bio page (known: {authors})")


def _word_count(c):
    return len(c.body_words())


def word_count_1500(c, r):
    n = _word_count(c)
    return ("PASS" if n >= r["min_words"] else "FAIL"), f"{n} body words (minimum {r['min_words']})"


def word_count_in_tier(c, r):
    n = _word_count(c)
    tier = c.fm.get("tier")
    if tier not in r:
        return "FAIL", f"unknown tier '{tier}'"
    lo, hi = r[tier]
    if lo <= n <= hi:
        return "PASS", f"{n} body words, {tier} range {lo}-{hi}"
    return "WARN", f"{n} body words, outside the {tier} range {lo}-{hi}: change the tier or the post, never pad"


def images_5plus(c, r):
    n = sum(1 for img, _, _ in c.all_links if img) + (1 if c.fm.get("cover") else 0)
    return ("PASS" if n >= r["min_images"] else "FAIL"), f"{n} image(s) including the cover"


def cover_alt_text(c, r):
    if not c.fm.get("cover"):
        return "WARN", "no cover image set yet (a person adds the photo); add cover_alt with it"
    return ("PASS", "cover_alt present") if str(c.fm.get("cover_alt", "")).strip() else ("FAIL", "cover has no cover_alt")


def inline_image_alt(c, r):
    imgs = [(label, u) for img, label, u in c.all_links if img]
    bad = [u for label, u in imgs if not label.strip()]
    return ("FAIL", f"images without alt text: {bad}") if bad else ("PASS", f"{len(imgs)} inline image(s), all with alt text")


def table_of_contents(c, r):
    has = bool(re.search(r"^##+ (table of )?contents\b", c.body, re.I | re.M))
    return ("PASS", "contents list present") if has else ("FAIL", "no contents list")


def _h2s(c):
    return [h for lvl, h in blog.HEADING_RE.findall(c.sec["main"]) if lvl == "##"]


def keyword_in_h2(c, r):
    hits = [h for h in _h2s(c) if c.kw in h.lower()]
    return ("PASS", f"'{hits[0]}'") if hits else ("FAIL", f"no '## ' heading contains '{c.kw}'")


def short_paragraphs(c, r):
    long_ones = [(len(blog.sentences(p)), p[:50]) for p in blog.paragraphs(c.sec["prose"])]
    long_ones = [(n, s) for n, s in long_ones if n > r["max_sentences"]]
    if long_ones:
        return "WARN", "; ".join(f"{n} sentences: '{s}...'" for n, s in long_ones)
    return "PASS", f"every paragraph has at most {r['max_sentences']} sentences"


def lists_where_helpful(c, r):
    has_list = c.sec["short"] is not None or re.search(r"^(\s*[-*]|\s*\d+\.) ", c.sec["prose"], re.M)
    return ("PASS", "short block or list present") if has_list else ("FAIL", "no list and no short block")


def _internal(c, text):
    return [u for img, _, u in blog.links(text) if not img and blog.is_internal(u) and not CTA_URL_RE.search(u)
            and not CONTACT_URL_RE.search(u)]


def internal_links_5(c, r):
    n = len(_internal(c, c.sec["prose"]))
    return ("PASS" if n >= r["min_links"] else "FAIL"), f"{n} internal link(s) in the body"


def internal_links_min(c, r):
    body = len(_internal(c, c.sec["prose"]))
    total = body + len(_internal(c, c.sec["keep_reading"]))
    ok = total >= r["min_total"] and body >= r["min_in_body"]
    return ("PASS" if ok else "FAIL"), f"{total} internal links, {body} in the body (need {r['min_total']}, {r['min_in_body']})"


def external_links_3(c, r):
    n = len(c.external)
    return ("PASS" if n >= r["min_links"] else "FAIL"), f"{n} external link(s)"


def one_cta(c, r):
    paras = [p for p in re.split(r"\n\s*\n", c.sec["prose"]) if any(CTA_URL_RE.search(u) for _, _, u in blog.links(p))]
    n = len(paras)
    if n == 0:
        return "WARN", "no product invitation (bot or early access) in the body"
    return ("PASS" if n <= r["max_cta_paragraphs"] else "FAIL"), f"{n} paragraph(s) with a product link"


def meta_description(c, r):
    m = " ".join(str(c.fm.get("meta_description", "")).split())
    n = len(m)
    probs = []
    if not r["min_chars"] <= n <= r["max_chars"]:
        probs.append(f"{n} characters (range {r['min_chars']}-{r['max_chars']})")
    if c.kw not in m.lower():
        probs.append(f"'{c.kw}' missing")
    return ("FAIL", "; ".join(probs)) if probs else ("PASS", f"{n} characters, keyword present")


def keyword_in_opening(c, r):
    opening = " ".join(c.body_words()[: r["within_words"]]).lower()
    ok = c.kw in opening
    return ("PASS" if ok else "FAIL"), f"'{c.kw}' {'found' if ok else 'not found'} in the first {r['within_words']} words"


def no_keyword_stuffing(c, r):
    text = blog.plain(c.sec["prose"] + c.sec["faq"])
    n = count_phrase(text, c.kw)
    per100 = 100 * n / max(1, len(blog.words(text)))
    return ("PASS" if per100 <= r["max_per_100_words"] else "FAIL"), f"'{c.kw}' {n} times, {per100:.2f} per 100 words (cap {r['max_per_100_words']})"


def short_version_early(c, r):
    if c.sec["short"] is None:
        return "FAIL", "no ```short block"
    before = c.sec["main"].split("```short")[0]
    start = len(blog.words(before))
    rows = [ln for ln in c.sec["short"].splitlines() if "|" in ln]
    probs = []
    if start > r["within_words"]:
        probs.append(f"starts after word {start} (cap {r['within_words']})")
    if not r["min_rows"] <= len(rows) <= r["max_rows"]:
        probs.append(f"{len(rows)} rows (range {r['min_rows']}-{r['max_rows']})")
    return ("FAIL", "; ".join(probs)) if probs else ("PASS", f"starts at word {start}, {len(rows)} rows")


def do_this_today(c, r):
    if c.sec["short"] is None:
        return "FAIL", "no ```short block"
    rows = [ln for ln in c.sec["short"].splitlines() if "|" in ln]
    last = rows[-1].split("|")[0].strip() if rows else ""
    return ("PASS", "last row is 'Do this today'") if last.lower() == "do this today" else ("FAIL", f"last row is '{last}'")


def question_heading(c, r):
    qs = [h for h in _h2s(c) if h.rstrip().endswith("?")]
    return ("PASS" if len(qs) >= r["min"] else "FAIL"), (f"'{qs[0]}'" if qs else "no '## ' heading ends with '?'")


def _faq_items(c):
    """Same pattern as parseFaqFromContent in the website's lib/blog/index.ts."""
    m = re.search(r"## FAQ[^\n]*\n([\s\S]*)", c.sec["faq"])
    if not m:
        return []
    return re.findall(r"\*\*(.+?)\*\*\n+([\s\S]+?)(?=\n\*\*|\n---|\n## |$)", m.group(1).rstrip() + "\n")


def faq_block(c, r):
    items = _faq_items(c)
    n = len(items)
    if not n:
        return "FAIL", "no '## FAQ' section with **bold questions**"
    return ("PASS" if r["min_items"] <= n <= r["max_items"] else "FAIL"), f"{n} question(s) (range {r['min_items']}-{r['max_items']})"


def faq_answers_standalone(c, r):
    probs = []
    for q, a in _faq_items(c):
        n = len(blog.words(a))
        if n > r["max_words"]:
            probs.append(f"'{q[:40]}': {n} words")
        if re.match(r"\s*(it|this|that|they)\b", a, re.I):
            probs.append(f"'{q[:40]}': opens with a pronoun")
    return ("FAIL", "; ".join(probs)) if probs else ("PASS", f"answers under {r['max_words']} words, none opening with a pronoun")


def statistics_or_named_source(c, r):
    body_ext = {u for img, _, u in blog.links(c.sec["prose"] + c.sec["faq"]) if not img and not blog.is_internal(u)}
    n = len(body_ext)
    return ("PASS" if n >= r["min_sources"] else "FAIL"), f"{n} external source(s) linked in the body"


def no_deficit_framing(c, r):
    text = blog.plain(c.sec["prose"] + c.sec["faq"] + (c.sec["short"] or "") + str(c.fm.get("title", ""))
                      + " " + str(c.fm.get("meta_description", "")))
    hits = [w for w in r["banned"] if re.search(rf"\b{re.escape(w)}", text, re.I)]
    return ("FAIL", f"found: {', '.join(hits)}") if hits else ("PASS", "none of the listed terms")


def small_words(c, r):
    text = blog.plain(c.sec["prose"] + c.sec["faq"] + (c.sec["short"] or ""))
    listed = [w for w in r["flag"] if re.search(rf"\b{re.escape(w)}", text, re.I)]
    allowed = {w.lower() for w in r["allowed_long"]}
    longw = sorted({w for w in re.findall(r"[A-Za-z]+", text) if len(w) >= r["long_word_chars"] and w.lower() not in allowed})
    detail = []
    if listed:
        detail.append(f"listed: {', '.join(listed)}")
    if longw:
        detail.append(f"long: {', '.join(longw)}")
    return ("WARN", "; ".join(detail)) if detail else ("PASS", "no listed or very long words")


def contact_link(c, r):
    text = c.sec["main"] + c.sec["faq"]
    probs = []
    for phrase in r["phrases"]:
        for m in re.finditer(re.escape(phrase), text, re.I):
            # The phrase must sit inside the label of a link to the contact page.
            linked = any(m.start() >= lm.start() and m.end() <= lm.start() + 1 + len(lm.group(2)) + 1
                         and CONTACT_URL_RE.search(lm.group(3)) for lm in blog.LINK_RE.finditer(text))
            if not linked:
                probs.append(f"'{text[m.start():m.end()]}' not linked to /contact")
    return ("FAIL", "; ".join(probs)) if probs else ("PASS", "every contact phrase links to /contact")


def sources_verified(c, r):
    if not c.cited:
        return "PASS", "no external citations"
    if c.ledger is None:
        return "FAIL", f"no sources ledger at {c.ledger_path.name}"
    entries = {e.get("url"): e for e in c.ledger}
    probs = [f"not in ledger: {u}" for u in c.cited if u not in entries]
    probs += [f"no supporting passage: {u}" for u in c.cited
              if u in entries and not str(entries[u].get("passage", "")).strip()]
    warn, titles = [], []
    if c.link_status is not None:
        for u, s in c.link_status.items():
            if isinstance(s, str) and s.startswith("200 ("):
                titles.append(f"{u} is '{s[5:-1]}'")
                continue
            if isinstance(s, int) and s < 400:
                continue
            if s in (401, 403, 429):
                warn.append(f"{u} answered {s} to the script (a bot wall); open it in a browser")
            else:
                probs.append(f"{u} -> {s}")
    if probs:
        return "FAIL", "; ".join(probs)
    checked = "links fetched" if c.link_status is not None else "links not fetched (use --check-links)"
    detail = f"{len(c.cited)} cited link(s) in the ledger; {checked}"
    detail += "".join(f"; {t}" for t in titles + warn)
    return ("WARN" if warn else "PASS"), detail


def no_ai_vocabulary(c, r):
    text = blog.plain(c.sec["prose"] + c.sec["faq"] + (c.sec["short"] or ""))
    hits = [w for w in r["flag"] if re.search(rf"\b{re.escape(w)}", text, re.I)]
    return ("WARN", f"found: {', '.join(hits)}") if hits else ("PASS", "none of the listed words")


def em_dash_cap(c, r):
    n = (c.sec["prose"] + c.sec["faq"] + (c.sec["short"] or "")).count("—")
    return ("PASS" if n <= r["max"] else "FAIL"), f"{n} em-dash(es) (cap {r['max']})"


def idiom_cap(c, r):
    text = blog.plain(c.sec["prose"] + c.sec["faq"] + (c.sec["short"] or ""))
    hits = [i for i in r["idioms"] if re.search(rf"\b{re.escape(i)}\b", text, re.I)]
    return ("PASS" if len(hits) <= r["max"] else "FAIL"), (f"listed idioms: {', '.join(hits)}" if hits else "no listed idioms")


def disclaimer(c, r):
    d = c.sec["disclaimer"]
    ok = "not medical advice" in d.lower() and "nhs.uk" in d
    return ("PASS", "footer present") if ok else ("FAIL", "missing the not-medical-advice footer with an NHS link")


def author_slots_filled(c, r):
    slots = AUTHOR_SLOT_RE.findall(c.body)
    return ("WARN", f"{len(slots)} open slot(s): " + "; ".join(s[:60] for s in slots)) if slots else ("PASS", "no open slots")


CHECKS = {f.__name__: f for f in [
    frontmatter_valid, unpublished, unique_focus_keyword, unique_slug, related_exist, title_has_keyword,
    title_length, slug_short_keyword, author_bio, word_count_1500, word_count_in_tier, images_5plus,
    cover_alt_text, inline_image_alt, table_of_contents, keyword_in_h2, short_paragraphs,
    lists_where_helpful, internal_links_5, internal_links_min, external_links_3, one_cta, meta_description,
    keyword_in_opening, no_keyword_stuffing, short_version_early, do_this_today, question_heading,
    faq_block, faq_answers_standalone, statistics_or_named_source, no_deficit_framing, small_words,
    contact_link, sources_verified, no_ai_vocabulary, em_dash_cap, idiom_cap, disclaimer,
    author_slots_filled]}


def evaluate(ctx):
    rows = []
    for rid, r in ctx.rules.items():
        kind = r["kind"]
        if kind == "auto" and rid not in CHECKS:
            raise SystemExit(f"rules.toml lists auto rule '{rid}' but check_post.py has no check for it")
        if kind == "auto":
            status, detail = CHECKS[rid](ctx, r)
            if not r["on"]:
                status, detail = "OFF", f"would be {status}: {detail}"
        elif kind == "site":
            status, detail = ("SITE" if r["on"] else "OFF"), "site-wide; not checked per post"
        else:
            status, detail = ("MANUAL" if r["on"] else "OFF"), "answer by hand in the report"
        rows.append((rid, r["source"], status, detail, r["why"]))
    unknown = set(CHECKS) - set(ctx.rules)
    if unknown:
        raise SystemExit(f"check_post.py has checks with no rule in rules.toml: {sorted(unknown)}")
    return rows


def render(ctx, rows):
    counts = {}
    for _, _, s, _, _ in rows:
        counts[s] = counts.get(s, 0) + 1
    order = ["FAIL", "WARN", "MANUAL", "PASS", "SITE", "OFF"]
    out = [f"# Checklist report: {ctx.path.name}", "",
           f"Focus keyword: **{ctx.kw}** · title: {ctx.fm.get('title')} · tier: {ctx.fm.get('tier')} · "
           f"{len(ctx.body_words())} body words", "",
           "Summary: " + ", ".join(f"{counts[s]} {s}" for s in order if s in counts), "",
           "| Rule | From | Result | Detail | Why the rule is on/off |", "|---|---|---|---|---|"]
    for rid, src, status, detail, why in sorted(rows, key=lambda x: order.index(x[2])):
        out.append(f"| `{rid}` | {src} | **{status}** | {detail.replace('|', '/')} | {why.replace('|', '/')} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("post")
    ap.add_argument("--site-blog", help="the website's content/blog folder")
    ap.add_argument("--sources", help="sources ledger JSON (default: POST.sources.json)")
    ap.add_argument("--check-links", action="store_true", help="fetch every external link")
    ap.add_argument("--rules", default=str(blog.RULES_FILE))
    ap.add_argument("--out", help="write the report here as well as to stdout")
    a = ap.parse_args()
    ctx = Ctx(a.post, blog.load_rules(a.rules), a.site_blog, a.sources, a.check_links)
    rows = evaluate(ctx)
    report = render(ctx, rows)
    print(report)
    if a.out:
        Path(a.out).write_text(report, encoding="utf-8")
    sys.exit(1 if any(s == "FAIL" for _, _, s, _, _ in rows) else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""LitReviewer ledger: search, record, assess and render a project's literature review.

Everything lives in <project>/litreview/:
  brief.json     the project's question, targets (T1..) and results so far (A1..), written by the agent
  ledger.json    every item ever seen, its verdict and history, and every search run
  synthesis.md   the agent's short reading of what the red and amber items mean for the project
  index.html     the interactive page, rebuilt from the three files above by `build`

Items enter the ledger only through a tool call that saw them (an API search, a citation expansion,
or `add`, which resolves the URL, DOI or arXiv id itself). Titles, dates and links therefore come
from the source, never from memory. Standard library only.
"""

import argparse
import datetime as dt
import difflib
import hashlib
import importlib.util
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "page.html"
UA = "LitReviewer/1.0 (literature review skill; stdlib urllib)"

RELEVANCE = ["red", "amber", "green", "irrelevant", "own"]
TYPES = ["paper", "preprint", "post", "repo", "dataset", "talk", "thesis", "book", "other"]
OVERLAP_VERDICTS = ["done", "partial", "competing", "related"]
BASES = ["abstract", "fulltext", "page", "citation", "secondary"]

# ---------------------------------------------------------------- utilities


def die(msg):
    sys.exit(f"litreview: {msg}")


def today():
    return dt.date.today().isoformat()


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def http_get(url, headers=None, retries=4, timeout=40, first_delay=3.0):
    """GET with backoff on 429/5xx. Returns (status, final_url, body_text)."""
    hdrs = {"User-Agent": UA}
    hdrs.update(headers or {})
    delay = first_delay
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.geturl(), r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                print(f"  HTTP {e.code} from {urllib.parse.urlparse(url).netloc}; retrying in {delay:.0f} s",
                      file=sys.stderr)
                time.sleep(delay)
                delay *= 2
                continue
            return e.code, url, e.read().decode("utf-8", "replace") if e.fp else ""
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return 0, url, str(e)
    return 0, url, "retries exhausted"


def first_date(dates):
    """Earliest date, ignoring year-only placeholders (YYYY-01-01) when a precise date exists."""
    ds = sorted(d for d in dates if d)
    precise = [d for d in ds if not d.endswith("-01-01")]
    return (precise or ds or [None])[0]


def norm_title(t):
    t = re.sub(r"<[^>]+>", " ", t or "").lower()
    for a, b in (("≤", " le "), ("≥", " ge "), ("\\leq", " le "), ("\\geq", " ge "), ("\\le", " le "),
                 ("\\ge", " ge "), ("−", "-")):
        t = t.replace(a, b)
    t = re.sub(r"\\[a-z]+", " ", t)  # remaining LaTeX commands (\mathrm, \left, ...)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def norm_doi(d):
    if not d:
        return None
    d = d.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    return d or None


ARXIV_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:)?(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?",
                      re.I)


def norm_arxiv(a):
    if not a:
        return None
    m = ARXIV_RE.search(a.strip())
    return m.group(1) if m else None


def arxiv_from_doi(d):
    d = norm_doi(d)
    if d and d.startswith("10.48550/arxiv."):
        return d[len("10.48550/arxiv."):]
    return None


# ---------------------------------------------------------------- the Referencer's quote checker

_REF = {}


def referencer():
    """The Referencer skill's module, from its sibling folder: one quote checker and one licence
    check for both skills, so a passage shown here is verified exactly as a citation is there."""
    if "m" not in _REF:
        path = SKILL_DIR.parent / "referencer" / "scripts" / "referencer.py"
        if not path.exists():
            die(f"the Referencer skill is needed for passages and full texts and was not found at {path}")
        spec = importlib.util.spec_from_file_location("referencer", path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _REF["m"] = m
    return _REF["m"]


def slug(key):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", key)


def held_text(project, key):
    """(chunks, labels, meta) of the text held for an item, or None."""
    d = lr_dir(project) / "fulltext"
    t, m = d / f"{slug(key)}.txt", d / f"{slug(key)}.json"
    if not (t.exists() and m.exists()):
        return None
    meta = json.loads(m.read_text())
    return t.read_text().split("\f"), meta["labels"], meta


def verify_passage(project, it, quote):
    """Where a quote sits in the item's held text (or its abstract): (label, link), or raises ValueError."""
    ref = referencer()
    held = held_text(project, it["key"])
    if held:
        chunks, labels, meta = held
        idx, err = ref.FullText.from_chunks(it["key"], chunks, labels).locate(quote)
        if err:
            raise ValueError(f"{err} (checked against litreview/fulltext/{slug(it['key'])}.txt)")
        label = labels[idx]
        link = meta["url"] + (f"#page={label[3:]}" if meta.get("format") == "pdf" and label.startswith("p. ") else "")
        return label, link
    if it.get("abstract") and it.get("abstract_by") != "agent" and len(quote) >= ref.MIN_QUOTE_CHARS \
            and ref.normalise(quote) in ref.normalise(it["abstract"]):
        return "abstract", it["url"]
    raise ValueError("no text held to check it against: run `fulltext` (open copies only), or quote the abstract")


def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.geturl()


def cmd_fulltext(a):
    """Hold an item's open full text (PDF or web page) so passages can be checked against it."""
    led = load(a.project)
    it = led["items"].get(a.key) or die(f"{a.key} is not in the ledger")
    ref = referencer()
    d = lr_dir(a.project) / "fulltext"
    d.mkdir(exist_ok=True)
    doi = it["dois"][0] if it["dois"] else None
    page_url = (a.url or it["url"]).split("#")[0]
    for other in led["items"].values():  # anchors on one records page share a single download
        held = held_text(a.project, other["key"]) if other["key"] != a.key and other.get("fulltext", {}).get("status") == "held" else None
        if held and held[2]["url"].split("#")[0] == page_url and held[2]["format"] == "html" and not a.file:
            src = d / slug(other["key"])
            Path(f"{d / slug(a.key)}.txt").write_text(Path(f"{src}.txt").read_text())
            Path(f"{d / slug(a.key)}.json").write_text(Path(f"{src}.json").read_text())
            it["fulltext"] = dict(other["fulltext"])
            save(a.project, led)
            print(f"{a.key}: reused the page text already held for {other['key']}")
            return
    if a.file:
        data, url = Path(a.file).read_bytes(), a.url or it["url"]
    else:
        url = a.url or (f"https://arxiv.org/pdf/{it['arxiv']}" if it.get("arxiv") else None)
        if not url:
            die("no open copy known: pass --url to one (an arXiv PDF, an author's copy, an open-access page)")
        try:
            data, url = fetch_bytes(url)
        except (urllib.error.URLError, TimeoutError) as e:
            die(f"could not download {url}: {e}")
    base = d / slug(a.key)
    if data[:5] == b"%PDF-":
        pdf = Path(f"{base}.pdf")
        pdf.write_bytes(data)
        v = ref.licence(pdf, doi)
        if v and v["refused"]:
            pdf.unlink()
            it["fulltext"] = {"status": "refused", "why": ref.refusal_text(v)}
            save(a.project, led)
            die(f"{a.key}: {ref.refusal_text(v)}; not extracted. Judge it from the abstract and list it "
                f"for the author to check.")
        chunks, labels = ref.pdf_chunks(pdf)
        fmt = "pdf"
    else:
        if doi and it["type"] == "paper":
            v = ref.licence(doi)
            if v and v["refused"]:
                die(f"{a.key}: {ref.refusal_text(v)}; not extracted")
        page = data.decode("utf-8", "replace")
        page = re.sub(r"(?is)<(script|style|nav|footer)[^>]*>.*?</\1>", " ", page)
        text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", page))
        chunks, labels, fmt, v = [re.sub(r"[ \t]+", " ", text)], ["page"], "html", None
    Path(f"{base}.txt").write_text("\f".join(chunks))
    meta = {"format": fmt, "labels": labels, "url": url, "fetched": now(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "licence": (v or {}).get("rights") or (v or {}).get("verdict") or "not checked"}
    Path(f"{base}.json").write_text(json.dumps(meta, indent=1))
    it["fulltext"] = {"status": "held", "url": url, "parts": len(chunks), "licence": meta["licence"]}
    save(a.project, led)
    print(f"{a.key}: {len(chunks)} {'pages' if fmt == 'pdf' else 'part'} held from {url} (licence: {meta['licence']})")


def cmd_find(a):
    """Rank passages of an item's held text by search terms, to find the one that shows the overlap."""
    led = load(a.project)
    if a.key not in led["items"]:
        die(f"{a.key} is not in the ledger")
    held = held_text(a.project, a.key)
    if not held:
        die(f"no text held for {a.key}; run `fulltext` first")
    ref = referencer()
    for score, label, text, hits in ref.rank_passages(ref.passage_windows(held[0], held[1]),
                                                       [t.lower() for t in a.terms], k=a.k):
        print(f"[{label}] {text}\n")


# ---------------------------------------------------------------- ledger


def lr_dir(project):
    return Path(project).expanduser().resolve() / "litreview"


def load(project):
    path = lr_dir(project) / "ledger.json"
    if not path.exists():
        die(f"no ledger at {path}; run `init` first")
    return json.loads(path.read_text())


def save(project, led):
    path = lr_dir(project) / "ledger.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(led, indent=1, ensure_ascii=False))
    tmp.replace(path)


def load_brief(project):
    path = lr_dir(project) / "brief.json"
    if not path.exists():
        die(f"no brief at {path}; write it first (see SKILL.md, step 1)")
    b = json.loads(path.read_text())
    for field in ("name", "mode", "active", "summary", "targets"):
        if field not in b:
            die(f"brief.json lacks '{field}'")
    if b["mode"] not in ("paper", "broad"):
        die("brief.json: mode must be 'paper' or 'broad'")
    ids = [t["id"] for t in b["targets"]] + [a["id"] for a in b.get("achieved", [])]
    if len(ids) != len(set(ids)):
        die("brief.json: target/achieved ids must be unique")
    if b["active"] and not b.get("achieved"):
        print("  note: an active project with no results of its own yet ('achieved' empty)", file=sys.stderr)
    return b


def project_references(project, brief):
    """DOIs, arXiv ids and normalised titles of the works the project already cites, from the files
    named in brief.json "references" (.bib, Markdown or plain text), so known items are marked."""
    dois, arx, titles = set(), set(), set()
    for rel in brief.get("references", []):
        path = Path(project).expanduser() / rel
        if not path.exists():
            die(f"brief.json references {rel}, which does not exist")
        text = path.read_text(errors="replace")
        dois |= {norm_doi(d).rstrip(".,;}") for d in re.findall(r"10\.\d{4,9}/[^\s\"<>{},]+", text)}
        arx |= {norm_arxiv(m) for m in re.findall(r"\b\d{4}\.\d{4,5}\b", text)}
        for t in re.findall(r"(?im)^\s*title\s*=\s*[{\"](.+?)[}\"]\s*,?\s*$", text):
            if len(norm_title(t)) > 20:
                titles.add(norm_title(t))
    return dois, arx, titles


def mark_known(project, led, brief):
    dois, arx, titles = project_references(project, brief)
    n = 0
    for it in led["items"].values():
        known = bool(set(it["dois"]) & dois or (it.get("arxiv") and it["arxiv"] in arx)
                     or norm_title(it["title"]) in titles)
        it["known"] = known
        n += known
    return n


def current_run(led):
    if not led["runs"]:
        die("no run open; run `run` first")
    return led["runs"][-1]


def find_key(led, doi=None, arxiv=None, title=None):
    """Match by DOI or arXiv id; by title only between two scholarly records (each with a DOI or
    arXiv id), since a web page titled like a paper ("The No-Three-In-Line Problem") is not that paper."""
    idx = led["index"]
    for probe in (f"doi:{doi}" if doi else None, f"arxiv:{arxiv}" if arxiv else None):
        if probe and probe in idx:
            return idx[probe]
    if title and (doi or arxiv) and len(norm_title(title)) > 25:
        k = idx.get(f"title:{norm_title(title)}")
        if k and (led["items"][k]["dois"] or led["items"][k].get("arxiv")):
            print(f"  note: merged by matching title into {k}: {led['items'][k]['title'][:70]}", file=sys.stderr)
            return k
    return None


def index_item(led, it):
    idx = led["index"]
    for d in it.get("dois", []):
        idx[f"doi:{d}"] = it["key"]
    if it.get("arxiv"):
        idx[f"arxiv:{it['arxiv']}"] = it["key"]
    if len(norm_title(it["title"])) > 25:
        idx[f"title:{norm_title(it['title'])}"] = it["key"]
    if it.get("url"):
        idx[f"url:{it['url']}"] = it["key"]


def upsert(led, rec, via, query):
    """Merge a record from a source into the ledger. Returns (key, is_new)."""
    run = current_run(led)
    doi = norm_doi(rec.get("doi"))
    arxiv = norm_arxiv(rec.get("arxiv")) or arxiv_from_doi(doi)
    if doi and arxiv_from_doi(doi):
        doi = None  # the arXiv DOI is the arXiv id; keep the DOI slot for the journal version
    key = find_key(led, doi, arxiv, rec.get("title"))
    if key is None and rec.get("url"):
        key = led["index"].get(f"url:{rec['url']}")
    src = {"run": run["id"], "via": via, "query": query}
    if key:
        it = led["items"][key]
        if doi and doi not in it["dois"]:
            it["dois"].append(doi)
        if arxiv and not it.get("arxiv"):
            it["arxiv"] = arxiv
        for d in rec.get("dates", []):
            if d and d not in it["dates"]:
                it["dates"].append(d)
        it["dates"].sort()
        it["date"] = first_date(it["dates"]) or it.get("date")
        if rec.get("abstract") and (it.get("abstract_by") == "agent" or not it.get("abstract")) and \
                rec.get("abstract_by") != "agent":
            it["abstract"], it["abstract_by"] = rec["abstract"], "source"
        if rec.get("venue") and not it.get("venue"):
            it["venue"] = rec["venue"]
        if doi and it["type"] == "preprint" and rec.get("type") == "paper":
            it["type"] = "paper"
            it["url"] = f"https://doi.org/{doi}"
        if not any(s["via"] == via and s["query"] == query for s in it["sources"]):
            it["sources"].append(src)
        index_item(led, it)
        return key, False
    if doi:
        key = f"doi:{doi}"
    elif arxiv:
        key = f"arxiv:{arxiv}"
    else:
        key = f"url:{rec['url']}"
    dates = sorted(d for d in rec.get("dates", []) if d)
    it = {
        "key": key,
        "title": re.sub(r"\s+", " ", rec.get("title") or "").strip() or "(untitled)",
        "authors": rec.get("authors", [])[:12],
        "n_authors": len(rec.get("authors", [])),
        "date": first_date(dates),
        "dates": dates,
        "date_basis": rec.get("date_basis", via),
        "venue": rec.get("venue"),
        "type": rec.get("type", "paper"),
        "url": rec.get("url") or (f"https://doi.org/{doi}" if doi else f"https://arxiv.org/abs/{arxiv}"),
        "dois": [doi] if doi else [],
        "arxiv": arxiv,
        "abstract": rec.get("abstract"),
        "abstract_by": rec.get("abstract_by", "source") if rec.get("abstract") else None,
        "sources": [src],
        "first_seen": run["id"],
        "relevance": "unscreened",
        "reason": None,
        "overlap": [],
        "basis": None,
        "history": [],
        "link_status": None,
    }
    led["items"][key] = it
    index_item(led, it)
    return key, True


def log_query(led, source, query, n, n_new, extra=None):
    q = {"source": source, "query": query, "results": n, "new": n_new, "time": now()}
    if extra:
        q.update(extra)
    current_run(led)["queries"].append(q)
    print(f"  {source}: '{query}' -> {n} results, {n_new} new")


# ---------------------------------------------------------------- sources

OA = "https://api.openalex.org"


OA_KEY_FILE = Path.home() / ".config" / "openalex" / "api_key"
OA_KEY = {"value": os.environ.get("OPENALEX_API_KEY") or (
    OA_KEY_FILE.read_text().strip() if OA_KEY_FILE.exists() else None)}


def oa_params(extra):
    p = dict(extra)
    if OA_KEY["value"]:
        p["api_key"] = OA_KEY["value"]
    return urllib.parse.urlencode(p)


OA_REFUSED = Path.home() / ".config" / "openalex" / "refused_at"
if OA_KEY["value"] and OA_REFUSED.exists() and time.time() - OA_REFUSED.stat().st_mtime < 3600:
    OA_KEY["value"] = None  # refused within the last hour: do not retry it on every call


def oa_fetch(path, params):
    """GET from OpenAlex; if the key is refused (not yet activated), drop it and retry keyless."""
    status, final, body = http_get(f"{OA}/{path}?{oa_params(params)}")
    if status in (401, 403) and OA_KEY["value"]:
        print("  OpenAlex refused the API key (not activated yet?); keyless for the next hour", file=sys.stderr)
        OA_KEY["value"] = None
        if OA_REFUSED.parent.exists():
            OA_REFUSED.touch()
        status, final, body = http_get(f"{OA}/{path}?{oa_params(params)}")
    return status, final, body


def oa_abstract(inv):
    if not inv:
        return None
    pos = []
    for word, places in inv.items():
        pos.extend((p, word) for p in places)
    return " ".join(w for _, w in sorted(pos))


def oa_record(w):
    doi = norm_doi(w.get("doi"))
    arxiv = arxiv_from_doi(doi)
    for loc in w.get("locations") or []:
        arxiv = arxiv or norm_arxiv((loc.get("landing_page_url") or "") if "arxiv" in (
            loc.get("landing_page_url") or "") else None)
    src = ((w.get("primary_location") or {}).get("source") or {})
    venue = src.get("display_name")
    is_pre = w.get("type") == "preprint" or (doi or "").startswith("10.48550") or (
        src.get("type") == "repository")
    return {
        "title": w.get("title") or w.get("display_name"),
        "authors": [a["author"]["display_name"] for a in w.get("authorships") or [] if a.get("author")],
        "dates": [w.get("publication_date")],
        "venue": venue,
        "type": "preprint" if is_pre else ("book" if w.get("type") in ("book", "book-chapter") else
                                           "thesis" if w.get("type") == "dissertation" else "paper"),
        "doi": doi,
        "arxiv": arxiv,
        "abstract": oa_abstract(w.get("abstract_inverted_index")),
        "url": f"https://doi.org/{doi}" if doi and not arxiv_from_doi(doi) else (
            f"https://arxiv.org/abs/{arxiv}" if arxiv else w.get("id")),
        "openalex": w.get("id"),
        "date_basis": "openalex",
    }


OA_SELECT = ("id,doi,title,display_name,publication_date,type,authorships,primary_location,locations,"
             "abstract_inverted_index,referenced_works,cited_by_count")


def oa_get(path, params):
    status, _, body = oa_fetch(path, params)
    if status != 200:
        die(f"OpenAlex {path} returned HTTP {status}: {body[:300]}")
    return json.loads(body)


def search_openalex(q, limit, since):
    filt = f"title_and_abstract.search:{q}"
    if since:
        filt += f",from_publication_date:{since}"
    data = oa_get("works", {"filter": filt, "per_page": min(limit, 100), "select": OA_SELECT})
    return [oa_record(w) for w in data["results"]]


def search_arxiv(q, limit, since, recent, id_list=None):
    if id_list:
        params = {"id_list": id_list, "max_results": 1}
    else:
        if not re.search(r"\b(ti|abs|all|au|cat|co|jr):", q):
            # unprefixed: every term (or "quoted phrase") must appear in the title or abstract
            terms = [t for t in re.findall(r'"[^"]+"|\S+', q) if t not in ("AND", "OR", "and")]
            q = " AND ".join(f"(ti:{t} OR abs:{t})" for t in terms)
        params = {"search_query": q, "max_results": limit,
                  "sortBy": "submittedDate" if recent else "relevance", "sortOrder": "descending"}
    time.sleep(3)  # arXiv asks for one request every three seconds
    status, _, body = http_get("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params),
                               retries=5, first_delay=10)
    if status != 200:
        print(f"  arXiv unavailable (HTTP {status}); logged as a failed query", file=sys.stderr)
        return None
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    out = []
    for e in ET.fromstring(body).findall("a:entry", ns):
        aid = norm_arxiv(e.findtext("a:id", "", ns))
        pub = (e.findtext("a:published", "", ns) or "")[:10]
        if since and pub < since:
            continue
        doi = e.findtext("x:doi", None, ns)
        out.append({
            "title": e.findtext("a:title", "", ns),
            "authors": [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)],
            "dates": [pub],
            "venue": e.findtext("x:journal_ref", None, ns) or "arXiv",
            "type": "preprint",
            "arxiv": aid,
            "doi": doi,
            "abstract": re.sub(r"\s+", " ", e.findtext("a:summary", "", ns)).strip(),
            "url": f"https://arxiv.org/abs/{aid}",
            "date_basis": "arxiv (v1 submission)",
        })
    return out


S2 = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,authors,publicationDate,year,venue,externalIds,abstract,publicationTypes"


def s2_headers():
    k = os.environ.get("S2_API_KEY")
    return {"x-api-key": k} if k else {}


def s2_record(p):
    ext = p.get("externalIds") or {}
    date = p.get("publicationDate") or (f"{p['year']}-01-01" if p.get("year") else None)
    arxiv = ext.get("ArXiv")
    doi = norm_doi(ext.get("DOI"))
    return {
        "title": p.get("title"),
        "authors": [a.get("name") for a in p.get("authors") or []],
        "dates": [date],
        "venue": p.get("venue") or None,
        "type": "paper" if doi and not arxiv_from_doi(doi) else ("preprint" if arxiv else "paper"),
        "doi": doi,
        "arxiv": arxiv,
        "abstract": p.get("abstract"),
        "date_basis": "semantic scholar" + ("" if p.get("publicationDate") else " (year only)"),
    }


def search_s2(q, limit, since):
    params = {"query": q, "limit": min(limit, 100), "fields": S2_FIELDS}
    if since:
        params["publicationDateOrYear"] = f"{since}:"
    time.sleep(1.1)
    status, _, body = http_get(f"{S2}/paper/search?" + urllib.parse.urlencode(params), s2_headers(), retries=5)
    if status != 200:
        print(f"  Semantic Scholar unavailable (HTTP {status}); logged as a failed query", file=sys.stderr)
        return None
    return [s2_record(p) for p in json.loads(body).get("data") or []]


def oa_lookup(ident):
    """OpenAlex work for a DOI or arXiv id, or None."""
    a = norm_arxiv(ident) if not ident.lower().startswith("10.") else None
    doi = norm_doi(ident) if not a else f"10.48550/arxiv.{a}"
    status, _, body = oa_fetch(f"works/doi:{doi}", {"select": OA_SELECT})
    return json.loads(body) if status == 200 else None


# ---------------------------------------------------------------- commands


def cmd_init(a):
    d = lr_dir(a.project)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "ledger.json"
    if path.exists():
        print(f"ledger exists at {path} ({len(json.loads(path.read_text())['items'])} items); kept")
        return
    path.write_text(json.dumps({"version": 1, "created": today(), "runs": [], "items": {}, "index": {}},
                               indent=1))
    print(f"created {path}")


def cmd_run(a):
    brief = load_brief(a.project)
    led = load(a.project)
    rid = f"r{len(led['runs']) + 1}"
    led["runs"].append({"id": rid, "date": today(), "started": now(), "mode": brief["mode"],
                        "targets": [t["id"] + ": " + t["text"] for t in brief["targets"]],
                        "note": a.note, "queries": []})
    save(a.project, led)
    print(f"opened run {rid} ({brief['mode']} mode)")
    if len(led["runs"]) > 1:
        prev = led["runs"][-2]
        if prev["targets"] != led["runs"][-1]["targets"]:
            print("  the targets changed since the last run: re-check every red and amber verdict (`stale`)")


def cmd_search(a):
    led = load(a.project)
    if a.source == "openalex":
        recs = search_openalex(a.query, a.limit, a.since)
    elif a.source == "arxiv":
        recs = search_arxiv(a.query, a.limit, a.since, a.recent)
    else:
        recs = search_s2(a.query, a.limit, a.since)
    if recs is None:
        log_query(led, a.source, a.query, 0, 0, {"failed": True})
        save(a.project, led)
        return
    n_new = 0
    for r in recs:
        if r.get("title"):
            n_new += upsert(led, r, a.source, a.query)[1]
    log_query(led, a.source, a.query, len(recs), n_new, {"since": a.since} if a.since else None)
    save(a.project, led)


def cmd_expand(a):
    """Citation-graph expansion through OpenAlex: refs (what it cites) or cites (what cites it)."""
    led = load(a.project)
    w = oa_lookup(a.id)
    if w is None:
        die(f"OpenAlex has no record for {a.id}; try `add` with the URL and expand from a related paper")
    seed = upsert(led, oa_record(w), "openalex", f"seed {a.id}")[0]
    recs = []
    if a.direction == "refs":
        ids = [r.rsplit("/", 1)[-1] for r in w.get("referenced_works") or []]
        for i in range(0, len(ids), 50):
            data = oa_get("works", {"filter": "openalex_id:" + "|".join(ids[i:i + 50]),
                                    "per_page": 50, "select": OA_SELECT})
            recs += [oa_record(x) for x in data["results"]]
    else:
        filt = f"cites:{w['id'].rsplit('/', 1)[-1]}"
        if a.since:
            filt += f",from_publication_date:{a.since}"
        data = oa_get("works", {"filter": filt, "per_page": min(a.limit, 200),
                                "sort": "publication_date:desc", "select": OA_SELECT})
        recs = [oa_record(x) for x in data["results"]]
    n_new = sum(upsert(led, r, "openalex", f"{a.direction} of {seed}")[1] for r in recs if r.get("title"))
    log_query(led, f"openalex-{a.direction}", seed, len(recs), n_new)
    if a.direction == "cites" and not recs and not w.get("cited_by_count"):
        print("  OpenAlex records no citations to this work (often just indexing lag for recent work); "
              "this is not evidence that nobody cites it")
    save(a.project, led)


def cmd_author(a):
    """Recent output of one author (OpenAlex), to follow the people behind the red and amber items."""
    led = load(a.project)
    data = oa_get("authors", {"search": a.name, "per_page": 5,
                              "select": "id,display_name,works_count,last_known_institutions"})
    if not data["results"]:
        die(f"OpenAlex knows no author matching '{a.name}'")
    for i, au in enumerate(data["results"][:5]):
        inst = ", ".join(x.get("display_name", "") for x in au.get("last_known_institutions") or [])
        print(f"  [{i}] {au['display_name']} ({au['works_count']} works; {inst})")
    au = data["results"][a.pick]
    filt = f"authorships.author.id:{au['id'].rsplit('/', 1)[-1]}"
    if a.since:
        filt += f",from_publication_date:{a.since}"
    works = oa_get("works", {"filter": filt, "per_page": min(a.limit, 200),
                             "sort": "publication_date:desc", "select": OA_SELECT})["results"]
    recs = [oa_record(x) for x in works]
    if a.topic:
        rx = re.compile(a.topic, re.I)
        recs = [r for r in recs if rx.search(f"{r.get('title') or ''} {r.get('abstract') or ''}")]
    n_new = sum(upsert(led, r, "openalex", f"works of {au['display_name']}")[1] for r in recs if r.get("title"))
    log_query(led, "openalex-author", f"{au['display_name']} since {a.since or 'ever'}", len(recs), n_new)
    save(a.project, led)


def cmd_screen_out(a):
    """Bulk-mark unscreened items irrelevant when a regex matches a field; dry run unless --yes."""
    led = load(a.project)
    if not a.match and not a.rest:
        die("give --match REGEX, or --rest to mark every item still unscreened")
    rx = re.compile(a.match or "", re.I)
    hits = [it for it in led["items"].values() if it["relevance"] == "unscreened" and (a.rest or rx.search(
        " ".join(str(it.get(f) or "") for f in (["title", "venue", "url"] if a.field == "any" else [a.field]))))]
    for it in hits[:15]:
        print(f"  {it['key']}\t{(it.get('venue') or '')[:25]}\t{it['title'][:80]}")
    if not a.yes:
        print(f"{len(hits)} unscreened items match (dry run; add --yes to mark them irrelevant)")
        return
    run = current_run(led)
    for it in hits:
        it["history"].append({"run": run["id"], "from": "unscreened", "to": "irrelevant", "why": a.reason,
                              "time": now()})
        it.update(relevance="irrelevant", reason=a.reason, assessed_in=run["id"])
    save(a.project, led)
    print(f"marked {len(hits)} items irrelevant: {a.reason}")


META_DATE = [r'property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)',
             r'content=["\']([^"\']+)["\'][^>]*property=["\']article:published_time',
             r'"datePublished"\s*:\s*"([^"]+)"',
             r'name=["\'](?:citation_publication_date|citation_date|dc\.date|date)["\'][^>]*content=["\']([^"\']+)',
             r'<time[^>]*datetime=["\']([^"\']+)']


def page_meta(body):
    title = None
    m = re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', body) or re.search(
        r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
    if m:
        title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
    date = None
    for pat in META_DATE:
        m = re.search(pat, body, re.I)
        if m:
            d = re.search(r"\d{4}-\d{2}-\d{2}", m.group(1).replace("/", "-"))
            if d:
                date = d.group(0)
                break
    return title, date


def cmd_add(a):
    """Add one item the agent found by other means: a DOI, an arXiv id, or a URL (post, repo, site)."""
    led = load(a.project)
    via = a.via
    if a.doi or a.arxiv:
        ident = a.doi or a.arxiv
        w = oa_lookup(ident)
        if w:
            rec = oa_record(w)
        elif a.arxiv:
            rec = (search_arxiv(None, 1, None, False, id_list=norm_arxiv(a.arxiv)) or [None])[0]
            if rec is None or not rec.get("title"):
                die(f"arXiv id {a.arxiv} not found")
        else:
            status, final, body = http_get(f"https://api.crossref.org/works/{urllib.parse.quote(norm_doi(a.doi))}")
            if status != 200:
                die(f"DOI {a.doi} resolves nowhere (OpenAlex and Crossref both fail); not added")
            m = json.loads(body)["message"]
            parts = (m.get("published") or m.get("issued") or {}).get("date-parts", [[None]])[0]
            date = "-".join(f"{p:02d}" for p in parts if p) if parts and parts[0] else None
            rec = {"title": (m.get("title") or [""])[0],
                   "authors": [f"{x.get('given', '')} {x.get('family', '')}".strip() for x in m.get("author", [])],
                   "dates": [date], "venue": (m.get("container-title") or [None])[0], "type": "paper",
                   "doi": a.doi, "abstract": re.sub(r"<[^>]+>", "", m.get("abstract") or "") or None,
                   "date_basis": "crossref"}
    else:
        status, final, body = http_get(a.url)
        if not 200 <= status < 300:
            die(f"{a.url} returned HTTP {status}; not added (an item must have a link that works)")
        title, date = page_meta(body)
        rec = {"title": a.title or title, "url": a.url, "dates": [a.date or date],
               "date_basis": "given by agent" if a.date else ("page metadata" if date else "none found"),
               "type": a.type or "post", "authors": [x.strip() for x in (a.authors or "").split(";") if x.strip()],
               "venue": a.venue or urllib.parse.urlparse(final).netloc}
        if not rec["title"]:
            die("no title found on the page; pass --title")
    if a.type:
        rec["type"] = a.type
    if a.abstract and not rec.get("abstract"):
        rec["abstract"], rec["abstract_by"] = a.abstract, "agent"
    key, new = upsert(led, rec, via, a.query or "")
    it = led["items"][key]
    if a.title and it["title"] != a.title:
        it["title"] = a.title  # e.g. a source that mangled the title
    if a.date and it["date"] != a.date:
        if a.date not in it["dates"]:
            it["dates"] = sorted(it["dates"] + [a.date])
        it["date"], it["date_basis"] = a.date, "given by agent"
    print(f"{'added' if new else 'merged into'} {key}: {it['title'][:90]} ({it['date']}, date from {it['date_basis']})")
    if not it["date"]:
        print("  WARNING: no date. Find it on the page and re-run with --date, or the item sorts last.")
    save(a.project, led)


def cmd_log(a):
    """Record a search made outside the script (Undermind, web search) so the search log is complete."""
    led = load(a.project)
    log_query(led, a.source, a.query, a.results, a.new, {"note": a.note} if a.note else None)
    save(a.project, led)


def cmd_pending(a):
    led = load(a.project)
    items = [it for it in led["items"].values() if it["relevance"] == "unscreened"]
    items.sort(key=lambda it: it["date"] or "", reverse=True)
    out = []
    if a.compact:
        out = [f"{it['key']}\t{it['date']}\t{it['type']}\t{(it.get('venue') or '')[:30]}\t{it['title'][:110]}"
               for it in items[: a.limit]]
    for it in ([] if a.compact else items[: a.limit]):
        ab = (it.get("abstract") or "(no abstract)")
        out.append(f"## {it['key']}\n{it['title']} | {it['date']} | {it['type']} | {it.get('venue') or ''}\n"
                   f"{', '.join(it['authors'][:4])}{' et al.' if it['n_authors'] > 4 else ''}\n"
                   f"{ab[: a.chars]}\n")
    text = "\n".join(out)
    more = f"; {len(items) - len(out)} more (raise --limit, or --compact for one line each)" if len(items) > len(out) else ""
    if a.out:
        Path(a.out).write_text(text)
        print(f"{len(out)} of {len(items)} unscreened items written to {a.out}{more}")
    else:
        print(text)
        print(f"[{len(out)} of {len(items)} unscreened items shown{more}]")


def cmd_assess(a):
    """Import verdicts from a JSON list: [{key, relevance, reason, overlap?, basis?, quote?}]."""
    led = load(a.project)
    brief = load_brief(a.project)
    ids = {t["id"] for t in brief["targets"]} | {x["id"] for x in brief.get("achieved", [])}
    run = current_run(led)
    verdicts = json.loads(Path(a.file).read_text())
    errors = []
    for v in verdicts:
        k = v.get("key")
        if k not in led["items"]:
            errors.append(f"{k}: not in the ledger (items enter only through search, expand or add)")
            continue
        if v.get("relevance") not in RELEVANCE:
            errors.append(f"{k}: relevance must be one of {RELEVANCE}")
            continue
        if not v.get("reason"):
            errors.append(f"{k}: a reason is required")
            continue
        ov = v.get("overlap") or []
        for o in ov:
            if o.get("target") not in ids:
                errors.append(f"{k}: overlap target '{o.get('target')}' is not in brief.json")
            if o.get("verdict") not in OVERLAP_VERDICTS:
                errors.append(f"{k}: overlap verdict must be one of {OVERLAP_VERDICTS}")
            if not o.get("item_achieved"):
                errors.append(f"{k}: overlap entry for {o.get('target')} needs 'item_achieved'")
            if v.get("relevance") in ("red", "amber") and not o.get("remaining"):
                errors.append(f"{k}: overlap entry for {o.get('target')} needs 'remaining' (what is left for the "
                              f"project; 'nothing' if the item settles it)")
        if v["relevance"] in ("red", "amber"):
            if not ov:
                errors.append(f"{k}: a {v['relevance']} item names the targets it overlaps")
            if v.get("basis") not in BASES:
                errors.append(f"{k}: a {v['relevance']} item records its basis, one of {BASES}")
        if v["relevance"] == "red" and not any(o.get("verdict") in ("done", "partial", "competing") for o in ov):
            errors.append(f"{k}: red means the item does all or part of a target, or competes for it directly; "
                          f"no overlap is 'done', 'partial' or 'competing'")
        if v["relevance"] == "red" and v.get("basis") not in ("citation", "secondary") and not any(o.get("passages") for o in ov):
            errors.append(f"{k}: a red item shows at least one passage (from its held text, or its abstract) "
                          f"that bears out the overlap")
        for o in ov:
            checked = []
            for ps in o.get("passages") or []:
                try:
                    where, link = verify_passage(a.project, led["items"][k], ps["quote"])
                    checked.append({"quote": ps["quote"], "where": where, "link": link})
                except ValueError as e:
                    errors.append(f"{k}: passage for {o.get('target')} rejected: {e}: \"{ps['quote'][:60]}...\"")
            o["passages"] = checked
        if v.get("quote"):
            try:
                v["quote_where"] = verify_passage(a.project, led["items"][k], v["quote"])[0]
            except ValueError as e:
                errors.append(f"{k}: quote rejected: {e}")
    if errors:
        die("verdicts rejected, nothing written:\n  " + "\n  ".join(errors))
    for v in verdicts:
        it = led["items"][v["key"]]
        if it["relevance"] != v["relevance"]:
            it["history"].append({"run": run["id"], "from": it["relevance"], "to": v["relevance"],
                                  "why": v["reason"], "time": now()})
        it.update(relevance=v["relevance"], reason=v["reason"], overlap=v.get("overlap") or [],
                  basis=v.get("basis"), quote=v.get("quote"), quote_where=v.get("quote_where"),
                  assessed_in=run["id"])
        if v.get("type"):
            if v["type"] not in TYPES:
                die(f"{v['key']}: type must be one of {TYPES}")
            it["type"] = v["type"]
    save(a.project, led)
    counts = {r: sum(1 for v in verdicts if v["relevance"] == r) for r in RELEVANCE}
    print(f"recorded {len(verdicts)} verdicts: " + ", ".join(f"{n} {r}" for r, n in counts.items()))


def cmd_stale(a):
    """Red and amber items assessed under targets that have since changed."""
    led = load(a.project)
    runs = {r["id"]: r for r in led["runs"]}
    cur = led["runs"][-1]["targets"]
    for it in led["items"].values():
        if it["relevance"] in ("red", "amber") and runs[it.get("assessed_in", "r1")]["targets"] != cur:
            print(f"{it['key']}\t{it['relevance']}\t{it['title'][:80]}")


def merge_items(led, keep, drop):
    """Fold item `drop` into `keep` (two versions of one work); verdict of the stronger colour wins."""
    k, d = led["items"][keep], led["items"].pop(drop)
    for f in ("dois", "dates", "sources", "history"):
        k[f] = k[f] + [x for x in d[f] if x not in k[f]]
    k["dates"].sort()
    k["date"] = first_date(k["dates"])
    k["arxiv"] = k.get("arxiv") or d.get("arxiv")
    if d.get("abstract") and (not k.get("abstract") or (k.get("abstract_by") == "agent" and d.get("abstract_by") != "agent")):
        k["abstract"], k["abstract_by"] = d["abstract"], d.get("abstract_by")
    if d["dois"] and k["type"] == "preprint":
        k["type"], k["url"], k["venue"] = "paper", f"https://doi.org/{d['dois'][0]}", d.get("venue") or k.get("venue")
    order = ["red", "amber", "green", "own", "irrelevant", "unscreened"]
    if order.index(d["relevance"]) < order.index(k["relevance"]):
        for f in ("relevance", "reason", "overlap", "basis", "quote", "assessed_in"):
            k[f] = d.get(f)
    if norm_title(k["title"]) in ("articles", "article", "") and d["title"]:
        k["title"] = d["title"]  # bad metadata on one version
    for ik, v in list(led["index"].items()):
        if v == drop:
            led["index"][ik] = keep
    print(f"  merged {drop} into {keep}")


def cmd_fix(a):
    """Correct an item's title, date (or clear it), type or abstract taken verbatim from its source."""
    led = load(a.project)
    it = led["items"].get(a.key) or die(f"{a.key} is not in the ledger")
    run = current_run(led)
    changes = []
    if a.title:
        changes.append(f"title {it['title']!r} -> {a.title!r}")
        it["title"] = a.title
    if a.clear_date:
        changes.append(f"date {it['date']} cleared")
        it["dates"] = [d for d in it["dates"] if d != it["date"]]
        it["date"] = first_date(it["dates"])
        it["date_basis"] = "cleared by agent" if not it["date"] else it["date_basis"]
    if a.date:
        if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", a.date):
            die("--date is YYYY-MM-DD, or YYYY-MM when only the month is known")
        changes.append(f"date {it['date']} -> {a.date}")
        it["dates"] = sorted(set(it["dates"]) | {a.date})
        it["date"], it["date_basis"] = a.date, "given by agent"
    if a.type:
        changes.append(f"type {it['type']} -> {a.type}")
        it["type"] = a.type
    if a.abstract:
        changes.append("abstract replaced with the source's text")
        it["abstract"], it["abstract_by"] = a.abstract, "source"
    if not changes:
        die("nothing to fix")
    it["history"].append({"run": run["id"], "from": it["relevance"], "to": it["relevance"],
                          "why": "fix: " + "; ".join(changes), "time": now()})
    save(a.project, led)
    print(f"{a.key}: " + "; ".join(changes))


def cmd_merge(a):
    led = load(a.project)
    for k in (a.keep, a.drop):
        if k not in led["items"]:
            die(f"{k} is not in the ledger")
    merge_items(led, a.keep, a.drop)
    save(a.project, led)


def cmd_dates(a):
    """Give every kept item with an arXiv id its v1 date, so it sorts by first public appearance."""
    led = load(a.project)
    todo = [it for it in led["items"].values() if it.get("arxiv") and it["relevance"] != "irrelevant"
            and not it.get("arxiv_v1")]
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        time.sleep(3)
        q = urllib.parse.urlencode({"id_list": ",".join(it["arxiv"] for it in chunk), "max_results": 50})
        status, _, body = http_get("https://export.arxiv.org/api/query?" + q)
        if status != 200:
            die(f"arXiv returned HTTP {status}")
        xns = "{http://arxiv.org/schemas/atom}"
        got, jdoi = {}, {}
        for e in ET.fromstring(body).findall("a:entry", ns):
            aid = norm_arxiv(e.findtext("a:id", "", ns))
            got[aid] = (e.findtext("a:published", "", ns) or "")[:10]
            jdoi[aid] = norm_doi(e.findtext(f"{xns}doi", None))
        for it in chunk:
            # the arXiv record names the journal version's DOI: fold a separate journal item into this one
            other = led["index"].get(f"doi:{jdoi.get(it['arxiv'])}") if jdoi.get(it["arxiv"]) else None
            if other and other != it["key"] and other in led["items"]:
                merge_items(led, other, it["key"])
                it = led["items"][other]
            d = got.get(it["arxiv"])
            if d:
                it["arxiv_v1"] = d
                if d not in it["dates"]:
                    it["dates"].append(d)
                    it["dates"].sort()
                if first_date(it["dates"]) == d and it["date"] != d:
                    print(f"  {it['key']}: {it['date']} -> {d} (arXiv v1)")
                    it["date"] = d
                    it["date_basis"] = "arxiv (v1 submission)"
    save(a.project, led)
    print(f"arXiv v1 dates checked for {len(todo)} items")


def cmd_links(a):
    led = load(a.project)
    bad = 0
    for it in led["items"].values():
        if it["relevance"] in ("unscreened", "irrelevant"):
            continue
        status, final, _ = http_get(it["url"], retries=2, timeout=25)
        if 200 <= status < 300:
            status = 200
        elif status in (401, 403, 418, 429, 503) and not it["dois"]:
            status = f"unverifiable (HTTP {status}: bot-blocking or a temporary outage)"
        elif status in (401, 403, 418, 429, 503) and it["dois"]:
            cs, _, _ = http_get(f"https://api.crossref.org/works/{urllib.parse.quote(it['dois'][0])}", retries=2)
            if cs == 200:
                status = "publisher blocks bots; DOI confirmed by Crossref"
        it["link_status"] = status
        if status != 200 and not isinstance(status, str):
            bad += 1
            print(f"  {status}\t{it['key']}\t{it['url']}")
        time.sleep(0.3)
    save(a.project, led)
    print(f"links checked; {bad} not returning 200")


def cmd_status(a):
    led = load(a.project)
    items = list(led["items"].values())
    print(f"{len(items)} items, {len(led['runs'])} runs, "
          f"{sum(len(r['queries']) for r in led['runs'])} queries")
    for r in ["unscreened"] + RELEVANCE:
        print(f"  {r:11s} {sum(1 for it in items if it['relevance'] == r)}")
    kept = [it for it in items if it["relevance"] in ("red", "amber", "green")]
    sur = lambda it: ((it["authors"][0].split(",")[0] if "," in it["authors"][0] else it["authors"][0].split()[-1])
                      .strip().lower() if it["authors"] else "")
    yr = lambda it: int((it["date"] or "0")[:4])
    for i, x in enumerate(kept):
        for y in kept[i + 1:]:
            if x["url"].split("#")[0] == y["url"].split("#")[0] and "#" in x["url"] + y["url"]:
                continue  # separate results on one records page, by design
            if sur(x) and sur(x) == sur(y) and abs(yr(x) - yr(y)) <= 3 and difflib.SequenceMatcher(
                    None, norm_title(x["title"]), norm_title(y["title"])).ratio() >= 0.9:
                print(f"  possible duplicate: {x['key']} / {y['key']} ({x['title'][:50]}); `merge` if same work")
    undated = [it["key"] for it in items if not it["date"] and it["relevance"] not in ("irrelevant",)]
    if undated:
        print(f"  undated (fix before build): {', '.join(undated[:10])}")


MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def md_inline(s):
    s = html.escape(s, quote=False)
    s = MD_LINK.sub(lambda m: f'<a href="{html.escape(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<em>\1</em>", s)


def md_to_html(md):
    out, para, items = [], [], []

    def flush():
        if para:
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{md_inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for line in md.splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("#"):
            flush()
            lvl = min(len(s) - len(s.lstrip("#")) + 2, 4)
            out.append(f"<h{lvl}>{md_inline(s.lstrip('#').strip())}</h{lvl}>")
        elif re.match(r"[-*] ", s):
            if para:
                out.append("<p>" + md_inline(" ".join(para)) + "</p>")
                para.clear()
            items.append(s[2:])
        elif items and line.startswith("  "):
            items[-1] += " " + s
        else:
            para.append(s)
    flush()
    return "\n".join(out)


def cmd_build(a):
    led = load(a.project)
    brief = load_brief(a.project)
    d = lr_dir(a.project)
    syn = d / "synthesis.md"
    n_known = mark_known(a.project, led, brief) if brief.get("references") else 0
    save(a.project, led)
    items = [it for it in led["items"].values() if it["relevance"] != "unscreened"]
    unscreened = len(led["items"]) - len(items)
    undated = [it["key"] for it in items if not it["date"] and it["relevance"] != "irrelevant"]
    if undated:
        print(f"WARNING: {len(undated)} kept items have no date and will sort last: {undated[:5]}")
    keep = ("key", "title", "authors", "n_authors", "date", "dates", "date_basis", "venue", "fulltext", "quote_where", "known", "type", "url", "arxiv",
            "dois", "relevance", "reason", "overlap", "basis", "quote", "first_seen", "history",
            "link_status", "sources", "abstract")
    data = {
        "brief": brief,
        "runs": [{k: r[k] for k in ("id", "date", "mode", "note")} | {"n_queries": len(r["queries"])}
                 for r in led["runs"]],
        "queries": [q | {"run": r["id"]} for r in led["runs"] for q in r["queries"]],
        "items": [{k: it.get(k) for k in keep if not (it["relevance"] == "irrelevant" and k in ("abstract", "sources"))}
                  for it in items],
        "unscreened": unscreened,
        "synthesis_html": md_to_html(syn.read_text()) if syn.exists() else "",
        "built": now(),
    }
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text().replace("__TITLE__", html.escape(f"Literature: {brief['name']}")).replace(
        "/*__DATA__*/null", blob)
    out = d / "index.html"
    out.write_text(page)
    n = {r: sum(1 for it in items if it["relevance"] == r) for r in RELEVANCE}
    print(f"wrote {out}: {n['red']} red, {n['amber']} amber, {n['green']} green "
          f"({n['irrelevant']} irrelevant and {n['own']} of the project's own hidden by default, "
          f"{unscreened} unscreened left out)")
    if unscreened:
        print("  WARNING: unscreened items remain; screen them or say in the synthesis why they were left")
    if not syn.exists():
        print("  WARNING: no synthesis.md; the page has no reading of what the red items mean")
    else:
        words = len(MD_LINK.sub(r"\1", syn.read_text()).split())
        if words > 600:
            print(f"  WARNING: synthesis.md is {words} words (links counted as their text); aim for about 500")
    if brief.get("references"):
        print(f"  {n_known} items are already cited by the project (marked on the page)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def sp(name, fn, help_):
        s = sub.add_parser(name, help=help_)
        s.add_argument("project", help="project directory (the ledger lives in <project>/litreview/)")
        s.set_defaults(fn=fn)
        return s

    sp("init", cmd_init, "create litreview/ledger.json")
    s = sp("run", cmd_run, "open a new search run (needs brief.json)")
    s.add_argument("--note", default="")
    s = sp("search", cmd_search, "search one source and record every hit")
    s.add_argument("--source", choices=["openalex", "arxiv", "s2"], required=True)
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=25)
    s.add_argument("--since", help="YYYY-MM-DD lower bound on the publication date")
    s.add_argument("--recent", action="store_true", help="arXiv: newest first instead of by relevance")
    s = sp("expand", cmd_expand, "add what a paper cites (refs) or what cites it (cites), via OpenAlex")
    s.add_argument("--id", required=True, help="DOI or arXiv id of the seed")
    s.add_argument("--direction", choices=["refs", "cites"], required=True)
    s.add_argument("--limit", type=int, default=100)
    s.add_argument("--since")
    s = sp("add", cmd_add, "add one item by DOI, arXiv id or URL; the script resolves it")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--doi")
    g.add_argument("--arxiv")
    g.add_argument("--url")
    s.add_argument("--via", default="manual", help="where it was found: undermind, web, citation, ...")
    s.add_argument("--query", help="the search that surfaced it")
    s.add_argument("--title")
    s.add_argument("--date", help="YYYY-MM-DD (or YYYY-MM), only as shown on the page when its metadata lacks it")
    s.add_argument("--type", choices=TYPES)
    s.add_argument("--authors", help="semicolon-separated")
    s.add_argument("--venue")
    s.add_argument("--abstract", help="a one-to-three sentence description taken from the page")
    s = sp("author", cmd_author, "add an author's recent works (OpenAlex), newest first")
    s.add_argument("--name", required=True)
    s.add_argument("--pick", type=int, default=0, help="which of the listed name matches to use")
    s.add_argument("--topic", help="keep only works whose title or abstract matches this regex")
    s.add_argument("--since")
    s.add_argument("--limit", type=int, default=50)
    s = sp("screen-out", cmd_screen_out, "bulk-mark unscreened items irrelevant by regex (dry run unless --yes)")
    s.add_argument("--match", help="regular expression, case-insensitive")
    s.add_argument("--rest", action="store_true",
                   help="every item still unscreened (after the kept ones are assessed); dry run lists them")
    s.add_argument("--field", choices=["any", "title", "venue", "url"], default="any")
    s.add_argument("--reason", required=True)
    s.add_argument("--yes", action="store_true")
    s = sp("log", cmd_log, "record a search made outside the script (Undermind, web search)")
    s.add_argument("--source", required=True)
    s.add_argument("--query", required=True)
    s.add_argument("--results", type=int, default=0)
    s.add_argument("--new", type=int, default=0, help="items it added (via `add`)")
    s.add_argument("--note")
    s = sp("pending", cmd_pending, "list unscreened items with abstracts, newest first")
    s.add_argument("--limit", type=int, default=60)
    s.add_argument("--chars", type=int, default=700)
    s.add_argument("--compact", action="store_true", help="one line per item, no abstracts")
    s.add_argument("--out")
    s = sp("assess", cmd_assess, "import verdicts from a JSON file (validated; all or nothing)")
    s.add_argument("--file", required=True)
    sp("stale", cmd_stale, "red/amber items assessed under targets that have since changed")
    s = sp("fulltext", cmd_fulltext, "hold an item's open full text (licence-checked) for passage checks")
    s.add_argument("--key", required=True)
    g = s.add_mutually_exclusive_group()
    g.add_argument("--url", help="an open copy (default: the arXiv PDF when the item has an arXiv id)")
    g.add_argument("--file", help="a PDF already on disk (still licence-checked)")
    s = sp("find", cmd_find, "rank passages of a held text by search terms")
    s.add_argument("--key", required=True)
    s.add_argument("terms", nargs="+")
    s.add_argument("-k", type=int, default=5)
    s = sp("fix", cmd_fix, "correct an item's title, date, type or abstract (recorded in its history)")
    s.add_argument("--key", required=True)
    s.add_argument("--title")
    s.add_argument("--date", help="YYYY-MM-DD, or YYYY-MM when only the month is known")
    s.add_argument("--clear-date", action="store_true", help="drop the current date (e.g. a guessed one)")
    s.add_argument("--type", choices=TYPES)
    s.add_argument("--abstract", help="the abstract copied verbatim from the source")
    s = sp("merge", cmd_merge, "fold one item into another (two versions of the same work)")
    s.add_argument("--keep", required=True)
    s.add_argument("--drop", required=True)
    sp("dates", cmd_dates, "date items with an arXiv id by their v1 submission (first public appearance)")
    sp("links", cmd_links, "check that every kept item's link returns 200")
    sp("status", cmd_status, "counts by relevance")
    sp("build", cmd_build, "write litreview/index.html")
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

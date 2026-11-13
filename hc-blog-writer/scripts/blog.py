"""Shared helpers: read a HerdingChickens post (frontmatter + Markdown body) and the rule register.

The post format is the one the website loads in lib/blog/index.ts: YAML frontmatter between
'---' lines, then Markdown with a ```short block, optional '## FAQ', '## Keep reading' and a
closing disclaimer after a final '---' line.
"""
import re
import sys
import tomllib
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is needed to read post frontmatter: pip install pyyaml")

SKILL_DIR = Path(__file__).resolve().parent.parent
RULES_FILE = SKILL_DIR / "rules.toml"

LINK_RE = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{2,3}) +(.+?)\s*$", re.M)
FENCE_RE = re.compile(r"^```(\w*)\n(.*?)^```\s*$", re.M | re.S)
SITE_HOSTS = ("herdingchickens.com", "www.herdingchickens.com")


def load_rules(path=RULES_FILE):
    with open(path, "rb") as f:
        return tomllib.load(f)["rules"]


def split_post(text):
    """Return (frontmatter dict, body str). A post without frontmatter is an error."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("no frontmatter block between '---' lines at the top of the file")
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def read_post(path):
    return split_post(Path(path).read_text(encoding="utf-8"))


def sections(body):
    """Split the body into the parts the rules look at."""
    # The disclaimer is everything after the last horizontal rule.
    parts = re.split(r"^---\s*$", body, flags=re.M)
    disclaimer = parts[-1] if len(parts) > 1 else ""
    main = "---".join(parts[:-1]) if len(parts) > 1 else body

    def cut(text, heading):
        m = re.search(rf"^## {heading}[^\n]*\n", text, re.M | re.I)
        if not m:
            return text, ""
        nxt = re.search(r"^## ", text[m.end():], re.M)
        end = m.end() + nxt.start() if nxt else len(text)
        return text[:m.start()] + text[end:], text[m.start():end]

    main, keep_reading = cut(main, "Keep reading")
    main, faq = cut(main, "FAQ")
    fences = FENCE_RE.findall(main)
    short = next((raw for lang, raw in fences if lang == "short"), None)
    prose = FENCE_RE.sub("", main)
    return {
        "main": main,            # body before FAQ / Keep reading / disclaimer, fences included
        "prose": prose,          # main without fenced blocks
        "short": short,          # raw text of the ```short block, or None
        "faq": faq,
        "keep_reading": keep_reading,
        "disclaimer": disclaimer,
    }


def links(text):
    """List of (is_image, label, url)."""
    return [(bang == "!", label, url) for bang, label, url in LINK_RE.findall(text)]


def is_internal(url):
    if url.startswith("/") or url.startswith("#"):
        return True
    host = re.sub(r"^https?://", "", url).split("/")[0]
    return host in SITE_HOSTS


def plain(text):
    """Text with links reduced to their labels and Markdown marks removed, for word checks."""
    text = LINK_RE.sub(lambda m: m.group(2), text)
    text = re.sub(r"[*_`>#]", " ", text)
    return text


def words(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", plain(text))


def paragraphs(text):
    out = []
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if not b or b.startswith(("#", "-", "*", "|", ">", "!", "1.", "```")) or re.match(r"^\d+\.", b):
            continue
        out.append(b)
    return out


def sentences(paragraph):
    return [s for s in re.split(r"(?<=[.!?])[\"”’)]*\s+(?=[A-Z\"“‘(\[])", plain(paragraph).strip()) if s.strip()]


def site_posts(blog_dir, exclude_slug=None):
    """Frontmatter of every post in the website's content/blog folder (published or not)."""
    posts = []
    for p in sorted(Path(blog_dir).glob("*.md")):
        if p.name == "README.md":
            continue
        fm, _ = read_post(p)
        if fm.get("slug") and fm.get("slug") != exclude_slug:
            posts.append({"file": p.name, **fm})
    return posts

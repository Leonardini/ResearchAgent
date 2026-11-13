#!/usr/bin/env python3
"""Rank keywords from an Ubersuggest position-tracking export and mark which ones the blog already covers.

    python3 keywords.py EXPORT.csv --site-blog ~/Downloads/herding-chickens-website/content/blog [--top 20]

The export's columns are: Keyword, Position, Change, Search Intent, Volume, SEO Difficulty, URL
("-" means empty). Each keyword gets a status:

  TAKEN      an existing post has it as focus_keyword, or its title contains it: do not write another
  RANKS      the site already ranks for it (Position is a number): improve that page instead
  NEAR-DUP   contains all the words of a keyword higher in the list (ignoring "adhd" and word
             order), e.g. "time blindness adhd" or "adhd daily planner": merge it into that post
  SECONDARY  only listed in some post's secondary_keywords: free to target, but take it out of
             that post's list when the new post goes live, so the two do not compete
  FREE       nobody covers it

Volume and difficulty come straight from the export; the script makes no judgement about which
trade-off is best. The table is sorted by volume, then by lower difficulty.
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blog  # noqa: E402

COLUMNS = ["Keyword", "Position", "Change", "Search Intent", "Volume", "SEO Difficulty", "URL"]


def read_export(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows or list(rows[0].keys()) != COLUMNS:
        raise SystemExit(f"{path}: expected columns {COLUMNS}, found {list(rows[0].keys()) if rows else 'nothing'}")
    out = []
    for r in rows:
        num = lambda v: None if v.strip() in ("", "-") else int(v)  # noqa: E731
        out.append({"keyword": r["Keyword"].strip().lower(), "position": num(r["Position"]),
                    "intent": r["Search Intent"], "volume": num(r["Volume"]) or 0,
                    "difficulty": num(r["SEO Difficulty"]), "url": None if r["URL"] == "-" else r["URL"]})
    return out


def word_key(kw):
    return frozenset(w for w in kw.split() if w != "adhd")


def classify(rows, posts):
    seen = {}
    for r in sorted(rows, key=lambda r: (-r["volume"], r["difficulty"] or 999)):
        kw = r["keyword"]
        focus = [p["slug"] for p in posts if str(p.get("focus_keyword", "")).lower() == kw]
        titled = [p["slug"] for p in posts if kw in str(p.get("title", "")).lower().replace("-", " ")]
        second = [p["slug"] for p in posts if kw in [str(s).lower() for s in p.get("secondary_keywords") or []]]
        key = word_key(kw)
        if focus or titled:
            r["status"], r["where"] = "TAKEN", ", ".join(sorted(set(focus + titled)))
        elif r["position"] is not None:
            r["status"], r["where"] = "RANKS", f"#{r['position']} {r['url']}"
        elif any(k and k <= key for k in seen):
            r["status"], r["where"] = "NEAR-DUP", f"of '{next(seen[k] for k in seen if k and k <= key)}'"
        elif second:
            r["status"], r["where"] = "SECONDARY", ", ".join(second)
        else:
            r["status"], r["where"] = "FREE", ""
        seen.setdefault(key, kw)
        yield r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export")
    ap.add_argument("--site-blog", required=True, help="the website's content/blog folder")
    ap.add_argument("--top", type=int, default=20, help="how many rows to print")
    a = ap.parse_args()
    posts = blog.site_posts(a.site_blog)
    print("| Keyword | Volume | Difficulty | Intent | Status | Where |\n|---|---|---|---|---|---|")
    for r in list(classify(read_export(a.export), posts))[: a.top]:
        print(f"| {r['keyword']} | {r['volume']} | {r['difficulty'] if r['difficulty'] is not None else '-'} | "
              f"{r['intent']} | {r['status']} | {r['where']} |")


if __name__ == "__main__":
    main()

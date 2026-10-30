#!/usr/bin/env python3
"""Put a computed trace (and optionally a quiz) into a demonstration page.

    embed_trace.py PAGE.html TRACE.json [--quiz QUIZ.json]

Replaces the contents of <script type="application/json" id="trace"> (and id="quiz-data")
in PAGE.html, after checking that the JSON parses and that every step has a title and a
narration. Run it every time compute.py changes the numbers, so the page never shows a value
the computation did not produce.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def replace_block(html, block_id, payload):
    pat = re.compile(rf'(<script type="application/json" id="{block_id}">)(.*?)(</script>)', re.S)
    if not pat.search(html):
        sys.exit(f'no <script type="application/json" id="{block_id}"> block in the page')
    text = json.dumps(payload, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return pat.sub(lambda m: m.group(1) + "\n" + text + "\n" + m.group(3), html, count=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("trace")
    ap.add_argument("--quiz")
    args = ap.parse_args()
    page = Path(args.page)
    trace = json.loads(Path(args.trace).read_text())
    steps = trace.get("steps")
    if not steps:
        sys.exit("the trace has no steps")
    bad = [i for i, s in enumerate(steps) if not s.get("title") or not s.get("narration")]
    if bad:
        sys.exit(f"steps without a title or narration: {bad}")
    for p in trace.get("parts", []):
        if not (p.get("title") and 0 <= p.get("step", -1) < len(steps)):
            sys.exit(f"part {p} needs a title and a step index inside the trace")
    legends = [("trace", trace.get("legend", []))] + [(f"step {i}", s["legend"]) for i, s in enumerate(steps) if "legend" in s]
    long = [f"{where}: '{label}'" for where, entries in legends for _, label in entries
            if len(re.findall(r"[^\W\d_]{2,}", re.sub(r"<[^>]+>", "", label))) > 4]
    if long:
        sys.exit("legend labels over four words (shorten them; the detail belongs in the narration):\n  "
                 + "\n  ".join(long))
    html = replace_block(page.read_text(), "trace", trace)
    if args.quiz:
        quiz = json.loads(Path(args.quiz).read_text())
        for q in quiz:
            assert {"q", "options", "answer", "explain"} <= set(q) and 0 <= q["answer"] < len(q["options"]), q
        html = replace_block(html, "quiz-data", quiz)
    page.write_text(html)
    print(f"{page}: {len(steps)} steps" + (f", {len(quiz)} quiz questions" if args.quiz else ""))


if __name__ == "__main__":
    main()

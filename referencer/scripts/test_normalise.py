"""Known-answer tests for quote matching: run `python3 test_normalise.py` (exits 1 on a failure).

A quote is accepted when normalise(quote) occurs in normalise(text). These cases fix what
that means at line breaks, where a hyphenation must be undone but a real dash must stay.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from referencer import normalise  # noqa: E402

# (text as extracted from a PDF, quote as copied on one line, should match)
CASES = [
    ("veri-\nfication", "verification", True),               # hyphenation across a line break
    ("veri‐\nfication", "verification", True),          # U+2010 hyphen
    ("veri­\nfication", "verification", True),          # soft hyphen
    ("8 —\n9", "8 — 9", True),                     # a "-" table cell at a row end
    ("the bound —\nwhich", "the bound — which", True),  # spaced em dash at a line end
    ("the bound—\nwhich", "the bound—which", True),     # unspaced em dash at a line end
    ("13 –\n20", "13 – 20", True),                 # en dash in a range
    ("x = −\n3", "x = −3", True),                  # minus sign at a line end
    ("two-thirds majority", "two thirds majority", False),   # negative: a hyphen is not a space
    ("8 —\n9", "8 — 10", False),                   # negative: a different number
    ("the bound —\nwhich", "the bound which holds", False),  # negative: an extra word
]


def main():
    failed = 0
    for text, quote, want in CASES:
        got = normalise(quote) in normalise(text)
        if got != want:
            failed += 1
            print(f"FAIL {text!r} / {quote!r}: matched={got}, expected {want} "
                  f"({normalise(text)!r} vs {normalise(quote)!r})")
    print(f"{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

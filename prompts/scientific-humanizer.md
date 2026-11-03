# Scientific-Humanizer — original prompt

Given 2026-10-23. Verbatim:

---

Now I would like to build a second skill called Scientific-Humanizer; it's very similar to the /humanizer skill I already have, but more tailored towards scientific writing. The shared part is avoiding common AI language patterns, as listed here: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing. The science-specific part is to avoid foreshadowing, unnecessary hedging, overstatements, and especially jargon that can just as well be replaced by simpler terms. The guidelines to use are those in @~/Downloads/GrantApplications/Style in Scientific Writing.pdf

---

## Design decisions (answers given 2026-10-23)

- **Shared part, one file:** the AI-tells catalogue lives once in `shared/ai-tells.md`,
  refreshed from the Wikipedia page as of 2026-10-23; both `~/.claude/skills/humanizer` and
  `scientific-humanizer` link to it, and `shared/check_shared.sh` fails if either becomes a
  copy. `shared/plain-strong-writing.md` (Aaronson distilled, with the user's August notes on
  "Notice…" and "And…") is shared the same way, unchanged. The pre-refresh humanizer copy is
  archived in `shared/archive/`.
- **Input:** both pasted passages (rewrite + change note + "For the author" flags) and
  manuscript files (.md/.tex, edited in place, maths/citations/references untouched, change list).
- **Claim strength:** fix the form, flag the strength. Reflexive or stacked hedges and empty
  boosters are fixed; a claim whose strength looks wrong for its evidence is flagged for the
  author, never changed.
- **Mechanical fidelity check:** `scripts/check_preservation.py` compares maths, citations,
  cross-references, numbers, URLs and code between original and rewrite.
- The user's manuscript conventions from CLAUDE.md (no foreshadowing, no reassurance about own
  checks, define before use, active voice where idiomatic, no imperative openers) are part of
  the science-specific layer (`references/scientific-style.md` §5).

## Review feedback on eval round 1 (2026-10-23), points now in the skill

- "Flagging claims to the author is the right fallback when unsure", but for a short paragraph
  the number of author recommendations was "slightly overwhelming": flags are now ranked and
  kept proportionate (about one per two or three sentences).
- Over-strong claims: "the point is to go back to neutral, not overcompensate"; and do not
  take "too much authority" (e.g. presuming a count is only simulated when it may be proven
  later).
- "Listing the proposed changes when not obvious is preferable to directly rewriting in
  place": file mode now applies only safe edits and lists the rest as proposals.
- Simplifying is good, "making new things up is not".
- Missed "This paper asks…" (inanimate subject, in the global CLAUDE.md): now an explicit
  sentence-by-sentence check. Good flag kept: roadmap mention of "checks of numerical
  reliability (Appendix E)" as possible reassurance.

## Review feedback, iteration 2 (2026-10-26)

His comments in `scientific-humanizer-workspace/iteration-2/feedback.json`, and what changed:

- **Pasted results paragraph, with the skill:** he agreed that empirical data cannot prove,
  only disprove. The pushbacks were good and every suggested fix was valid. But "a paradigm
  shift" was not handled firmly enough: it should be cut with no further discussion, though
  leaving the final decision to the author was right. **Change:** pure hype that no evidence
  could support is recommended for cutting outright, with no conditions for putting it back.
  It stays a proposal in file mode.
- **Pasted paragraph, baseline:** more conservative and further from the original. The skill
  staying closer to the original is acceptable, since authors should self-censor hyperbole,
  but a decisive review is appreciated. A citation must appear exactly where it is needed; that
  is the Referencer's job. **Change:** `referencer/SKILL.md` gained the rule "a citation must
  sit exactly where it is needed".
- **TeX theory section, with the skill:** a good review, especially the "for the author"
  section, with sound decisions on what to change automatically and what to defer to him.
- **TeX theory section, baseline:** good and concise. In general it helps to say "this is my
  recommendation" or "this is your own convention" when it is not obvious which. **Change:**
  each flag now says what it rests on when that is not obvious: his convention, the style
  references, or the agent's own suggestion.
- **BME introduction, with the skill:** he agreed with every point raised and every automatic
  fix.
- **BME introduction, baseline:** all its comments were valid, and the skill should catch the
  ones it missed. **Change:** method step 5, "Reference and grouping", covers what the baseline
  caught:
  - back-references with no antecedent ("In this sense…");
  - a list after a noun that reads as extra items ("heuristics, NJ and…" → "heuristics, namely…");
  - experimental numbers in the introduction, flagged against the no-foreshadowing rule as his
    call.
  The jargon pass now flags coined names at first use ("a pinning result") and terms used in
  tables and captions.

## Author-year citations (2026-11-03)

His words: "Let's fix the author-year citations please". check_preservation.py found 0 citations and
0 references in both Kemeny MSS papers (plain-text author-year, hand-typed "Section 3.4"). It now
extracts author-year pairs ("Shepardson and Tovey 2009", "Eggermont et al. 2013a") and hand-typed
cross-references: 119 + 242 and 72 + 240 items in the two papers; both humanizer edits still pass;
a changed year and a changed section number are both caught (negative control).

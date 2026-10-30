# Report template

```markdown
# Review of "<title>" — round <N>

<date> · reviewed version: <file name, and commit or version if known>

## Summary

<Two to four sentences: what the paper does, how, on what. One sentence of overall
impression. In later rounds, one sentence on how the revision went.>

## Status of previous points            <!-- rounds 2+ only -->

| # | Point (round N-1) | Status | Note |
|---|---|---|---|
| M1 | <short title> | resolved / partly / not resolved | <what changed, or what is missing> |
| m3 | ... | ... | ... |

## Major points

1. **<Short title stating the problem>** (<location: section, equation, lemma, table>).
   <What is wrong or missing. Why it matters. The remedy, and a cheaper fallback if there is
   one.> [carried over from M2]            <!-- tag carried-over points -->

2. ...

## Minor points

1. **<Short title>** (<location>). <One to three sentences.>
...
k. **Typos and slips.** `wrong → right` (location); `wrong → right` (location); ...

## The strongest objection

<The objection in two or three sentences, and what would defeat it. If it is already a major
point, one line pointing to it. If the paper already defeats it, say how, in one or two
sentences.>

## Mechanics                              <!-- only if needed, one line each -->

<e.g. "Several tables wrap and Table 1 is clipped on the page; the formatter skill can check
the layout.">
```

Rules:
- At most 1,000 words from Summary to the end, excluding the status table. Two to four
  sentences per point.
- At most 5 major and 10 minor points, carried-over points included. The typo bundle counts
  as one minor point.
- Number points within each list; the status table refers to them as M1…M5 and m1…m10.
- Locations use the manuscript's own numbering (section, equation, theorem, table, page).
- No overall score, recommendation or verdict.
- Do not list the deferred points in the report.

Deferred file (`…_deferred.md`): the same point format, ranked, with a one-line note on why
each was cut ("lower impact than M1–M5", "depends on M2 being fixed first").

# Formatter — original prompt

Given 2026-10-23. Verbatim:

---

Will table the review of round 2 for now. Next skill I'd like to build is the Formatter skill. It needs to address the following points (most of them already in the global CLAUDE.md): -every term is defined before first use (except possibly in the abstract) -the math renders consistently in LaTeX -no table or figure is split across two pages -no big chunks of wasted space -flag dangling short lines as potential targets for removing some words in the paragraph to shorten the paper -every reference is cited, and the numbers are in increasing order -every table and figure is cited -all numbers are given to at most 5 significant figures; large numbers are only given exactly when they matter, otherwise they are rounded for readability -no table rows get wrapped -no paragraph exceeds about 12 lines, any longer ones should ideally be split up -every section and every subsection except the first one of a section has a title -there is transition text between every section -the first section (typically Introduction) ends with "The rest of this paper is organised as follows", at least when the writing is more on the mathematical side

---

## Design decisions (answers given 2026-10-23)

- **Fix or flag:** fix layout mechanically (citation order inside a bracket, keeping a table on
  one page, column sizing so rows do not wrap); propose everything that changes wording or
  content (definitions, rounding, paragraph splits, transitions, trimming short last lines)
  with exact suggested text.
- **"Math renders consistently" means all three:** the same notation for the same object
  everywhere; no maths leaking as text (Unicode maths in prose, unconverted `$` or `\commands`
  in the PDF); typesetting quality (no overfull boxes from formulas, displays inside the margin,
  consistent display/inline choice).
- **Output:** an annotated copy of the compiled PDF (each problem highlighted with a margin note)
  plus a Markdown list of all issues by section with page numbers.
- The paper is compiled privately (separate output folder), never overwriting the author's
  own PDF or build folder.
- **Titles:** a section's opening text, before its first subsection, needs no title; every
  section and every subsection has one.
- **Ownership:** Formatter owns structure (setup section separate from the experiments;
  experiment subsection titles stating their conclusion; results tables in an appendix with a
  narrative main text; section openings and closings; roadmap coverage; reference topic
  symbols and legend). Scientific-Humanizer owns sentences (imperative openers, active voice,
  inanimate subjects, foreshadowing, reassurance). Undefined terms: both, from different angles.
- From a review note by his docket session (adopted): check both the opening and the closing
  transition of every section; the roadmap must name every section and appendix; "increasing
  order" means IEEE numbering by first citation; re-check after every layout fix.
- **Stopping rule for layout fixes** (relayed from his docket session, which he agreed to on
  2026-10-23): fix, recompile, re-check, at most 2-3 passes; stop early if a pass does not reduce
  the number of layout problems; report what remains instead of continuing.

## Review feedback, iteration 1 (2026-10-26)

His comments in `formatter-workspace/iteration-1/feedback.json`, and what changed:

- **Planted paper:** every planted error was found. The baseline found fewer, showed none of
  them in context, and had no false positives.
- **BME paper, with the skill:**
  - He agreed with the paragraph splits and liked the format of the review. Kept as it is.
  - "Pauplin weight" is defined early: $w_{ij}=2^{-\tau_{ij}}$ with the Pauplin citation, at
    line 188 of the fixture. The skill now looks for the concept under another name before
    calling a term undefined; the fix is then to attach the label at the definition.
  - The drafted transition "the next section compares…" broke his rule on inanimate subjects;
    it should be "in the next section we…". "The theory imply" was a grammar error introduced by
    a proposed cut. Now any text the skill drafts must follow §5 of `scientific-style.md`, and
    each proposal is re-read once for grammar.
  - Use $\log_2$ throughout for the manifold, since that is the paper's definition: the proof
    takes the appropriate multiplier, or uses a base-2 divergence between Shannon entropies
    directly. The skill now proposes the form the paper defines and says what switching costs.
  - **Thresholds:** no short-last-line findings for paragraphs under 3-4 lines (they are hard to
    cut) or inside algorithms and other displayed or special environments. A paragraph under 15
    lines that holds a single idea is fine. The script now:
    - reports short last lines only for paragraphs of 5 or more lines (`--min-trim-lines`);
    - skips algorithm listings, and any line that does not end a sentence (one that leads into
      a display or a list);
    - makes paragraphs of 13-14 lines review items ("split only if it holds more than one
      idea"), and proposes a split from 15 lines up (`--hard-max-lines`).
    On the BME paper this took the short-last-line findings from 25 to 15.
- **BME paper, baseline:** "very compact (borderline terse)", but some of its catches are worth
  having: the FastME version discrepancy, the undefined working label "arm" in a caption,
  threads vs cores, computer exponent notation, and mixed spelling. The last two were already
  scripted after iteration 1. The rest are now a "consistency read" review step: captions
  against their tables, repeated facts, one name per quantity, and no working labels.

## Gaps seen on the BME paper (2026-10-29), not yet fixed

- **The log check missed "! LaTeX Error: File `needspace.sty' not found."** latexmk ran in
  nonstop mode, so the build "succeeded" and the error never reached the report. Any `^!`
  line in the log should be a fix-level finding.
- **"Table D2 is never referred to" was a false positive.** The reference "(Table D2)" was
  broken across two lines of the PDF. The float-citation check should join lines, or check
  the source.
- **Six false long-paragraph findings.** This layout has no space between paragraphs, and
  the script took run-together paragraphs for single long ones (found by the BME run on
  2026-10-27).

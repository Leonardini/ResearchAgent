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

## Request, 2026-11-03: everything by label

His words: "please add a pointer/requirement to the /formatter skill: every section, subsection,
figure, table and reference needs to be done by label, so that reordering is trivial and
automatic; and also add a note to that effect to the global CLAUDE.md file, the section about
writing conventions; and finally, do that in this paper before any reordering takes place."
(Prompted by a planned reordering of the BME paper's sections and appendices.)

Applied: a "fix"-level row in SKILL.md's table, a "Labels before reordering" note (conversion
comes before any restructuring; use the paper's own mechanism or propose one; equation numbers
in parentheses are searched by hand), and `check_hardcoded_refs` in formatter.py, which
reports hand-numbered references per kind and headings that carry numbers. On the BME paper
(2026-11-03) it found 122 section, 78 table, 37 appendix, 27 theorem, 15 lemma, 16 proposition,
7 algorithm, 5 conjecture and 3 figure references, and 51 numbered headings.

## Fixes after the Kemeny MSS runs (2026-11-03)

His words: "Let's fix the four issues in the formatter now" (the four: the author's build, the
roadmap false positive, paragraphs merged under parskip, `p{}` columns reported as wrapped rows).
- **Author's build.** A Markdown draft is compiled from the author's generated `.tex`
  (`<draft>.tex` if not older than the draft, or `--tex`), not a default pandoc build: the Kemeny
  papers are 31 pages with build_mss.py and 43-46 with pandoc defaults. The build used is printed
  and written to report.md; a stale or missing .tex is warned about, naming any build script.
  The engine is pdflatex unless a magic comment or an unconditional fontspec says otherwise.
- **Roadmap.** The title written as a `#` heading (the first heading, alone at its level or
  followed by the abstract) and front matter (Abstract, Highlights, Keywords) are no longer taken
  for the first section.
- **Paragraphs.** A PDF row starting with the first four words of a source paragraph starts a new
  paragraph; in justified text a short row ending a sentence does too. (Under parskip the gap
  between paragraphs, 15 pt in paper 1, was smaller than one inside a paragraph raised by inline
  primes, 16 pt, so no layout cue alone separates them.) Lettered captions ("Figure A.1:") are
  recognised as captions.
- **Wrapped rows.** Reported only when a fixed-width cell's first and last words land on different
  table rows of the PDF; prose quoting the cell and tables whose rows start alike no longer match.
  Results: paper 1 wrapped rows 5 -> 0, long paragraphs 7 -> 5 (the false 20-line one gone),
  roadmap 1 -> 0; paper 2 wrapped rows 8 -> 0, roadmap 1 -> 0. Positive control: a wrapping
  `p{}` cell is still found, a fixed-width table that does not wrap is not.
- Also: report.md no longer cuts the review JSON part-way (points to issues.json when too long).
- **Identifiers (his words: "Formatter's doi and orcid should be allowed as exact numbers").**
  DOIs, ORCIDs, arXiv numbers, ISBNs and numbers inside web addresses are skipped by the
  significant-figures check (paper 1: 69 -> 35 findings, all now genuine counts).
- **Author-year citations ("Let's fix the author-year citations please").** For an author-year
  reference list, every entry must be cited (surname and year in the text, appendices after the
  list included; an entry named without its year is reported as such) and every citation must
  have an entry (dash-joined names, hyphenated surnames, possessives handled). Both Kemeny papers:
  0 findings, as the Referencer found; negative control (an entry deleted, a fake one added): both
  flagged.
- **Short words ("Let's not flag really short words in the formatter").** The -ise/-ize check needs
  at least three letters before -is-/-iz-, so "rising", "arise", "size", "seize" are not spelling
  variants; "organise", "realized", "minimisation" still are.
- **Subsection titles (2026-11-05, his words: "For subsection names: going over one line is a flag, as is using
  'and' such as 'clause 1 AND clause 2' - these should be split into separate subsections; please update the
  /formatter skill accordingly as well").** New check `subsection-titles`: a subsection title that wraps in the
  PDF (a heading row holding a prefix of the title's words, the next row holding the words that follow) is a
  proposed change; every subsection title containing "and" (or ", but"/", while"/", whereas") is listed for the
  agent to judge whether it joins two claims (split) or nouns (fine). Top-level sections are exempt (journals fix
  some, e.g. "Declaration of competing interest"). BME paper: 2 wrapping titles (both two-claim titles), 8 "and"
  candidates, of which those 2 join claims; the earlier 3 false wraps from shared first words are gone.
- **Roadmap without appendices (2026-11-05, his words: "The appendices in 'the rest is organised as follows'
  need either cutting or a separate paragraph, I prefer the former").** The roadmap check now requires the
  sections only, and a roadmap that lists appendices gets a proposed cut. Controls: the BME roadmap before
  the cut is flagged (10 appendix mentions), after it is not.
- **Long paragraph across a page (2026-11-05, his words: "On p.7 there is an insanely long paragraph, this
  should have been flagged by the formatter").** It was found (27 lines) but reported and highlighted on
  page 6, where only its first 2 lines are. A long paragraph is now marked on the page holding most of its
  lines, and the message names every page it covers ("pages 6–7").
- **Sections without subsections (2026-11-05, his words: "In general, I don't want short sections (with no
  subsections), except the intro and the conclusion/discussion, as that reflects poor organisation of the
  ideas - please add a note to the formatter").** New check `flat-section`: a main-text section with no
  subsections is a proposed change, except the introduction, the conclusion or discussion, front and back
  matter (declarations, funding, CRediT, data availability, acknowledgements), unnumbered sections and
  everything from the first appendix or the reference list on. Prompted by folding the BME paper's
  "From the formulation to a solver" into its introduction and solver description. Results: BME 1 (the
  cut-value ladder section), Kemeny paper 1 6 (sections 2-6 and 9), Kemeny paper 2 0.

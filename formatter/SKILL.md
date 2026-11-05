---
name: formatter
description: Check and fix the layout and structure of a scientific manuscript (pandoc Markdown or LaTeX) against the author's formatting conventions. It compiles a private copy and finds tables split across pages, large empty spaces, paragraphs over about 12 lines, short dangling last lines worth trimming, wrapped table rows, overfull or inconsistent mathematics, uncited references, tables and figures, cross-references and headings numbered by hand instead of by label, citation numbers out of order, numbers with more than 5 significant figures, terms used before they are defined, untitled sections, sections without subsections, subsection titles that wrap or join two claims with "and", missing section openings and closings, and a missing or incomplete "The rest of this paper is organised as follows" paragraph. Layout problems are fixed mechanically, wording changes are proposed, and everything is marked on an annotated PDF. Use this whenever the user asks to format, typeset-check, polish the layout of, tighten, shorten, or prepare a paper for submission, mentions page breaks, floats, cross-references, labels, renumbering or reordering sections or appendices, overfull boxes, widows or orphans, citation order or numbering, the roadmap paragraph or section transitions, or asks whether a manuscript follows their conventions.
---

# Formatter

A paper is read as pages. A table broken across two of them, half a page left empty, a
paragraph that runs for most of a page, or a reference never cited all cost the reader effort
and tell a referee the paper was not checked. This skill finds these problems on the compiled
pages and in the source. It fixes the ones that only move ink, and proposes exact wording for
the ones that change what the paper says.

It covers **structure and layout**. Sentence-level style (hedging, jargon, AI tells, imperative
openers, active voice, foreshadowing) belongs to the `scientific-humanizer` skill, and
whether citations support their claims belongs to the `referencer` skill. Say so in the report
if the user seems to expect them here.

## What is checked

| Convention | Found by | Severity |
|---|---|---|
| No table split across two pages | script (PDF) | fix |
| No large empty areas | script (PDF) | fix |
| Table rows never wrap | script (TeX column types) | fix |
| Mathematics renders consistently: nothing sticks into the margin, no Unicode maths in prose, no raw markup in the PDF, one notation per object | script + agent | fix / propose / review |
| Every reference cited; numbers increase in order of first citation and inside each bracket; references carry topic symbols and a legend. Author-year papers: every entry cited, every citation has an entry | script (PDF; author-year from the source) | fix / propose / review |
| Every table and figure referred to in the text | script (PDF) | propose |
| Every section, subsection, appendix, figure, table, theorem-like statement, algorithm, numbered equation and reference is cited by label, never by a hand-written number, and headings carry no hand-written numbers | script (source) | fix |
| At most 5 significant figures; large numbers exact only when exactness matters | script finds, agent judges | propose |
| No paragraph over about 12 lines (13-14 lines only if it holds more than one idea) | script (PDF) | propose / review |
| Short last lines flagged as places to trim a few words (paragraphs of 5+ lines, outside algorithms and displays) | script (PDF) | propose |
| Every term defined before first use (the abstract is exempt) | script (acronyms) + agent (all terms) | propose / review |
| Every section and subsection has a title (a section's opening text before its first subsection needs none) | script | propose |
| No section without subsections, except the introduction and the conclusion or discussion (back matter and appendices are exempt): a flat section signals ideas that belong elsewhere | script | propose |
| A subsection title fits on one line and makes one point: a title that wraps, or that joins two claims with "and" ("X certifies … and is slower"), means the subsection should be split | script (wrapping, PDF; candidate "and"s, source) + agent judges | propose / review |
| Each section opens with 1-2 sentences on what it does and closes with 1-2 leading into the next | script finds gaps, agent judges | propose |
| The first section ends with "The rest of this paper is organised as follows", naming every section, and not the appendices (required when the paper is mathematical) | script | propose |
| Experimental setup in its own section, experiment subsection titles state their conclusion, results tables in an appendix with a narrative main text | agent, using the headings list | review |

**Labels before reordering.** Cross-references by label are what make moving a section,
appendix or table trivial: the build renumbers everything and no reference goes stale. So
when a paper numbers by hand, converting it to labels comes before any restructuring, and a
request to reorder sections or appendices starts with this conversion. For pandoc Markdown,
use the paper's existing mechanism if it has one (pandoc-crossref, a Lua filter); otherwise
propose one before converting, since the choice affects the author's build. References are
already by key under citeproc. The script does not see bare parenthesised equation numbers
such as "(4)–(9)": search for those by hand.

**fix** = mechanical: apply it, then re-check. **propose** = changes wording or content: write
the exact suggested text, do not apply it. **review** = needs the author's judgement.

## Workflow

### 1. Run the checks

```
python3 <skill-dir>/scripts/formatter.py check paper.md     # or paper.tex
```

This compiles a private copy into `formatter/` next to the draft (its own `.gitignore`), with
pandoc's defaults file taken from the folder's Makefile when there is one. It never runs the
author's own build and never touches their PDF. It writes `issues.json`, `report.md` and
`annotated.pdf`. It needs pandoc, latexmk and PyMuPDF. If the compilation fails, report the
LaTeX error and stop: do not edit the paper to make it compile unless asked.

**Check the pages the author actually produces.** Many Markdown papers are built by their own
script (a custom preamble, margins, floats), and a default pandoc build can differ by a dozen
pages, which makes every page, gap and overfull finding wrong. So the script compiles the
`.tex` the author's build produced: `<draft>.tex` beside the draft when it is at least as new
as the draft, or the file given with `--tex`. The source checks still read the Markdown. The
first line of the output, and of `report.md`, says which build was used. If it warns that the
`.tex` is stale or missing and names a build script, run the author's build (into a scratch
copy if it writes beside the draft) and pass its `.tex` with `--tex`. If the page count still
differs from the author's PDF, say so before reporting any layout finding.

Read `report.md` in full. Some findings are false positives: a "short last line" that is the
end of a list item, an "acronym" that is a product name (CPLEX, MOSEK) or a standard symbol.
Drop those, and say in one line which kinds you dropped.

### 2. Apply the layout fixes, then re-check (at most three passes)

Look before you edit: if the draft is in git with uncommitted changes, or not in git, copy it
(and any preamble you change) to `<name>.before-formatter.<ext>` first and say so.

Fixes by finding:

- **Split table**: a table shorter than a page should be a float, which LaTeX never splits
  and places where it fits. In a LaTeX source, turn the short `longtable` into
  `\begin{table}[tbp]` around a `tabular`, keeping caption, label and rules. In a pandoc
  source (which always writes `longtable`), add `assets/keep-longtables-together.tex` to the
  preamble (append it to the file listed under `include-in-header`). That moves a breaking
  table whole to the next page, which can leave a gap behind it: re-check, and if the gap is
  large, move the table's position in the source to just before a paragraph break near
  where it fell. A table genuinely longer than a page may split; repeat its header and say so.
- **Large empty area**: find the cause on that page of `paper.tex`. Usual causes, in order:
  a float too tall for the space left (try `assets/float-placement.tex`, which loosens LaTeX's
  float limits, or a `[tbp]`/`[!tbp]` specifier); a float with `[H]`/`[h]` (relax it); a
  `\clearpage`/`\newpage` (remove it unless a part or appendix needs a new page); a long
  unbreakable display. Change placement, never content.
- **Wrapped table rows**: give columns their natural width (pandoc defaults `columns: 1000`;
  LaTeX `l`/`c`/`r` instead of `p{…}`), and if the table is then too wide set it in `\small`
  (the author's convention is that cells never wrap and the font shrinks instead).
- **Citation numbers out of order inside a bracket**: reorder the keys in the source citation
  (`[@b; @a]` → `[@a; @b]`, `\cite{b,a}` → `\cite{a,b}`) to match the reference numbers.
  If numbers first appear out of order across the paper, the bibliography style is not
  numbering by first citation: report that as a finding, since it is a style choice.
- **A line in the margin from a long formula**: let it break (`\allowbreak` at a relation),
  or move it to a display. **Unicode maths or raw markup in the PDF**: write it as LaTeX maths
  (`−` → `$-$`, `≤` → `$\le$`).
- **Undefined reference or citation**: report it; the label or bibliography entry is missing.

Then run `check` again. Every fix reflows the pages, so it can create a new split, gap or
short line further down, and a second round can undo the first. **Stop after at most three
passes, and stop early when a pass does not reduce the number of layout findings** (split
tables, empty areas, wrapped rows, margin overflows). Report whatever remains instead of
continuing.

### 3. Propose the wording changes

For each, give the location (section and page), the current text, and the exact suggested
text. Never apply them. Keep each proposal short enough to accept or reject at a glance.

**Text you draft must already follow the author's conventions**, or the author has to fix your
fix. Before writing any proposed sentence (a transition, a roadmap, a definition, a cut), read
§5 of `../scientific-humanizer/references/scientific-style.md`. The rules most often broken in
drafted transitions: no inanimate subject doing something only a person does ("the next section
compares…" → "in the next section we compare…"), no imperative openers, active voice. Then
re-read each proposal once for grammar, above all subject-verb agreement after a cut ("the
theoretical results imply" cut to "the theory imply" is wrong; "the theory implies").

- **Long paragraph**: name the sentence where it splits naturally (where the topic shifts).
  Quote the first words of the new paragraph. The script proposes paragraphs of 15 lines or
  more, and lists those of 13-14 lines as review items: propose a split for these only when
  the paragraph holds two ideas; a single argument of 13-14 lines can stay whole.
- **Short last line**: propose the cut that removes it: the line holds N characters, so suggest
  removing about N + 2 characters elsewhere in the paragraph (a redundant clause, a padding
  phrase). Only propose cuts that lose no content; if none exists, say so and move on. These
  are the cheapest way to shorten a paper, so list them all, but briefly. The script already
  skips paragraphs under 5 lines (too little to cut from), algorithm listings, and lines that
  lead into a display or a list; drop any it still reports inside an algorithm, a theorem
  statement's display or another special environment.
- **Numbers**: say whether the exact value matters (a certified optimum, a count the reader may
  check, an identifier) or whether it should be rounded, and give the rounded form
  (12,160,639 → "about 12.2 million"; 802.589 → 802.59). Keep a value exact, and say why,
  when the paper's argument uses its exact value.
- **Terms used before they are defined**: read the paper in order from the end of the abstract
  and list every term (not only acronyms) used before its definition: technical terms, symbols
  introduced in prose, the authors' own working labels. For each, point to where it is defined
  (if anywhere) and propose the shortest fix: move the definition up, or add a definition at
  first use. Take the definition's wording from the paper itself; if the paper never defines
  the term, say so and leave the definition to the author. Before calling a term undefined,
  look for the *concept* under another name, from the abstract on: a paper may define the
  object without attaching the label ("$w_{ij}=2^{-\tau_{ij}}$ [Pauplin]" defines what it later
  calls "Pauplin weights"). Then the fix is one phrase at that definition ("…, the Pauplin
  weights"), not a new definition. Product names and standard
  abbreviations of the field need no definition; mention them in one line if the script
  listed them.
- **Section openings and closings**: `issues.json` → `review_material.section_openings_and_closings`
  gives each section's first and last sentences. A section must open by saying what it does
  ("In this section we…") and close with a sentence leading into the next, making the
  connection explicit. A closing sentence that names the next section's question is a
  transition, not foreshadowing: it states no result. Propose a sentence for each one missing,
  drawn from the actual content of the two sections. Mark it as a draft for the author.
- **Roadmap paragraph**: if missing, draft it from the headings (every section, each with what
  it does). If present, list the sections it leaves out. It does not list the appendices: the
  author prefers cutting them from the roadmap to giving them a paragraph of their own, since
  each appendix is reached from the text that uses it. If the roadmap lists them, propose the cut.
- **Untitled section or subsection**: propose a title that states the content. For an
  experiment subsection, the title states the conclusion ("The minimum-cut family carries most
  of the root bound"), not the topic.
- **Section without subsections** (`flat-section`): the author treats a main-text section with
  no subsections, other than the introduction and the conclusion or discussion, as a sign that
  the ideas are poorly organised. Propose where its content belongs: usually split between the
  first place the paper introduces the idea (for the high-level point) and the section that
  uses it in detail (for the specifics), as when a short "from the formulation to a solver"
  section was folded into the introduction and the solver's description. If the content does
  stand on its own, propose the subsections it needs instead. This is a flag, not a rule: a short
  paper made of genuinely one-off results (a run of separate counterexamples or bounds) can keep
  flat sections, so say which case the paper looks like and leave the call to the author.
- **Subsection titles** (`subsection-titles`): a subsection title that runs over one line, or
  that joins two claims with "and" (each side with its own verb: "The compact solver certifies
  every instance … and is mostly slower than …"), covers two things, so propose splitting the
  subsection in two, one claim per title, and say where the text divides. The script lists every
  subsection title containing "and" (or ", but", ", while", ", whereas"); dismiss the ones where
  it joins nouns ("Trees, splits and tree metrics", "NJ and FastME miss the optimal tree"). A
  title that wraps but states one claim is shortened instead. This applies to subsections, not to
  top-level sections, whose titles a journal sometimes fixes ("Declaration of competing
  interest").
- **Uncited table or figure**: propose the sentence where it should be referred to.
- **Uncited reference**: cite it where it belongs, or remove it from the bibliography.

### 4. Review items

- **Notation**: `review_material.maths_inventory` lists letters used as maths symbols that also
  appear as plain text (an "n" in prose where `$n$` is meant), operator names written both
  wrapped and bare (`\mathrm{entr}` and `entr`), and mixed inline fraction commands. Check each,
  and look for one object written two ways (`W[S]` and `W_T[S]` without saying how they
  relate, `w` and `\mathbf w`, `\le` in one place and `\leqslant` in another, `\log_2` in the
  definition and `\ln` in a proof), and for comparable formulas displayed in one place and
  inline in another. Propose the form the paper defines and uses most, and say what the change
  costs where the other form was used (switching a proof from `\ln` to `\log_2` adds a factor
  $\ln 2$, or the proof can use the base-2 form of the quantity directly).
- **Consistency read**: the same fact stated twice must agree. Check that each table caption
  describes the table's actual columns and marks (a caption explaining "a cell marked *" when no
  cell carries one); that a software version, hardware figure or count is the same wherever it
  is stated (FastME 2.1.6 in one place, 2.1.6.3 in another; 32 taxa vs 30); that one quantity
  has one name ("ten cores" in one caption, "10 threads" in another); and that captions and
  table headers use no working labels the text never defines ("arm"). Generated tables (between
  sync markers, or written by a script) are fixed in their generator, not in the paper: say so.
- **Structure**: from `review_material.headings`, check that the experimental setup (hardware,
  software, instances, metrics) has its own section, separate from the experiments; that
  each experiment subsection title states its conclusion; and that the main text states
  results in words, with detailed tables (timings, node counts) in an appendix.

### 5. Mark your own findings on the PDF

Write the proposals and review items to a JSON list and render them with the script's:

```
[{"check": "definitions", "severity": "propose", "message": "...", "find": "words on the page", "section": "2. Preliminaries"}, ...]

python3 <skill-dir>/scripts/formatter.py annotate paper.md --extra review.json
```

`find` is a short phrase that occurs on the page (it is searched for, and narrowed to fit a
line if needed). The annotated PDF and `report.md` then carry everything.

## Reporting to the user

Lead with what changed in the files (each layout fix, with the file and line), then the
number of passes and what still remains. Then the proposals, grouped by kind, most
consequential first: definitions, transitions and roadmap, then uncited items, numbers, long
paragraphs, and short last lines last (with a count, since there may be many). Then the
review items. Give the path to `annotated.pdf`. Each highlight there carries a note, coloured
red for fixes, orange for proposals and blue for review items.

Keep it proportionate. For a long paper, group the short-line and long-paragraph proposals in
a table rather than one bullet each.

---
name: peer-reviewer
description: Review a scientific manuscript the way a highly competent, constructive peer reviewer would, with the methods judged on their own merits first and presentation, clarity and reproducibility second. Writes a referee report of at most 1,000 words and 5 major and 10 minor points, each locating the problem, saying why it matters and proposing a concrete remedy. It checks every claimed error with a verification subagent before raising it, puts the paper in the context of prior work (through the LitReviewer skill when one is available) to judge novelty, and states the strongest objection to the main claim. When given the previous round's review, it first reports which points were resolved and then reviews again, so it can run in a review-fix-confirm loop. Use this whenever the user asks for a review, referee report, critique, assessment or "what would a reviewer say" on a paper, preprint or draft, asks whether a manuscript is ready to submit, asks to re-review after revisions, or mentions the PeerReviewer.
---

# PeerReviewer

A good referee report changes the paper. It finds what would make a careful reader stop
trusting a result, says exactly where and why, and proposes something the authors can do
about it. Copy-editing finds many small things and changes little; a report built on the
methods finds the few things that matter. That is the job here.

The report is written for the authors, in the voice of a senior colleague who has read the
paper carefully, checked what can be checked, and wants it to succeed. Constructive does not
mean soft: an error is called an error. It means every criticism comes with the reason it
matters and a way forward.

## Scope, and what belongs to other skills

| Focus | Weight |
|---|---|
| **Methods, on their own merits**: are the mathematics, algorithms, models, statistics and experimental design correct and suited to the question? Do the results support the claims? | primary |
| **Presentation, readability, clarity**: can a competent reader follow the argument, find the definitions, and see what was done? | secondary |
| **Reproducibility**: could someone redo the work from what is given? | secondary |
| **Novelty and contribution**, in the context of prior work | informs both |

"On their own merits" means judging whether a method is sound and fit for its purpose, not
whether it beats the state of the art. A method that is slower but correct and honestly
assessed is a contribution; a fast method whose evaluation cannot support its claim is not.
Ask for an extra experiment or analysis only when you can say what its outcome would decide.

**Internal papers** (the user's own, with a public reproduction repository): treat the
reproduction repository as meeting the reproducibility goal. Do not raise reproducibility
points beyond a mismatch between what the paper says and what it points the reader to.

Mechanics have their own skills; mention them in one line at the end if they look needed,
rather than spending points on them:
- layout, table wrapping, citation order, section transitions → `formatter`
- sentence-level style, hedging, AI tells → `scientific-humanizer`
- whether each citation supports its claim → `referencer`

A presentation problem earns a point here only when it stops a reader understanding or
trusting the work (an undefined quantity a proof depends on, a model never fully stated, a
table that contradicts the text). Typos and small slips go together in one minor point.

## Inputs

- The manuscript: pandoc Markdown, LaTeX or PDF. Read the source if there is one, and look at
  the compiled PDF too for tables, figures and anything the source cannot show.
- Optional: the previous round's review (see **The loop**), the reproduction repository, the
  supplementary material, the target venue.
- Confidentiality: a manuscript under review by someone else is confidential. Send no part of
  its text to any outside service; describe its topic in your own words when searching.

## Workflow

### 1. Read the paper as a referee

Read it all, appendices included, before writing anything. Then write down, for yourself:
- the main claims, in one line each, and the evidence offered for each (proof, experiment,
  citation, nothing);
- the methods: what is computed or proved, under which assumptions, and how it is evaluated;
- where the argument is weakest: an assumption doing heavy lifting, a step the proof skips,
  a comparison that is not like with like, a conclusion broader than its evidence.

`references/methods-checklist.md` lists the questions to ask of each kind of method (proofs,
optimisation models, algorithms, statistical models, machine learning, simulations,
benchmarks). Use the parts that apply. For every theorem, ask whether the same proof gives a
stronger statement (a hypothesis it never uses, constraints that enter only through their
sum, a bound with slack): a stronger form is often the most useful thing a referee can offer.

Then make one **consistency pass**, mechanically, with the checklist's last section: every
caption's legend against its table's cells, every inequality or definition that appears in
two places against itself, every number in the text against the table it comes from, every
choice in the pseudocode specified. These errors are cheap to find and each one costs a
reader's trust; they become minor points (or one bundled minor point if there are several
small ones).

### 2. Place it in the literature (when novelty is in doubt)

If the contribution's novelty or its relation to prior work is unclear, use the **LitReviewer**
skill if it is available: give it two or three questions describing the contribution in your
own words (never the manuscript's text) and ask for the closest prior work. Run it as a
**novelty check, not a full review**: paper mode, one round of searches, stop once the
closest prior work for each question is found, and skip its web page unless the user wants
it. Without the skill, search the web directly, and read full text only from open copies
(arXiv, bioRxiv, open access); for anything else, use the title, abstract and short quotes.

**Outside searches are allowed by default**: literature databases (Undermind, OpenAlex,
Semantic Scholar, arXiv), web search and fetching open copies need no confirmation, including
when the skill runs as a subagent. Two limits still hold: the queries describe the work in
your own words (see **Inputs**), and the user's email address is never sent to any service
(for example an Unpaywall `email=` or an OpenAlex `mailto=` parameter) unless the user has
agreed to it in this conversation.

Use what you find to judge novelty and to name specific missing or mischaracterised work. A
missing reference is a point only if it changes how the contribution should be read.

### 3. Verify before you accuse

Every point that says something is **wrong**, such as a proof step, a derivation, a number
that contradicts another, or a claim the data cannot support, must be checked before it goes
in the report. Spawn up to four checker subagents in parallel, one claim each, with the
instructions in `references/checkers.md`. Each returns CONFIRMED, REFUTED or UNCLEAR with its
reasoning.

- CONFIRMED: raise it as a statement, with the evidence.
- UNCLEAR: raise it as a question ("unless I am missing something, …").
- REFUTED: drop it.

A wrong accusation costs more than a missed point: it wastes a round of the loop and teaches
the authors to discount the rest of the report.

### 4. The strongest objection

Construct the strongest objection a hostile but honest expert could make to the paper's main
claim, and say what evidence or argument would defeat it. If the paper already defeats it,
say so in one or two sentences. If it does not, it is a major point. See
`references/devils-advocate.md`.

### 5. Choose the points

Draft every candidate point, then rank and cut.

- **Major** (at most 5): would change a conclusion, the validity of a result, or a reader's
  ability to trust or use the method. A proof gap, an evaluation that cannot support the
  claim, a missing comparison without which the contribution cannot be judged, a model that
  is never fully specified.
- **Minor** (at most 10): local and fixable without changing the conclusions. A step that
  needs a sentence of justification, a missing definition, a figure that is hard to read,
  a reference that should be added. All typos and slips go in **one** minor point, as
  `wrong → right` pairs.

The caps are hard. They exist because the report runs in a loop: a short list of the most
important points gets fixed; a long one gets triaged by the authors instead of by you. When
there are more candidates than room, keep the ones with the largest effect on what the
reader can believe. Write the rest to the deferred file (see **Output**) so the next round
can pick them up; do not mention them in the report.

### 6. Write the report

Follow `references/review-template.md`. The voice and the shape of each point follow the
user's own reviews, summarised in `references/style-guide.md`. Read it before writing: in
short, each point locates the problem precisely, says why it matters, and proposes a
concrete remedy, often with a cheaper fallback ("if no other dataset can be obtained, at
the very least…").

**At most 1,000 words**, from the Summary to the end (the status table of later rounds does
not count). Each point takes two to four sentences: what and where, why it matters, the
remedy. If a point seems to need more, the extra is usually evidence the authors do not need
in full: give the conclusion and one line of the derivation ("at n = 4, A_T is a segment").
Count the words before finishing and cut until the report fits.

Give no overall verdict, score or recommendation (accept, minor or major revision, reject),
not in the report and not in the chat summary, even when reviewing "as a referee for" a named
venue whose forms ask for one. The loop decides when to stop. If the user explicitly asks for
a recommendation, give it in chat, in one line, with the point that decides it.

### 7. A style pass with scientific-humanizer

Run the `scientific-humanizer` skill on the finished report file, in place. Tell it three
things: this is a referee report; keep every hedge that marks a genuine doubt ("unless I am
missing something", "I believe … but"), since those encode the checkers' UNCLEAR verdicts;
and keep the point numbers, locations, `wrong → right` pairs and the 1,000-word budget. The
pass matters most when the report goes to someone else (a collaborator's paper, an external
review); for the user's own papers it is still worth doing. If the skill is not available,
say so and skip it.

## The loop

The skill is called repeatedly: review → the authors fix → review again. When a previous
review is supplied (or found as the newest `*_peer-review-r<N>.md`, or the newest report whose title
ends "— round <N>", beside the manuscript or in its `reviews/` folder),
start the report with **Status of previous points**: for each earlier point, resolved,
partly resolved, or not resolved, with one line on what changed or what is still missing.
Check the revised text itself; do not take a response letter's word for it.

Then review the revised paper as in steps 1–6. Points not resolved or only partly resolved
are carried into the new lists and count towards the caps (5 major, 10 minor), together with
any new points. Pull from the previous deferred file first, if one exists, when there is
room. Do not raise as new a point the authors resolved, and do not re-raise a point in a new
form after they addressed its substance.

When nothing major remains and the minor points are only polish, say so plainly in the
summary.

## Output

Write the report beside the manuscript, in a `reviews/` folder if one exists:
`<YYYY-MM-DD>_peer-review-r<N>.md`, with N the round number (1 if no earlier
`*_peer-review-r*.md` exists). Write the deferred points, if any, to
`<YYYY-MM-DD>_peer-review-r<N>_deferred.md` in the same folder. If the user (or the agent
that called you) names the report's path, use it, write the deferred points beside it as
`<report stem>_deferred.md`, and keep the template's title line (`# Review of "…" — round <N>`)
so the next round can find it by content rather than by name. In chat, give the counts
(major, minor, and for later rounds resolved / partly / not), the one-line titles of the
major points, and the path. Do not paste the whole report.

## Reference files

- `references/style-guide.md` — the user's reviewing voice, with examples from his reviews.
  Read before writing.
- `references/review-template.md` — the report's structure.
- `references/methods-checklist.md` — questions to ask of each kind of method.
- `references/checkers.md` — the instructions for a checker subagent.
- `references/devils-advocate.md` — how to build the strongest objection.

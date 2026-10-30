---
name: lit-reviewer
description: Review the literature around a research project and build an interactive web page of every relevant paper, preprint, blog post or repository, each linked, colour-coded by how much it overlaps the project (red = overlap risk, amber = closely related, green = background) and sorted by date. For a project already under way, it also states, target by target, what each overlapping item has already achieved and what remains for the project. Two modes - paper mode (journal and conference papers, with preprints that pose a real overlap risk) and broad mode for fast-moving fields (adds preprints, blogs, project sites, repositories, leaderboards, OEIS-style records). Keeps a ledger, so a re-run shows what is new since last time. Use this whenever the user asks for a literature review, a related-work search, a "has anyone done this" or scooping check, prior art, the state of the art, novelty or competition around a project, what has appeared since a survey, or mentions the LitReviewer, even if they do not say "literature review".
---

# LitReviewer

A literature review for a working researcher answers two questions: **has someone already done
what we are trying to do**, and **what does the field already know that we should build on**.
The first is the expensive one to get wrong, so the page leads with it: every item is coloured by
how much it overlaps the project, and for an active project each red or amber item says exactly
which target it touches, what it achieved, and what is left for the project.

Three things make the review trustworthy, and the workflow exists to protect them:

1. **Every item comes from a tool result, never from memory.** Items enter the ledger only through
   `litreview.py` (an API search, a citation expansion, or `add`, which resolves the DOI, arXiv id
   or URL itself and refuses a link that does not load). Titles, authors and dates are the
   source's, not yours. A paper you "know" exists but cannot surface with a tool does not go on
   the page; mention it in the synthesis as unverified if it matters.
2. **Every search is logged**, including the ones made outside the script (Undermind, web search),
   so the reader can see what was looked for and judge what might be missing.
3. **A verdict says what it rests on.** An item judged from its abstract is marked "abstract only".
   Red means the item does all or part of a project target, and the script refuses a red verdict
   that does not name the target and say what the item achieved.

## Files

Everything lives in `<project>/litreview/` (create it; never in /tmp or a scratchpad, since the
ledger is what makes the next run incremental):

| file | written by | content |
|---|---|---|
| `brief.json` | you | the project's question, targets `T1..`, results so far `A1..`, mode |
| `ledger.json` | the script | every item ever seen, its verdict and history; every search |
| `synthesis.md` | you | a short reading of what the red and amber items mean for the project |
| `index.html` | `build` | the interactive page (self-contained, works offline) |

The script is `scripts/litreview.py` (Python standard library only). Run it as
`python3 <skill-dir>/scripts/litreview.py <command> <project> ...`; `--help` on any command lists
its options.

## Step 0: is there already a ledger?

If `<project>/litreview/ledger.json` exists, this is a re-run. Read `brief.json`, ask whether the
targets have changed (update the brief if so), then continue from step 2. The new run marks items
first seen in it as **new**, and `stale` lists red and amber verdicts made under different targets;
re-assess those. Never delete an item from the ledger: an item that no longer matters gets a new
verdict, and its history shows the change.

## Step 1: the brief

Read the project: README, CLAUDE.md or AGENTS.md, notes, prompt logs, the manuscript and its
bibliography if there is one, recent commits. Then write `brief.json`:

```json
{
  "name": "Short project name",
  "mode": "paper",
  "active": true,
  "summary": "Two or three plain sentences: the question, the approach, why it matters.",
  "targets": [{"id": "T1", "text": "What the project aims to establish, one claim per target"}],
  "achieved": [{"id": "A1", "text": "A result the project already has (active projects only)"}],
  "terms": ["key phrases and synonyms used in the field"],
  "seeds": ["DOIs or arXiv ids of the papers the project is closest to"],
  "references": ["Manuscript/references.bib"]
}
```

`references` names the project's own reference list (a `.bib`, or a Markdown or text file with
DOIs and titles). `build` marks every item the project already cites, so the reader can tell a
discovery from a paper they know, and the page can show only what is not yet cited. Look for one
in any project (a manuscript's `.bib`, a References section in notes); without it, a review can
present the user's own key references as news.

Targets are what the overlap is judged against, so make each one a specific, checkable claim
("a scheduler that provably meets every deadline on 500-job instances", not "work on scheduling"). When the user
already knows part of a target is settled ("only the weighted case is still open"), phrase the target
as the open part; the source that settled the rest is then amber context, not red.

An **active** project is one with results already (code that runs, numbers, a draft). List under
`achieved` the results the project would claim as its own (a theorem, a solver's reach, a new
dataset), not textbook facts it reproduced along the way, because for an active project the worst
overlap is an item that already obtained one of them. Add `"own": [...]` with the project's own
DOIs, arXiv ids or URLs (its preprint, code deposit, talk); when searches return them, give them
the relevance `own` so they are kept apart from the literature.

**Mode.** Use what the user asked for. Otherwise: paper mode for established fields where the
record is in journals and arXiv; broad mode when the field moves faster than journals (machine
learning, AI tooling, live computational records, competitions), or when the user mentions blogs,
preprints or "what's new". In paper mode, posts and repositories are not searched for, but a
preprint that is a real overlap risk is always kept: an unrefereed scoop is still a scoop.

If the user is in the conversation, show them the targets (one line each) before searching and
let them correct them: a wrong target makes every colour on the page wrong. If they are not, go
ahead and state your reading of the targets in the synthesis.

## Step 2: search

`init` creates the ledger; `run --note "..."` opens a run (it needs the brief). Then search from
several directions, because each misses what the others find:

- **Citation graph.** For each seed, `expand --direction cites` (who cites it, newest first; this
  is where recent overlap shows up) and, for the closest one or two, `expand --direction refs`.
  Expanding from the newest red items found so far often finds the rest.
- **Keyword searches** on `--source openalex` and `--source arxiv`: 8 to 20 queries mixing the
  field's terms, the problem's other names, and the method's names. For overlap risk add
  `--since` (about 3 years back in fast fields, 5 to 10 in slow ones) or `--recent` on arXiv.
  An unprefixed arXiv query requires every word (or "quoted phrase") in the title or abstract;
  raw arXiv syntax (`abs:`, `ti:`, `au:`, `cat:`) is passed through unchanged. arXiv rate-limits
  hard: a failed query is logged as failed, so move on and come back to it later.
- **People.** The groups behind the seeds and the first red or amber items are the likeliest to
  have the next result. For the two to four most active ones, `author --name "..." --since ...`
  adds their recent works; check their web pages too (preprints, working papers, talks).
- **Web search, in both modes.** Journals and arXiv miss a lot of early work: discussion and
  working-paper series (RePEc, institutional repositories), conference programmes and extended
  abstracts, theses, technical reports, and anything too recent for the indexes. Search the web
  for the problem's names and for the active groups' names with the topic. In paper mode keep
  what is scholarly (add papers by `--doi` or `--arxiv`, and grey literature by `--url
  --type paper|talk|thesis`); in broad mode keep posts and repositories as well.
  `--source s2` (Semantic Scholar) usually returns HTTP 429 without an `S2_API_KEY`; the script
  logs that as a failed query, which is fine.
- **Undermind**, when connected: one to three deep searches phrased as the project's question
  (call `get_orientation` and `list_workspaces` first). Record each with `log --source undermind`
  and add every relevant hit with `add --doi ... --via undermind` (or `--arxiv`). Undermind's
  corpus is papers only, and its summaries can be wrong about things outside that corpus, so
  treat its claims as leads, not verdicts. If it is unavailable or out of quota, log that, lean
  harder on web search and author tracking, and name the gap in the synthesis.
- **Tools for the web:** use WebSearch and WebFetch (or `curl`) first. Keep Firecrawl for pages
  those cannot read (heavy JavaScript, blocked fetches): its credits are limited and shared.
- **Broad mode adds** blog posts, lab and company announcements, project sites, GitHub
  repositories, leaderboards and records pages (OEIS, a maintainer's table). Add each with
  `add --url ... --via web --type post|repo|dataset|talk`. When a records page or log announces
  results by different people (a new record, a solved case), give each result that bears on a
  target its own item (the page's anchor if it has one, `--title "Smith: first tiling of
  order 41"`-style, `--date` of the result), so a competitor's result can be coloured red on its
  own instead of being buried in an amber "records page" entry.

Log every search made outside the script with `log` (and `--new N` for the items it added). For
web items the script reads the title and date from the page; give `--date` (or `--title`, when a
source mangles it) only from what you saw on the page, and add a one-sentence `--abstract`.

Stop when the last several queries add nothing new that you would keep. Typical sizes: 50 to 600
candidates, of which 15 to 80 are kept. `status` shows counts at any time. Broad keyword searches
pull in junk (Zenodo uploads, unrelated fields); `screen-out --match REGEX --reason "..."` lists
the unscreened items a pattern catches and, with `--yes`, marks them irrelevant in one step.
Look at every title the dry run lists before confirming; a pattern loose enough to catch the junk
also catches the odd on-topic paper. Once every item worth keeping has a verdict, `screen-out
--rest --reason "..."` marks whatever is still unscreened in one step (dry run first). For author
tracking in broad fields, `author --topic REGEX` keeps only the works on the topic.

**OpenAlex budget.** The script reads an API key from `OPENALEX_API_KEY` or
`~/.config/openalex/api_key`, and drops it (with a notice) if OpenAlex refuses it. Without a working
key OpenAlex shares a small daily budget per network address; if it starts failing part way, lean
on arXiv, Undermind and web search, and say in the synthesis which searches were cut short.

## Step 3: screen

`pending --out <file>` writes the unscreened items, newest first, with abstracts (`--compact`
gives one line each for a first pass). Read them and write verdicts as a JSON list, then
`assess --file <verdicts.json>`. Do this in batches. An illustration (a made-up project whose
target T2 is an exact solver for graph colouring on 200-vertex instances):

```json
[{"key": "arxiv:2501.00001", "relevance": "green", "reason": "Survey of colouring heuristics; background."},
 {"key": "doi:10.1000/example.2025.42", "relevance": "red", "basis": "fulltext",
  "reason": "Branch-and-price that proves optimality on random graphs up to 150 vertices.",
  "overlap": [{"target": "T2", "verdict": "partial",
               "item_achieved": "certified optima for random graphs with up to 150 vertices",
               "remaining": "150 to 200 vertices, and structured instances"}]}]
```

`references/relevance.md` defines the colours with examples; read it before the first batch.
In short: **red** = does all or part of a target or of an achieved result, or is in direct
competition for it (its authors are visibly racing for the same target); **amber** = same
problem by other means, or a method or tool the project builds on or competes with; **green** =
background a paper on the topic would cite; **irrelevant** = a false hit (kept in the ledger so
the next run does not screen it again, hidden on the page by default). The `reason` is one plain
sentence a reader can check against the item; it is shown on the page.

The script rejects the whole file if any verdict is malformed (unknown key or target, red without
a `done` or `partial` overlap, red or amber without a basis), so nothing half-recorded gets in.

## Step 4: assess red and amber items properly

The colour of a red item is a claim about someone else's work, and the project may change course
on it. So for each red item, and each amber item that touches a target:

- Read beyond the title: the abstract at least, and the full text where it is openly available
  (arXiv, an open-licence journal copy). The `license-check` hook decides what may be read: a
  subscription paper's full text is not read, and the verdict stays `"basis": "abstract"`. Use
  `"page"` for a post, repository or records page you read, `"citation"` when the verdict rests
  on how the project's own manuscript describes the item, and `"secondary"` when it rests on
  another work's description of it (a survey, a later paper). For an arXiv paper, the abstract page or
  the HTML version reads better than the PDF through WebFetch; a saved PDF can be read with the
  Read tool page by page.
- Fill one `overlap` entry per target or achieved result it touches: `done` (it achieves it),
  `partial` (part of it: a smaller case, a weaker bound, a special class), `competing` (not yet
  achieved, but its authors are pushing towards the same target, e.g. setting records one step
  short of it), or `related` (bears on it without achieving it). An item moves from amber to red
  as soon as it is clear that it competes directly with what the project is trying to do. `item_achieved` states what the item actually did, with its numbers;
  `remaining` states what is still open for the project. These two fields are the overlap
  analysis the user asked for, so make them concrete.
- **Every full text goes through `fulltext`, before you open it.** Do not curl or read a PDF
  yourself first: the licence check has to come before any reading, and a subscription copy
  read "just to look" has already been sent to the model. Keep your working files (pending lists,
  verdict batches) in `litreview/work/`; they are not part of the review.
- **Show the passage.** The reader wants the exact words behind an overlap, not only your
  summary. Hold the open full text with `fulltext --key K` (the arXiv PDF by default, or `--url`
  to another open copy or a web page; it goes through the same licence check as the Referencer,
  which refuses subscription copies), find candidate passages with `find --key K term ...`, and
  put one or two verbatim sentences in the overlap entry: `"passages": [{"quote": "..."}]`.
  `assess` checks each one word for word against the held text (or the abstract) with the
  Referencer's matcher and records where it sits (`p. 7`), and the page links straight to that
  page of the PDF. A paraphrase or a misremembered quote is refused. Every red item needs at
  least one passage, unless its verdict rests only on the manuscript's own description of it.
- **Before writing that a target is still the project's, search for that exact claim.** "Nothing
  found" is a claim about the search, and a reassurance that turns out wrong is the most costly
  mistake this skill can make: the author keeps a novelty claim that a referee will strike. For
  each target or result you are about to call open, run two or three targeted web searches on its
  precise statement (the specific numbers, the characterisation, the threshold), including the
  names of the groups closest to it, and look at their recent working papers and conference
  abstracts. Only then write "remains the project's", and say what was searched.
- Watch both failure directions: a similar title is not overlap (check what was actually proved
  or built), and a blog post or a records table can scoop a project as surely as a paper.

## Step 5: dates, links, synthesis, page

1. `dates`: items with an arXiv id get their v1 date, so a paper sorts by when it first appeared,
   not by its journal date (and year-only placeholders such as 2026-01-01 never beat a real date).
   Then `status`: it lists undated kept items and possible duplicates. Correct a date with
   `fix --key K --date YYYY-MM-DD` (or `YYYY-MM` when the source gives only the month; never
   invent a day), drop a guessed one with `fix --clear-date`, and repair a title or abstract a
   source mangled with `fix --title` / `fix --abstract` (the abstract verbatim from the source).
   Possible duplicates are
   usually an arXiv preprint beside its journal version. Fold each true pair with `merge --keep
   <journal key> --drop <arXiv key>`; the merged item keeps both dates and the stronger verdict.
2. `links`: checks every kept link; replace any that fails.
3. Write `synthesis.md`, at most about 500 words, for the user: first the overlap position (what
   is already done, by whom, and what that leaves open, citing items as Markdown links), then what
   the amber items offer the project, then gaps in the search. Give the numbers the sources give
   (sizes reached, compute spent, growth rates) and what they imply for the project's targets, as
   an estimate labelled as yours; "it will cost several times more" helps less than "about 2,000
   CPU-years if the growth over the last two sizes continues". Check each claim you make about a key item
   against its text (what method it used, which bound it states): a wrong description of the
   closest paper misleads more than a missing one. If an item changes one of the project's own
   stated targets (a bound the project still quotes has moved), say so first. Only the points that matter; no
   list of every green item. Plain words, defined at first use; no reassurance about your checks.
4. `build`: writes `index.html`. It warns about unscreened items and a missing synthesis; deal
   with both.

## Step 6: report

Tell the user: the full path to `index.html` (open it with `open <path>` on macOS if they are
at the machine), the counts by colour, each red item in two or three lines (who, when, what it
does to which target, what is left), what changes for the project, and anything the search could
not reach. Then list, with a link each, every red or amber item you could not read in full
(subscription copies, no open copy found), so the user can check those themselves; the page's
Summary tab carries the same list. The page is the deliverable; the reply is the headline and
the to-check list.

## The page

Generated, never hand-edited. It has four tabs: **Literature** (the list, sorted by date, newest
first by default, or by overlap risk then date; filterable by colour, type, target, "new since" a
past run, and free text; red items open with their overlap table and verified passages showing), **Overlap with the project** (for each target and
achieved result, the red and amber items that bear on it, `done` first), **Summary** (the
synthesis, the red and amber items not read in full with links, and the brief) and **Search log** (every search, with result counts). Each item shows
its date, type, venue, a link, the reason for its colour, and whether the verdict rests on the
abstract only.

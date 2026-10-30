---
name: referencer
description: Verify the citations in a manuscript against the full text of every cited work, and show the exact supporting passage for each one. Downloads full texts, records for each citation the verbatim passage that backs the claim, mechanically checks every quote against the downloaded text, and builds a "verification mode" HTML view of the paper in which clicking a citation opens the claim beside the cited passage. A toggle in the draft switches between this view and the normal compiled paper. Use this whenever the user wants citations checked, verified, audited or fact-checked, asks whether a paper really says what the draft claims, wants to find unsupported or mis-attributed citations, prepares a manuscript for submission or review, or mentions the Referencer, verification mode or citation evidence, for pandoc Markdown (`[@key]`) or LaTeX (`\cite{key}`) drafts with a .bib file.
---

# Referencer

A citation is a claim that the cited work says something. "I checked, this paper supports
the claim" is not evidence. The passage is. This skill makes every citation in a draft
point to the exact words in the cited work that support it, so that a reader (the author,
a coauthor, a referee) can see the claim and the source side by side and judge for
themselves in seconds.

Two properties make the evidence trustworthy, and the workflow exists to protect them:

1. **Every quote is checked mechanically against the obtained text.** The script refuses
   a quote that does not occur verbatim in the text, ignoring case, hyphenation, ligatures
   and whitespace but not a single word. A paraphrase, a quote misremembered from training
   data, a formula retyped in your own notation, or two fragments glued together will fail.
   The location (PDF page or section) is computed by the script, never taken from you.
2. **Nothing is verified from a text that was not read.** A citation whose source could not
   be obtained stays "no full text". One checked only against an abstract is shown as
   "supported (abstract only)", a separate status, never as plain "supported".

## The toggle

The draft carries one switch, set with `referencer.py mode DRAFT final|verification`
(do not edit it by hand: the command is exact, a hand edit that misses leaves the wrong mode):

- Markdown: `referencer: final` or `referencer: verification` in the YAML header.
- LaTeX: `\usepackage{referencer}` plus `\referencermode{final}` or `{verification}` in the
  preamble. `referencer.sty` compiles as a no-op; in verification mode pdflatex warns.

`final` means the paper compiles exactly as before, through the author's usual pipeline
(Makefile, pandoc, latexmk), with the references taken from the .bib file as normal. The
skill never runs that pipeline. `verification` means `build` writes
`evidence/html/manuscript.html`: the paper with every citation coloured by status, each
opening its evidence page in a new tab, with the claim (the citing sentence plus surrounding
context) on the left and the cited passage(s) on the right, linked to the page in the PDF.

## Files

Everything lives in `evidence/` next to the draft:

| Path | What | In git? |
|---|---|---|
| `ledger/<key>.json` | the assessments: one file per cited work | yes, this is the record |
| `citations.json` | every citation instance with its ID and context | yes |
| `sources.json`, `missing.md` | where each text came from and which version; what is missing | yes |
| `fulltext/` | PDFs and extracted text | **no** (copyrighted) |
| `html/` | the verification view | no (rebuilt in seconds) |

`init` writes the `.gitignore` that enforces this. Do not commit full texts unless the user
explicitly asks. Never delete files in `fulltext/` that you did not create in this session.
Other agents and the user put files there.

### The download log: why the texts can be trusted

Every file that enters `fulltext/` (the original PDF or XML, the extracted `.txt`, its
metadata) has its MD5 and SHA-256 appended to `evidence/hashes.log` (tracked in git), with
the time, the source and the URL. Each line also carries the SHA-256 of the line before it.
On macOS the script sets the file's user append-only flag, so the file can be appended to,
but not edited, truncated or deleted. `check` and `record` recompute every hash. A text
that differs from its logged download is never quoted from. Every citation of that work
turns into an error, and so does any assessment recorded against a text that was later
replaced (`record` pins the SHA-256 of the text it was judged against).

This exists so that nobody (including you, under pressure to make a claim look supported)
can change what a paper says. So: **never edit, move or delete anything in `fulltext/` or
`hashes.log`, and never run `chflags` on them.** If a text is wrong (a garbled extraction,
the wrong paper), replace it with `fetch --refresh` or `add`. Both log the new file, and
the assessments made against the old text then show as needing re-checking, which is
correct. The flag can be lifted by the file's owner, and an edit to the last line has no
later line to contradict it. That is why the log is tracked in git and why the user can
make it unremovable (below). Mention this when reporting if `check` warns that the flag is
missing.

For a hard guarantee the user can run, once, the system append-only flag, which only root
can set and which cannot be lifted while the system is running normally:
`sudo chflags sappnd <paper>/evidence/hashes.log`. Give them the command; never run sudo.
Deleting an `evidence/` folder later needs `chflags nouappnd evidence/hashes.log` first
(or single-user mode for `sappnd`).

## Workflow

Run everything as `python3 <skill-dir>/scripts/referencer.py <command> <draft> ...`. The
script finds the bibliography in the draft's metadata, in `\bibliography{}`, or in a pandoc
defaults file named in the folder's Makefile (`--defaults FILE` gives one explicitly).

### 1. Set up and list the citations

```
referencer.py init    paper.md   # adds the toggle (final) and evidence/
referencer.py extract paper.md   # -> evidence/citations.json
```

A *citation instance* is one occurrence of a citation in the text: `[@a; @b]` in one
sentence is one instance with two keys, and the same key cited in five places is five
instances, each with its own claim. Each instance's ID is derived from its citing sentence,
its position in that sentence, and its keys. Editing the sentence changes the ID, which
turns the old assessment stale and the citation back to "unchecked". That is deliberate,
because a changed claim needs re-checking.

### 2. Get the texts

```
referencer.py fetch paper.md
```

The script tries, per cited work: arXiv, OpenAlex open-access locations, Unpaywall,
Europe PMC, Semantic Scholar (its open PDF, and the arXiv and PubMed Central copies its
`externalIds` name) and the DOI landing page's declared PDF. It tries the published
version first and the preprint last. A download is kept only if its first pages show the
entry's title, and each text is labelled with its version (published, accepted, preprint).
Unpaywall runs only if `UNPAYWALL_EMAIL` is set. That sends the user's email address to
Unpaywall, so **never set it yourself; ask the user first.** The same goes for any other
request that carries the user's email.

**The licence decides what the agent may read.** The user's rule, enforced by the papers
plugin's `license-check` (installed with the co-scientist-toolkit plugins): a subscription
paper's full text goes to no AI service, whoever's licence gave access. The Referencer runs
`license-check` on every PDF before extracting its text, whether downloaded, dropped in by the
user, or added, and on the work's DOI for supplied text. A refused copy is deleted unread (a
dropped-in file is left alone and not read). Each `fetch` also re-checks texts obtained
earlier, and withdraws any that are refused: their extracted text is deleted, and the agent's
verdicts that rested on it no longer count. Abstracts are always usable. Open copies (arXiv, PubMed
Central, CC-licensed publisher copies, accepted manuscripts outside Elsevier, IOP and SAGE)
pass. Only the user can lift a refusal, in their own words in the chat (`license-check
allow`). Never run that on your own initiative, and never work around a refusal by copying
or retyping a text. The Referencer sends no subscription text to you, and you must not fetch
one by other means either: what cannot be read goes on the worksheet (below). Without
`license-check` installed the gate is off; say so in the report.

Then **search for what the script missed** (`evidence/missing.md` lists it). The indexes
miss many legitimate copies. In order of preference:

1. **Institutional repositories and author pages.** Search for the title (web search or
   the Firecrawl search tools). University repositories (DSpace, HAL, institutional "dial"
   or "eprints" sites), the authors' home pages, and conference versions often hold the
   published PDF or the accepted manuscript.
2. **Free-to-read publisher pages that block scripts** (Oxford Academic's Mol Biol Evol is
   the common case: free to read, but HTTP 403 to `curl`). A scraping service such as
   Firecrawl may be used to fetch the PDF **only when the publisher's page is free to
   read**. Never for paywalled articles, and never through shadow libraries.
3. **Third-party copies** (a published article posted on a course page): add them as
   `--version third-party` so the evidence page flags them. The licence check refuses a
   subscription paper's publisher copy wherever it is hosted.
4. **Abstract only** (PubMed `efetch`, the publisher's abstract page) as a last resort:
   add the abstract as a text file with `--version abstract`. It can carry a claim an
   abstract makes ("NJ was introduced by Saitou and Nei"), and the status says so.

Install each one with `add`, and **let the script download it whenever a direct URL works**:

```
referencer.py add paper.md KEY --download URL --version V        # preferred: the script fetches it
referencer.py add paper.md KEY FILE --url WHERE_FROM --version V  # when only you can get the file
```

`V` is one of `published`, `accepted`, `preprint`, `third-party`, `abstract`, `unknown`.
With `--download` the script hashes the file exactly as the server sent it, before anyone
touches it. That is what makes the text trustworthy. A `FILE` is logged as handed over,
so prefer the original PDF or XML to any text you produced from it. If the only way to read
a work is a tool that returns text (Firecrawl's PDF reader, say), you may `add` that text as a
`.txt`. The evidence page then states that the text was supplied rather than extracted from
a logged original, and you must say so in the report. Never type, summarise or excerpt
a text into a file yourself.

A scanned PDF has no text layer, and `add` refuses it until you pass `--ocr`. That runs
`ocrmypdf`, keeps the scan as `<key>.scan.pdf`, and logs both files. `add` also warns if the
title is not on the first pages, and keeps `missing.md` current. A file the user drops in
as `evidence/fulltext/<key>.pdf` is picked up by `fetch` as version "unknown".

`fetch` also asks Crossref (which carries the Retraction Watch database) and OpenAlex
whether each work has been retracted, withdrawn or given an expression of concern, every time
it runs, since a retraction can come after the paper was first checked. `check` and the
evidence pages flag any such work.

Whatever is still missing goes to the user as a **worksheet**:

```
referencer.py worksheet paper.md            # -> evidence/worksheet.md
referencer.py worksheet paper.md --import   # after the user has ticked boxes
```

For each work it cannot read, most-cited first, `worksheet.md` gives the link, the reason
(no open copy, a subscription licence, only the abstract), and every citing sentence. Each
sentence comes with the cited clause in bold, the specific claim to verify, the citation
key, and boxes to tick (supported / partly / not supported / contradicted) with a note line.
The user opens the paper, finds the passage and ticks a box. `--import` records the ticked
entries as checked by the author, without a passage. The evidence page says so, and these
works leave the list. `worksheet` refuses to overwrite ticks that have not been imported.
`check` prints the same list, and `index.html` shows it with the sentences.

**When the user has their own copy, `assist` does the searching for them.** In their own
terminal (never yours, and not through `!`, whose output enters the conversation), the user runs:

```
referencer.py assist paper.md KEY --pdf <their copy>
```

It extracts the text in memory only, searches it for each citation's claim, and shows the five
best passages with the matching words highlighted. The user types a verdict, picks the
passage to keep (at most 400 characters: a short quote, which the licence rule allows), and adds
a note. Then:
- the passage is matched against their copy;
- the copy's hash goes into `hashes.log` as `<key>.author-copy.pdf`;
- the verdict is recorded as checked by the author, with the quote and its page.

Nothing else of the text is saved. It refuses to run inside Claude Code.

**Your part is the search terms.** Its automatic terms come from the claim's words and
numbers, and they miss what a source says differently: a formula, a table row, a theorem
under another name. Before handing over the worksheet, add the words the source would
probably use, for each item where the claim's own words are unlikely to find it:

```
referencer.py terms paper.md ID "triangle inequality" "facet-defining" "Theorem 2"
```

A citation in a table cell is shown with its whole row as context, since the cell alone
("[3]") claims nothing. Give those terms always. They have institutional access. Assess what is available meanwhile. Books,
manuals and software are often better handled as `not-a-claim` (below) than chased.

### 3. Assess each citation

```
referencer.py todo   paper.md [--key K]           # instances still needing an assessment
referencer.py find   paper.md KEY "term" "term"   # passages in KEY's text, with page labels
referencer.py record paper.md KEY ID --verdict V --quote "..." [--quote "..."] --note "..." [--secondary] [--doubt "why"]
```

Work **one cited work at a time**: read `evidence/fulltext/<key>.txt` (pages separated by
form feeds), then assess every instance that cites it. For more than a handful of works,
give each work (or a few) to its own subagent with this file, the key(s), the `todo --key`
output, and these rules: record only through `record`, never delete files in `fulltext/`,
and never send the user's email anywhere.

`record` checks the entry first: the quotes are located in the text, a note is present
where one is needed, the instance cites that key. It writes nothing if any check fails,
and tells you why. When it fails, go back to the text. Do not trim the quote until it
matches something nearby.

For each instance, ask: **does this work, in its own words, say what this sentence uses
it for?**

- **Verdicts:**
  - `supported`: the passage states the claim, at the strength the draft states it.
  - `partial`: it supports part of the claim, a weaker version, a special case, or
    different conditions. The note says what is missing.
  - `unsupported`: you read the work and nothing in it backs the claim. Passages are
    optional (give the closest one if it helps the author see the gap).
  - `contradicted`: the work says the opposite. Quote it.
  - `not-a-claim`: the citation attributes a tool, data set, method or notation and asserts
    nothing checkable ("solved with MOSEK [@mosek]", "following the notation of [@x]").
    Use it sparingly. "X proved Y [@x]" *is* a claim.
- **Quotes** (`--quote`): copy them from the `.txt` or `find` output, never retype them
  from memory or rewrite their mathematics. Use `[...]` only to drop words *within* one
  passage, never to join distant sentences into a claim the work does not make. A passage
  needs at least a full clause.
- **Abstract only**: when the only text is the abstract, record `supported` only if the
  abstract itself states the claim (it is then shown as "supported by the abstract"), or
  `contradicted` if it says the opposite. Otherwise record nothing: an abstract cannot show
  that a claim is unsupported, so the work stays on the retrieval list. `record` refuses
  `partial` and `unsupported` on an abstract.
- **Doubtful claims** (`--doubt`): if the claim itself looks false, flag it *whatever the
  verdict*: a cited work can support a statement that the draft's own results, another cited
  work, or established knowledge contradict. Say why in one sentence. This is separate from
  the verdict and shows as a warning on the citation and its evidence page.
- **Note** (`--note`): required for every verdict except `supported`. One sentence the
  author can act on ("the paper proves this only for n <= 8; the draft states it for all n").
- **Secondary** (`--secondary`): **check this every time.** If the supporting sentence
  credits the point to someone else ("as shown by Smith [12]", "has recently been revealed
  to be ... [2]"), the cited work is not the source. Record it with `--secondary` and put
  the original in the note (author, year, and the reference as the cited work gives it).
  The author will usually want to cite the original instead or as well. Look at the
  reference markers next to your passage before recording anything as plain `supported`.

What makes a good assessment:

- **Judge the clause the citation is attached to.** When a sentence holds several
  citations, each one is responsible for the part of the sentence it sits on (the `target`
  span in `todo` output marks it), not for the whole sentence. "X is greedy [@a], and it is
  exact for n <= 8 [@a]" is two claims needing two passages.
- **A citation must sit exactly where it is needed.** If the source supports a different
  clause of the sentence than the one the citation is attached to, or the citation sits on the
  authors' own result ("our method improves accuracy [@lefort2015]", where the source describes
  the method being compared against), record it as `unsupported` for this position. Say in the
  note which clause or sentence it does support, so that the fix is to move the citation, not
  to drop it. The same applies to a citation at the end of a long sentence whose claims come
  from several sources.
- **A multi-key citation** `[@a; @b]` gets an assessment under each key. Each key is judged
  on whether it supports the claim (or the part of it the sentence attributes to it).
- **Match the strength.** If the draft says "proved" and the source says "conjectured" or
  "observed in simulations", that is partial. If the draft says "always" and the source
  shows "for n <= 8", that is partial too. Numbers, directions of effect, and the
  population or setting must match.
- **Versions of the same work can differ** (a preprint says 30, the published version 32).
  That is not an error in the draft. The draft should match the version it cites, so check
  against the version of record. If you could only read another version and a detail
  differs, say which version you read, and ask the user for the cited version rather than
  calling the claim wrong.
- **Be exact in notes.** Say precisely what the source says and how the draft differs
  ("the model has Θ(n⁴) quartet variables, not Θ(n³)"), not a looser paraphrase that is
  itself inaccurate. A note the author has to correct costs more than no note.
- **Prefer the result over the abstract.** The abstract is fine for a headline claim, but
  a theorem statement or a results sentence is stronger evidence for a specific one.
- **PDF text extraction garbles mathematics.** Choose prose passages where you can. When the
  supporting statement is a formula, quote the sentence around it that states it in words.
- **When unsure, say partial and explain**, rather than rounding up to supported. The point
  is to surface the citations the author should look at.

### 4. Check and build

```
referencer.py check paper.md                      # every quote against its text; exit 1 on error
referencer.py mode  paper.md verification
referencer.py build paper.md                      # -> evidence/html/manuscript.html, index.html
referencer.py mode  paper.md final                # always switch back afterwards
```

`check` reports counts per status and lists every problem: quotes not found, missing notes,
invalid verdicts, and stale ledger entries left behind by edited sentences. For a stale
entry, the claim was reworded. Re-judge it against the new sentence (the old quote may
still be right), record it under the new ID, and delete the stale entry from the ledger
file.

## Reporting to the user

Lead with what needs their attention, worst first: retracted works, doubtful claims,
contradicted, unsupported, partial and secondary-source citations. Give each one the citing
sentence, the cited work, the passage, and the note. In a group of citations, name the one
key at fault; the others are fine and should read as fine. **Assume the user reads one item
at a time**, the manuscript or the report but never both side by side, so each item must
stand on its own: never "see above" or "as for the previous one". Then point to `evidence/worksheet.md` for the works the agent could not read, with
their number and the most-cited few by name. A work read only as an abstract that did not
settle its claims is on the worksheet too. Say how many texts the licence check refused
or withdrew. Then the abstract-only verdicts. Then give the counts. Say which texts were not the version of
record (preprints, accepted manuscripts, third-party copies), since page numbers and
wording can differ. Never summarise as "all citations verified" while any are unchecked,
abstract-only, or without full text. Say how many of each.

**When a citation does not support its claim, find the one that does.** Look first at the
other works the draft already cites, then at the references the cited work itself gives
for the point (the original behind a secondary citation). Obtain that work's text and
verify it to the same standard. A work the bibliography does not cite yet can be added with
`add ... --title "Its title"`, and its passage checked with
`referencer.py locate paper.md KEY "quote"`. Put the passage in the report as the proposed
replacement, with a suggested rewording if the claim itself needs tightening. Present
these as suggestions. The skill does not edit the manuscript's claims unless asked. Point the user to
`evidence/html/manuscript.html` for the side-by-side view.

## Statuses at a glance

Six colours, one per kind of status. In a group such as [3, 5, 8] each number is coloured
and linked on its own, so one weak citation does not taint the others.

| Colour | Status | Meaning |
|---|---|---|
| green | supported | every cited work supports the claim, with a checked passage |
| green, dashed | supported by the abstract | the abstract alone states the claim |
| amber | partly supported | some support, or support for a weaker claim |
| red | not supported / contradicted | the work was read and does not back / opposes the claim |
| grey | not yet checked / full text not retrieved | not verified yet |
| blue | attribution only | `not-a-claim`: a tool, data set or notation |
| purple | evidence does not check out | an entry fails the mechanical check: do not trust it until fixed |

A ⚠ after a citation marks a doubtful claim or a retracted work. Evidence pages open in a new
tab, and "back to the manuscript" closes that tab.

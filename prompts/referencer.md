# Referencer — original prompt

Given 2026-10-23. Built with `/skill-creator:skill-creator`. Verbatim:

---

Full text for every citation. For every citation, the referencer downloads the full text of the article.
A toggle with two modes, as a macro or some other object in the draft:
Final compilation mode: the reference is taken from the bibliography file and inserted into the manuscript as it is normally done.
Verification mode (working name): clicking a reference opens a new tab that shows
the citing sentence, perhaps with a couple of sentences around it, i.e. what is actually being claimed; and
next to it or underneath it, the exact passage in the cited paper that supports that claim.
The point: it is not enough for the agent to say “this paper supports this claim, I have verified that”. There needs to be a way to show the exact supporting passage.

---

## Design decisions (answers given 2026-10-23, during skill creation)

- **Formats:** pandoc Markdown (`[@key]`) and LaTeX (`\cite{key}`), both with a .bib file.
- **Full-text sources:** open access (arXiv, OpenAlex, Unpaywall, Europe PMC, Semantic
  Scholar, repository landing pages) plus a manual drop: the user saves paywalled PDFs as
  `evidence/fulltext/<key>.pdf`. No circumvention of publisher access controls.
- **Storage:** inside the paper's repository, with full texts gitignored
  (`evidence/fulltext/`), and the evidence ledger (`evidence/ledger/<key>.json`) tracked.
- **Verification output:** an HTML rendering of the manuscript; each citation opens its
  own evidence page in a new tab (claim on the left, verbatim passage with page link on
  the right).
- **First real application:** retroactively, to papers already produced in agentic
  collaboration, starting with
  `~/Downloads/Phylogenetics/BalancedMinEvolution/Manuscript/BME_wSpace_Manuscript.md`.

## Source policy (answers given 2026-10-23, after the first eval round)

- **Free-to-read publisher PDFs blocked to scripts** (e.g. OUP Mol Biol Evol): may be
  fetched through a scraping service such as Firecrawl, **only** when the publisher's page is
  free to read. Never for paywalled articles.
- **Copies on third-party course pages**: usable, but flagged on the evidence page as a
  third-party copy.
- **Abstract only**: may count as evidence for claims an abstract can carry, shown with an
  "abstract only" badge, never confused with a full-text check.
- **The user's email** (e.g. Unpaywall's `email=`): usually fine, but the user must be
  consulted first; the agent never sets it on its own.

## Additional requirement (given 2026-10-23, after the first review), verbatim

> whenever a paper is downloaded, the file gets an md5 sum and that this sum gets appended to a file that is not editable, only appendable (if such a thing is possible), so that an agent trying too hard to make the claim sound supported cannot alter the text.

Implemented as `evidence/hashes.log`: MD5 and SHA-256 of every original file, extracted text
and metadata file; each line chained to the previous line's SHA-256; macOS user append-only
flag (`uappnd`) set by the script; the user may set the root-only `sappnd` once
(`sudo chflags sappnd evidence/hashes.log`). `check`/`record` recompute every hash, never
quote from a text that fails, and flag assessments recorded against a since-replaced text.

## Review feedback on the first eval round (2026-10-23), points kept in the skill

- Proposing and verifying the correct reference when a citation fails: "more than I had
  bargained for but is a nice feature worth keeping".
- A difference between versions of the same paper (preprint 30 vs published 32): "we just
  need to focus on getting the right reference", not flag the claim as wrong.
- Notes must be technically exact (e.g. Θ(n⁴) is "more than Θ(n³)" only loosely).
- Not settling a claim when the paper cannot be downloaded, and asking the user for it
  instead, is "exactly the right behaviour".

## Review feedback, iteration 2 (2026-10-26)

His comments in `referencer-workspace/iteration-2/feedback.json` ("This is excellent"), and what changed:

- **Grouped citations:** when several citations follow each other and only one is partly
  supported, only that one should be highlighted; the rest should show as fully supported.
  Assume he reads one item at a time, the manuscript or the comments, never both. **Change:**
  - In verification mode each citation of a group is its own link with its own colour,
    rendered as "[17, 18, 19]". Citeproc renders each one alone to get its label, so
    numbering is unchanged.
  - Each link opens its own block on the evidence page, and its tooltip gives that key's
    status and note.
  - The evidence page heads a group with each key's own status.
  - The report must make each item stand on its own.
- **Blocked texts:** works with no full text, or not checked because of access, should come
  to him as a list of clickable URLs, ordered by importance, so he can retrieve them quickly.
  **Change:** `check` prints "full texts to retrieve, most-cited first", with a DOI, URL or
  Google Scholar link for each. `index.html` has the same list under "Full texts to retrieve",
  linked from the banner. Evidence pages for these works carry a "Retrieve it" link.
- **Abstract-only:** mark it verified only if the abstract is actually enough to verify;
  otherwise it belongs with the failures to retrieve. **Change:** on an abstract-only text,
  `record` accepts only `supported` (shown as "supported by the abstract"), `contradicted` or
  `not-a-claim`. With nothing recorded, the work goes on the retrieval list.
- **Colours:** clear, capped at 6 categories. **Change:** the nine statuses now share six
  colours:
  - green: supported;
  - amber: partly supported;
  - red: not supported or contradicted;
  - grey: not verified yet;
  - blue: attribution only;
  - purple: the evidence check failed (previously too close to red).
- **Navigation:** a citation opens a new tab (good), but "back" did not close it. **Change:**
  "back to the manuscript" closes the tab, and follows the link when the browser will not let
  the page close itself. Not yet tried by hand in a real browser.
- **False claims:** something that appears false should be flagged as such, whether or not
  the citation supports it. **Change:** `record --doubt "why"`. It is independent of the
  verdict, shows as ⚠ on the citation, as a warning box on the evidence page, and in `check`.
- **Retractions:** any citation of a retracted paper should be flagged ("a quick check and
  worth doing in general"). **Change:** `fetch` asks Crossref `updated-by` (which includes
  Retraction Watch) and OpenAlex `is_retracted` for every work with a DOI, on every run. A
  retracted work is flagged in `check`, with ⚠ on the citation and a warning box on the
  evidence page. Tested: the Wakefield 1998 Lancet paper is flagged with its notice, and
  Pauplin 2000 is clear.
- **Without the skill:** the suggestions were much harder to follow.
- **Also from this round:** a citation must sit exactly where it is needed (his comment on the
  Scientific-Humanizer). This was added to the assessment rules.

## Requests relayed by his docket agent (2026-10-26)

From the PersonalDevelopment docket session, on his behalf. He is happy with the design: no
full text means no verdict, and "abstract verified" only when the statement is in the
abstract, as weaker evidence. The aim is to make the list he checks by hand shorter and
faster to work through.

1. **Open-copy fallback** before a paper is listed as inaccessible: an arXiv preprint, a
   PubMed Central copy or an accepted manuscript, found through OpenAlex `oa_url` and its
   locations, and Semantic Scholar `externalIds`. Show which source the text came from.
   **Done:**
   - OpenAlex `open_access.oa_url` (direct PDF links) was added;
   - Semantic Scholar `externalIds` → arXiv PDF and Europe PMC XML were added;
   - the evidence page now says "Text read: <version>, from <source>".
2. **A worksheet, not bare URLs:** for each inaccessible paper, the citing sentence, the
   specific claim, the key, the link, and a place to mark supported / not supported / partly.
   **Done:** `referencer.py worksheet` writes `evidence/worksheet.md`, and `--import` records
   the ticked boxes as `checked_by: author`. The claim is the clause holding the citation,
   bounded by `;` or `:`. `worksheet` refuses to overwrite ticks that have not been imported.
3. **Test with the papers plugin's licence-check hook** (installed today, project scope).
   - The hook's rule: no subscription full text to any AI service.
   - What the simulation showed: feeding hook.sh the events the Referencer's tool calls
     produce, the hook refuses Reading a subscription PDF, but lets through the extracted
     `.txt` and `referencer.py find`, which run outside its sight. The iteration-2 BME
     evidence folder held 7 such texts, including Atteson 1999 (Springer), Aringhieri 2011
     (an Elsevier accepted manuscript) and Fiorini 2015 (ACM).
   - **Done:** the Referencer itself now runs `license-check` on every PDF before
     extraction, and on the DOI for supplied text. Each `fetch` re-checks held texts and
     withdraws refused ones: the `.txt` is deleted, and the agent's verdicts on them are void,
     so they go to the worksheet. Abstracts are exempt.
   - Tested on a copy of the BME run: 7 texts withdrawn; 18 remain readable, plus Pauplin's
     abstract.
   - Not yet tested: a live session with the hook loaded (it needs a restart).
   - **This reverses an earlier decision** ("open access plus manual drop"): a paywalled PDF
     he drops in is no longer read by the agent unless he lifts the refusal in his own words.

## `assist`: searching the author's own copy without the agent seeing it (2026-10-26)

His question: "would something like 'build a regex search for the claim text that I can run
on the full text without letting you see it' be a possible thing to request?" The answer was
yes, within the licence rule, because the text never reaches the AI. Three conditions apply:
- it runs in his own terminal, not through `!`;
- only his verdict and at most a short quote come back;
- mining rights are his call (UK CDPA s29A covers non-commercial research by people with
  lawful access).

He asked for it to be built.

**What it does:** `referencer.py assist paper.md KEY --pdf <copy>`, which is interactive.
- It refuses to run if `CLAUDECODE` or `AI_AGENT` is set, or if stdin is not a terminal.
- It runs pdftotext in memory only, splits each page into two-sentence windows, and leaves
  out the reference list.
- It ranks the windows by the claim's terms, weighting numbers by 3, word pairs by 2 and
  single words by 1, each times an inverse document frequency. It shows the top 5, with the
  matches highlighted.
- He types a verdict (s/p/n/c, or `/words` to search again), picks a passage of at most 400
  characters (matched against the copy) and adds a note.
- The ledger records `checked_by: author` with the quote, page and `author_copy_sha256`. The
  hash goes into hashes.log as `<key>.author-copy.pdf` when the first verdict is recorded.

**What the agent adds:** `referencer.py terms paper.md ID TERM...` stores the agent's search
terms in `evidence/search_terms.json`, for formulas, table rows and theorem names.

**Fixed along the way:**
- Citations in table cells now carry their row and header as context, so the instance ID is
  unchanged. Found because BME Table 3's "[@forcey2016]" cells had no claim at all.
- `cited_claim` ignores `;` and `:` inside citation groups and maths.

Tested on an open arXiv copy (Forcey 2016) with a scripted driver.

## Fixes after the Kemeny MSS runs (2026-11-03)

His words: "Let's fix the referencer for figure captions and license refusals".
- Citations inside raw-LaTeX figure captions in a Markdown draft were silently skipped (pandoc leaves
  raw LaTeX unparsed). Each `\caption{...}` is now parsed as Markdown (`\cite{a,b}` read as `[@a; @b]`),
  inserted as a "Caption:" paragraph after its block, and `check` warns that citeproc will not resolve
  a citation there in the final PDF.
- A licence refusal during `add` was not recorded, so the worksheet said "no open copy found". It is now
  stored in sources.json (status refused, unless a text is already held) and shown as the reason.
- Dash at a line end (his "go for both", 2026-11-03): only a true hyphen after a letter is undone
  as a hyphenation; en/em dashes and minus signs stay, and spacing around a dash is ignored on both
  sides. `test_normalise.py` holds 11 known-answer cases (3 negative). Citation IDs hash the sentence
  with the old normalisation (`id_text`, frozen) so recorded assessments keep their IDs: the
  first attempt re-keyed 7 + 3 Kemeny assessments to "unchecked", caught by an old-vs-new check run.
- `fetch --key` no longer rewrites missing.md with only the fetched keys.
- `keyify DRAFT BIB` ("Let's fix the author-year citations please"): the documented route for
  author-year drafts with a typed reference list; writes DRAFT_keyed.md citing the .bib, reports
  unconvertible and loose citations. Kemeny paper 2: 58 citations of 25/25 works, identical to the
  agent's hand-made copy; paper 1: 33/33 works, and its three loose citations ("McKay's catalogue
  (2026)") are exactly where it differs from the agent's hand-keyed copy.
- `add --download` ("let's fix the --download option so it fails gracefully"): a 404, a bad host or a
  timeout now exits 1 with the reason ("HTTP 404 Not Found") instead of a traceback, records the
  attempt in sources.json (shown in missing.md and the worksheet), installs nothing, and never
  downgrades a text already held.

---
name: scientific-humanizer
description: Rewrite scientific prose (papers, manuscripts, abstracts, grant applications, theses, referee responses, technical reports) so it reads as if a careful scientist wrote it. Strips the AI voice (inflated significance, filler, negative parallelism, em-dash habits, AI vocabulary) and the four science-specific faults: foreshadowing, unnecessary hedging, overstatement, and jargon that a plain word can replace. Every number, symbol, equation, citation and the strength of every claim is preserved. Works on a pasted passage or edits a pandoc Markdown or LaTeX manuscript file in place, and flags (never silently changes) claims whose strength looks wrong. Use this whenever the user asks to humanize, de-AI, polish, tighten, plain-language, or edit for style any scientific or academic text, mentions Aaronson's "Style in Scientific Writing", or says a paper, abstract or section "reads like an LLM", is too hedged, overclaims, or is full of jargon; prefer it over the general humanizer for anything written for a scientific reader.
---

# Scientific-Humanizer

Rewrite scientific text so it reads as if a careful scientist wrote it: transparent, brief,
clear and precise. Aaronson's *Style in Scientific Writing* states the target: *"in science
writing the best style is transparent; the reader sees through the words to the underlying
phenomena and concepts."* AI prose fails that test the same way pompous human prose does: it
is written to impress. This skill removes both.

It is the scientific sibling of the general `humanizer` skill and shares its catalogue of AI
tells (`references/ai-tells.md`, one shared file). What it adds is the science-specific layer in
`references/scientific-style.md`.

## The contract

These come before everything else.

1. **Content is untouchable.** Every number, unit, symbol, equation, citation key,
   cross-reference, label, defined term, and logical relationship survives exactly. So does
   **the strength of every claim**: "proves" stays "proves" and "suggests" stays "suggests",
   unless it is a reflexive hedge or empty booster as defined below. When a claim's strength
   looks wrong, flag it for the author; do not change it. You change how things are said,
   never what is claimed.
2. **Add nothing.** No new examples, results, citations, definitions or transitions that assert
   something. If a term needs defining or a section needs a transition, flag it: only the author
   knows what it should say.
3. **Keep the register: formal, but plain.** A scientific paper stays a scientific paper. Formal
   is not pompous, and technical is not jargon-laden. Terms of art stay; dignifying words go.
4. **Never edit inside mathematics.** Maths environments, `$...$`, code, citation commands and
   reference commands are copied verbatim. Prose around them may change.

`scripts/check_preservation.py` checks contract items 1 and 4 mechanically. Run it on every
rewrite.

## Method

1. **Read the whole text first**: its field, its claims, the evidence it gives for each, and
   which terms are defined where. A hedge or a term can only be judged against what the text
   establishes.
2. **Pass 1: AI tells.** Work through the catalogue in `references/ai-tells.md`: inflated
   significance, "-ing" filler tails, negative parallelism ("not X but Y", "Y rather than X"),
   forced triplets, copula avoidance, vague attribution, disclaimer templates, em-dash habits,
   uniform short sentences. Fix the *move*, not the word: removing "not merely" while keeping
   the two-part contrast only redecorates it. Collapse it to one plain statement of what is
   true.
3. **Pass 2: the four science-specific moves**, detailed in `references/scientific-style.md`:
   - **Foreshadowing**: cut previews of later results and promises of significance ("as we
     will see, this turns out to be crucial"). A bare pointer ("we return to this in Section 5")
     may stay. Abstracts, contribution summaries, roadmaps and section-closing transitions are
     not foreshadowing.
   - **Unnecessary hedging**: one qualifier per real uncertainty. Unstack ("may potentially
     suggest a possible" → "suggests"), but count the uncertainties first: in "the results
     suggest that the constraints could be facet-defining" the evidence is uncertain *and* the
     property is unproven, so "suggest … may be facet-defining" keeps both, whereas "suggest …
     are facet-defining" strengthens the claim. The hedge attached to the claim itself is the
     last to go; turn the impersonal hedge into a named view ("It is
     suggested that" → "We propose"); cut "It is important to note that". Keep every hedge that
     carries information: ranges, assumptions, conjectures, stated limitations.
   - **Overstatement**: cut boosters that assert importance instead of showing it ("clearly",
     "novel", "remarkable", "of great importance", non-statistical "significant"). For a
     mismatch between a claim and its evidence ("proves" on a simulation, causal verbs on a
     correlation, "always" beyond the tested range), **flag it**. Pure hype that no evidence
     could support ("a paradigm shift", "revolutionises the field") is different: recommend
     cutting it, plainly, with no conditions for putting it back. The author still decides, so
     in file mode it goes in "Proposed changes", but the recommendation itself is decisive.
   - **Jargon a plain word can replace**: ask whether each word *denotes* or *dignifies*. Keep
     terms of art; replace dress-up words ("utilise" → "use", "methodology" → "method",
     "elucidate" → "explain"). Repeat a term instead of varying it, since a new word suggests a
     new object. Flag undefined terms and private working labels, including the author's own
     coined names for results or objects ("a pinning result"): a coined name needs a few words
     saying what it means at first use ("a uniqueness result, which we call pinning"). Check
     the terms in tables and captions too, not only in running prose.
4. **Pass 3: plain, strong writing** (`references/plain-strong-writing.md`): short words,
   un-nominalised verbs ("perform an analysis of" → "analyse"), active voice where the agent is
   named, no padding. Apply the user's manuscript conventions in `scientific-style.md` §5: no
   imperative sentence openers except "Let…"/"Suppose…", inanimate subjects with active verbs
   only when idiomatic, no reassurance about the authors' own checks. **Check the inanimate
   subjects mechanically, sentence by sentence:** list every sentence whose subject is the
   paper, a section, a table, a figure, an experiment, a result or the data, and test its verb.
   "This paper asks / argues / believes / considers / wants", "the table argues", "the
   experiment tries" are forced; rewrite them with "we". "The table lists", "Figure 2 shows",
   "the bound prunes the node" are idiomatic; leave them. This is easy to miss by reading, so
   do the listing.
5. **Reference and grouping.** Check each back-reference has something to point at: "in this
   sense", "this approach", "such constraints" need an antecedent in the preceding sentences,
   or they are padding ("In this sense our approach is itself…" → "Our approach is also…").
   Check lists that follow a noun: "applied through heuristics, NJ and the tree searches of
   FastME" reads as three items; "heuristics, namely NJ and…" or a colon makes it two
   examples of one thing. And in an introduction or theory section, flag experimental numbers
   against the no-foreshadowing convention: they may be deliberate motivation, so it is the
   author's call, but name the rule.
6. **Do not create new tells while fixing old ones.** Do not swap em-dashes for a run of
   identical 12-word sentences, or "not just X but Y" for "both X and more". Vary sentence
   length as the content allows.
7. **Check.** Run the preservation script (below), then re-read against the source: same
   claims at the same strength, nothing added, register intact, reads naturally aloud. Revert
   any edit that made a sentence worse.

## Two ways of working

### A pasted passage

Save the original and your rewrite to two files in the scratchpad and run
`python3 <skill-dir>/scripts/check_preservation.py original.md rewrite.md` (or `.tex`). Then
return, in this order:

```
<rewritten text, alone, ready to copy>

---
**Changed:** <one to three lines grouping the kinds of edits>. Claims, numbers, symbols and
citations preserved; nothing added.

**For the author:** <only if there is something; one line each>
- <location or quoted phrase>: <claim-strength mismatch / undefined term / possible real claim cut / ...>
```

Write the note plainly too: no em-dashes and no AI vocabulary in it.

**Keep the "For the author" list proportionate.** Order it by importance (claim-strength
mismatches first, then undefined terms, then the rest) and keep it to what the author must
act on: roughly one flag per two or three sentences of input, so a five-sentence paragraph
gets two or three. Collapse minor points into one closing line ("Also check: …"). The
author's attention is the scarce resource. A long list of small flags buries the one that
matters.

**Say what each flag rests on when it is not obvious**: the author's own convention ("your
rule: no experimental numbers in the introduction"), the style references ("Aaronson: …"),
or your own recommendation ("my suggestion"). The author treats a breach of their own rule
differently from a matter of taste, so they need to know which one it is.

**When you suggest a rewording for an over-strong claim, aim for neutral, not for timid.**
The fix for "these results prove X is always better" is the claim the evidence supports at
full strength ("on all 48 datasets, X was more accurate on average"), not a weaker one hedged
into saying nothing. And do not presume what the author has or has not shown elsewhere: "if
this is proved later in the paper, cite the result here; if not, narrow it to the simulated
cases" beats asserting that it is only a simulation.

### A manuscript file (`.md` or `.tex`)

1. **Look before you overwrite.** Check `git status` for the file. If it has uncommitted
   changes, or the folder is not a git repository, copy it to `<name>.before-humanizer.<ext>`
   next to it first and say so.
2. Edit the file in place, section by section, **but apply only the safe, obvious edits**:
   removing AI tells, stacked hedges and boosters, plain-word swaps, fixing forced inanimate
   subjects and imperative openers, deleting a redundant word. Anything a careful author might
   disagree with (cutting a sentence that could be a claim, restructuring a paragraph,
   rewording a claim) goes in a **"Proposed changes"** list with the old and the suggested
   wording, not into the file. Leave maths, citations, references, labels, comments, YAML front
   matter, the LaTeX preamble and tables' cell contents untouched.
3. Run the preservation check against the original (`git show HEAD:<file> > <scratch>/orig.md`
   or the backup copy). It must report "all preserved". If not, fix the edit, do not argue
   with the checker.
4. Report: a change list grouped by section, giving for each substantive change the old and
   the new wording (skip trivial word swaps after the first example of each kind). Then the
   "For the author" list with section and quoted phrase. Then the checker's summary line.

If the manuscript builds with a Makefile or pandoc command, do not run it unless asked.

## Worked examples

**1. Stacked hedging, boosters, jargon** (a results paragraph)

Before:
> It is important to note that our novel methodology may potentially offer significant
> improvements, clearly underscoring its pivotal role in elucidating the intricate interplay
> between topology and edge weights. Notably, the approach leverages a robust framework that
> could possibly facilitate the analysis of numerous datasets.

After:
> Our method may give substantial improvements, and it helps explain how topology and edge
> weights interact. It could make many datasets easier to analyse.

> **Changed:** cut the disclaimer, the boosters ("novel", "clearly", "pivotal", "notably") and
> the stacked hedges, keeping one hedge per claim ("may", "could"); replaced "methodology",
> "elucidating", "leverages a robust framework", "facilitate" and "numerous" with plain words.
> Nothing added. **For the author:** "substantial improvements" over what, and how large? The
> source does not say, so I did not invent a comparison. If "significant" was meant
> statistically, restore it with the test.

**2. Foreshadowing and reassurance in a theory section**

Before:
> As we will see in the experiments, this bound turns out to be surprisingly tight. We prove
> Theorem 3 in Appendix B; we also verified it numerically for all trees with $n \le 9$.

After:
> We prove Theorem 3 in Appendix B.

> **Changed:** cut the preview of an experimental result from the theory section, and the
> numerical check beside a proof. **For the author:** the tightness of the bound belongs in the
> experiments section; check it is stated there. If the $n \le 9$ check was meant as evidence
> (for instance, before the proof existed), restore it there and say why it is needed.

Note: in example 2 the checker reports `$n \le 9$` and `9` as missing. That is expected: the
sentence was cut on purpose. Every such report must be explained in the note.

**3. Claim strength flagged, not changed**

Before:
> Our simulations prove that NJ always recovers the true tree when distances are accurate.

After:
> Our simulations prove that NJ always recovers the true tree when distances are accurate.

> **Changed:** nothing; the sentence is already plain. **For the author:** "simulations prove"
> and "always": simulations show agreement in the cases run, not a proof for every input. Either
> cite the theorem (e.g. Atteson's radius result) or narrow the claim to the simulated cases.

## Do not over-correct

- **Fidelity outranks style.** If a fix would change a claim, flag it instead.
- **Terms of art are not jargon.** "Branch-and-cut", "p-value", "polytope", "posterior",
  "eigenvalue" stay. So do technical uses of words that are AI tells elsewhere: statistical
  "significant", "robust" statistics, "associated with" as a statistical claim, fitness
  "landscape", "empirical".
- **Not every hedge is a fault.** Conditions, ranges, conjectures and limitations are content.
- **Formal is not a tell.** Perfect grammar, long sentences and an academic register are
  normal in human scientific writing (`ai-tells.md` §7). The target is the cluster of tells,
  not formality.
- **Do not churn.** Leave plain sentences alone; minimal faithful edits beat a wall-to-wall
  paraphrase. But fog (nominalisations, padding, dress-up words) is not "already plain".
- **Do not inject personality**: no rhetorical questions, jokes or first-person warmth the
  source did not have. "We" is standard in scientific writing and fine where the source has an
  agent.
- **Thin em-dashes, do not abolish them**; one in a page is human.

## References

- `references/scientific-style.md`: the four science-specific moves in full, Graham's glossary
  of hedges, the jargon test and swap table, the user's manuscript conventions, and the list
  of what to flag rather than fix. Read it on every task.
- `references/ai-tells.md` (shared with `humanizer`): the AI-tell catalogue by model era,
  including the mid-2026 patterns (uniform short sentences, caution templates) and what is
  *not* a reliable tell. Consult it for heavy passages or to check a phrase.
- `references/plain-strong-writing.md` (shared with `humanizer`): Aaronson's plain-word swaps,
  redundancy and padding lists, un-nominalising, active voice, and when "Notice…" and a
  sentence-initial "And" are fine.

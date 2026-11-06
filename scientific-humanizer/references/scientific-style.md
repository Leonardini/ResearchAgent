# Scientific style: the four science-specific moves

The science-specific layer of the `scientific-humanizer` skill. The sources are Steve Aaronson,
*Style in Scientific Writing* (Current Contents, 10 January 1977; *Essays of an Information
Scientist* 3:4-13), which quotes C.D. Graham's "Glossary for research reports", Orwell, Zinsser,
Platt and Oppenheimer, and the user's own manuscript conventions. Page numbers refer to the
essay as printed in *Essays*.

Aaronson's thesis governs everything below: *"in science writing the best style is transparent;
the reader sees through the words to the underlying phenomena and concepts. The best scientific
writing is characterized by brevity, clarity, and precision"* (p. 4). And its enemy: *"If a man
intends to impress someone, his work will not be clear, because he does not intend clarity: he
intends to impress"* (Rubinstein, quoted p. 12). Foreshadowing, reflexive hedging, overstatement
and dignifying jargon are four ways of writing to impress.

**Contents**
1. Foreshadowing
2. Unnecessary hedging
3. Overstatement
4. Jargon that a plain word can replace
5. The user's manuscript conventions
6. What to flag rather than fix

---

## 1. Foreshadowing

**What it is.** A passage that previews a result belonging to a later part of the paper, or
promises significance before it has been earned: "as we will see, this bound turns out to be
tight", "this seemingly minor detail will prove crucial", "surprisingly, the experiments show"
(in a theory section), "a striking pattern emerges later". It makes the reader carry a claim
without its evidence, and it inflates what follows. The user's rule: *the theory section does
not preview experimental results; a forward pointer is at most "we revisit this in Section X",
and the result is stated there.*

**Fix.** Cut the preview. If the reader really needs to know the point will return, leave a bare
pointer ("we return to this in Section 5") with no result in it. Never move the result itself
earlier, and never delete the result from where it is actually established.

**Not foreshadowing (leave it alone):**
- The abstract, and an introduction's statement of the paper's contributions: summarising
  results there is their job.
- The roadmap paragraph ("The rest of this paper is organised as follows…").
- A section's closing sentence that names the question the next section answers, without stating
  its answer. The user wants these transitions.
- Definitions and notation set up for later use ("we use $w$ throughout").

## 2. Unnecessary hedging

Hedging is right when it reports real uncertainty: Oppenheimer's style *"complements affirmation
with limitation and with humility"* (p. 12). It is wrong when it is reflexive, stacked, or a way
of not saying who thinks something.

**Graham's glossary** (p. 8) is the classic diagnosis; working scientists, Aaronson notes,
"will recognize the essential veracity of his translations":

| Written | Graham's reading | Fix |
|---|---|---|
| "It is suggested that…", "It is believed that…", "It may be that…" | "I think…" | Say who: "We think", "We propose", or state it as a claim with its evidence. |
| "It has long been known that…" | "I haven't bothered to look up the original reference." | Cite the source, or state the fact plainly. |
| "of great theoretical and practical importance" | "A couple of other guys think so too." | Cut, or say what it is important *for*. |
| "It is clear that much additional work will be required before a complete understanding…" | "I don't understand it." | Say what is not understood. |

**Stacked hedges.** One qualifier per uncertainty. "These results may potentially suggest a
possible link" → "These results suggest a link". Count the uncertainties before cutting:
"it may suggest that the constraints could be facet-defining" carries two (the inference and
the property), so it becomes "it suggests that the constraints may be facet-defining", never
"… are facet-defining", which turns an open question into a claim. Keep the hedge that matches the evidence and
drop the rest: "may", "might", "could", "potentially", "possibly", "perhaps", "appears to",
"seems to", "to some extent", "in some sense", "arguably", "somewhat", "relatively" (with no
comparison), "it is possible that".

**Disclaimer templates** (see `ai-tells.md` §4): "It is important to note that…", "It should
be noted that…", "It is worth mentioning that…" → state the point. "This does not establish…"
or "should be interpreted as… rather than…" used reflexively → keep only if it corrects a
reading a reader would plausibly make, and then say it once, plainly.

**Keep:** hedges that carry information. "For $n \le 11$", "under the assumption that…", "in
all 16 data sets but one", "we conjecture" (a real epistemic status in mathematics),
confidence intervals, and stated limitations of a method. These are precision, not hedging.

## 3. Overstatement

**Boosters that assert importance instead of showing it.** Cut them or replace them with the
fact that would justify them: "clearly", "obviously", "of course", "it is well known that"
(cite instead), "novel", "unprecedented", "groundbreaking", "remarkable", "striking",
"powerful", "elegant" (of one's own work), "comprehensive", "dramatically", "significantly"
and "significant" when not statistical, "crucial", "fundamental", "key" (as an adjective of
praise), "state-of-the-art" (unless a named comparison follows), "for the first time" (unless
the claim is checkable and checked), and "it is important to note".

"Clearly" deserves its own line: if the step is clear, the word is redundant; if it is not, the
word is a bluff.

**Claim-strength mismatches: flag them, do not fix them.** Whether a claim is too strong
depends on evidence only the author can weigh, so the skill never changes the strength of a
claim on its own. List these for the author:
- "proves", "demonstrates", "establishes", "confirms" where the support is a simulation, a
  finite computation, or one data set;
- "always", "never", "all", "any", "guarantees" beyond the cases actually covered;
- causal verbs ("causes", "drives", "leads to") on correlational or observational evidence;
- "the first", "the only", "the best" without a stated comparison;
- generalisation past the tested range (sizes, parameter values, data sets);
- the opposite case: a proven result written as "suggests" or "appears to", which undersells it.

## 4. Jargon that a plain word can replace

Aaronson's line (p. 6): jargon *"can be a useful form of shorthand, especially in cases where
the discovery of a new substance or property demands that new terms be coined"*; but too
often it is used by writers who *"prefer pretentious, abstract words to simple, concrete
ones. Such writers want to dignify not only the subject, but also the writer."* Orwell's fifth
rule (p. 10): *"Never use a foreign phrase, a scientific word or a jargon word if you can think
of an everyday English equivalent."*

**The test: does the word denote or dignify?** A term of art denotes something a plain word
cannot: *branch-and-cut*, *p-value*, *eigenvalue*, *BME polytope*, *nearest-neighbour
interchange*. Keep it, and make sure it is defined at first use. A dignifying word dresses a
plain idea: replace it.

**Plain-word swaps from the essay** (p. 7): facilitate → ease, numerous → many, remainder →
rest, initial → first, implement → do, sufficient → enough, refer to as → call, attempt → try,
utilize → use, perform → do, chemotherapeutic agent → drug, cease → stop, commence → begin,
conceal → hide, visualize → foresee/picture, purchase → buy, locate → find, obtain → get,
transmit → send, proceed → go. Orwell's dress-up words (p. 10): phenomenon, element,
individual, objective, categorical, effective, virtual, basic, primary, promote, constitute,
exhibit, exploit, utilize. Zinsser's (p. 6): interface, operational, viable, dimension,
replicate, infrastructure, functional, time-phase, reciprocal, systematized, organizational.

**Common in current scientific prose** (same test; keep any that is the precise term):

| Dignifying | Plain |
|---|---|
| methodology (meaning a method) | method |
| utilise, leverage, harness, exploit (meaning use) | use |
| elucidate, shed light on | explain, show |
| in order to | to |
| a plethora / myriad / multitude of | many |
| paradigm, framework, landscape (when nothing structural is meant) | approach, setting, field |
| modality, granularity, dimensionality (when not technical) | kind, level of detail, number of dimensions |
| operationalise, instantiate (outside programming or logic) | define, measure, use |
| at this point in time, at the present time | now |
| due to the fact that, in view of the fact that | because |
| a large number of, a majority of | many, most |
| conduct an investigation of, perform an analysis of | investigate, analyse |
| exhibits a tendency to | tends to |
| plays a key role in | (say what it does) |

**Excess-baggage nouns and padding** (p. 7-8): "of a … nature/character", "the time factor",
"weather conditions", "render inoperative", "be subjected to", "give rise to" (→ cause),
"with respect to" (→ about), "the fact that" (→ that). The full list is in
`plain-strong-writing.md` §2.

**Popularised scientific words used loosely.** The essay's examples (p. 7) are *acid test,
reaction, end product, potentials* (from chemistry and physics), *dilemma, beg the question,
dichotomy* (from logic), and *factor, progression, to the nth, proportion, curve, differential*
(from mathematics). Current equivalents, not in the essay: "exponential(ly)" for "fast",
"orders of magnitude" for "much", "quantum leap", "parameter" for "limit". In a scientific
paper these are worse than elsewhere, because the reader will take the technical sense. Use the
precise word.

**Undefined terms and private labels.** Every term must be defined before its first use. Labels
coined while the work was being done ("arm", "phase 2", "the lean variant", a script's mode
name) mean nothing to a reader: explain at first use or replace with a plain description. When
a term is undefined, flag it with where it first appears; do not write a definition the source
does not give. Abbreviations: define at first use, and drop any used fewer than three times.

**Elegant variation is a precision bug here.** Calling one object "the bound", "the estimate"
and "the limit" in successive sentences tells the reader there are three objects. Repeat the
term.

## 5. The user's manuscript conventions

These come from the user's standing instructions for papers and apply whenever the text is a
manuscript:

- **"Square submatrix", not "crop"**: a distance matrix restricted to some of its taxa is "the
  square submatrix on its first $n$ leaves", never a "crop" or "cropped to" (added
  2026-10-29: "it's more rigorous").

- **Active voice where it fits**: "the table presents", "we present", not "is presented". Keep
  the passive where the agent is genuinely irrelevant, and never invent an agent the source
  does not name.
- **An inanimate subject with an active verb only when the pairing is idiomatic.** "The bound
  prunes the node" is fine; "the table argues", "the experiment believes" are not. Use "we",
  "the solver" (software acting), or a less active verb. Converting passives tends to produce
  forced pairings, so check every one.
- **No sentence starting with an imperative** unless justified: "We take the quartet…", not
  "Take the quartet…". Justified: instructions the reader carries out (README steps), and the
  mathematical "Let $G$ be…", "Suppose…". Check mid-sentence forms too.
- **No reassurance about the authors' own checks**: cut "we checked that…", "we verified
  that…", "the experiments used only families verified to be…", "we also confirmed with a second
  solver". Look in the roadmap paragraph and in appendix titles too: "checks of numerical
  reliability (Appendix E)" is the same move at the level of structure. Flag it, since the
  author decides whether that appendix is evidence or reassurance. Keep a check only when it *is* the evidence (a computer-assisted proof's validation,
  support for a conjecture). In particular, a theorem with a proof is not followed by "we also
  verified this empirically": that reads as doubting the proof.
  **The line is proof vs computation** (his ruling, 2026-11-06): a *computational* result
  confirmed by a second, independent computation (a second solver, an independent verifier, a
  different encoding, a count that matches an OEIS value or a published census) stays. That is
  good practice and part of the evidence, not reassurance: *"mathematical theorems don't need
  them, but computational results confirming computational results is not only useful, but
  actually good practice."* Flag only an empirical check placed beside a *proof*, and vague
  reassurance that names no check ("we carefully checked all results").
  **But the confirmation must be independent.** Sanity checks by a second implementation of
  the authors' own (a self-test, a positive-detection test, the same pipeline rerun a second
  way) are flagged as reassurance: *"two implementations of our own are more likely to be
  flawed in the same way, so it's not real reassurance, just sanity checking"* (2026-11-06,
  on a list of such checks behind an exhaustive screen). Those belong in the reproduction
  repository, not the paper. The test: would the check catch a flaw shared by the authors'
  whole pipeline? A different solver, an outside count or a published census can; a rerun of
  their own code cannot.
- **Count from 1** (added 2026-11-06): the manuscript numbers things for human readers, so
  indices, positions, labels and ranges start at 1, and $[n]$ means $\{1, \dots, n\}$. Watch for
  0-based ranges carried over from code: a window the code writes as `{0..23}` has 24 elements,
  so it is $[24]$, never $[23]$. Two exceptions keep their own numbering: objects whose
  elements *are* numbers starting at 0 (residues modulo $q$, field elements of
  $\mathrm{GF}(q)$, exponents), and quoted code or file contents. An off-by-one changes a
  stated quantity, so flag it with the evidence (the code or the count it contradicts) rather
  than editing it silently.
- **No foreshadowing** (§1) and **define every term before use** (§4).
- **Numbers**: tables do not wrap; a numerical inequality gets an argument, not a spot check.
  These are content: flag, do not fix.

## 6. What to flag rather than fix

The skill changes how things are said. These would change what is said, so they go in the
"For the author" list with the location and a one-line reason:

- claim-strength mismatches (§3);
- undefined terms and private labels (§4);
- a hedge whose removal would change the claim, when it is unclear whether the uncertainty is real;
- a missing section transition (§1 "not foreshadowing"): the author writes it, because it must
  name the next section's question correctly;
- placeholders ("[add reference]", "TODO") and abrupt endings;
- a cut that might have removed a real claim.

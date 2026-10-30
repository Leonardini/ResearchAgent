# AI writing tells: full reference

Shared by the `humanizer` and `scientific-humanizer` skills: this file is the single copy,
and both skills' `references/ai-tells.md` are symbolic links to it
(`shared/check_shared.sh` fails if either becomes a separate copy).

Distilled from Wikipedia's *[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)*
as read on 2026-10-23, scoped to **general prose**. The wiki-specific plumbing (citation-markup
bugs, edit summaries, wikitext, AfC drafts, category and template calls) is dropped, because it
does not apply to text a user pastes in. Use this file to recognise tells, and the skill's
contract and method to fix them. The previous version (2026-08-11) is in
`shared/archive/`.

**Contents**
1. Vocabulary that spiked by model era
2. Content-level tells
3. Cadence, symmetry and sentence-shape tells
4. Hedging disclaimers and assistant framing
5. Typography and formatting tells
6. Historical tells (older models; still seen)
7. What is *not* a reliable tell

---

## 1. Vocabulary that spiked by model era

Presence of one of these is weak evidence on its own. Density is what matters: the guide's
signal is a *cluster* of them in one passage. Do not blanket-ban them; a single natural
"crucial" is fine. Context matters too ("underscore" can be literal).

**2023 to mid-2024 (GPT-4 era):** additionally, boasts, bolstered, crucial, delve, emphasizing,
enduring, garner, intricate / intricacies, interplay, key, landscape, meticulous / meticulously,
pivotal, underscore, tapestry, testament, valuable, vibrant.

**Mid-2024 to mid-2025 (GPT-4o era):** align with, bolstered, crucial, emphasizing, enhance,
enduring, fostering, highlighting, pivotal, showcasing, underscore, vibrant.

**Mid-2025 to mid-2026 (GPT-5 era):** emphasizing, enhance, highlighting, showcasing, plus the
notability-and-coverage wording of §2 ("featured in", "independent coverage").

**Mid-2026 onward (GPT-6 era):** challenge, clearer, dependable, echoed, foster, leverage,
matters, multifaceted, practical, prioritize, quietly, steady, universally. This era also
writes **more periods and commas and sentences of a uniform 8 to 20 words** (see §3).

**Grok-flavoured:** causal, empirical, correlate, underscore. (In scientific text these words
are usually doing real work; see §7.)

**Claude-flavoured:** **load-bearing** (metaphorical). Outside structural engineering (a
load-bearing wall, a load-bearing beam) this is a strong and specific Claude tell, and readers who
know the model recognise it on sight. It attaches to claims, assumptions, sentences, citations,
details: "the load-bearing claim", "that adjective is load-bearing". Nothing is wrong with the
metaphor; the problem is that Claude reaches for it constantly, so its density is diagnostic even
when any single use reads fine. **Fix by naming what the thing actually does**, which is almost
always more precise: *the claim the argument rests on* · *the step that has to hold* · *the
assumption doing the work* · *foundational* · *the critical one*. If none of those fit, the sentence
probably did not need the emphasis at all.

Related favourites seen across models: deep dive, realm, foster, leverage, robust, seamless,
spearhead, navigate (used metaphorically), commitment to, groundbreaking, renowned, diverse
array, rich, profound, exemplifies.

---

## 2. Content-level tells

**Undue emphasis on significance, legacy and broader trends**, inflating a mundane subject's
importance: "stands / serves as", "is a testament / reminder", "plays a crucial / pivotal / vital /
significant / key role", "underscores / highlights its importance", "reflects broader", "setting
the stage for", "marking / shaping the", "represents a shift", "key turning point", "evolving
landscape", "focal point", "indelible mark", "deeply rooted". Also situating a subject amid
unnamed "debates" or "public discussions".
> *e.g. a small town's name change "highlighting the enduring legacy of the community's resistance."*

**Superficial analysis via present participles**, vacuous commentary tacked on, usually a trailing
"-ing" clause: "highlighting / underscoring / emphasizing", "ensuring", "reflecting / symbolizing",
"contributing to", "cultivating / fostering", "encompassing", "enhancing", "valuable insights",
"align / resonate with".
> *e.g. "…has supported various services, contributing to the socio-economic development of the region."*

**Promotional / advertisement tone**: "boasts a", "vibrant", "rich", "profound", "showcasing",
"exemplifies", "nestled", "in the heart of", "natural beauty", "groundbreaking", "renowned",
"featuring", "diverse array", "commitment to". Newer models are subtler and avoid open
superlatives ("the best"), so the tone survives without the obvious words.

**Canned emphasis on coverage and recognition**: "independent coverage", "cited / featured /
profiled in", "written by a leading expert", "was identified by", "trade publications". The tell
is prose about the *sources* rather than about the subject.

**Vague connection or association**: "in connection with", "connected to", "in association
with", "particularly / widely associated with", used to suggest a relationship without saying
what it is. (In scientific text, "associated with" is often a precise statistical claim; see §7.)

**Vague attribution / overgeneralization**: opinions pinned on undefined authorities, or source
count exaggerated: "Industry reports", "Observers have cited", "Experts argue", "Some critics
argue", "several sources / publications" (when few or none are cited), "such as" before an
exhaustive list, one source presented as a consensus. **Do not resolve these by inventing a
source**: name the real one or cut the claim.

**Outline-like conclusion**: the formula "Despite [positives], [subject] faces challenges" then
vague future speculation: "Despite its…", "faces several challenges", "Despite these
challenges", "Challenges and Legacy", "Future Outlook", "Looking ahead". The tell is the rigid
formula, not the mention of challenges.

**Copula avoidance**, dodging plain "is/are": "serves as / stands as / marks / functions as /
operates as / represents", "boasts / features / maintains / offers", "refers to".
> *e.g. "Gallery 825 is LAAA's exhibition arm" rewritten as "…serves as LAAA's exhibition space."*

---

## 3. Cadence, symmetry and sentence-shape tells

**Negative parallelism**, three shapes:
- "Not only… but (also)" / "It is not just…, it's": implies correcting an incomplete thought.
  > *"This is not only a work of self-representation, but a visual document of her obsessions."*
- "Not X, but Y" / "It's not…, it's…" / "no…, no…, just": denies the first thing to elevate the second.
  > *"This is not a mirror but a portal: not a representation of self, but a mechanism for reinvention."*
- "Y rather than X": the reversal, now the most common shape in recent output.
  > *"prioritizing empirical consolidation of power… rather than ideological purity."*

Fix: state the positive claim directly. Most of the time the negated half can go.

**Rule of three**: triplet adjectives, triplet phrases joined with "and", or three parallel
list items, used to make shallow analysis look complete. Keep the items that carry distinct
meaning; three genuinely distinct things is not a tell.

**Uniform short sentences and punctuation crowding (mid-2026 onward).** Models trained to
suppress em-dashes now over-use periods and commas instead: a run of sentences all 8 to 20
words long, each a single clause, reads as machine cadence just as surely as the em-dash did.
Vary the length where the content allows it: join two clauses that belong together, and let
one sentence carry a subordinate clause.

---

## 4. Hedging disclaimers and assistant framing

**Didactic disclaimers (2023 to 2024)**: "it's important to note", "it is worth noting",
"it should be noted", reminders about safety, controversy or differences between jurisdictions.
Cut them; state the point.

**Availability disclaimers (2024 to 2025)**: claims that information is "not publicly
available", "isn't widely documented", "based on available information", "maintains a low
profile", followed by speculation. Cut the disclaimer and the speculation.

**Caution templates (mid-2026 onward)**: "should be treated as… rather than…", "this does not
establish…", "should not be confused with…" (the last is the least reliable). These were
almost unheard of before mid-2026. In scientific writing a statement of what a result does
*not* show can be exactly right; the tell is the template used reflexively, especially when
paired with an assertion of importance.

**Collaborative / assistant phrasing**: "Certainly!", "Of course!", "You're absolutely right!",
"I hope this helps", "Let me know if…", "Would you like…", "Here is a…". Always cut: this is
the chatbot frame, not the content.

**Placeholders left in**: "[Describe the method here]", "(add reference)", "INSERT_SOURCE",
"2025-xx-xx". Flag them; never fill them with invented content.

---

## 5. Typography and formatting tells

- **Title Case In Headings** → sentence case ("Impact of technology", not "Impact of Technology").
- **Boldface overuse**: mechanically bolding terms "key takeaways" style. Keep bold for genuine
  emphasis only.
- **Inline-header vertical lists**: bullets with a **bolded label:** then a colon and a
  sentence, repeated. Often prose that was chopped into a list. Restore to prose if the items are
  really sentences.
- **Unusual small tables** that would read better as a sentence.
- **Emoji as bullets or decorative separators** → remove.
- **Curly "quotes"/apostrophes** → straight `'` `"` where the destination is plain text or
  Markdown. (Weak on its own: word processors produce them, and Claude and Gemini usually do not.)
- **Heading problems**: a title heading repeating the document name, skipped levels (H2 → H4),
  headings containing only headings, `---` before every heading → normalise.
- **Markdown when the destination is plain text**: `**bold**`, `# header` where none was wanted.

---

## 6. Historical tells (older models; still seen)

The guide moved these to "historical": newer models produce them much less, but older models and
some current ones still do, so they remain worth fixing when they appear.

- **Em-dash overuse (2022 to September 2026)**: em-dashes, often spaced, where a person would use
  a comma, a colon or parentheses. Recent OpenAI models suppress them, but **Claude still writes
  them**, so in text drafted by Claude the em-dash remains the most common surface tell. Reduce
  them with commas, colons, periods or parentheses. Do not zero them out and then over-use
  periods instead (§3).
- **Elegant variation**: repetition-penalty artefacts that swap in synonyms ("Soviet artistic
  constraints" → "non-conformist artists" → "their creativity") instead of repeating the core
  term. In technical writing this is worse than inelegant: a reader assumes a new word names a
  new thing. Repeat the term.
- **Section summaries**: "In summary", "In conclusion", "Overall", and restating the
  paragraph's point at its end.
- **Knowledge-cutoff disclaimers**: "As of my last update…", "Up to my last training update…".
  Always cut.
- **Abrupt cut-offs**: a text that stops mid-thought. Flag it; do not invent an ending.

---

## 7. What is *not* a reliable tell (avoid false positives)

The guide is explicit that these, **alone**, do not show AI authorship, so do not mangle good
writing chasing them:

- Any single "AI vocabulary" word used naturally.
- Perfect grammar, formal or academic register, "fancy" words, or "bland" prose. Much human
  scientific writing is all of these.
- Transition words on their own ("However", "Moreover" used where the logic needs them).
- Promotional language on its own (some results really are notable), or a vague attribution in
  isolation (some claims lack a nameable source).
- A mix of casual and formal registers (several authors, house styles).
- **Technical uses of flagged words.** In scientific text "significant" (statistical),
  "robust" (robust statistics, robust optimisation), "associated with" (statistical
  association), "empirical", "causal", "correlate", "landscape" (fitness or energy landscape),
  "key" (cryptographic), and "enhance" (signal enhancement) can each be the precise term. Judge
  by whether the word denotes something.

The guide also lists what tends to mark *human* writing: plain "there is" / "it has"
constructions, occasional stiff synonyms ("authored"), confident definite statements ("was the
first"), ordinary qualifiers ("perhaps", "tends to") and some wordiness ("in order to"). A
rewrite need not remove these.

The real target is the **cluster**: several tells co-occurring, plus the underlying moves
(inflated significance, empty analysis, false symmetry, reflexive disclaimers). Fix the cluster;
leave clean prose alone.

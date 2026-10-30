# Checker subagents

A checker verifies one claim that the report is about to make, before it is made. Spawn up
to four in parallel. Give each one only what it needs: the claim, the exact passage (section,
equation, lemma, table, with the surrounding text), and the path to the manuscript so it can
read more context. Use a fresh general-purpose agent, not a fork, so it judges the claim
without the reviewer's expectations.

## Prompt for a checker

```
You are checking one claim a peer reviewer wants to make about a manuscript. Your job is to
find out whether the claim is TRUE, not to agree with the reviewer. Try hard to refute it.

Manuscript: <path>  (read whatever you need; the relevant passage is <location>)
Claim: <one or two sentences, e.g. "In the proof of Lemma 3, the step from (12) to (13)
reverses the inequality because the subtracted term can be negative.">

Check it by the most direct means available:
- a derivation: redo the step by hand, in full;
- a claimed counterexample or bound: construct the instance and compute;
- a numerical inconsistency: recompute from the numbers given, and look for an explanation
  in the text (a footnote, a different unit, a different subset) before calling it an error;
- a claim about code or data in a repository: run or read it.
You may write and run small scripts (Python, R) in a scratch directory. Do not send any part
of the manuscript to an outside service.

Answer in this form:
VERDICT: CONFIRMED | REFUTED | UNCLEAR
EVIDENCE: <the derivation, computation or quotation that settles it; short>
SEVERITY: fatal to the result | fixable without changing the result | cosmetic
FIX: <the correction or the missing argument, if you found one>
```

## Using the verdicts

- **CONFIRMED** → state it as a fact, with the evidence in brief, and the fix if one was found
  ("the statement is true, but should be proven inductively").
- **UNCLEAR** → ask it as a question, with the specific doubt ("unless I am missing something,
  α cannot take the same value in (1) and (S1)").
- **REFUTED** → drop it. If the checker found the claim was a misreading caused by unclear
  text, that may still be a minor clarity point.

Checks that need more than a few minutes of computation are a sign that the point should be
a question to the authors rather than a verified claim.

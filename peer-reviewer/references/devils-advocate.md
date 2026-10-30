# The strongest objection

Adapted from the Devil's Advocate role of the co-scientist-toolkit `paper-review` skill
(MIT licence, after Dominik Lukeš's paper-reviewer-skill).

The point is to find the one objection that, if it stands, undermines the paper's main claim,
and to state it at full strength. A hostile but intellectually honest expert reads the paper
looking for the weakest load-bearing step. Be that reader for a few minutes.

1. State the main claim in one sentence, as the abstract or introduction makes it.
2. List what it rests on: each theorem, experiment, dataset, comparison or assumption without
   which it would not follow.
3. For each, ask what would have to be true for it to fail, and how plausible that is. Typical
   forms:
   - the evaluation cannot distinguish the claimed explanation from a simpler one (a
     confounder, a baseline not run, data leakage, a tuned simulation);
   - the result holds on the instances shown but nothing says it generalises, and the claim is
     general;
   - the proof covers a narrower case than the statement;
   - the comparison is not like with like (different hardware, budgets, implementations, or
     starting points), and the claim is about the method;
   - the contribution is already known, or follows directly from known results.
4. Pick the strongest one. Write it in two or three sentences, as the expert would say it.
5. Say what would defeat it: the analysis, experiment, proof or citation that would answer
   it.

Then decide:
- the paper already defeats it → say how, in one or two sentences, under "The strongest
  objection";
- it stands → it is a major point (usually the first), and the section points to it;
- it might stand → raise it as a major point phrased as a question, with what would settle it.

Do not manufacture an objection the evidence does not support. "The strongest objection is
weak" is a legitimate finding and a useful one for the authors.

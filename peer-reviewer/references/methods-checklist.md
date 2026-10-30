# Questions to ask of the methods

Use the sections that apply. These are prompts for reading, not a list to reproduce in the
report: a point is raised only when the answer is "no" or "not shown" and it matters.

## Proofs and mathematical claims
- Does each theorem state all its hypotheses? Does the proof use one it does not state?
- Does the proof cover the full statement (all n, all cases, the boundary, the degenerate
  case)? Check small cases (n = 1, 2, 3) against the statement.
- Redo the key steps: signs under subtraction, direction of inequalities, strict versus
  non-strict for integers, interchange of limits and sums, optimum at a critical point versus
  on the boundary.
- Are constants explicit, or do "for some constant C" results hide whether the bound means
  anything at realistic sizes?
- Is a numerical claim (an inequality "for all n ≥ 5") proved, or only checked numerically?
- Is a computer-assisted result's computation described well enough to be rerun and checked?

- Is the theorem as strong as its proof allows? Look for a hypothesis the proof never uses,
  a family of constraints that enters only through its sum (one aggregated inequality may
  replace many), an inequality with slack, a special case that generalises. If so, state the
  stronger form and what the weaker one still buys.

## Optimisation models (LP, MILP, conic, SAT, CP)
- Is the model fully stated: variables, domains, objective, every constraint family, which
  families are separated lazily and how?
- Are logical constraints (implications, disjunctions) linearised, and how tightly (big-M
  values, indicator constraints)?
- Is the strength of a formulation reported by its relaxation gap, not only by run time?
- Are two formulations claimed to differ in strength actually different (prove equivalence or
  give an instance)?
- Is the solver comparison fair: same hardware, threads, time limit, starting incumbent,
  tolerances? Are timings repeated over seeds where differences are small?
- Are optimality certificates trustworthy given floating-point tolerances?

## Algorithms
- Correctness: is there an argument, and does it cover the termination and the edge cases?
- Complexity: stated and proved, and does the practical cost match it?
- Is the pseudocode complete enough to implement (every choice specified, every tie broken)?

## Statistical models and inference
- Is the model written down (likelihood, priors, link function)? Are assumptions checked?
- Multiple testing, confounders, the direction and size of effects (not only significance).
- Is the sample representative, deduplicated, and independent where the method assumes it?

## Machine learning and prediction
- Train/validation/test separation, with no leakage (deduplication, related samples, study
  or batch structure, time).
- Validation on independent data (another site, another period); if impossible, a temporal or
  leave-one-study-out split.
- Number of parameters against the data; how hyperparameters were finally chosen.
- Baselines beyond the naive one, including simple non-deep methods.
- Where does the method lose, and why?

## Simulations
- Is the simulation model justified independently of the method being tested, or does it
  favour the method?
- Do the simulated settings resemble the real data (size, noise, dimension)?

## Benchmarks and empirical comparisons
- Instances: chosen how, and are they representative? Are failures reported?
- Is variance reported (seeds, repeats), and is a claimed ratio larger than that variance?
- Is the conclusion about the method or about an implementation?

## Claims and conclusions
- Does each claim in the abstract and conclusion have evidence in the body?
- Is a general claim supported only by special cases?
- Does the paper say what the result means in practice (cost, value, scale)?

## Reproducibility (external papers; for internal papers see SKILL.md)
- Code and data available? Seeds fixed? Software versions given? Could you actually run it?

## The consistency pass (always, mechanically)
Go through the paper once for each line below; grep the source where it helps.
- Every table and figure caption: does each label, symbol and footnote marker it explains
  occur in the cells, and does every marker in the cells have an explanation?
- Every inequality, definition or parameter stated in two places (main text and appendix,
  table and text): the same statement both times? Is one marked "not used" where the other
  is used?
- Every number quoted in the text: is it in a table, and does it match?
- Every pseudocode step: is each choice specified (which candidate, which tie-break, which
  pool), and does the prose describe the same algorithm?
- Every term and symbol: defined before first use, and used with one meaning (one log base,
  one definition of a condition)?
- Version numbers, thread counts, instance lists: the same everywhere?

# The reviewing voice

Drawn from fifteen of the user's own reviews (journal reports for Bioinformatics, BMC
Bioinformatics, Microbial Genomics and Nature Communications, NeurIPS and RECOMB-CG reviews,
and margin notes), all on papers since published under open licences. The examples below are
his words.

## The shape of a report

1. **A neutral summary first**, two to four sentences: what the paper does, how, and on what
   data. No praise inflation, no adjectives doing the work of an assessment. Then one
   sentence of overall impression, which is honest in both directions: "The paper is
   well-written and coherently argued." / "The manuscript is reasonably well written but
   lacks clarity in the main messages."
2. **A bridge into the points**: "However, I have the following significant concerns which I
   would like to see addressed before the paper can be accepted", "I have several major and
   minor comments which I believe could substantially improve this manuscript."
3. **Numbered major points, then numbered minor points.** Three to five majors is typical.
4. Optionally **one closing sentence** that weighs the whole: "Overall, the paper is an
   interesting contribution. However, it seems that the high cost of switching to
   calculations with the algebra of genomes does not come with the corresponding benefit of
   gaining biological insights into genome rearrangements."

Reports are short: 300–700 words for a journal report. Every sentence carries a point.

## The shape of a point

Each major point does three things, usually in two to four sentences:

1. **Locates** the problem precisely: an equation, lemma, table or step, by number.
2. **Says why it matters**: what fails, or what a reader cannot conclude, if it is not fixed.
3. **Proposes a remedy**, concrete enough to act on, and often a cheaper fallback.

> The equivalence between equation (1) in the main manuscript and equation (S1) in the
> supplement is not clear. The authors want to find a score vector s minimizing the
> objective in equation (1), and they appear to derive (S1) by differentiating it. However,
> as the score vector is defined on the compact set [0, 1]^N, where N is the dimension of the
> space, it may attend a minimum on the boundary rather than at a critical point - this is
> not something the authors seem to have considered.

> The penultimate step in the proof of lemma S1.4 does not work because of the subtraction
> which reverses the sign; I believe that the statement is true, but should be proven
> inductively, rather than directly as attempted here.

> If no other similar dataset can be obtained, at the very least a sensitivity analysis that
> should be done is to keep the last 2-3 years of the data for validation, and use only the
> earlier years to train and test the models. In this way any possible effect from
> increasing resistance trends could be mitigated.

> It is not completely clear that the nullspace matrix in equation (11) has full rank - this
> generally may depend on the relationship between T and N. The authors should address this
> in more detail, if only by showing that to make the MCS^2 approach work in this context, it
> is enough to exhibit any matrix that annihilates the original coefficient matrix in (10).

## What he looks for

- **Mathematical correctness, checked line by line**: a sign reversed by a subtraction, a
  minimum on the boundary instead of at a critical point, a strict inequality that should be
  `y >= 1` for integers, a parameter that cannot be the same in two equations, a missing
  square in a lemma that makes it false for n = 1, an incorrect partial derivative. He says
  whether the error is fatal: "while certainly non-fatal", "I am not sure that the argument
  survives".
- **Optimisation models**: how an implication is linearised ("a big-M approach may be
  suboptimal relative to a tighter constraint"), the LP-relaxation gap as a better guide than
  run time, whether formulations are equivalent and could be proved so, solver tuning.
- **Statistical and ML validity**: overfitting (a model with 4,000 parameters, a threshold per
  domain-drug pair), held-out or independent validation, deduplication of samples,
  confounding by study structure, how a hyperparameter was finally chosen when folds disagree,
  the sign and direction of associations, not just their existence.
- **Fair evaluation**: comparisons against only a naive baseline, a simulation model "tailored
  to show their method in the best possible light", no explanation of where the method loses.
- **Whether the result means anything in practice**: constants in bounds that make guarantees
  uninterpretable, asymptotics for finite data, super-exponential cost with no practical
  route, value never demonstrated (cost-effectiveness).
- **Concrete illustrations**: "show a complete computation of possible distances between all
  genomes with n = 3 genes, and small examples (with n = 4 or 5 genomic segments)".
- **Prior work, specifically**: a named more recent reference (Mash rather than MHAP; the
  2021 WHO catalogue), or a correction of how a cited contribution is described ("the real
  theoretical contribution of [21] is the proof that …; this should be acknowledged").
- **Domain plausibility**: "I find it extremely unlikely that their abundance can be related
  to obesity", "Isn't that just because they are ordered alphabetically?!", "Main issue here
  is 'post hoc ergo propter hoc'".
- **Reproducibility, practically**: fixed random seeds in a configuration file, scripts named
  for what they do, code factored into functions, and whether he could actually run it.
- **Readability as structure**: "the majority of the readers will be more interested in what
  you have found than in how you went about finding it"; technical derivations moved to
  appendices so the application leads.

## Tone

- Collegial and direct. Disagreement is stated, not softened into vagueness.
- Honest about his own uncertainty: "unless I am missing something", "I believe that the
  statement is true, but", "though I could be wrong", "as far as I was able to follow them
  (which is, not all the way)".
- Credits what is good, specifically, and does not pad: "The analytical approach is reasonable
  and transparent".
- Acknowledges circumstances fairly: "I appreciate that the article may have been written
  prior to …, but …".
- Many points are questions that open a line of inquiry: "would it not be cost-effective to
  compute an LU or QR factorization of the coefficient matrix … ?", "How do your findings
  square with those of …?"
- Minor wording fixes as `it is necessary consider → it is necessary to consider`.

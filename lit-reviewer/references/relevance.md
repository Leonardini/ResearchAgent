# Relevance colours

The colour answers one question: **how much does this item take away from, or feed into, what
the project is trying to do?** It is judged against the targets (`T1..`) and results already
obtained (`A1..`) in `brief.json`, not against the topic in general. A famous paper on the topic
can be green; an obscure blog post can be red.

## Red: overlap risk

The item does all or part of a target or an achieved result, or competes directly for a target.
At least one `overlap` entry is `done`, `partial` or `competing`.

- `done`: the item already establishes the target, or something at least as strong. Example:
  the project aims to prove a bound for graphs on up to 60 vertices; the item proves it for
  every size.
- `partial`: it achieves a weaker version, a special case, a subset of the instances, or the same
  result by a method the project meant to be first with. Examples: the item settles the
  small instances the project planned to cover, leaving the large ones; it proves the
  result for planar graphs but not for general ones; it reaches the record by the same search method
  the project proposed, at a smaller size.
- For an **active** project, an item that obtained one of the project's own results (`A1..`)
  first is red with `done` on that result, even if it is older than the project: the project
  cannot claim it as new.

Red is a strong statement about someone else's work, so check what the item actually proved,
built or measured before giving it. Similar words in a title are not overlap.

- `competing`: the item has not reached the target, but its authors are visibly racing for it:
  records set one step short of it, an announced attack on it, a method scaled up towards it.
  Direct competition is red even before the target falls, because it changes how urgent the
  project is and whether it is still worth doing.

## Amber: closely related

The item does not achieve a target, but the project must know it. Its `overlap` entries are
`related`.

- Same problem attacked by other means, with results that do not reach the target (a lower
  bound, a heuristic, a smaller case solved differently, a negative result).
- A method, tool, dataset or benchmark the project builds on or competes with directly: the
  baseline the project will be compared against, the solver it extends, the data it uses.
- A record, table or repository that defines the current state of the art the targets are
  measured against.

## Green: background

A paper on the topic would cite it, but it neither threatens nor directly feeds a target: the
classic results, surveys, older methods since superseded, related problems. Green items need no
overlap entries.

## Irrelevant

A false hit: shares words, not substance. Give the reason in a few words ("different 'line'
sense: production lines"). These stay in the ledger so the next run does not screen them again,
and are hidden on the page unless the reader turns them on.

## Borderline calls

- Between red and amber: if the item's existence changes what the project can claim as new, it
  is red. If it only changes how the project should be done or compared, amber.
- Between amber and green: if the project's paper would discuss it in more than one sentence, or
  compare against it, amber.
- A preprint or post is judged like a paper. An unrefereed result that matches a target is still
  red; say in the reason that it is unrefereed.
- An item that **claims** a target without a credible argument (an unreviewed upload announcing
  a famous open value, a heuristic titled as a proof) is amber, not red, with the reason saying
  what it claims and why it does not settle it. The reader should see it, so it is not green.
- When a verdict rests on the abstract only and the abstract is vague, choose the colour the
  abstract supports and say what reading the full text would settle.

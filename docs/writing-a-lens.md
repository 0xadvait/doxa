# Writing a Lens

A lens is the question doxa asks while reading. It should describe what counts
as a belief for your project.

Good lenses are specific:

```yaml
lens:
  name: decision-theory
  description: Extract claims about judgment, uncertainty, incentives, and action.
  question: What does this source believe about making decisions under uncertainty?
  stances: [supports, questions, rejects, complicates]
  tags: [uncertainty, incentives, judgment]
```

String shorthand also works -- it fills in sensible defaults for the name,
guiding question, stances, and tags:

```yaml
lens: Extract claims about courage, duty, risk, and practical judgment.
```

Avoid asking for "everything interesting." The narrower the lens, the cleaner
the belief base.

## The lens library

"What lens should I use?" is the first hard question, so doxa ships an
opinionated library -- you don't have to invent your first one.

```bash
doxa lenses list                              # browse the built-ins + your own
doxa lenses show investment-memo              # see one as a copy-pasteable lens: block
doxa init --lens-template founder-strategy    # seed a new config from a template
```

Built-in templates:

| Template | For |
| --- | --- |
| `durable-beliefs` | general-purpose: timeless claims and principles (the default) |
| `founder-strategy` | building companies: decisions, tradeoffs, startup lessons |
| `investment-memo` | backing a company: thesis, risks, what would have to be true |
| `technical-design` | engineering: architecture decisions, tradeoffs, failure modes |
| `research-literature` | papers: findings, claims, stated limitations |
| `policy-analysis` | policy: positions, tradeoffs, stakeholders, consequences |
| `personal-principles` | a personal canon: operating principles for work and life |
| `customer-discovery` | talking to users: pains, jobs-to-be-done, signal strength |

### Make it your own

Templates are a starting point. Fork one (or supply your own) and it becomes a
first-class template you can `--lens-template` into any new base:

```bash
doxa lenses add my-thesis --from investment-memo   # fork a built-in to customize
doxa lenses add team-lens --file ./team-lens.yaml  # or bring your own YAML
doxa lenses path                                    # where your lenses live
```

User templates live under `~/.config/doxa/lenses/` (override with `DOXA_LENS_DIR`)
and shadow a built-in of the same name, so you can override the defaults wholesale.


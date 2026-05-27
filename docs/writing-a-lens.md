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

Avoid asking for "everything interesting." The narrower the lens, the cleaner
the belief base.


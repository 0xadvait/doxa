# Contributing

doxa is a clean-room, public, open-source project for building verbatim-grounded
belief bases. Contributions should keep that guarantee intact.

## Development

```bash
python -m pip install -e ".[all]"
python -m pytest -q
```

Core functionality must keep working with only the base dependency set. Tests
must not require network access, API keys, Postgres, or private data.

## Source and example policy

- Do not commit personal notes, private corpora, private transcripts, or copied
  material with unclear rights.
- Example content must be public domain, pre-1929, or explicitly licensed for
  redistribution.
- Beliefs must never contain invented quotes. If a quote cannot be verified as a
  real substring of the source after whitespace normalization, drop it.

## Provider policy

Providers should implement the small `complete(system, user) -> str` interface.
If a binary, package, or key is missing, raise a clear `DoxaError` that tells the
user exactly what to install or set.


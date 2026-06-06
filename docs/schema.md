# Schema reference

Beliefs and quotes are stored as line-delimited JSON (`data/*.jsonl`).

`Belief`:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable belief identifier. |
| `belief` | string | Concise claim or stance. |
| `reasoning` | string | Why the linked quote supports the belief. |
| `stance` | string | Usually `supports`, `questions`, `rejects`, or `complicates`. |
| `conviction` | number | 0 to 1 score based only on quote support. |
| `tags` | list[string] | Optional retrieval/filtering tags. |
| `source` | object | `title`, `author`, `date`, `url`. |

`Quote`:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable quote identifier. |
| `quote` | string | Exact source substring. |
| `speaker` | string | Speaker or author label when available. |
| `source` | object | `title`, `author`, `date`, `url`. |
| `context` | string | Short surrounding context. |
| `tags` | list[string] | Optional quote tags. |
| `belief_ids` | list[string] | Linked belief identifiers. |

Stored source records keep the full text so quote faithfulness can be checked
again later.

Domain preferences use normal tags such as `domain:technical`, plus optional
plain-tag aliases under `preferences.domain_aliases`; no schema migration is
required. Keyword search can use active aliases for low-weight candidate
discovery before final ranking.

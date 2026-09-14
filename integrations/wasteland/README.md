# Wasteland commons profile

[Wasteland](https://github.com/gastownhall/wasteland) federates Gas Town rigs
through one shared Dolt database (`hop/wl-commons` on DoltHub, schema version
1.2). There is no wire protocol: participants insert rows, commit, and
propagate them by Dolt fork, pull request, and merge. Identity is a DoltHub
account plus a rig handle; reputation is a per-author hash chain of `stamps`.

RCP uses Wasteland as an **asynchronous public ledger** for tasks, completions,
and validation outcomes across institutions. A2A remains the live transport
between two nodes; the ledger is where third parties see that work was posted,
who claimed it, what came back, and whether it validated. Nothing in the ledger
is trusted for authorization: receivers re-run the RCP pipeline on the carried
JSON-LD before acting.

## Row profile

| Wasteland table.column | RCP source | Rule |
|---|---|---|
| `wanted.id` | `ResearchTask.@id` | `w-` + first 10 hex of SHA-256 of the IRI |
| `wanted.type` | constant | `rcp-task` (raw SQL; `wl post --type` rejects it) |
| `wanted.title` | task class local name + first dataset | display only |
| `wanted.description` | the whole task | canonical JSON (sorted keys, compact), at most 1 MiB |
| `wanted.tags` | `taskType`, `semanticContract` | `["rcp","rcp-task","rcp-class:<Local>","rcp-contract:<IRI>"]` |
| `wanted.sandbox_required` | any `RestrictedDataset` in `usesDataset` | `1` when present |
| `wanted.sandbox_scope` | profile IRI and document digest | `{"profile": ..., "digest": "sha256:..."}` |
| `wanted.posted_by` | operator input | rig handle of the posting node |
| `completions.id` | `ResearchContribution.@id` | `c-` + first 10 hex of SHA-256 |
| `completions.wanted_id` | `addresses` | derived with the `wanted.id` rule |
| `completions.evidence` | the whole contribution | canonical JSON |
| `completions.completed_at` | `generatedAtTime` | |
| `stamps.context_id` / `context_type` | completion id / `completion` | one stamp per validating rig per completion |
| `stamps.valence` | `SemanticValidationReport` | `semantic` and `quality` are 1.0 for `entailed`, 0.5 for `unknown`, 0.0 otherwise; `rcp_status`, `contract`, `bundleDigest`, `checker`, `checks` are copied |
| `stamps.author` / `subject` | validating rig / contributing rig | the schema rejects `author = subject` |

`rigs` rows are managed by `wl join`; a node that also exposes an A2A Agent
Card should put the card URL in `rigs.hop_uri` so ledger readers can find its
live endpoint.

## Commands

```bash
research-commons to-wanted task.jsonld --posted-by <rig-handle> --sql | dolt sql
research-commons to-completion contribution.jsonld --completed-by <rig-handle> --sql | dolt sql
research-commons to-stamp report.json --author <validator> --subject <contributor> \
  --completion <c-id> --sql | dolt sql
dolt commit -S -am "rcp: ..." && dolt push origin main   # -S signs with GPG; wl verify checks it
```

Without `--sql` the commands print the row as JSON for `wl serve` or a custom
loader. `example.sql` shows the three statements for the metagenomics example.
Statements are `INSERT ... ON DUPLICATE KEY UPDATE`, so re-posting a task is
idempotent. String literals are escaped for Dolt/MySQL; the payload is hostile
by assumption and the schema has no DDL surface, but consumers must still call
`validate-structure`, `validate-shacl`, and `validate-semantics` on the carried
document before executing anything.

Reading back:

```python
from research_commons.wasteland import wanted_to_task
task = wanted_to_task(row)   # re-validates and checks the id derivation
```

## Trust model and limits

- Wasteland `trust_level` and stamps are reputation signals, not RCP
  authorization. Only an `entailed` result under a locally trusted manifest
  can open an execution gate.
- Restricted data never enters the ledger: the task row carries dataset IRIs
  and class assertions, not data. `sandbox_required = 1` flags such tasks.
- Wasteland is v0.4 with a single maintainer and requires `dolt` plus a DoltHub
  account for the public commons. A consortium can run its own commons with
  `wl create <org>/rcp-commons`, which applies the same DDL.

# Beads projection

[Beads](https://github.com/gastownhall/beads) (`bd`) is the Dolt-backed issue
graph that Gas Town and Gas City agents use as working memory. RCP does not
adopt beads as a semantic layer. It projects RCP messages onto beads so that
agent orchestrators can schedule, block, and audit research tasks with the
tooling they already run, while the JSON-LD document stays authoritative.

## Mapping

| RCP | Bead field | Notes |
|---|---|---|
| `ResearchRequest` | `issue_type = epic`, label `rcp-request` | title = `question` |
| `ResearchTask` | `issue_type = task`, label `rcp-task`, label `rcp-class:<TaskClass>` | title = task class + first dataset |
| `ResearchContribution` | `issue_type = task`, `status = closed`, label `rcp-contribution` | `closed_at = generatedAtTime` |
| `@id` | `external_ref`, `metadata.rcp.id` | bead id = `<prefix>-` + first 8 hex of SHA-256(`@id`) |
| `semanticContract` | `spec_id`, `metadata.rcp.semanticContract` | |
| `ontologyProfile` | `metadata.rcp.ontologyProfile` | |
| whole message | `metadata.rcp.document` | canonical digest in `metadata.rcp.digest` |
| `partOfRequest` | dependency `parent-child` on the request bead | |
| `addresses` | dependency `relates-to` on the task bead | |
| `RestrictedDataset` present | label `rcp-restricted-data` | |
| `onBehalfOf` / `requestedBy` / `producedBy` name | `created_by` | attribution hint only |
| all RCP beads | `source_system = rcp` | lets `from-bead` skip unrelated beads |

Priority, assignee, estimate, and status transitions are operational state and
are never written back into the RCP document.

## Commands

```bash
research-commons to-bead examples/metagenomics/request.jsonld \
  examples/metagenomics/task.jsonld examples/metagenomics/contribution.jsonld | bd import -
bd list --label rcp-task
bd export -o issues.jsonl && research-commons from-bead issues.jsonl
```

`from-bead` re-validates the carried document against `message.schema.json`
and refuses beads whose `metadata.rcp.digest` or `external_ref` disagree with
the carried document. Tested against `bd` 1.2.2.

## Formula

`formulas/rcp-task.formula.toml` is a `bd` workflow formula that orders the
conformance pipeline: recover, validate shape, semantic gate, execute, package,
independent validation (human gate), publish. Copy it into `.beads/formulas/`
or point `GT_ROOT` at a checkout that contains it.

## Configuration

`config.yaml` shows the `validation.metadata` fragment that makes `bd` reject
malformed `metadata.rcp` blocks.

## Federation

`bd federation add-peer` synchronizes whole Dolt databases between labs. That
is appropriate inside one trust domain (a lab and its own agents). Between
institutions use the Wasteland commons profile in `../wasteland/`, which shares
individual rows rather than whole databases.

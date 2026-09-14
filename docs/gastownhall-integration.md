# Using the Gas Town ecosystem with RCP

[gastownhall](https://github.com/gastownhall) publishes the Gas Town family of
agent-orchestration tools. This document records what each piece is, where it
fits RCP, and where it does not. Status as of 2026-09-14.

## Inventory

| Repository | What it is | Maturity | RCP use |
|---|---|---|---|
| `beads` (`bd`) | Dolt-backed issue graph used as agent memory; JSONL import/export, formulas, gates, HTTP API, MCP server | 1.3 rc, production | Per-lab task ledger. `research-commons to-bead` / `from-bead`. |
| `wasteland` (`wl`) | Federation of towns through one shared Dolt database on DoltHub: `wanted`, `completions`, `stamps`, `rigs` tables | 0.4, single maintainer | Inter-institution public ledger. `to-wanted`, `to-completion`, `to-stamp`. |
| `gascity` (`gc`) | Orchestration-builder SDK: cities, rigs, agents, formulas v2 with exec checks, packs, exec beads providers | pre-1.0 rolling | Pack in `integrations/gascity/rcp-pack`. |
| `gascity-packs` | First-party pack registry | active | Publication target for the pack. |
| `bdp` | Draft HTTP/JSON Bead Protocol with JSON Schema typed beads and links | draft v0 | Type descriptors in `integrations/bdp`. |
| `gastown` (`gt`) | Original orchestrator, superseded by gascity | maintained | none |
| `marketplace` | Claude Code plugin marketplace (one wasteland plugin) | small | Optional later `rcp` plugin. |

## Boundary

RCP defines what a research task, contribution, and validation result mean.
Gas Town tools decide who works on what and when. The mapping keeps that split:

```text
RCP JSON-LD message  --(projection)-->  bead / wanted row / completion / stamp
        ^                                          |
        |            document carried verbatim      |
        +------------------(recovery + re-validation)+
```

Every projected record carries the complete JSON-LD document and its canonical
SHA-256 digest. Recovery functions refuse records whose digest, id derivation,
or root type disagree, then run `message.schema.json` validation again. Nothing
read from a ledger is trusted for authorization: the receiving node re-runs
JSON Schema, SHACL, and the SROIQ gate under its own manifest.

## Concept mapping

| RCP | Beads | Wasteland | Gas City |
|---|---|---|---|
| `ResearchRequest` | epic, label `rcp-request` | (not posted; tasks are) | convoy of task beads |
| `ResearchTask` | task, label `rcp-task`, `metadata.rcp.document` | `wanted` row, `type = rcp-task`, JSON in `description` | work bead slung to `rcp-worker` |
| `ResearchContribution` | closed task, label `rcp-contribution`, `relates-to` the task | `completions` row, JSON in `evidence` | output of the `package` step |
| `SemanticValidationReport` | comment or bead note | `stamps` row, `valence.semantic` in {1, 0.5, 0} | exit code of the `gate` exec check |
| `Agent`, node | `created_by`, assignee | `rigs` row, `hop_uri` = A2A Agent Card URL | `agents/<name>/agent.toml` |
| `partOfRequest` | `parent-child` dependency | `project` tag | formula epic |
| `RestrictedDataset` | label `rcp-restricted-data` | `sandbox_required = 1` | human gate |
| execution order | formula steps with `needs` | claim / done / accept states | formula v2 with `check` scripts |

## What was adopted

- `src/research_commons/beads.py`, `wasteland.py`, `ledger.py`: projections and
  recovery with digest and id checks. CLI: `to-bead`, `from-bead`, `to-wanted`,
  `to-completion`, `to-stamp`.
- `integrations/beads/`: mapping table, config fragment, `rcp-task` formula
  (verified with `bd formula show`, `bd cook`, `bd mol pour` on `bd` 1.2.2).
- `integrations/wasteland/`: row profile, example SQL, trust notes.
- `integrations/gascity/rcp-pack/`: pack with agent, formula, commands,
  doctor check, exec check scripts. Authored to the pack spec; not yet run
  against a `gc` city.
- `integrations/bdp/`: type descriptors aligning RCP messages with BDP.

## What was not adopted, and why

- **Beads as the semantic model.** Beads fields are operational; RCP semantics
  stay in JSON-LD, SHACL, and OWL.
- **Wasteland trust levels or stamps as authorization.** They are reputation
  signals; only an `entailed` result under a locally trusted manifest opens an
  execution gate (ADR 0001, ADR 0002).
- **Whole-database `bd federation` between institutions.** It shares the entire
  issue graph including private beads. Between labs, share rows through the
  Wasteland profile or A2A instead.
- **`wl post` for tasks.** Its `--type` vocabulary is fixed; the profile writes
  `type = 'rcp-task'` with SQL.
- **Exec beads provider.** Worth doing once an RCP node exposes task storage;
  see `integrations/gascity/rcp-pack/README.md`.

## Risks

Gas City changes schema between releases (formula v1 to v2 already), Wasteland
depends on one maintainer and DoltHub, and BDP has only a read-profile
reference. The stable anchors are the `bd` JSONL contract, the `commons.sql`
DDL, and the pack directory convention. The projection code touches only those.

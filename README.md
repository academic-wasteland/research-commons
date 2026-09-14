# Research Commons Protocol

Research Commons Protocol (RCP) is a specification-first interoperability layer
for exchanging machine-readable research tasks and contributions between
independently operated agents and services.

The v0.1 implementation focuses on semantic contracts:

- JSON Schema validates the wire representation;
- SHACL validates explicit RDF graph structure;
- OWL 2 Direct Semantics validates consistency, entailment, and compatibility;
- [Kobayashi-MaRust](https://github.com/bio-ontology-research-group/kobayashi-marust)
  is the reference SROIQ checker; and
- A2A carries tasks and artifacts without introducing another task lifecycle.

## Quick start

```bash
uv sync --extra dev
uv run research-commons validate-structure examples/metagenomics/task.jsonld
uv run research-commons validate-shacl examples/metagenomics/task.jsonld
uv run pytest
```

Semantic checks additionally require the `km` binary:

```bash
uv run research-commons validate-semantics \
  examples/metagenomics/task.jsonld \
  --manifest examples/contracts/public-research.contract.json \
  --km-bin /path/to/km
```

## Orchestrator integrations

RCP messages can be projected onto the Gas Town ecosystem
([gastownhall](https://github.com/gastownhall)) without giving up the semantic
contract: beads for per-lab scheduling, Wasteland for a cross-institution
ledger, a Gas City pack for rig agents, and BDP type descriptors.

```bash
uv run research-commons to-bead examples/metagenomics/task.jsonld | bd import -
uv run research-commons to-wanted examples/metagenomics/task.jsonld --posted-by <rig> --sql
```

See `docs/gastownhall-integration.md`, ADR 0002, and `integrations/`.

The motivating proposal is preserved in
`federated_agentic_research_commons_biohackathon_2026.md`.

## Status

This is a pre-release conformance prototype, not a production authorization or
workflow-execution system. See `docs/architecture.md` and
`docs/semantic-validation.md` before implementing a node.

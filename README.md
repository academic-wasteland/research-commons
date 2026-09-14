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

The motivating proposal is preserved in
`federated_agentic_research_commons_biohackathon_2026.md`.

## Status

This is a pre-release conformance prototype, not a production authorization or
workflow-execution system. See `docs/architecture.md` and
`docs/semantic-validation.md` before implementing a node.

# ADR 0002: External ledgers carry RCP messages, they do not define them

## Status

Accepted.

## Context

Gas Town tooling (beads, wasteland, gascity) offers mature scheduling,
federation, and reputation machinery. Adopting it wholesale would make bead
fields or Wasteland stamps the source of truth for what a task is and whether
it may run.

## Decision

Beads, Wasteland rows, and Gas City work items are projections. Each carries
the complete RCP JSON-LD document and its canonical digest. Identifiers are
derived deterministically from the RCP `@id`. Recovery re-validates the
carried document and rejects digest, id, or type mismatches. Ledger state
(status, priority, claims, stamps, trust levels) never feeds the semantic gate;
only `entailed` under a locally trusted manifest does.

## Consequences

Orchestrators can use their native tools without RCP-specific storage.
Projection code stays small and touches only stable interchange contracts
(`bd` JSONL, `commons.sql` DDL, pack directory layout). Any ledger can be
dropped or replaced without changing a single RCP message. The cost is
duplication: the same task exists as a message, a bead, and a wanted row, and
operational state lives outside the semantic object by design.

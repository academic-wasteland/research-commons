# ADR 0001: SROIQ semantic contracts with KM as reference checker

## Status

Accepted.

## Decision

RCP conformance is defined by OWL 2 Direct Semantics. Contract ontologies may
use full SROIQ. Kobayashi-MaRust is the shipped reference checker, but any
complete implementation returning the same normative entailments conforms.

JSON Schema and SHACL retain responsibility for explicit message shape. A2A
retains responsibility for transport and task lifecycle. Operational policy is
not encoded as OWL.

## Consequences

The protocol can express rich capability and delegation contracts without
coupling its semantics to one reasoner. Implementations must isolate reasoning,
pin ontology versions, and preserve `unknown` as distinct from rejection and
acceptance.

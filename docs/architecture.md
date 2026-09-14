# Architecture

RCP separates transport, explicit graph validation, semantic reasoning, and
operational policy. These layers intentionally do not replace one another.

```text
A2A message or artifact
        |
        v
JSON Schema ----- malformed wire data
        |
        v
SHACL ----------- missing explicit values and graph-shape violations
        |
        v
SROIQ ----------- inconsistency, entailment, and contract compatibility
        |
        v
Policy/state ----- authorization, budgets, deadlines, and lifecycle
```

## Trust boundary

A receiving node reasons only against ontology files named by a locally trusted,
digest-verified contract manifest. Remote messages contribute ABox assertions;
they cannot contribute imports, class definitions, property definitions, or
ontology mappings. This prevents a sender from redefining terms such as
`RestrictedDataset` or `PermittedTask` to bypass policy.

Each manifest also allowlists the classes and object properties that a message
may assert, so a sender cannot assert the contract's own `AcceptedTask` class.
This is syntactic authority, not factual attestation: policy-sensitive facts
such as dataset access status must still come from a receiver-trusted source or
be verified independently before execution.

## Federation

Nodes are discovered from configured A2A Agent Card URLs. Agent Cards advertise
one or more RCP contract manifests and the task/output classes supported under
each contract. Registries and global crawling are outside v0.1.

## Result model

Semantic validation is five-valued: `entailed`, `contradicted`, `unknown`,
`invalid`, or `indeterminate`. Only `entailed` can satisfy an execution or
authorization gate. In particular, open-world absence is never permission.

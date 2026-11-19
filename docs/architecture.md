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

## RO-Crate carrier

Per ADR 0002, an RO-Crate carries an RCP message; it does not define it.
`research-commons to-crate` (or `to-completion --crate-out`) writes a directory
or `.zip` crate with the verbatim message as `rcp-message.jsonld` and
`ro-crate-metadata.json` conforming to `spec/ro-crate-rcp-profile.json`.
`research-commons from-crate` recovers and re-validates the message.

- **Context:** the metadata uses exactly the RO-Crate 1.1 context plus the
  inline carrier context `{"rcp": "https://w3id.org/research-commons/v0.1/",
  "digest": "rcp:digest"}`. It never references the RCP message context, which
  is not independently resolvable and redefines RO-Crate terms (`Person`,
  `Organization`, `name`, `license`, `object`). Recovery rejects any other
  context and any `@context` below the top level, and parses offline.
- **Profiles:** the root conforms to RO-Crate 1.1 and the carrier profile, and
  to Process Run Crate 0.5 when the `CreateAction` has an instrument. Each
  profile is also described as a `CreativeWork` entity.
- **Producer:** RCP types are kept (`Agent` becomes `rcp:Agent`); RCP `Person`
  and `Organization` also get the schema.org type; other IRIs (including CURIEs
  with RCP-context prefixes such as `prov:`) are kept as absolute IRIs. Strings
  the RCP context leaves undefined are dropped; the fallback type is `Thing`.
- **Integrity:** recovery rejects digest, `about`/`@id`, root type and derived
  `CreateAction` identifier mismatches.
- **Independent conformance:** the test suite validates generated crates with
  roc-validator 0.11.4 (`ro-crate-1.1` and `process-run-crate-0.5` at the
  required level, plus pinned recommended-level deviations). These tests need
  network access to w3id.org.

Crates written before the self-contained carrier context (referencing
`https://w3id.org/research-commons/v0.1/context.jsonld` or Process Run Crate
0.1) are not accepted by recovery; rebuild them from the carried message.

# Semantic validation

Let `O` be the trusted SROIQ ontology bundle, `M` the validated message ABox,
and `m` the message individual.

## Checks

1. Reject the message as `invalid` if `O union M` is inconsistent.
2. Prove `m : C` by testing whether `O union M union {m : not C}` is
   inconsistent.
3. Prove `A subClassOf B` by testing whether `A and not B` is unsatisfiable.
4. Mark the result `unknown` when neither a proposition nor its complement is
   entailed.
5. Mark failures and resource-limit exhaustion as `indeterminate`.

The reference checker creates probe axioms in OWL Functional Syntax and invokes
KM as an isolated subprocess. Contract ontologies may use full SROIQ. Messages
may assert individuals and their types/relations but cannot add TBox or RBox
axioms.

The v0.1 contract bundle is one flattened, import-free Functional Syntax
ontology. Its digest is the SHA-256 of its exact bytes. The bundle digest is the
SHA-256 of the UTF-8 sequence `ontologyIRI`, a NUL byte, the prefixed file
digest, and a newline. This removes network imports from the reasoning boundary.

## Receiver assertions

A receiving node may add its own ABox facts before reasoning, for example
`ClassAssertion(ReputableRequester requester)` derived from a reputation
ledger it trusts, or `ClassAssertion(RestrictedDataset dataset)` from its
access-control list. Receiver assertions bypass the sender allowlist because
the sender did not write them, but they are rendered through the checked
serializer, limited to class assertions, and listed in the report under the
`receiver-assertions` check so the decision can be audited and repeated.
Receiver assertions are node policy (section 8.14 of the proposal); they are
never transmitted with the message.

## What OWL does not validate

OWL uses open-world semantics and does not assume differently named individuals
are distinct. Consequently, explicit field presence, list closure, and JSON
cardinality remain SHACL or JSON Schema concerns. Time, budget, token revocation,
and deny-overrides policy remain procedural concerns.

## Reproducibility

Every report records the contract identifier, ontology bundle digest, checker
name/version, check kind, outcome, runtime, and diagnostic. A receiving node
must retain the exact message and ontology bundle needed to repeat a decision.

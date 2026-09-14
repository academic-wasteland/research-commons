# A2A binding

## Extension identifier

`https://w3id.org/research-commons/v0.1/a2a`

Clients and servers advertise this URI through A2A extension negotiation.

## Agent Card parameters

The extension parameters conform to `agent-card-extension.schema.json`. Each
entry identifies a contract manifest, its digest, an accepted task class, and a
guaranteed output class.

## Messages and artifacts

- A `ResearchTask` is carried in an A2A structured-data message part with media
  type `application/ld+json;profile="https://w3id.org/research-commons/v0.1/task"`.
- A `ResearchContribution` is returned as an A2A artifact part with media type
  `application/ld+json;profile="https://w3id.org/research-commons/v0.1/contribution"`.
- The A2A context identifier groups tasks belonging to one `ResearchRequest`.
- A2A task states, cancellation, streaming, and authentication are not repeated
  in RCP objects.

## Failure mapping

Structural or semantic rejection produces an A2A rejected task with a
`SemanticValidationReport` artifact. Reasoner failure or timeout produces an
indeterminate report and must not start execution. Clarification may be
requested when the semantic result is `unknown`.

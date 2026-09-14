# Bead Protocol type descriptors

[BDP](https://github.com/gastownhall/bdp) is a draft HTTP/JSON protocol for
bead stores: `Bead {id, type, revision, properties}` plus first-class
`Link {type, source, target}` records, discovered through an RFC 8631
`service-desc` link and typed by Type Descriptors that name a JSON Schema for
`properties`. It is the one spec-first artifact in the gastownhall ecosystem
and the closest fit to RCP's own approach.

`rcp-types.json` declares one bead type per RCP message kind and one link type
per RCP object property that connects messages. A BDP store hosting RCP
messages uses the message `@id` as the bead id, the descriptor id as the bead
type, and the JSON-LD document as `properties`; links mirror `partOfRequest`,
`addresses`, and validation. BDP is draft v0 with a TypeScript reference
implementation only, so this directory is an alignment note rather than a
supported transport. Watch the `bdp` repository before building on it.

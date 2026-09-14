# Threat model

The conformance checker assumes that messages, artifacts, identifiers, and
natural-language content are hostile.

- Reject messages containing ontology imports or axiom-bearing fields.
- Reject ABox terms outside the contract allowlist and never allow decision
  classes themselves to be asserted by the sender.
- Resolve contract files only beneath the manifest directory unless explicitly
  installed by the operator.
- Verify every ontology file against its manifest SHA-256 digest.
- Build Functional Syntax through the checked serializer; never concatenate raw
  message fragments.
- Run KM with fixed wall-time, memory, input-size, and concurrency limits.
- Treat timeout, crash, malformed output, and unsupported fragments as
  `indeterminate`, never as successful validation.
- Never execute code or dereference artifacts during semantic validation.
- Keep conflicting scientific claims in separate contribution graphs and test
  selected combinations explicitly.
- Do not treat a logically consistent sender assertion as proof that the
  asserted real-world fact is true.

# Gas City pack: academic-wasteland/rcp

A [Gas City](https://github.com/gastownhall/gascity) pack (pack spec schema 2)
that gives a rig the Research Commons Protocol tooling:

- `agents/rcp-worker`: rig-scoped agent whose prompt encodes the RCP gate rules.
- `formulas/rcp-task.formula.toml`: task workflow whose `gate` and `package`
  steps close only when the exec check scripts confirm validation.
- `commands/rcp/validate`, `commands/rcp/to-bead`: `gc rcp validate`, `gc rcp to-bead`.
- `doctor/rcp-tooling`: warm-up check for `research-commons`, `bd`, `km`, `dolt`.

Import into a city:

```bash
gc import add https://github.com/academic-wasteland/research-commons.git//integrations/gascity/rcp-pack
```

Then add `rcp` to a rig's `imports` in `city.toml`. Set `RCP_MANIFEST` in the
rig environment to the trusted contract manifest.

Status: authored against the pack spec and formula spec v2 in the gascity
repository as of 2026-09-14 and not yet exercised against a running `gc`, which
is a rolling pre-1.0 release. Expect to adjust field names when importing.

Not included: an `exec:` beads provider that would let Gas City use an RCP task
service as its native bead store (`docs/reference/exec-beads-provider.md` in
gascity). That is the natural next step once an RCP node exposes task storage.

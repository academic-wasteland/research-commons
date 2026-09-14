# The Academic Wasteland

**A federated agentic research commons. BioHackathon 2026 project.**

DBCLS BioHackathon 2026, Matsuyama, Japan, 13 to 19 September 2026.

Can independently operated research agents, data resources, analysis services,
and humans discover each other, exchange machine-readable research tasks and
results, and collaborate with explicit provenance, attribution, permissions,
and reproducibility, without a central platform?

This repository is the working space for that question during the hackathon.
Nothing here is decided. The proposal, the prototype code, and the integration
sketches are starting points to argue with, replace, or throw away.

## Where things stand

- `federated_agentic_research_commons_biohackathon_2026.md` is the full
  proposal: motivation, principles, candidate architecture, work packages,
  risks, open questions. Read sections 1, 5, 6, 17, 18, and 24 first.
- `spec/`, `src/`, `examples/` are **one** candidate answer, built before the
  hackathon so there is something concrete to test against: JSON-LD messages
  validated by JSON Schema, SHACL, and an OWL 2 semantic gate, carried over
  A2A. It is a strawman. If the group prefers a different data model,
  transport, or validation stack, the code changes, not the question.
- `integrations/` sketches how the Gas Town ecosystem
  ([gastownhall](https://github.com/gastownhall): beads, wasteland, gascity)
  could serve as scheduling and federation ledgers. The project name nods to
  wasteland's federation model. Whether to build on it is itself open.

## Open questions we want to settle this week

These come from sections 17, 18, and 24 of the proposal. Each is genuinely
open; the prototype takes a position only so there is something to disagree with.

1. **Architecture.** Federated, peer to peer, or hybrid? How much global
   discovery infrastructure before federation turns into centralization?
2. **Unit of exchange.** What is the minimal ResearchRequest, ResearchTask,
   and ResearchContribution? Is a task even the right primitive?
3. **Semantics.** How strongly typed must inputs and outputs be? JSON-LD and
   OWL, plain JSON Schema, or something in between? What happens when two
   nodes use incompatible ontologies?
4. **Transport.** A2A, MCP, ActivityPub-style, plain REST, a shared
   versioned database (Dolt, as wasteland does), or several?
5. **Discovery.** Agent Cards at known URLs, a registry, federated indexes,
   crawling, DNS-like resolution?
6. **Identity and delegation.** How are agents identified, how is "acting on
   behalf of a human" represented, and what does ORCID or ROR anchor?
7. **Validation and trust.** How does a node decide a task may run? How is a
   result independently replicated or challenged? Are reputation signals
   (stamps, trust levels) useful, dangerous, or both?
8. **Provenance and packaging.** PROV, RO-Crate, nanopublications: which, and
   at what granularity?
9. **Attribution and credit.** How do contributions by agents and humans map
   to something researchers can cite or claim?
10. **Governance.** Who owns the specification after the week, and how does
    an independently developed node join using only the spec?
11. **First useful application.** Which biological use case would make a lab
    want to run a node tomorrow?

Add your own as GitHub issues with the label `open-question`.

## How to take part

- **Talk.** Open an issue or a discussion in this repository. Proposals for
  alternative data models, transports, or validation approaches are welcome
  as pull requests to `docs/` or as new directories under `examples/`.
- **Build.** Pick a work package below or define a new one. Independent
  implementations in any language are the point: the success criterion is
  that a node written from the specification alone can interoperate.
- **Break.** Hostile messages, ontology injection, spoofed provenance. The
  threat model in `docs/threat-model.md` is a start; please make it worse.

Coordination: Robert Hoehndorf (robert.hoehndorf@kaust.edu.sa, ORCID
0000-0001-8149-5890) is most available in the afternoons Saudi time this
week (roughly 13:00 to 18:00 UTC+3, which is 19:00 to 24:00 JST). Asynchronous
work through issues and pull requests is fine at any hour.

## Candidate work tracks

Adapted from the proposal's work packages. Reshuffle freely.

| Track | Question it answers | Possible deliverable |
|---|---|---|
| Use cases and requirements | What would a lab actually send? | Three concrete biological scenarios as messages |
| Research object model | What is the minimal request, task, contribution, claim, evidence? | Revised or replaced `spec/` |
| Protocol mapping | Which existing standards do we reuse? | Profile over A2A, MCP, PROV, RO-Crate, or an alternative |
| Reference node | Can someone run a node in minutes? | Small free-software server, any language |
| Capability discovery | How does a node say what it can do? | Agent Card extension or an alternative |
| Workflow adapter | Can a task reach Galaxy, CWL, Nextflow, Slurm? | One working adapter |
| Provenance and packaging | Can a distributed interaction be packaged reproducibly? | RO-Crate from a multi-node run |
| Independent validation | Can node B replicate or challenge node A's result? | Replication and critique messages end to end |
| Identity, policy, security | Who is allowed to do what? | Threat model, delegation representation, prototype |
| Orchestration ledgers | Do beads, wasteland, or gascity help or hurt? | Verdict plus working or discarded `integrations/` |
| Governance and adoption | What happens on 20 September? | One-page governance proposal |

## Success criteria

From the proposal, in increasing order:

- Two independently operated implementations exchange a research task and result.
- Three nodes take part dynamically in one research request.
- The nodes use existing scientific standards for semantic types and provenance.
- A complete distributed interaction is packaged as a reproducible RO-Crate.
- A result from one node is independently replicated or challenged by another
  without bespoke integration.

## Running the prototype

The current strawman is a Python conformance checker.

```bash
uv sync --extra dev
uv run research-commons validate-structure examples/metagenomics/task.jsonld
uv run research-commons validate-shacl examples/metagenomics/task.jsonld
uv run pytest
```

Semantic checks additionally require the
[Kobayashi-MaRust](https://github.com/bio-ontology-research-group/kobayashi-marust)
`km` binary:

```bash
uv run research-commons validate-semantics \
  examples/metagenomics/task.jsonld \
  --manifest examples/contracts/public-research.contract.json \
  --km-bin /path/to/km
```

Projections onto orchestration ledgers:

```bash
uv run research-commons to-bead examples/metagenomics/task.jsonld | bd import -
uv run research-commons to-wanted examples/metagenomics/task.jsonld --posted-by <rig> --sql
```

## Repository layout

```text
federated_agentic_research_commons_biohackathon_2026.md   the proposal
spec/           candidate JSON Schema, SHACL shapes, OWL vocabulary, A2A binding
src/            candidate conformance checker and ledger projections (Python)
examples/       example requests, tasks, contributions, contracts, reports
docs/           architecture, semantic validation, threat model, ADRs,
                Gas Town integration notes
integrations/   beads, wasteland, gascity, bdp sketches
tests/          conformance tests for the candidate implementation
```

Decisions taken so far, and why, are recorded as ADRs in `docs/adr/`. An ADR
can be reversed by a new ADR; that is what they are for.

## License

Code: Apache-2.0 (see `LICENSE`). Proposal text: CC BY 4.0.

# A Federated Agentic Research Commons
## BioHackathon Japan 2026 project proposal

**Working title:** A Federated Agentic Research Commons  
**Short names to discuss:** Research Commons Network, ResearchMesh, ScienceMesh, Open Research Network  
**Event:** DBCLS BioHackathon 2026, Matsuyama, Japan  
**Dates:** 13–19 September 2026  
**Status:** Discussion / hackathon proposal  
**License:** Proposal text: CC0 or CC BY; software developed by the project should use an OSI-approved free-software license.

---

## 1. One-sentence idea

Develop an open, federated protocol and reference implementation through which researchers, research agents, data resources, analysis services, compute systems, and institutions can discover each other, exchange machine-readable research tasks and results, and form temporary collaborations with explicit provenance, attribution, permissions, and reproducibility.

---

## 2. Motivation

Agentic AI systems are likely to become integrated into most research workflows. Researchers will interact not only with software tools but with agents that can:

- search and synthesize literature;
- query databases and knowledge graphs;
- formulate hypotheses;
- perform analyses;
- write and execute workflows;
- interact with institutional data and compute infrastructure;
- evaluate results;
- critique claims;
- request additional evidence;
- communicate with other agents;
- identify relevant human collaborators.

Most current work treats these agents as applications operated by an individual user or organization. A more consequential possibility is that **agents operated by different researchers and institutions communicate directly across an open network**.

The resulting system would not be a single global AI research platform. It would be closer to the Internet or email:

- no central owner;
- open protocols;
- independently operated nodes;
- portable identities;
- local control over data and compute;
- interoperable research objects;
- multiple implementations;
- both human and machine participants.

A researcher should be able to ask a local agent a research question. That agent could discover relevant remote resources, delegate subtasks, execute workflows where the data reside, request independent validation, and bring relevant humans into the collaboration.

The objective of this BioHackathon project is to determine what the minimal protocol and architecture for such a system should be and to implement a small working prototype.

---

## 3. Why BioHackathon Japan?

This problem lies directly at the intersection of several communities represented at BioHackathon:

- biological databases;
- ontologies and semantic web technologies;
- FAIR data;
- RDF and knowledge graphs;
- workflow systems;
- provenance;
- persistent identifiers;
- federated data access;
- APIs and interoperability;
- bioinformatics analysis services;
- research software;
- LLMs and scientific agents.

The 2026 BioHackathon explicitly emphasizes interoperability, standardization, FAIR knowledge graphs, heterogeneous biological and biomedical data, reproducibility, and the integration of LLMs with curated databases and ontologies.

This makes the BioHackathon a good environment to answer the main question:

> **Can we define and demonstrate a minimal open protocol for distributed agentic scientific collaboration using existing standards wherever possible?**

The hackathon should not attempt to solve the entire problem. It should establish whether the idea can be made technically concrete and identify the difficult social, governance, security, and adoption questions.

---

# 4. Vision

Consider the following request:

> "Does inhibition of pathway X plausibly affect phenotype Y, and can this be tested using existing public or accessible data?"

A local research agent could:

1. represent the question as a machine-readable research request;
2. discover relevant literature, datasets, knowledge graphs, software, workflows, compute resources, agents, and researchers;
3. decompose the question into subtasks;
4. advertise or delegate those subtasks to remote nodes;
5. negotiate authentication, permissions, licensing, resource limits, and data-use constraints;
6. send analysis workflows to data that cannot leave an institution;
7. receive structured results and provenance;
8. request an independent replication from another node;
9. ask another agent to critique the methodology or interpretation;
10. aggregate claims, evidence, uncertainty, and disagreements;
11. identify humans whose expertise is relevant;
12. invite those humans into the collaboration;
13. produce a persistent research object describing the entire process.

The collaboration may involve several institutions and last only minutes or hours.

The basic organizational unit could therefore shift from:

> **laboratory -> project -> paper**

towards:

> **question -> dynamically assembled collaboration -> research objects**

Papers may remain useful human-readable summaries, but they would no longer be the only unit through which scientific work is exchanged.

---

# 5. Guiding principles

The network should be designed around the following principles.

## 5.1 Open protocols

The protocol specification must be publicly available and implementable without permission.

## 5.2 Free software

At least one complete reference implementation should be free software.

## 5.3 Federation rather than centralization

Institutions and individuals should be able to operate independent nodes.

No central service should be required for basic operation.

## 5.4 Local control

A node decides:

- which data it exposes;
- which agents it exposes;
- who may use them;
- what computations may execute;
- what results may leave the node;
- what resource limits apply.

## 5.5 FAIR research objects

Questions, tasks, workflows, data, claims, evidence, and results should be as Findable, Accessible, Interoperable, and Reusable as their access restrictions permit.

## 5.6 Machine-readable semantics

Agents should exchange structured objects rather than relying exclusively on natural-language chat.

## 5.7 Provenance by default

Every relevant research result should be traceable to:

- input data;
- software;
- model;
- workflow;
- parameters;
- execution environment;
- agent;
- human;
- institution;
- time;
- dependencies.

## 5.8 Reproducibility and challenge

Replication, criticism, contradiction, and re-analysis should be first-class operations.

## 5.9 Human participation

The network is not intended to remove humans from science.

It should support:

- human-agent collaboration;
- agent-agent collaboration;
- human-human discovery and collaboration.

## 5.10 Pluralism

The system should support multiple:

- models;
- agent frameworks;
- workflow engines;
- databases;
- ontologies;
- programming languages;
- institutions;
- governance models.

No particular AI provider or model should be required.

---

# 6. Non-goals

The initial project is **not** intended to:

- build a universal scientific AI;
- replace peer review;
- replace journals;
- replace existing biological databases;
- create a global centralized data repository;
- define a universal scientific ontology;
- create a cryptocurrency;
- create a universal reputation score;
- require all scientific data to be open;
- require researchers to expose private data;
- standardize every internal agent implementation.

The goal is interoperability between independently operated components.

---

# 7. Conceptual architecture

A research node may expose one or more of the following:

```text
+----------------------------------------------------------+
|                    Research Node                         |
|                                                          |
|  Human interface                                         |
|       |                                                  |
|  Local research agent                                    |
|       |                                                  |
|  ------------------------------------------------------  |
|  Capability registry                                     |
|  Task / collaboration interface                          |
|  Research object store                                   |
|  Provenance store                                        |
|  Identity / authorization                                |
|  Policy engine                                           |
|  ------------------------------------------------------  |
|       |             |             |             |        |
|    Agents          Data        Workflows       Compute    |
|       |             |             |             |        |
|    LLMs          Databases      CWL/WDL/...    HPC/cloud  |
|                  KGs/APIs       Galaxy/...     local      |
+----------------------------------------------------------+

                     open protocol

+----------------------------------------------------------+
|                 Remote Research Node                     |
+----------------------------------------------------------+
```

A node might be operated by:

- an individual researcher;
- a laboratory;
- a university;
- a database provider;
- a hospital;
- a national infrastructure;
- a workflow platform;
- an HPC center;
- a scientific society;
- a software project.

---

# 8. Core components

The following components should be treated as separable layers.

## 8.1 Identity

Need persistent identity for:

- humans;
- organizations;
- agents;
- software;
- datasets;
- workflows;
- computational executions;
- claims.

Possible existing components:

- ORCID for researchers;
- ROR for organizations;
- DOI / DataCite;
- Software Heritage identifiers;
- decentralized identifiers where useful;
- cryptographic keys for node/agent identity.

### Questions

- Is an "agent" a persistent scientific actor or simply software acting on behalf of a human?
- Who is accountable for an agent action?
- Can an agent act under delegated authority from multiple humans?
- How are identities revoked or rotated?
- How do institutional identities interact with individual identities?

---

## 8.2 Node and capability discovery

A node should be able to advertise capabilities such as:

```yaml
node:
  id: https://example.org/research-node
  operator: https://ror.org/...
  capabilities:
    - literature_search
    - sparql_query
    - protein_function_prediction
    - variant_prioritization
    - differential_expression
    - workflow_execution
    - human_expertise
  resources:
    - dataset
    - knowledge_graph
    - compute
    - software
  policies:
    authentication: required
    data_residency: local
```

Discovery could occur through:

- direct URLs;
- registries;
- federated indexes;
- semantic web discovery;
- DNS-like mechanisms;
- ActivityPub-style federation;
- peer discovery.

### Open question

How much global discovery infrastructure is required before federation gradually becomes centralization?

---

## 8.3 Capability description

Natural-language descriptions are insufficient for reliable delegation.

Capabilities may need descriptions of:

- task type;
- expected inputs;
- expected outputs;
- semantic types;
- ontologies used;
- access policy;
- cost;
- expected runtime;
- reliability;
- provenance guarantees;
- supported licenses;
- data restrictions.

Existing ontology and semantic-web communities may be particularly useful here.

---

## 8.4 Agent-to-agent communication

Existing agent communication protocols should be reused where possible rather than inventing another general messaging system.

Candidate technologies include:

- Agent2Agent (A2A);
- MCP for agent-to-tool/resource interaction;
- HTTP/REST;
- JSON-LD;
- RDF;
- ActivityPub;
- message queues where asynchronous execution is necessary.

A key architectural distinction may be:

- **MCP-like interfaces:** agent <-> tool/resource;
- **A2A-like interfaces:** agent <-> agent;
- **research protocol:** semantics of scientific requests, contributions, evidence, and provenance.

The BioHackathon project should determine whether a research-specific semantic layer can sit on top of existing transport/agent protocols.

---

## 8.5 Research Request

A research request should be a first-class object.

Example:

```yaml
type: ResearchRequest
id: urn:uuid:...
created_by: orcid:...
question: >
  Does inhibition of pathway X affect phenotype Y?
context:
  organism: Homo sapiens
  phenotype: HP:...
constraints:
  data:
    public_only: true
  compute:
    max_cpu_hours: 100
expected_outputs:
  - evidence_graph
  - analysis_report
  - executable_workflow
```

Possible fields:

- question;
- hypothesis;
- scope;
- background knowledge;
- assumptions;
- constraints;
- available resources;
- required evidence;
- requested confidence;
- deadline;
- budget/resource limits;
- licensing requirements;
- privacy constraints.

---

## 8.6 Research Task

Agents should be able to decompose requests into structured tasks.

```yaml
type: ResearchTask
task_type: differential_expression
inputs:
  dataset: doi:...
  case_group: ...
  control_group: ...
requirements:
  normalization: ...
expected_output:
  format: parquet
  semantics: ...
validation:
  independent_replication: preferred
```

Tasks should support:

- delegation;
- cancellation;
- progress;
- failure;
- partial results;
- dependency graphs;
- alternative methods;
- bids/offers;
- resource negotiation.

---

## 8.7 Research Contribution

A contribution is anything returned to the research network.

Possible types include:

- hypothesis;
- claim;
- evidence;
- dataset;
- annotation;
- analysis;
- workflow;
- software;
- critique;
- replication;
- negative result;
- experimental measurement;
- interpretation.

Example:

```yaml
type: ResearchContribution
contribution_type: analysis
addresses: urn:uuid:research-task
produced_by:
  agent: ...
  delegated_by: orcid:...
inputs:
  - doi:...
method:
  workflow: ...
outputs:
  - artifact: ...
claims:
  - ...
provenance: ...
license: ...
```

---

## 8.8 Research objects

Research activity should be packaged into persistent machine-readable research objects.

RO-Crate is a strong candidate for the packaging layer.

A research object may contain:

- question;
- hypotheses;
- task graph;
- input datasets;
- workflow definitions;
- source code;
- parameters;
- execution logs;
- results;
- claims;
- evidence;
- critiques;
- replications;
- people and agents;
- licenses;
- provenance.

The hackathon should investigate whether a profile of RO-Crate can represent an agentic collaboration.

Possible output:

> **Agentic Research RO-Crate Profile**

---

## 8.9 Claims and evidence

Agents should not merely exchange prose conclusions.

A claim should ideally connect explicitly to evidence.

```text
Claim
  |
  +-- supported_by --> AnalysisResult
  |
  +-- derived_from --> Dataset
  |
  +-- produced_by --> WorkflowExecution
  |
  +-- contradicted_by --> Claim
  |
  +-- replicated_by --> Replication
```

Nanopublications may provide a useful model:

- assertion;
- provenance;
- publication information.

The network should permit multiple conflicting claims to coexist.

It should not require a central authority to decide which claim is "true."

---

## 8.10 Provenance

Potential foundation:

- W3C PROV;
- PROV-O;
- RO-Crate provenance;
- workflow provenance standards;
- cryptographic signatures.

Important provenance includes:

### Data provenance

Where did the data originate?

### Computational provenance

Which code, environment, parameters, and hardware produced the result?

### Model provenance

Which model generated or interpreted something?

For LLMs this may include:

- provider/model;
- model version;
- system configuration where disclosure is possible;
- tools available;
- retrieval sources;
- relevant prompts or structured inputs;
- temperature/sampling parameters where relevant.

### Delegation provenance

Who asked whom to perform the task?

### Human provenance

Which steps were approved, edited, interpreted, or rejected by humans?

---

## 8.11 Workflow execution

The network should not invent another workflow language.

Instead, nodes should expose existing workflow engines.

Candidates include:

- CWL;
- WDL;
- Nextflow;
- Snakemake;
- Galaxy;
- containerized command-line tools;
- notebook environments;
- workflow execution APIs.

A remote agent could request execution without needing to understand the local scheduler.

```text
Research Agent
      |
      | ResearchTask
      v
Remote Node
      |
      +--> Policy check
      |
      +--> Workflow adapter
      |
      +--> Galaxy / Slurm / Kubernetes / local executor
      |
      +--> Result + provenance
```

---

## 8.12 Data access and data locality

"Open research" cannot imply that all data are publicly downloadable.

The architecture must support:

- open data;
- embargoed data;
- institutional data;
- controlled-access genomic data;
- clinical data;
- commercial datasets;
- data that legally cannot leave a jurisdiction.

Therefore:

> **Move computation to data when data cannot move to computation.**

Useful precedents include GA4GH federated analysis.

The task protocol should permit:

- remote execution;
- disclosure controls;
- aggregation restrictions;
- output review;
- trusted execution environments;
- secure enclaves where appropriate.

---

## 8.13 Authorization and delegation

Agents will often act on behalf of humans.

The system needs explicit delegated authority.

Examples:

> Agent A may query public resources without approval.

> Agent A may spend up to 10 CPU-hours without approval.

> Agent A must ask before sending controlled data.

> Agent A may contact external researchers but may not share unpublished results.

Potential technologies:

- OAuth/OIDC;
- capability-based authorization;
- scoped tokens;
- signed delegation statements.

---

## 8.14 Policy engine

Each node needs machine-readable policies.

Policies may describe:

- permitted users;
- permitted institutions;
- permitted task types;
- data-use restrictions;
- licensing constraints;
- compute quotas;
- rate limits;
- human approval requirements;
- geographic restrictions;
- publication constraints.

Policy interoperability may become one of the hardest parts of the system.

---

## 8.15 Human collaboration layer

The network should route people to people, not only agents to agents.

A useful response could be:

> Three researchers are independently investigating related questions and have opted into collaboration discovery.

Functions might include:

- expertise discovery;
- collaborator discovery;
- collaboration invitations;
- discussion threads linked to research objects;
- human approval queues;
- attribution negotiation;
- conflict resolution.

Privacy must be considered carefully. Researchers should control whether they are discoverable.

---

## 8.16 Attribution and credit

Traditional authorship is too coarse for highly distributed research.

The network could represent a contribution graph:

```text
Person A
   |
   +-- proposed --> Hypothesis H
                        |
                        +-- tested_by --> Agent B
                                             |
                                             +-- used --> Dataset D
                                             |
                                             +-- produced --> Result R
                                                                  |
Person C ------------------------------------------------ replicated
                                                                  |
Person D ------------------------------------------------ challenged
```

Possible contribution categories:

- conceptualization;
- hypothesis;
- data;
- software;
- methodology;
- execution;
- validation;
- interpretation;
- critique;
- curation;
- supervision;
- compute/resource provision.

CRediT taxonomy may provide a useful starting point but probably needs extension for agents.

Important question:

> Can an AI agent receive credit, or should credit always flow to accountable humans/organizations?

---

## 8.17 Reputation and trust

A naive global reputation score would create serious problems.

Possible alternatives:

### Evidence-based trust

Trust results because they are reproducible.

### Contextual reputation

A node may be reliable for one task type and poor for another.

### Web-of-trust

Researchers/institutions decide whose assertions they trust.

### Verifiable history

Agents expose prior task outcomes.

### Independent validation

Important claims are re-executed by independent nodes.

The architecture should avoid requiring a universal ranking of researchers.

---

## 8.18 Replication as a protocol operation

Replication should be exceptionally easy.

```yaml
type: ReplicationRequest
target: urn:uuid:result
requirements:
  independent_node: true
  alternative_implementation: preferred
```

This could enable a powerful change in scientific practice:

> **Replication becomes a machine-actionable network operation instead of a separate research project.**

Agents could automatically request replication when:

- a result is surprising;
- confidence is low;
- a claim is highly consequential;
- reviewers request confirmation;
- multiple methods disagree.

---

## 8.19 Critique and adversarial agents

The network should permit specialized agents whose role is to attack results.

Examples:

- statistical reviewer;
- ontology consistency checker;
- literature contradiction finder;
- reproducibility checker;
- methodological reviewer;
- hallucination/evidence checker;
- data-leakage detector.

These agents should produce structured critiques, not merely prose.

---

## 8.20 Negative results and failed attempts

Agents may perform huge numbers of analyses.

Recording failures can prevent repeated waste.

Possible contribution types:

```text
UnsupportedHypothesis
FailedWorkflow
NegativeResult
NonReplication
InconclusiveResult
```

However, storing every failed attempt could produce enormous noise.

Policies for significance and retention will be needed.

---

# 9. Relation to existing standards and infrastructure

One goal of the hackathon should be to identify **what already exists** and avoid unnecessary invention.

| Requirement | Candidate technology / standard |
|---|---|
| Researcher identity | ORCID |
| Organization identity | ROR |
| Persistent publications/data | DOI / DataCite |
| Software identity | Software Heritage / SWHID |
| Research packaging | RO-Crate |
| Provenance | W3C PROV |
| Atomic claims | Nanopublications |
| Semantic representation | RDF / JSON-LD |
| Ontologies | OBO ecosystem and domain ontologies |
| Agent-agent communication | A2A |
| Agent-tool communication | MCP |
| Federation/social communication | ActivityPub concepts |
| Workflow representation | CWL / WDL / Nextflow / Galaxy |
| Containers | OCI |
| Biomedical federation | GA4GH |
| Authentication | OAuth2 / OIDC |
| FAIR principles | FAIR / FAIR Digital Objects |
| Contribution taxonomy | CRediT |
| Reproducible execution | containers + workflow provenance |

The initial specification should preferably be a **profile/composition of existing standards**, not a new monolithic standard.

---

# 10. Candidate protocol objects

A minimal vocabulary might contain:

```text
ResearchNode
Agent
Human
Organization
Capability
Resource

ResearchRequest
ResearchTask
TaskOffer
TaskAcceptance
TaskResult

ResearchObject
ResearchContribution
Dataset
Workflow
Execution
Claim
Evidence
Critique
Replication

Policy
Permission
Delegation

Attribution
Contribution
```

Relationships might include:

```text
askedBy
delegatedTo
performedBy
uses
generated
supports
contradicts
replicates
critiques
derivedFrom
attributedTo
requiresPermission
governedBy
```

One hackathon work package should determine whether most of these concepts already exist in suitable ontologies.

---

# 11. Minimal API

A first research node might expose something as small as:

```text
GET  /.well-known/research-node
GET  /capabilities
GET  /resources/{id}

POST /tasks
GET  /tasks/{id}
POST /tasks/{id}/cancel

GET  /objects/{id}
POST /objects

POST /messages
```

Alternative transport implementations could later use A2A or other protocols.

The important artifact is the semantic contract, not the REST API itself.

---

# 12. Example end-to-end BioHackathon demo

A useful demonstration should involve at least **three independently operated nodes**.

## Node A — Question / orchestration

Operated on one participant's laptop.

Capabilities:

- human interface;
- task decomposition;
- orchestration;
- research-object assembly.

## Node B — Knowledge node

Operated independently.

Capabilities:

- SPARQL endpoint;
- biological ontology;
- literature or knowledge graph query;
- evidence retrieval.

## Node C — Analysis node

Operated independently.

Capabilities:

- example dataset;
- workflow execution;
- result generation;
- provenance.

Optional:

## Node D — Validation node

Runs an independent method or reproducibility check.

### Example sequence

```text
Human
  |
  v
Node A: ResearchRequest
  |
  +------------ discover ------------+
  |                                  |
  v                                  v
Node B                             Node C
knowledge                         analysis
  |                                  |
  +---------- contributions ----------+
                  |
                  v
               Node A
                  |
                  +------> Node D
                           replication
                              |
                              v
                      ReplicationResult
                              |
                              v
                    Research RO-Crate
```

The final object should allow a third party to determine:

- what question was asked;
- what tasks were delegated;
- which nodes participated;
- what data were used;
- what code was executed;
- what claims were produced;
- what evidence supports them;
- whether replication succeeded;
- who/what contributed.

---

# 13. Suggested biological demonstrators

The scientific question should be simple enough that infrastructure, rather than domain complexity, remains the focus.

Possible demonstrations:

## 13.1 Gene–phenotype question

> Find evidence connecting a gene to a phenotype, query relevant KGs and databases, run an analysis, and assemble a provenance-preserving evidence object.

## 13.2 Protein function

> Predict a function for a protein using one remote computational service and compare it against ontology/annotation resources hosted by another node.

## 13.3 Variant interpretation

> Given a variant and phenotype profile, query distributed annotation resources and produce structured supporting and contradicting evidence.

## 13.4 Differential expression

> Ask whether a gene/pathway differs between two conditions in a public dataset; execute the workflow remotely and independently validate the result.

## 13.5 Knowledge-graph consistency

> Generate a candidate biological claim and ask separate ontology/knowledge-graph agents to support, contradict, or qualify it.

---

# 14. Hackathon work packages

Several groups can work in parallel.

## WP1 — Use cases and requirements

Deliverables:

- 3–5 concrete scientific use cases;
- minimum requirements;
- threat/abuse cases;
- explicit non-goals.

People needed:

- bench/computational scientists;
- database providers;
- agent developers.

---

## WP2 — Research object model

Define:

- ResearchRequest;
- ResearchTask;
- ResearchContribution;
- Claim/Evidence;
- Replication;
- Critique;
- Attribution.

Deliverables:

- JSON Schema and/or SHACL;
- JSON-LD context;
- RDF vocabulary/profile;
- example objects.

People needed:

- RDF/ontology experts;
- FAIR/RO-Crate experts;
- provenance experts.

---

## WP3 — Protocol mapping

Determine what should be reused from:

- A2A;
- MCP;
- HTTP;
- ActivityPub;
- GA4GH;
- existing workflow APIs.

Deliverable:

- minimal protocol specification;
- architecture decision record explaining reuse vs new components.

---

## WP4 — Node reference implementation

Implement a small free-software server.

Possible stack:

```text
Python
FastAPI
JSON-LD
RDFLib
RO-Crate
A2A adapter
MCP adapter
Docker
```

Deliverable:

```bash
docker run research-node
```

A participant should be able to run a node locally in minutes.

---

## WP5 — Capability discovery

Implement:

- node metadata;
- capability advertisement;
- resource description;
- simple federated discovery.

Deliverable:

```bash
research discover "protein function prediction"
```

---

## WP6 — Workflow adapter

Connect one node to a real analysis environment.

Candidates:

- Galaxy;
- CWL runner;
- Nextflow;
- Snakemake;
- local Docker;
- Slurm.

Deliverable:

structured task -> workflow execution -> structured result + provenance.

---

## WP7 — Provenance and research-object packaging

Generate a research object automatically from the distributed execution.

Deliverable:

```text
research-object.crate.zip
```

containing machine-readable provenance.

---

## WP8 — Independent replication

Implement:

```text
Result -> ReplicationRequest -> independent node -> ReplicationResult
```

Deliverable:

a demonstration in which two nodes independently execute or evaluate the same claim.

---

## WP9 — Identity, policy, and security prototype

Implement minimal:

- node identity;
- agent identity;
- signed messages or tokens;
- delegation;
- access control.

Deliverable:

one task that is rejected by policy and one that is accepted.

---

## WP10 — Human collaboration and attribution

Represent human involvement and contribution.

Deliverables:

- contribution graph;
- attribution metadata;
- optional ORCID integration;
- proposal for agent attribution.

---

## WP11 — Governance and adoption

This is as important as implementation.

Produce a short governance/adoption document covering:

- ownership;
- stewardship;
- protocol evolution;
- conformance tests;
- security disclosure;
- community decision-making;
- sustainability;
- institutional adoption.

---

# 15. Concrete BioHackathon deliverables

A successful week does **not** require production infrastructure.

Minimum useful outputs:

1. **Architecture document**
2. **Minimal terminology / object model**
3. **JSON-LD/RDF representation**
4. **ResearchRequest schema**
5. **ResearchContribution schema**
6. **Research-node capability description**
7. **Minimal protocol**
8. **Free-software reference node**
9. **Three-node federated demonstration**
10. **RO-Crate/provenance output**
11. **Replication demonstration**
12. **Threat model**
13. **Open-questions document**
14. **Adoption/governance roadmap**

Stretch outputs:

15. A2A interoperability
16. MCP resource/tool adapters
17. Galaxy adapter
18. ORCID identity integration
19. nanopublication export
20. GA4GH-compatible controlled-data example
21. public node registry
22. conformance tests

---

# 16. Success criteria for the hackathon

The project should be considered successful if:

### Minimum

Two independently operated implementations can exchange a research task and result.

### Good

Three nodes can dynamically participate in one research request.

### Better

The nodes use existing scientific standards for semantic types and provenance.

### Strong

A complete distributed interaction is packaged as a reproducible RO-Crate.

### Very strong

A result produced by one node can be independently replicated or challenged by another node without bespoke integration.

The main success criterion is therefore:

> **Can an independently developed research node join the network using only the specification?**

---

# 17. Open technical questions

## Protocol boundary

- What belongs in the scientific protocol versus A2A/MCP?
- Should transport be standardized or left implementation-specific?
- Synchronous vs asynchronous tasks?
- Streaming results?

## Semantics

- How strongly typed must inputs and outputs be?
- RDF/JSON-LD versus simpler JSON schemas?
- How are ontology mappings negotiated?
- What happens when nodes use incompatible ontologies?

## Discovery

- Central registry?
- Federated registry?
- DNS-like discovery?
- Search engine over public capability descriptions?
- DHT?
- Web crawling?

## Identity

- Who signs results?
- Human, institution, agent, or all three?
- How are transient agents represented?
- How is compromised identity revoked?

## Execution

- How are resource requirements represented?
- How are long-running jobs handled?
- How are failed jobs represented?
- How are software/environment versions frozen?

## Data

- How are controlled-access datasets advertised without revealing sensitive information?
- How are usage restrictions represented?
- How do agents prove compliance with data-use agreements?

## Provenance

- How much agent reasoning/provenance should be stored?
- Full interaction log versus minimal reproducibility record?
- How are proprietary model calls represented?
- How are nondeterministic model outputs reproduced?

## Claims

- What constitutes a scientific claim?
- How granular should claims be?
- How is uncertainty represented?
- How are contradictions represented?
- Can a claim be withdrawn?

## Replication

- What counts as independent replication?
- Same workflow/different executor?
- Same data/different method?
- Different data/same hypothesis?
- Who requests replication and who pays for it?

---

# 18. Open social and governance questions

## Accountability

If an agent generates a false analysis that is propagated through the network:

- who is responsible?
- the researcher?
- node operator?
- model provider?
- software developer?
- institution?

This is likely context-dependent and cannot be solved entirely at protocol level.

---

## Scientific authority

The network must not create an implicit central authority over scientific truth.

Prefer:

- transparent evidence;
- provenance;
- reproducibility;
- multiple competing analyses.

Avoid:

- global "truth score";
- universal researcher ranking;
- opaque agent ranking.

---

## Human autonomy

Agents should not silently:

- publish results;
- disclose unpublished hypotheses;
- share restricted data;
- contact external parties;
- spend substantial resources.

Delegation boundaries need to be explicit.

---

## Governance of the protocol

Questions:

- Who owns the specification?
- Foundation?
- W3C community group?
- Research Data Alliance?
- GA4GH?
- independent consortium?
- BioHackathon community?

Desirable properties:

- open membership;
- public specifications;
- transparent decisions;
- multiple implementations;
- no vendor control.

---

## Sustainability

Free software does not imply zero cost.

Costs include:

- compute;
- storage;
- bandwidth;
- security;
- curation;
- maintenance;
- identity infrastructure.

Possible sustainable operators:

- universities;
- national research infrastructure;
- funders;
- libraries;
- database providers;
- learned societies;
- nonprofit foundations.

Commercial nodes could participate without controlling the protocol.

---

# 19. Adoption blockers

The largest blockers may be social rather than technical.

## 19.1 No incentive to expose resources

Why should a group expose:

- compute;
- datasets;
- agents;
- expertise;
- workflows?

Possible incentives:

- attribution;
- citations;
- contribution records;
- reciprocal access;
- institutional metrics;
- grant recognition;
- increased reuse/visibility.

---

## 19.2 Fear of being scooped

Researchers may not want agents advertising:

- hypotheses;
- current work;
- unpublished datasets;
- expertise indicating current research direction.

Required:

- private nodes;
- trusted federation groups;
- selective disclosure;
- embargoes;
- invitation-only collaboration.

---

## 19.3 Credit

If a remote node performs an essential analysis:

- is its operator an author?
- should software authors receive credit?
- does the agent receive credit?
- how are hundreds of small contributions represented?

Traditional authorship cannot scale to this model.

---

## 19.4 Institutional restrictions

Universities may restrict:

- external AI systems;
- external compute;
- data transfer;
- automated contracting;
- clinical data access.

Institutional policy adapters may be necessary.

---

## 19.5 Reliability

Researchers will not use a network dominated by unreliable agents.

Trust will require:

- provenance;
- conformance testing;
- reproducibility;
- validation;
- reputation scoped to capabilities.

---

## 19.6 Complexity

If joining requires expertise in:

- RDF;
- OAuth;
- A2A;
- MCP;
- RO-Crate;
- containers;
- workflow systems;

adoption will fail.

Target:

```bash
pip install research-node
research-node init
research-node serve
```

or:

```bash
docker compose up
```

---

## 19.7 Network effects

A research network is not useful when nobody else participates.

Bootstrapping should therefore focus on existing communities with interoperable resources.

Bioinformatics is a strong initial domain because it already has:

- public databases;
- APIs;
- ontologies;
- workflows;
- FAIR standards;
- distributed infrastructure;
- open-source culture.

---

# 20. Major system-level risks

## 20.1 Scientific spam

Agents can generate hypotheses, analyses, and papers at near-zero marginal cost.

The network could become flooded with low-value output.

Possible defenses:

- computational cost budgets;
- rate limits;
- evidence requirements;
- replication;
- trust filters;
- local acceptance policies;
- separation of generated hypotheses from validated claims.

---

## 20.2 Hallucinated evidence

An agent may fabricate:

- references;
- data;
- analyses;
- provenance.

Structured evidence must be resolvable and independently checkable.

---

## 20.3 Malicious nodes

Nodes might intentionally return false results.

Mitigations:

- signatures;
- independent validation;
- sandboxing;
- reputation;
- policy controls.

---

## 20.4 Prompt injection and hostile research objects

Research objects may contain malicious text/data intended to control remote agents.

Treat remote content as untrusted input.

Need:

- sandboxing;
- content separation;
- permission boundaries;
- explicit trust models.

---

## 20.5 Supply-chain attacks

Remote workflows may contain malicious code.

Need:

- signed containers;
- reproducible builds where feasible;
- sandbox execution;
- allowlists;
- software provenance.

---

## 20.6 Resource abuse

Agents could consume large amounts of compute.

Need:

- quotas;
- cost estimates;
- authorization;
- cancellation;
- budgets.

---

## 20.7 Privacy leakage

Agents may infer protected information even when raw data are not returned.

Federated execution alone does not guarantee privacy.

---

## 20.8 Monopolization

A nominally open standard could become dependent on:

- one model provider;
- one registry;
- one identity provider;
- one cloud;
- one implementation.

Protocol design should explicitly resist this.

---

# 21. Adoption strategy

A realistic path may be:

## Phase 1 — Bioinformatics developers

Target people already operating:

- databases;
- SPARQL endpoints;
- ontologies;
- workflow services;
- analysis tools.

Value proposition:

> Make your existing resource agent-discoverable and agent-callable.

---

## Phase 2 — Research laboratories

Provide a local node that connects:

- lab agents;
- local files/data;
- institutional HPC;
- public research network.

Value proposition:

> Your research agent can use resources exposed by other labs without custom integrations.

---

## Phase 3 — Research infrastructure

Integrate:

- ELIXIR;
- EOSC;
- national compute infrastructure;
- institutional repositories;
- biological databases;
- hospital/federated research infrastructure.

---

## Phase 4 — Broader disciplines

The protocol should ultimately be domain-independent, but biology is an appropriate starting point.

---

# 22. The "killer feature"

The network probably needs an immediate benefit before the full vision is useful.

Candidates:

## A. Universal research capability discovery

> "Find an available service that can perform X."

## B. One research task, many implementations

Submit the same task to several independent tools/agents.

## C. Automatic provenance

Every distributed analysis automatically produces a FAIR research object.

## D. Automatic replication

One command:

```bash
research replicate <result-id>
```

## E. Human collaborator discovery

> "Who is currently willing and able to help with this question?"

The BioHackathon should identify which of these produces enough immediate value to motivate early adoption.

---

# 23. Questions specifically for BioHackathon participants

The following questions could be discussed early in the week.

### Semantic web / ontology community

- Which concepts already exist?
- Should we define a small ontology or an application profile?
- Can SHACL provide conformance validation?

### RO-Crate / FAIR community

- Can agentic collaborations be represented cleanly as RO-Crates?
- What profile extensions are necessary?

### Workflow community

- What is the minimum interoperable task description?
- Can workflow execution APIs be normalized?

### Database providers

- What information would you be willing to expose through a research node?
- What would prevent you from operating one?

### GA4GH / controlled-data experts

- How should data-local execution and authorization be represented?
- Which existing GA4GH standards should be reused?

### Agent developers

- Can the research semantics be layered over A2A/MCP?
- Which information do agents actually need for reliable delegation?

### Researchers

- What would make you trust a remote analysis?
- What would make you contribute compute/data/expertise?
- Which actions must always require human approval?

### Infrastructure operators

- What are the security blockers?
- What deployment model would be acceptable institutionally?

---

# 24. Decisions the hackathon should try to make

By the end of the week, aim to answer:

1. **Is the architecture federated, P2P, or hybrid?**
2. **What is the minimal unit of exchange?**
3. **What is the minimal ResearchRequest?**
4. **What is the minimal ResearchContribution?**
5. **How are claims linked to evidence?**
6. **How is provenance represented?**
7. **How are agents identified?**
8. **How is human delegation represented?**
9. **How are capabilities advertised?**
10. **Which existing protocols are reused?**
11. **How does a node join the network?**
12. **How is a result independently validated?**
13. **How is attribution represented?**
14. **What is the governance model?**
15. **What is the first immediately useful application?**

---

# 25. Suggested schedule during the BioHackathon

## Day 1 — Scope

- refine use cases;
- identify existing standards;
- agree on principles/non-goals;
- define minimal architecture;
- assign work packages.

## Day 2 — Data model

- ResearchRequest;
- ResearchTask;
- ResearchContribution;
- provenance;
- JSON-LD/RDF schemas;
- examples.

## Day 3 — Nodes

- implement reference node;
- capability discovery;
- task submission;
- workflow adapter.

## Day 4 — Federation

- connect independently operated nodes;
- test authentication;
- test failures;
- generate provenance.

## Day 5 — Validation

- add replication;
- add critique;
- create RO-Crate;
- test interoperability.

## Day 6 — Hardening / documentation

- threat model;
- adoption blockers;
- conformance tests;
- documentation;
- governance proposal.

## Final wrap-up

Demonstrate:

```text
question
  -> discovery
  -> distributed task execution
  -> structured evidence
  -> independent validation
  -> reproducible research object
```

---

# 26. Repository structure

Possible initial repository:

```text
research-commons/
├── README.md
├── LICENSE
├── GOVERNANCE.md
├── CONTRIBUTING.md
├── docs/
│   ├── architecture.md
│   ├── use-cases.md
│   ├── threat-model.md
│   ├── adoption.md
│   └── open-questions.md
├── spec/
│   ├── protocol.md
│   ├── vocabulary.ttl
│   ├── context.jsonld
│   ├── research-request.schema.json
│   ├── research-task.schema.json
│   └── research-contribution.schema.json
├── examples/
│   ├── gene-phenotype/
│   ├── protein-function/
│   └── differential-expression/
├── node/
│   └── reference implementation
├── adapters/
│   ├── a2a/
│   ├── mcp/
│   ├── galaxy/
│   └── sparql/
└── tests/
    └── conformance/
```

---

# 27. Minimal prototype milestone

A particularly useful initial milestone would be:

```text
$ research ask \
  "Find evidence that gene X is associated with phenotype Y"

Discovering capabilities...

Node B:
  knowledge-graph-query

Node C:
  literature-evidence

Node D:
  analysis-service

Delegating tasks...

3 contributions received.

Requesting independent validation...

Research object created:
  urn:uuid:...

Claims:
  C1 supported by B,C
  C2 contradicted by D

Provenance:
  complete

Attribution:
  4 nodes
  3 agents
  2 humans
```

Whether an LLM is used internally by any particular node is irrelevant to the protocol.

That separation is important.

---

# 28. Longer-term possibilities

If the basic network succeeds, it could support much more ambitious functions.

## Autonomous scientific markets without mandatory money

Agents advertise available tasks and capabilities.

Contributions may be exchanged based on:

- reciprocity;
- reputation;
- institutional agreements;
- compute credits;
- funding;
- direct payment.

The protocol should not require a particular economic model.

## Distributed scientific observatories

Agents continuously integrate:

- publications;
- datasets;
- experimental results;
- surveillance data.

Research questions could remain "live" and update as evidence changes.

## Continuous systematic reviews

A systematic review becomes a persistent computational object rather than a static paper.

## Machine-actionable peer review

Claims can be automatically routed to:

- statistical agents;
- ontology agents;
- domain experts;
- replication services.

## Dynamic research teams

Collaborations form around tasks rather than organizational boundaries.

## Scientific knowledge graph of provenance

The network itself becomes a graph connecting:

```text
questions
hypotheses
claims
evidence
datasets
software
executions
agents
people
institutions
replications
contradictions
```

This could be substantially more useful to machines than a literature corpus consisting primarily of PDFs.

---

# 29. Fundamental research questions

The project also raises scientific questions about science itself.

- What is the correct computational unit of scientific contribution?
- What does "independent replication" mean for agentic research?
- How should uncertainty propagate across distributed agent workflows?
- How should trust propagate through provenance graphs?
- How should contradictory evidence be represented?
- Can credit be derived from contribution graphs?
- How should AI-generated hypotheses be filtered?
- How much automation improves science before automation begins amplifying noise?
- What parts of scientific collaboration depend fundamentally on human social relationships?
- Can open federation compete with vertically integrated proprietary research-agent platforms?

These may ultimately be as interesting as the infrastructure itself.

---

# 30. Primary blockers

The project should explicitly test the following blockers rather than assuming they can be solved.

### Technical

- interoperability;
- semantic typing;
- provenance;
- authentication;
- policy representation;
- reproducibility;
- agent security;
- controlled-data execution.

### Scientific

- reliability;
- hallucination;
- uncertainty;
- validation;
- replication;
- scientific spam.

### Social

- trust;
- credit;
- fear of being scooped;
- willingness to share;
- collaboration norms;
- researcher autonomy.

### Institutional

- data governance;
- cybersecurity;
- procurement;
- liability;
- clinical regulation;
- IP policies.

### Economic

- compute cost;
- maintenance;
- infrastructure funding;
- unequal access to resources.

### Governance

- protocol ownership;
- versioning;
- conformance;
- dispute resolution;
- avoiding capture by individual vendors.

---

# 31. What would falsify the idea?

It is useful to identify conditions under which the proposal would not work.

The approach may fail if:

1. scientific tasks cannot be described with enough structure for independent agents to exchange them reliably;
2. provenance cannot compensate for low agent reliability;
3. institutional policies make meaningful federation impossible;
4. researchers have insufficient incentive to expose capabilities or resources;
5. the network produces much more scientific noise than useful evidence;
6. credit systems cannot accommodate distributed micro-contributions;
7. security risks make automated cross-institutional execution unacceptable;
8. proprietary integrated platforms are sufficiently convenient that open federation cannot obtain network effects.

The BioHackathon prototype can begin testing items 1, 2, and 7 directly.

Participant discussions can substantially clarify 3, 4, 6, and 8.

---

# 32. Immediate questions for the kickoff discussion

1. Does the network need a new protocol at all, or only profiles of existing protocols?
2. What should be the smallest interoperable research object?
3. Can RO-Crate + PROV + nanopublications represent the required semantics?
4. Can A2A provide the agent communication layer?
5. Can MCP provide local resource/tool access?
6. What should a node advertise?
7. How does an agent express a scientific task without natural-language ambiguity?
8. How do we represent human delegation and approval?
9. How do we represent conflicting results?
10. How do we make independent replication a first-class operation?
11. What is the smallest demo that would convince us this idea is useful?
12. What would make a database/resource provider actually deploy a node?
13. What would make a researcher trust and use a remote node?
14. What should remain deliberately unspecified?

---

# 33. Proposed outcome

The desired outcome is **not another AI application**.

It is the beginning of an open interoperability layer for research.

A useful analogy is:

```text
Web:
  HTTP + URLs + HTML
       ->
  independently operated information systems

Email:
  SMTP + DNS + addresses
       ->
  independently operated communication systems

Agentic research:
  identity + discovery + research objects +
  delegation + provenance + validation
       ->
  independently operated research systems
```

The central design question for the BioHackathon is:

> **What is the smallest set of open conventions that allows independently developed research agents and scientific resources to collaborate?**

If that set can be identified and demonstrated by multiple nodes during the BioHackathon, the project would provide a concrete foundation for a much larger open research ecosystem.

---

# 34. Initial reference points

These are starting points rather than fixed dependencies.

- DBCLS BioHackathon 2026: https://2026.biohackathon.org/
- Agent2Agent protocol: https://a2a-protocol.org/
- Model Context Protocol: https://modelcontextprotocol.io/
- RO-Crate: https://www.researchobject.org/ro-crate/
- W3C PROV: https://www.w3.org/TR/prov-overview/
- Nanopublications: https://nanopub.net/
- ORCID: https://orcid.org/
- ROR: https://ror.org/
- Software Heritage: https://www.softwareheritage.org/
- GA4GH: https://www.ga4gh.org/
- Common Workflow Language: https://www.commonwl.org/
- Galaxy: https://galaxyproject.org/
- FAIR Principles: https://www.go-fair.org/fair-principles/
- CRediT taxonomy: https://credit.niso.org/

---

# 35. Working principle for the hackathon

**Reuse standards. Keep the protocol small. Build several independent nodes. Make provenance unavoidable. Make replication easy. Keep humans in control.**

The most valuable outcome may be discovering which parts do *not* need to be invented.

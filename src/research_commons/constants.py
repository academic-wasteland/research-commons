from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
SPEC_ROOT = REPOSITORY_ROOT / "spec"

RCP = "https://w3id.org/research-commons/v0.1/"
CONTEXT_IRI = f"{RCP}context.jsonld"

COMPACT_IRIS = {
    "ResearchRequest": f"{RCP}ResearchRequest",
    "ResearchTask": f"{RCP}ResearchTask",
    "ResearchContribution": f"{RCP}ResearchContribution",
    "Claim": f"{RCP}Claim",
    "Evidence": f"{RCP}Evidence",
    "Critique": f"{RCP}Critique",
    "ReplicationRequest": f"{RCP}ReplicationRequest",
    "ReplicationResult": f"{RCP}ReplicationResult",
    "Person": f"{RCP}Person",
    "Organization": f"{RCP}Organization",
    "Agent": f"{RCP}Agent",
    "PublicDataset": f"{RCP}PublicDataset",
    "RestrictedDataset": f"{RCP}RestrictedDataset",
    "ResearchArtifact": f"{RCP}ResearchArtifact",
}

OBJECT_PROPERTIES = {
    "partOfRequest": f"{RCP}partOfRequest",
    "requestedBy": f"{RCP}requestedBy",
    "onBehalfOf": f"{RCP}onBehalfOf",
    "producedBy": f"{RCP}producedBy",
    "addresses": f"{RCP}addresses",
    "usesDataset": f"{RCP}usesDataset",
    "hasOutput": f"{RCP}hasOutput",
    "hasClaim": f"{RCP}hasClaim",
    "hasEvidence": f"{RCP}hasEvidence",
    "supports": f"{RCP}supports",
    "contradicts": f"{RCP}contradicts",
    "replicates": f"{RCP}replicates",
    "critiques": f"{RCP}critiques",
}

RO_CRATE_BASE_CONTEXT = {
    "@version": 1.1,
    "schema": "https://schema.org/",
    "Dataset": "schema:Dataset",
    "File": "schema:MediaObject",
    "CreateAction": "schema:CreateAction",
    "SoftwareApplication": "schema:SoftwareApplication",
    "Person": "schema:Person",
    "Organization": "schema:Organization",
    "CreativeWork": "schema:CreativeWork",
    "hasPart": {"@id": "schema:hasPart", "@type": "@id"},
    "instrument": {"@id": "schema:instrument", "@type": "@id"},
    "agent": {"@id": "schema:agent", "@type": "@id"},
    "mentions": {"@id": "schema:mentions", "@type": "@id"},
    "about": {"@id": "schema:about", "@type": "@id"},
    "conformsTo": {"@id": "http://purl.org/dc/terms/conformsTo", "@type": "@id"},
    "name": "schema:name",
    "description": "schema:description",
    "encodingFormat": "schema:encodingFormat",
    "object": {"@id": "schema:object", "@type": "@id"},
    "result": {"@id": "schema:result", "@type": "@id"},
}


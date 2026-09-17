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
    "schema": "http://schema.org/",
    "Dataset": "http://schema.org/Dataset",
    "File": "http://schema.org/MediaObject",
    "CreateAction": "http://schema.org/CreateAction",
    "SoftwareApplication": "http://schema.org/SoftwareApplication",
    "Person": "http://schema.org/Person",
    "Organization": "http://schema.org/Organization",
    "CreativeWork": "http://schema.org/CreativeWork",
    "hasPart": {"@id": "http://schema.org/hasPart", "@type": "@id"},
    "instrument": {"@id": "http://schema.org/instrument", "@type": "@id"},
    "agent": {"@id": "http://schema.org/agent", "@type": "@id"},
    "mentions": {"@id": "http://schema.org/mentions", "@type": "@id"},
    "about": {"@id": "http://schema.org/about", "@type": "@id"},
    "conformsTo": {"@id": "http://purl.org/dc/terms/conformsTo", "@type": "@id"},
    "name": "http://schema.org/name",
    "description": "http://schema.org/description",
    "encodingFormat": "http://schema.org/encodingFormat",
    "object": {"@id": "http://schema.org/object", "@type": "@id"},
    "result": {"@id": "http://schema.org/result", "@type": "@id"},
}


import json
from importlib import resources
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]

# Locate spec root: either as bundled package data or repository spec directory
try:
    _pkg_spec = Path(str(resources.files("research_commons") / "spec"))
    if _pkg_spec.exists():
        SPEC_ROOT = _pkg_spec
    elif (REPOSITORY_ROOT / "spec").exists():
        SPEC_ROOT = REPOSITORY_ROOT / "spec"
    else:
        SPEC_ROOT = PACKAGE_ROOT / "spec"
except (TypeError, ModuleNotFoundError, FileNotFoundError):
    SPEC_ROOT = REPOSITORY_ROOT / "spec" if (REPOSITORY_ROOT / "spec").exists() else PACKAGE_ROOT / "spec"

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

RO_CRATE_BASE_CONTEXT_PATH = SPEC_ROOT / "ro-crate-1.1-context.jsonld"
if RO_CRATE_BASE_CONTEXT_PATH.exists():
    with open(RO_CRATE_BASE_CONTEXT_PATH, encoding="utf-8") as _f:
        RO_CRATE_BASE_CONTEXT = json.load(_f)["@context"]
else:
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
        "datePublished": "http://schema.org/datePublished",
        "encodingFormat": "http://schema.org/encodingFormat",
        "object": {"@id": "http://schema.org/object", "@type": "@id"},
        "result": {"@id": "http://schema.org/result", "@type": "@id"},
    }

RO_CRATE_SPEC = "https://w3id.org/ro/crate/1.1"
RO_CRATE_CONTEXT_IRI = f"{RO_CRATE_SPEC}/context"
PROCESS_RUN_PROFILE = "https://w3id.org/ro/wfrun/process/0.5"

# Self-contained carrier context, embedded inline in every crate after the RO-Crate 1.1
# context. It only adds the RCP namespace prefix and the canonical digest slot, so it
# needs no network lookup and redefines none of the schema.org terms of RO-Crate 1.1
# (unlike the full RCP message context, which maps Person, Organization, name, license
# and object to RCP terms).
CARRIER_CONTEXT = {
    "rcp": RCP,
    "digest": "rcp:digest",
}

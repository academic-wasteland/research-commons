"""Independent conformance and interoperability tests for generated RO-Crate carriers.

These tests check generated crates without the repository's own context handling in
`ro_crate_graph`: the RO-Crate validator (roc-validator) resolves contexts itself, and
the RDF checks parse the metadata exactly as written, with only the RO-Crate 1.1
context IRI replaced by its vendored copy (the same published document). The RDF
helper deliberately does not reuse `ro_crate_graph`, to stay independent of it.

The roc-validator tests need network access (the validator fetches the RO-Crate
context and profile resources from w3id.org) and cache them under
`$XDG_CACHE_HOME/rocrate-validator` (default `~/.cache/rocrate-validator`). They are
not skipped offline on purpose: they are the independent conformance evidence.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from rdflib import RDF, Graph, Namespace, URIRef
from rocrate_validator import services
from rocrate_validator.models import Severity

from research_commons.constants import (
    CARRIER_CONTEXT,
    CONTEXT_IRI,
    PROCESS_RUN_PROFILE,
    RCP,
    RO_CRATE_BASE_CONTEXT,
    RO_CRATE_CONTEXT_IRI,
)
from research_commons.rdf_validation import ro_crate_graph
from research_commons.ro_crate import build_crate, unpack_and_verify_crate
from research_commons.schema import (
    StructuralValidationError,
    load_json,
    validate_against,
)

SCHEMA = Namespace("http://schema.org/")
RCP_NS = Namespace(RCP)

# Pinned in pyproject.toml; Process Run Crate 0.5 is the version roc-validator 0.11.4 ships
ROC_VALIDATOR_PROCESS_RUN_PROFILE = "process-run-crate-0.5"

TOOL = {
    "@id": "https://example.org/tools/runner",
    "@type": "SoftwareApplication",
    "name": "Runner",
}


def _metadata(crate_dir: Path) -> dict[str, Any]:
    return json.loads((crate_dir / "ro-crate-metadata.json").read_text(encoding="utf-8"))


def _write_metadata(crate_dir: Path, metadata: dict[str, Any]) -> None:
    (crate_dir / "ro-crate-metadata.json").write_text(json.dumps(metadata), encoding="utf-8")


def _graph_as_written(metadata: dict[str, Any]) -> Graph:
    """Parse metadata as written, resolving only the RO-Crate 1.1 context IRI offline."""
    context = [RO_CRATE_BASE_CONTEXT if c == RO_CRATE_CONTEXT_IRI else c for c in metadata["@context"]]
    assert all(isinstance(c, dict) for c in context), "metadata references another remote context"
    graph = Graph()
    graph.parse(data=json.dumps({**metadata, "@context": context}), format="json-ld")
    return graph


def _roc_validate(crate_dir: Path, profile: str, severity: Severity = Severity.REQUIRED) -> list[str]:
    settings = services.ValidationSettings(
        rocrate_uri=str(crate_dir.resolve()),
        profile_identifier=profile,
        requirement_severity=severity,
    )
    result = services.validate(settings)
    # Guard against a vacuous pass (e.g. a validator that skipped its checks)
    assert result.executed_checks, f"roc-validator executed no checks for {profile}"
    issues = [f"{issue.check.identifier}: {issue.message}" for issue in result.get_issues()]
    assert result.passed() == (not issues)
    return issues


def test_crate_context_is_self_contained(repository_root, tmp_path):
    crate_dir = build_crate((repository_root / "examples/metagenomics/task.jsonld").read_bytes(), tmp_path / "c")
    metadata = _metadata(crate_dir)

    assert metadata["@context"] == [RO_CRATE_CONTEXT_IRI, CARRIER_CONTEXT]
    assert CONTEXT_IRI not in (crate_dir / "ro-crate-metadata.json").read_text(encoding="utf-8")


def test_crate_terms_keep_ro_crate_meaning(repository_root, tmp_path):
    """The carrier context redefines no RO-Crate term; RCP terms only appear prefixed."""
    assert not set(CARRIER_CONTEXT) & set(RO_CRATE_BASE_CONTEXT)

    task = load_json(repository_root / "examples/metagenomics/task.jsonld")
    crate_dir = build_crate(task, tmp_path / "c")
    graph = _graph_as_written(_metadata(crate_dir))

    assert (None, RDF.type, SCHEMA.Dataset) in graph
    assert (None, RDF.type, SCHEMA.CreateAction) in graph
    assert (None, RDF.type, SCHEMA.MediaObject) in graph
    assert (None, RCP_NS.digest, None) in graph
    assert (None, SCHEMA.name, None) in graph
    assert (None, RCP_NS.name, None) not in graph
    assert (None, RCP_NS.license, None) not in graph
    assert (None, RCP_NS.object, None) not in graph
    # The task's requester is an rcp:Agent, which is not a schema:Person
    requester = URIRef(task["requestedBy"]["@id"])
    assert (requester, RDF.type, RCP_NS.Agent) in graph
    assert (requester, RDF.type, SCHEMA.Person) not in graph


@pytest.mark.parametrize(
    ("source_type", "expected"),
    [
        ("Agent", "rcp:Agent"),
        ("Person", ["Person", "rcp:Person"]),
        (f"{RCP}Organization", ["Organization", "rcp:Organization"]),
        (["Agent", "https://example.org/Robot"], ["rcp:Agent", "https://example.org/Robot"]),
        ("urn:example:robot", "urn:example:robot"),
        ("did:example:bot", "did:example:bot"),
        # CURIEs with prefixes of the RCP context are expanded as that context would
        ("rcp:Person", ["Person", "rcp:Person"]),
        (["Agent", "prov:SoftwareAgent"], ["rcp:Agent", "http://www.w3.org/ns/prov#SoftwareAgent"]),
        # Not RCP terms: undefined in the RCP context, so not reinterpreted by RO-Crate's
        (["Agent", "SoftwareApplication"], "rcp:Agent"),
        ("SoftwareApplication", "Thing"),
        ("schema:Person", "Thing"),
    ],
)
def test_crate_preserves_producer_type(repository_root, tmp_path, source_type, expected):
    contribution = load_json(repository_root / "examples/metagenomics/contribution.jsonld")
    contribution["producedBy"]["@type"] = source_type
    crate_dir = build_crate(contribution, tmp_path / "c")
    producer_id = contribution["producedBy"]["@id"]

    producer = next(e for e in _metadata(crate_dir)["@graph"] if e.get("@id") == producer_id)
    assert producer["@type"] == expected
    assert unpack_and_verify_crate(crate_dir) == contribution


def test_recovery_rejects_remote_rcp_context(repository_root, tmp_path):
    crate_dir = build_crate(load_json(repository_root / "examples/metagenomics/task.jsonld"), tmp_path / "c")
    metadata = _metadata(crate_dir)
    metadata["@context"] = [RO_CRATE_CONTEXT_IRI, CONTEXT_IRI]
    _write_metadata(crate_dir, metadata)

    with pytest.raises(StructuralValidationError):
        unpack_and_verify_crate(crate_dir)


def test_recovery_rejects_altered_carrier_context(repository_root, tmp_path):
    crate_dir = build_crate(load_json(repository_root / "examples/metagenomics/task.jsonld"), tmp_path / "c")
    metadata = _metadata(crate_dir)
    metadata["@context"][1] = {**CARRIER_CONTEXT, "name": "rcp:name"}
    _write_metadata(crate_dir, metadata)

    with pytest.raises(StructuralValidationError):
        unpack_and_verify_crate(crate_dir)


@pytest.mark.parametrize("nested_in_value", [False, True], ids=["entity", "nested-value"])
def test_recovery_rejects_nested_context(repository_root, tmp_path, nested_in_value):
    """Nested contexts are rejected (each would expand to the full RO-Crate context)."""
    crate_dir = build_crate(load_json(repository_root / "examples/metagenomics/task.jsonld"), tmp_path / "c")
    metadata = _metadata(crate_dir)
    carried = next(e for e in metadata["@graph"] if e.get("@id") == "rcp-message.jsonld")
    target = carried["about"] if nested_in_value else carried
    target["@context"] = RO_CRATE_CONTEXT_IRI
    _write_metadata(crate_dir, metadata)

    if not nested_in_value:
        # The profile schema rejects entity-level contexts before any RDF parsing
        with pytest.raises(StructuralValidationError, match="must not carry their own @context|should not be valid"):
            validate_against(metadata, "ro-crate-rcp-profile.json")
    with pytest.raises(ValueError, match="Nested @context is not allowed"):
        ro_crate_graph(metadata)
    with pytest.raises(ValueError, match="should not be valid|Nested @context is not allowed"):
        unpack_and_verify_crate(crate_dir)


def test_recovery_rejects_deeply_nested_metadata_cleanly(repository_root, tmp_path):
    crate_dir = build_crate(load_json(repository_root / "examples/metagenomics/task.jsonld"), tmp_path / "c")
    metadata = _metadata(crate_dir)
    deep: list[Any] = []
    for _ in range(5000):
        deep = [deep]
    root = next(e for e in metadata["@graph"] if e.get("@id") == "./")
    root["keywords"] = deep
    with pytest.raises(ValueError, match="nested too deeply"):
        ro_crate_graph(metadata)


def test_recovery_accepts_parameterized_json_ld_media_type(repository_root, tmp_path):
    task = load_json(repository_root / "examples/metagenomics/task.jsonld")
    crate_dir = build_crate(task, tmp_path / "c")
    metadata = _metadata(crate_dir)
    carried = next(e for e in metadata["@graph"] if e.get("@id") == "rcp-message.jsonld")
    carried["encodingFormat"] = f'application/ld+json;profile="{RCP}task"'
    _write_metadata(crate_dir, metadata)

    assert unpack_and_verify_crate(crate_dir) == task


@pytest.mark.parametrize("media_type", ["application/ld+jsonx", "application/ld+json\n", "application/ld+json;\nx"])
def test_recovery_rejects_other_media_type(repository_root, tmp_path, media_type):
    crate_dir = build_crate(load_json(repository_root / "examples/metagenomics/task.jsonld"), tmp_path / "c")
    metadata = _metadata(crate_dir)
    carried = next(e for e in metadata["@graph"] if e.get("@id") == "rcp-message.jsonld")
    carried["encodingFormat"] = media_type
    _write_metadata(crate_dir, metadata)

    with pytest.raises(StructuralValidationError):
        validate_against(metadata, "ro-crate-rcp-profile.json")
    with pytest.raises((StructuralValidationError, ValueError)):
        unpack_and_verify_crate(crate_dir)


def test_process_run_crate_declares_profile_entities(repository_root, tmp_path):
    crate_dir = build_crate(
        load_json(repository_root / "examples/metagenomics/task.jsonld"), tmp_path / "c", workflow_tool=TOOL
    )
    graph = _metadata(crate_dir)["@graph"]
    root = next(e for e in graph if e.get("@id") == "./")
    declared = [ref["@id"] for ref in root["conformsTo"]]

    assert PROCESS_RUN_PROFILE in declared
    for profile_id in declared:
        entity = next(e for e in graph if e.get("@id") == profile_id)
        assert entity["@type"] == "CreativeWork"
    assert next(e for e in graph if e.get("@id") == PROCESS_RUN_PROFILE)["version"] == "0.5"


@pytest.mark.parametrize("message", ["task.jsonld", "contribution.jsonld"])
def test_roc_validator_ro_crate_1_1(repository_root, tmp_path, message):
    crate_dir = build_crate((repository_root / "examples/metagenomics" / message).read_bytes(), tmp_path / "c")
    assert _roc_validate(crate_dir, "ro-crate-1.1") == []


def test_roc_validator_process_run_crate(repository_root, tmp_path):
    """The exact Process Run Crate version the crate claims (0.5) is validated independently."""
    crate_dir = build_crate(
        (repository_root / "examples/metagenomics/task.jsonld").read_bytes(), tmp_path / "c", workflow_tool=TOOL
    )
    root = next(e for e in _metadata(crate_dir)["@graph"] if e.get("@id") == "./")
    assert {"@id": "https://w3id.org/ro/wfrun/process/0.5"} in root["conformsTo"]

    assert _roc_validate(crate_dir, "ro-crate-1.1") == []
    assert _roc_validate(crate_dir, ROC_VALIDATOR_PROCESS_RUN_PROFILE) == []


# SHOULD-level findings of roc-validator 0.11.4 on the example crates with a tool,
# accepted for now and pinned exactly so that both new and fixed findings show up.
COMMON_RECOMMENDED_DEVIATIONS = {
    "ro-crate-1.1_22.1",  # license is an IRI reference without a contextual entity
    "ro-crate-1.1_22.2",  # no crate author: RCP messages do not name one
    "ro-crate-1.1_22.3",  # no crate publisher
    "ro-crate-1.1_24.1",  # hasPart and mentions are singleton arrays
    "process-run-crate-0.5_3.2",  # the example tool has no url (caller-supplied)
    "process-run-crate-0.5_4.1",  # the example tool has no version (caller-supplied)
    "process-run-crate-0.5_8.3",  # the action has no description
    "process-run-crate-0.5_8.4",  # no endTime: RCP messages carry no run end time
    "process-run-crate-0.5_8.6",  # the producer stays rcp:Agent, not Person/Organization
    "process-run-crate-0.5_10.1",  # object/result also point at RCP datasets and tasks
}
EXPECTED_RECOMMENDED_DEVIATIONS = {
    # A task crate records the request; its result arrives with the contribution
    "task.jsonld": COMMON_RECOMMENDED_DEVIATIONS | {"process-run-crate-0.5_11.1"},
    "contribution.jsonld": COMMON_RECOMMENDED_DEVIATIONS,
}


@pytest.mark.parametrize("message", sorted(EXPECTED_RECOMMENDED_DEVIATIONS))
def test_roc_validator_recommended_level_deviations_are_pinned(repository_root, tmp_path, message):
    crate_dir = build_crate(
        (repository_root / "examples/metagenomics" / message).read_bytes(), tmp_path / "c", workflow_tool=TOOL
    )
    issues = _roc_validate(crate_dir, ROC_VALIDATOR_PROCESS_RUN_PROFILE, Severity.RECOMMENDED)
    assert {issue.split(":", 1)[0] for issue in issues} == EXPECTED_RECOMMENDED_DEVIATIONS[message], issues


def test_roc_validator_rejects_process_run_crate_without_instrument(repository_root, tmp_path):
    """Control: the validator profile is real and does check Process Run requirements."""
    crate_dir = build_crate((repository_root / "examples/metagenomics/task.jsonld").read_bytes(), tmp_path / "c")
    assert _roc_validate(crate_dir, ROC_VALIDATOR_PROCESS_RUN_PROFILE) != []

"""Independent conformance and interoperability tests for generated RO-Crate carriers.

These tests check generated crates without the repository's own context handling in
`ro_crate_graph`: the RO-Crate validator (roc-validator) resolves contexts itself, and
the RDF checks parse the metadata exactly as written, with only the RO-Crate 1.1
context IRI replaced by its vendored copy (the same published document).
"""

import json
import subprocess
import sys
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


def _roc_validate(crate_dir: Path, profile: str) -> list[str]:
    settings = services.ValidationSettings(
        rocrate_uri=str(crate_dir.resolve()),
        profile_identifier=profile,
        requirement_severity=Severity.REQUIRED,
    )
    result = services.validate(settings)
    return [f"{issue.check.identifier}: {issue.message}" for issue in result.get_issues()]


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


def test_recovery_accepts_parameterized_json_ld_media_type(repository_root, tmp_path):
    task = load_json(repository_root / "examples/metagenomics/task.jsonld")
    crate_dir = build_crate(task, tmp_path / "c")
    metadata = _metadata(crate_dir)
    carried = next(e for e in metadata["@graph"] if e.get("@id") == "rcp-message.jsonld")
    carried["encodingFormat"] = f'application/ld+json;profile="{RCP}task"'
    _write_metadata(crate_dir, metadata)

    assert unpack_and_verify_crate(crate_dir) == task


def test_recovery_rejects_other_media_type(repository_root, tmp_path):
    crate_dir = build_crate(load_json(repository_root / "examples/metagenomics/task.jsonld"), tmp_path / "c")
    metadata = _metadata(crate_dir)
    carried = next(e for e in metadata["@graph"] if e.get("@id") == "rcp-message.jsonld")
    carried["encodingFormat"] = "application/ld+jsonx"
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


def test_roc_validator_rejects_process_run_crate_without_instrument(repository_root, tmp_path):
    """Control: the validator profile is real and does check Process Run requirements."""
    crate_dir = build_crate((repository_root / "examples/metagenomics/task.jsonld").read_bytes(), tmp_path / "c")
    assert _roc_validate(crate_dir, ROC_VALIDATOR_PROCESS_RUN_PROFILE) != []


@pytest.mark.parametrize("document", ["[1, 2]", '{"@type": [1]}', '"text"'])
def test_to_completion_reports_malformed_input(tmp_path, document):
    source = tmp_path / "doc.jsonld"
    source.write_text(document, encoding="utf-8")
    crate_out = tmp_path / "crate.zip"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "research_commons.cli",
            "to-completion",
            str(source),
            "--completed-by",
            "rig-1",
            "--crate-out",
            str(crate_out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout)["status"] == "invalid"
    assert "Traceback" not in result.stderr
    assert not crate_out.exists()

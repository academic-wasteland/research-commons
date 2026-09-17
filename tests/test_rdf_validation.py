import json
import zipfile

import pytest

from research_commons.constants import SPEC_ROOT
from research_commons.rdf_validation import (
    ROCrateBuilder,
    from_crate,
    message_graph,
    ro_crate_graph,
    to_crate,
    unpack_and_verify_crate,
    validate_crate_shacl,
    validate_shacl,
)
from research_commons.schema import StructuralValidationError, load_json


def test_direct_ro_crate_module_import():
    # Verify no circular import between ro_crate and rdf_validation
    import importlib

    import research_commons.ro_crate

    importlib.reload(research_commons.ro_crate)
    assert hasattr(research_commons.ro_crate, "ROCrateBuilder")
    assert hasattr(research_commons.ro_crate, "build_crate")
    assert hasattr(research_commons.ro_crate, "unpack_and_verify_crate")


def test_ro_crate_serialized_context_jsonld_expansion():
    # Verify that serialized metadata @context expands CreateAction.object as schema:object
    import tempfile

    from rdflib import URIRef

    from research_commons.ro_crate import build_crate

    task_doc = load_json(SPEC_ROOT.parent / "examples/metagenomics/task.jsonld")
    with tempfile.TemporaryDirectory() as tmp_dir:
        crate_path = build_crate(task_doc, tmp_dir)
        metadata = json.loads((crate_path / "ro-crate-metadata.json").read_text(encoding="utf-8"))

        graph = ro_crate_graph(metadata)
        # Check that triple (?action, schema:object, rcp-message.jsonld) is in the graph
        schema_object = URIRef("http://schema.org/object")
        rcp_object = URIRef("https://w3id.org/research-commons/v0.1/object")

        predicates = {p for _, p, _ in graph}
        assert schema_object in predicates, "Expected schema:object in expanded graph"
        assert rcp_object not in predicates, "Unexpected rcp:object override on CreateAction"


def test_task_jsonld_expands_without_network(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    graph = message_graph(document)
    assert len(graph) > 5


def test_all_messages_conform_to_shapes(repository_root):
    for path in [
        repository_root / "examples/metagenomics/task.jsonld",
        repository_root / "examples/metagenomics/contribution.jsonld",
        repository_root / "examples/messaging/restricted-task.jsonld",
        repository_root / "examples/messaging/unknown-task.jsonld",
        repository_root / "examples/messaging/delegated-task.jsonld",
        repository_root / "examples/messaging/delegation-denial-task.jsonld",
    ]:
        result = validate_shacl(load_json(path))
        assert result.conforms, result.report


def test_shacl_requires_explicit_producer(repository_root):
    document = load_json(repository_root / "examples/metagenomics/contribution.jsonld")
    del document["producedBy"]
    result = validate_shacl(document)
    assert not result.conforms


def test_ro_crate_zip_archive_bad_zip_signature_rejected(tmp_path):
    bad_zip = tmp_path / "corrupt.zip"
    bad_zip.write_text("not a real zip file", encoding="utf-8")

    with pytest.raises(ValueError, match="not a valid zip archive"):
        unpack_and_verify_crate(bad_zip)


def test_ro_crate_zip_archive_missing_carried_file_rejected(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "valid_crate"
    builder.build_crate(task_doc, crate_dir)

    zip_path = tmp_path / "missing_payload.crate.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(crate_dir / "ro-crate-metadata.json", arcname="ro-crate-metadata.json")
        # Do not include rcp-message.jsonld

    with pytest.raises(ValueError, match="not found in zip archive"):
        unpack_and_verify_crate(zip_path)


def test_ro_crate_builder_with_instrument_entity(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    workflow_tool = {
        "@id": "https://example.org/software/predictor",
        "@type": "SoftwareApplication",
        "name": "Predictor Tool",
    }
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "instrument_crate"
    builder.build_crate(task_doc, crate_dir, workflow_tool=workflow_tool)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    # Verify instrument is referenced in CreateAction and included in @graph
    action = next(e for e in metadata["@graph"] if e.get("@type") == "CreateAction")
    assert action.get("instrument") == {"@id": "https://example.org/software/predictor"}

    tool = next(e for e in metadata["@graph"] if e.get("@id") == "https://example.org/software/predictor")
    assert tool.get("@type") == "SoftwareApplication"

    recovered = unpack_and_verify_crate(crate_dir)
    assert recovered["@id"] == task_doc["@id"]


def test_ro_crate_failed_build_cleans_up_staged_output(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    bad_workflow_tool = {
        "@id": "https://example.org/software/predictor",
        "@type": "SoftwareApplication",
        "name": "Predictor Tool",
        "@context": "https://attacker.invalid/injected.jsonld",
    }
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "staged_fail_crate"

    # Build should fail validation
    with pytest.raises(ValueError, match="Unsupported external context"):
        builder.build_crate(task_doc, crate_dir, workflow_tool=bad_workflow_tool)

    # Output directory must not exist or must remain completely empty so retry succeeds
    assert not crate_dir.exists() or not any(crate_dir.iterdir())

    # Retrying with valid tool succeeds without tripping non-empty directory guard
    valid_workflow_tool = {
        "@id": "https://example.org/software/predictor",
        "@type": "SoftwareApplication",
        "name": "Predictor Tool",
    }
    built_path = builder.build_crate(task_doc, crate_dir, workflow_tool=valid_workflow_tool)
    assert built_path == crate_dir
    assert (crate_dir / ROCrateBuilder.METADATA_FILENAME).exists()


def test_ro_crate_builder_with_tool_unapproved_context_rejected(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    workflow_tool = {
        "@id": "https://example.org/software/predictor",
        "@type": "SoftwareApplication",
        "name": "Predictor Tool",
        "@context": "https://attacker.invalid/injected.jsonld",
    }
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "bad_tool_crate"

    with pytest.raises(ValueError, match="Unsupported external context"):
        builder.build_crate(task_doc, crate_dir, workflow_tool=workflow_tool)


def test_ro_crate_root_entity_metadata_properties(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "metadata_crate"
    builder.build_crate(task_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    root_entity = next(e for e in metadata["@graph"] if e.get("@id") == "./")

    assert "name" in root_entity
    assert "description" in root_entity
    assert root_entity.get("license") == {"@id": "https://creativecommons.org/licenses/by/4.0/"}

    # Verify license maps to schema:license in RDF graph
    graph = ro_crate_graph(metadata)
    from rdflib import URIRef
    schema_license = URIRef("http://schema.org/license")
    predicates = {p for _, p, _ in graph}
    assert schema_license in predicates


def test_ro_crate_graph_nested_remote_context_rejected(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "nested_remote_ctx_crate"
    builder.build_crate(task_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    # Attacker embeds remote context inside an entity in @graph
    for entity in metadata["@graph"]:
        if entity.get("@id") == "./":
            entity["@context"] = "https://attacker.invalid/injected.jsonld"

    with pytest.raises(ValueError, match="Unsupported external context"):
        ro_crate_graph(metadata)


def test_ro_crate_graph_nested_or_non_string_context_rejected(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "nested_ctx_crate"
    builder.build_crate(task_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["@context"].append(["https://attacker.invalid/nested.jsonld"])

    with pytest.raises(TypeError, match="Unsupported context entry"):
        ro_crate_graph(metadata)


def test_ro_crate_graph_unsupported_context_rejected(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "custom_ctx_crate"
    builder.build_crate(task_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    # Attacker appends an overriding context
    metadata["@context"].append("https://attacker.invalid/context.jsonld")

    with pytest.raises(ValueError, match="Unsupported external context"):
        ro_crate_graph(metadata)


def test_ro_crate_builder_refuses_non_empty_directory(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "non_empty_crate"
    crate_dir.mkdir()
    (crate_dir / "stale_secret.txt").write_text("preexisting sensitive content")

    with pytest.raises(ValueError, match="is not empty; refusing to overwrite"):
        builder.build_crate(task_doc, crate_dir)


def test_ro_crate_builder_and_serialization(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "test_crate"
    builder.build_crate(task_doc, crate_dir)

    metadata_path = crate_dir / "ro-crate-metadata.json"
    message_path = crate_dir / "rcp-message.jsonld"

    assert metadata_path.exists()
    assert message_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert "@graph" in metadata
    assert "@context" in metadata

    carried_file = json.loads(message_path.read_text(encoding="utf-8"))
    assert carried_file["@id"] == task_doc["@id"]

    # Carrier SHACL validation
    shacl_result = validate_crate_shacl(metadata)
    assert shacl_result.conforms, shacl_result.report


def test_ro_crate_functional_api_roundtrip(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    crate_dir = tmp_path / "functional_crate"
    to_crate(task_doc, crate_dir)
    recovered = from_crate(crate_dir)
    assert recovered == task_doc


def test_ro_crate_verbatim_bytes_preserved(repository_root, tmp_path):
    # Test that raw bytes with custom formatting/whitespace are bit-for-bit preserved
    task_file = repository_root / "examples/metagenomics/task.jsonld"
    original_bytes = task_file.read_bytes()
    crate_dir = tmp_path / "verbatim_crate"
    to_crate(original_bytes, crate_dir)

    stored_file = crate_dir / ROCrateBuilder.MESSAGE_FILENAME
    assert stored_file.read_bytes() == original_bytes


def test_ro_crate_multi_action_unrelated_action_ignored(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    crate_dir = tmp_path / "multi_action_crate"
    to_crate(task_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    # Add an unrelated CreateAction for another artifact that is also a JSON-LD file with a digest
    metadata["@graph"].append({
        "@id": "auxiliary-message.jsonld",
        "@type": "File",
        "name": "Auxiliary payload",
        "encodingFormat": "application/ld+json",
        "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    })
    metadata["@graph"].append({
        "@id": "#unrelated-action",
        "@type": "CreateAction",
        "name": "Unrelated action",
        "object": {"@id": "auxiliary-message.jsonld"},
    })
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    # Both SHACL validation and crate recovery must disambiguate the carried RCP message
    shacl_res = validate_crate_shacl(metadata)
    assert shacl_res.conforms, shacl_res.report

    recovered = from_crate(crate_dir)
    assert recovered == task_doc


def test_ro_crate_zip_archive_roundtrip(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    zip_path = tmp_path / "bundle.crate.zip"
    build_result = to_crate(task_doc, zip_path)
    assert build_result == zip_path
    assert zip_path.is_file()

    recovered = from_crate(zip_path)
    assert recovered == task_doc


@pytest.mark.parametrize(
    "malicious_member",
    [
        "../secret.json",
        "..\\secret.json",
        "/etc/passwd",
        "C:\\Windows\\system32\\calc.exe",
        "nested/../../secret.json",
    ],
)
def test_ro_crate_zip_archive_path_traversal_rejected(tmp_path, malicious_member):
    zip_path = tmp_path / "malicious.crate.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(malicious_member, "malicious payload")
        zf.writestr("ro-crate-metadata.json", "{}")

    with pytest.raises(ValueError, match="Insecure zip archive member"):
        unpack_and_verify_crate(zip_path)


def test_ro_crate_zip_archive_member_limit_rejected(tmp_path):
    zip_path = tmp_path / "too_many_members.crate.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for i in range(15):
            zf.writestr(f"file_{i}.txt", "content")
        zf.writestr("ro-crate-metadata.json", "{}")

    with pytest.raises(ValueError, match="too many members"):
        unpack_and_verify_crate(zip_path, max_members=10)


def test_ro_crate_zip_archive_size_limit_rejected(tmp_path):
    zip_path = tmp_path / "too_large.crate.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("large.txt", "A" * 5000)
        zf.writestr("ro-crate-metadata.json", "{}")

    with pytest.raises(ValueError, match="uncompressed size exceeds limit"):
        unpack_and_verify_crate(zip_path, max_uncompressed_bytes=1000)



def test_ro_crate_cli_to_and_from_crate(repository_root, tmp_path, capsys):
    from research_commons.cli import main

    task_doc_path = repository_root / "examples/metagenomics/task.jsonld"
    zip_target = tmp_path / "cli_bundle.crate.zip"

    # Test to-crate CLI
    ret = main(["to-crate", str(task_doc_path), str(zip_target)])
    assert ret == 0
    assert zip_target.is_file()

    # Test from-crate CLI
    capsys.readouterr()  # clear buffer
    ret = main(["from-crate", str(zip_target)])
    assert ret == 0
    captured = capsys.readouterr()
    recovered = json.loads(captured.out)
    original = load_json(task_doc_path)
    assert recovered == original


def test_ro_crate_carrier_shacl_auxiliary_creative_work_allowed(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "test_crate_shacl_cw"
    builder.build_crate(task_doc, crate_dir)

    metadata_path = crate_dir / "ro-crate-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    # Auxiliary CreativeWork without about: ./ should be allowed
    metadata["@graph"].append({
        "@id": "auxiliary-article.pdf",
        "@type": "CreativeWork",
        "name": "Auxiliary Documentation Article",
    })
    shacl_result = validate_crate_shacl(metadata)
    assert shacl_result.conforms, shacl_result.report


def test_ro_crate_carrier_shacl_rejection(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "test_crate_shacl_fail"
    builder.build_crate(task_doc, crate_dir)

    metadata_path = crate_dir / "ro-crate-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    # Strip digest from CreateAction to test SHACL rejection
    for entity in metadata["@graph"]:
        if entity.get("@type") == "CreateAction":
            del entity["digest"]

    shacl_result = validate_crate_shacl(metadata)
    assert not shacl_result.conforms


def test_ro_crate_carrier_shacl_auxiliary_dataset_and_missing_haspart(repository_root, tmp_path):
    task_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "test_crate_shacl_aux"
    builder.build_crate(task_doc, crate_dir)

    metadata_path = crate_dir / "ro-crate-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    # Adding an auxiliary Dataset without hasPart should not violate RootDataEntityShape
    metadata["@graph"].append({
        "@id": "auxiliary-dataset",
        "@type": "Dataset",
        "name": "Auxiliary Dataset without parts",
    })
    shacl_result = validate_crate_shacl(metadata)
    assert shacl_result.conforms, shacl_result.report

    # Omitting the carried file from root Dataset's hasPart should be rejected
    for entity in metadata["@graph"]:
        if entity.get("@id") == "./":
            entity["hasPart"] = [{"@id": "other-part.txt"}]

    shacl_result_missing = validate_crate_shacl(metadata)
    assert not shacl_result_missing.conforms


@pytest.mark.parametrize(
    "doc_fixture_path",
    [
        "examples/metagenomics/task.jsonld",
        "examples/metagenomics/contribution.jsonld",
        "examples/metagenomics/request.jsonld",
    ],
)
def test_ro_crate_unpack_and_verify_success(repository_root, tmp_path, doc_fixture_path):
    original_doc = load_json(repository_root / doc_fixture_path)
    builder = ROCrateBuilder()
    crate_dir = tmp_path / f"crate_{abs(hash(doc_fixture_path))}"
    builder.build_crate(original_doc, crate_dir)

    unpacked_doc = unpack_and_verify_crate(crate_dir)
    assert unpacked_doc == original_doc


@pytest.mark.parametrize(
    "tamper_field,tamper_value",
    [
        ("semanticContract", "https://example.org/tampered-contract"),
        ("ontologyProfile", "sha256:0000000000000000000000000000000000000000000000000000000000000000"),
    ],
)
def test_ro_crate_unpack_and_verify_tampered_rejected(repository_root, tmp_path, tamper_field, tamper_value):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / f"tampered_{tamper_field}"
    builder.build_crate(original_doc, crate_dir)

    # Silently tamper with the carried JSON-LD file
    message_path = crate_dir / ROCrateBuilder.MESSAGE_FILENAME
    carried = json.loads(message_path.read_text(encoding="utf-8"))
    carried[tamper_field] = tamper_value
    message_path.write_text(json.dumps(carried), encoding="utf-8")

    with pytest.raises(ValueError, match="digest"):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_and_verify_no_referencing_action_rejected(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "action_unlinked_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@type") == "CreateAction":
            entity["object"] = {"@id": "some-other-file.json"}
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="(No CreateAction entity found referencing carried file|RO-Crate metadata failed SHACL shape validation)"):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_and_verify_symlink_metadata_rejected(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "symlink_meta_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    outside_meta = tmp_path / "outside-metadata.json"
    metadata_path.rename(outside_meta)
    metadata_path.symlink_to(outside_meta)

    with pytest.raises(ValueError, match="(must be regular file, not symlink|Metadata file path traversal detected)"):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_and_verify_id_mismatch_rejected(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "id_mismatch_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
            entity["about"] = {"@id": "urn:uuid:00000000-0000-0000-0000-000000000000"}
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="identifier derivation"):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_directory_traversal_component_rejected(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "traversal_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
            entity["@id"] = "nested/../rcp-message.jsonld"
        if entity.get("@id") == "./":
            entity["hasPart"] = [{"@id": "nested/../rcp-message.jsonld"}]
        if entity.get("@type") == "CreateAction":
            entity["object"] = {"@id": "nested/../rcp-message.jsonld"}
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="Path traversal detected in carried file reference"):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_and_verify_action_id_mismatch_rejected(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "action_id_mismatch_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@type") == "CreateAction":
            entity["@id"] = "#action-000000000000"
        if entity.get("@id") == "./":
            entity["mentions"] = [{"@id": "#action-000000000000"}]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="CreateAction identifier derivation mismatch"):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_and_verify_non_string_entity_id_cleanly_rejected(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "malformed_id_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    # Add malformed entity with non-string @id
    metadata["@graph"].append({"@id": 123, "@type": "File"})
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(StructuralValidationError):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_and_verify_missing_about_rejected(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "missing_about_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
            del entity["about"]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(StructuralValidationError):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_and_verify_invalid_root_type_rejected(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "invalid_root_type_crate"
    builder.build_crate(original_doc, crate_dir)

    # Modify carried file to have an invalid root type
    message_path = crate_dir / ROCrateBuilder.MESSAGE_FILENAME
    carried = json.loads(message_path.read_text(encoding="utf-8"))
    carried["@type"] = "SoftwareSourceCode"
    # Also update digests to bypass digest check so root type check is isolated
    from research_commons.ledger import canonical_json, document_digest

    new_digest = document_digest(carried)
    message_path.write_bytes(canonical_json(carried).encode("utf-8"))

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
            entity["digest"] = new_digest
        if entity.get("@type") == "CreateAction":
            entity["digest"] = new_digest
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises((ValueError, StructuralValidationError)):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_and_verify_missing_id_rejected(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "missing_id_crate"
    builder.build_crate(original_doc, crate_dir)

    # Modify carried file to drop @id
    message_path = crate_dir / ROCrateBuilder.MESSAGE_FILENAME
    carried = json.loads(message_path.read_text(encoding="utf-8"))
    del carried["@id"]

    from research_commons.ledger import canonical_json, document_digest

    new_digest = document_digest(carried)
    message_path.write_bytes(canonical_json(carried).encode("utf-8"))

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
            entity["digest"] = new_digest
            entity["about"] = {"@id": ""}
        if entity.get("@type") == "CreateAction":
            entity["digest"] = new_digest
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises((ValueError, StructuralValidationError)):
        unpack_and_verify_crate(crate_dir)


@pytest.mark.parametrize(
    "malicious_path",
    [
        "/etc/passwd",
        "../../secret.json",
        "file:///etc/passwd",
        "http://attacker.com/payload.jsonld",
        "..\\secret.json",
    ],
)
def test_ro_crate_unpack_path_traversal_rejected(repository_root, tmp_path, malicious_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "traversal_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
            entity["@id"] = malicious_path
        if entity.get("@type") == "CreateAction":
            for slot in ("object", "result"):
                if slot in entity:
                    if isinstance(entity[slot], dict) and entity[slot].get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
                        entity[slot]["@id"] = malicious_path
                    elif isinstance(entity[slot], list):
                        for item in entity[slot]:
                            if isinstance(item, dict) and item.get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
                                item["@id"] = malicious_path
        if entity.get("@id") == "./":
            for part in entity.get("hasPart", []):
                if isinstance(part, dict) and part.get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
                    part["@id"] = malicious_path
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="Path traversal|Insecure|invalid carried file path|StructuralValidationError"):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_disambiguates_multiple_files_with_digests(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "multi_file_crate"
    builder.build_crate(original_doc, crate_dir)

    # Add extra non-RCP data file with a digest into the crate
    extra_file = crate_dir / "data.csv"
    extra_file.write_text("col1,col2\n1,2\n", encoding="utf-8")

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["@graph"].append(
        {
            "@id": "data.csv",
            "@type": "File",
            "name": "Dataset artifact",
            "encodingFormat": "text/csv",
            "digest": "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        }
    )
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    unpacked = unpack_and_verify_crate(crate_dir)
    assert unpacked == original_doc


def test_ro_crate_unpack_rejects_missing_create_action(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "no_action_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["@graph"] = [e for e in metadata["@graph"] if e.get("@type") != "CreateAction"]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_rejects_conventional_filename_without_valid_carrier_properties(
    repository_root, tmp_path
):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "conventional_bypass_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    # Turn rcp-message.jsonld into an entity that is not referenced by CreateAction and not a File
    for entity in metadata["@graph"]:
        if entity.get("@id") == ROCrateBuilder.MESSAGE_FILENAME:
            entity["@type"] = "Dataset"
            del entity["digest"]
        if entity.get("@type") == "CreateAction":
            # Point CreateAction away from rcp-message.jsonld
            entity["object"] = {"@id": "some-other-file.txt"}

    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="does not contain a valid carried RCP message file entity|failed SHACL shape validation|does not contain items matching the given schema",
    ):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_unpack_rejects_ambiguous_carried_files(repository_root, tmp_path):
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "ambiguous_crate"
    builder.build_crate(original_doc, crate_dir)

    # Rename rcp-message.jsonld to task1.jsonld and create duplicate task2.jsonld
    (crate_dir / "rcp-message.jsonld").rename(crate_dir / "task1.jsonld")
    (crate_dir / "task2.jsonld").write_text((crate_dir / "task1.jsonld").read_text(encoding="utf-8"), encoding="utf-8")

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@id") == "rcp-message.jsonld":
            entity["@id"] = "task1.jsonld"
        if entity.get("@id") == "./":
            entity["hasPart"] = [{"@id": "task1.jsonld"}, {"@id": "task2.jsonld"}]
        if entity.get("@type") == "CreateAction":
            entity["object"] = [{"@id": "task1.jsonld"}, {"@id": "task2.jsonld"}]

    metadata["@graph"].append({
        "@id": "task2.jsonld",
        "@type": "File",
        "name": "Second task file",
        "encodingFormat": "application/ld+json",
        "digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    })
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="Ambiguous carried RCP JSON-LD file"):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_workflow_run_profile_declaration(repository_root, tmp_path):
    """Test that generated crates declare the Workflow Run RO-Crate profile when workflow tool is present."""
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "wfrun_crate"
    tool = {
        "@id": "https://example.org/tools/runner",
        "@type": "SoftwareApplication",
        "name": "Runner",
    }
    builder.build_crate(original_doc, crate_dir, workflow_tool=tool)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    root_entity = next(e for e in metadata["@graph"] if e.get("@id") == "./")
    conforms = [c.get("@id") for c in root_entity.get("conformsTo", []) if isinstance(c, dict)]
    assert "https://w3id.org/ro/crate/1.1" in conforms
    assert "https://w3id.org/ro/wfrun/process/0.1" in conforms
    assert any("ro-crate-rcp-profile.json" in c for c in conforms)

    # For default crates without workflow_tool, process run profile should not be falsely claimed
    plain_crate_dir = tmp_path / "plain_crate"
    builder.build_crate(original_doc, plain_crate_dir)
    plain_meta = json.loads((plain_crate_dir / ROCrateBuilder.METADATA_FILENAME).read_text(encoding="utf-8"))
    plain_root = next(e for e in plain_meta["@graph"] if e.get("@id") == "./")
    plain_conforms = [c.get("@id") for c in plain_root.get("conformsTo", []) if isinstance(c, dict)]
    assert "https://w3id.org/ro/wfrun/process/0.1" not in plain_conforms


def test_ro_crate_to_completion_rejects_task_without_emitting_crate(repository_root, tmp_path):
    """Test that to-completion with --crate-out fails on task and does not create the crate."""
    import subprocess
    import sys

    task_path = repository_root / "examples/metagenomics/task.jsonld"
    crate_out = tmp_path / "should_not_exist.zip"

    cmd = [
        sys.executable,
        "-m",
        "research_commons.cli",
        "to-completion",
        str(task_path),
        "--completed-by",
        "did:key:z6MkuV8zD6H7338C",
        "--crate-out",
        str(crate_out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode != 0
    assert not crate_out.exists()


def test_ro_crate_referencing_action_missing_digest_rejected(repository_root, tmp_path):
    """Test that a referencing CreateAction missing a digest is rejected unconditionally."""
    original_doc = load_json(repository_root / "examples/metagenomics/task.jsonld")
    builder = ROCrateBuilder()
    crate_dir = tmp_path / "missing_digest_action_crate"
    builder.build_crate(original_doc, crate_dir)

    metadata_path = crate_dir / ROCrateBuilder.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for entity in metadata["@graph"]:
        if entity.get("@type") == "CreateAction":
            del entity["digest"]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(Exception, match="(CreateAction digest mismatch|RO-Crate metadata failed SHACL shape validation|does not contain items matching the given schema)"):
        unpack_and_verify_crate(crate_dir)


def test_ro_crate_to_completion_automatic_crate_emission(repository_root, tmp_path):
    """Test that CLI to-completion automatically emits a valid RO-Crate when requested."""
    import subprocess
    import sys

    doc_path = repository_root / "examples/metagenomics/contribution.jsonld"
    crate_out = tmp_path / "completion_crate.zip"

    cmd = [
        sys.executable,
        "-m",
        "research_commons.cli",
        "to-completion",
        str(doc_path),
        "--completed-by",
        "did:key:z6MkuV8zD6H7338C",
        "--crate-out",
        str(crate_out),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert crate_out.is_file()
    assert crate_out.stat().st_size > 0

    # Verify that the emitted crate unpacks and verifies correctly
    unpacked = unpack_and_verify_crate(crate_out)
    assert unpacked["@id"] == "urn:uuid:757d2882-b533-4fc2-9bd1-8c6b21227284"





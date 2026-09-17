"""Project RCP messages onto Workflow Run RO-Crates per ADR 0002.

Carries the complete, verbatim RCP JSON-LD document inside an RO-Crate and records
its canonical SHA-256 digest in crate metadata. Recovery verifies crate structural
conformance, carrier SHACL constraints, digest integrity, and message semantics.
"""

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from .constants import RCP
from .ledger import canonical_json, document_digest, root_types
from .schema import load_json, validate_against, validate_message

MESSAGE_FILENAME = "rcp-message.jsonld"
METADATA_FILENAME = "ro-crate-metadata.json"
PROFILE_ID = f"{RCP}ro-crate-rcp-profile.json"
PROFILE_SCHEMA = "ro-crate-rcp-profile.json"

VALID_ROOT_TYPES = {
    "ResearchTask",
    f"{RCP}ResearchTask",
    "ResearchContribution",
    f"{RCP}ResearchContribution",
    "ResearchRequest",
    f"{RCP}ResearchRequest",
}


def build_crate(rcp_message: dict[str, Any] | str | bytes, output_target: str | Path) -> Path:
    """Package task inputs and outputs and generate a Workflow Run RO-Crate.

    Accepts an RCP message as a dict or raw JSON string/bytes (preserving verbatim bytes),
    and accepts either a directory path or a `.zip` archive destination path.
    """
    if isinstance(rcp_message, (str, bytes)):
        raw_bytes = rcp_message.encode("utf-8") if isinstance(rcp_message, str) else rcp_message
        message_doc = json.loads(raw_bytes.decode("utf-8"))
        if not isinstance(message_doc, dict):
            raise TypeError("RCP message must parse to a JSON-LD object")
    else:
        message_doc = rcp_message
        raw_bytes = canonical_json(message_doc).encode("utf-8")

    validate_message(message_doc)
    target_path = Path(output_target)
    is_zip = target_path.suffix.lower() == ".zip"

    if is_zip:
        temp_dir = Path(tempfile.mkdtemp(prefix="ro_crate_"))
        out_path = temp_dir
    else:
        out_path = target_path
        if out_path.exists() and any(out_path.iterdir()):
            # Prevent stale or unrelated files from being disclosed or included in the crate
            raise ValueError(f"Output directory {out_path} is not empty; refusing to overwrite")
        out_path.mkdir(parents=True, exist_ok=True)

    try:
        message_file = out_path / MESSAGE_FILENAME
        message_file.write_bytes(raw_bytes)

        digest = document_digest(message_doc)
        msg_id = message_doc.get("@id", "")
        types = root_types(message_doc)

        action_id, action_entity = _assemble_action_entity(message_doc, msg_id, types, digest)

        graph: list[dict[str, Any]] = [
            {
                "@id": METADATA_FILENAME,
                "@type": "CreativeWork",
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                "about": {"@id": "./"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "conformsTo": [
                    {"@id": "https://w3id.org/ro/crate/1.1"},
                    {"@id": PROFILE_ID},
                ],
                "hasPart": [
                    {"@id": MESSAGE_FILENAME},
                ],
                "mentions": [
                    {"@id": action_id},
                ],
            },
            {
                "@id": MESSAGE_FILENAME,
                "@type": "File",
                "name": "Verbatim RCP JSON-LD Message",
                "encodingFormat": "application/ld+json",
                "digest": digest,
                "about": {"@id": msg_id},
            },
            action_entity,
        ]

        agent_info = message_doc.get("producedBy") or message_doc.get("requestedBy")
        if isinstance(agent_info, dict) and agent_info.get("@id"):
            raw_type = agent_info.get("@type")
            if isinstance(raw_type, list):
                entity_type = raw_type if raw_type else "Agent"
            elif isinstance(raw_type, str):
                entity_type = raw_type
            else:
                entity_type = "Agent"
            graph.append(
                {
                    "@id": agent_info["@id"],
                    "@type": entity_type,
                    "name": agent_info.get("name", "Agent"),
                }
            )

        crate_metadata: dict[str, Any] = {
            "@context": [
                "https://w3id.org/ro/crate/1.1/context",
                "https://w3id.org/research-commons/v0.1/context.jsonld",
                {
                    "object": {"@id": "http://schema.org/object", "@type": "@id"},
                    "name": "http://schema.org/name",
                },
            ],
            "@graph": graph,
        }

        validate_against(crate_metadata, PROFILE_SCHEMA)

        metadata_file = out_path / METADATA_FILENAME
        metadata_file.write_text(json.dumps(crate_metadata, indent=2, ensure_ascii=False), encoding="utf-8")

        if is_zip:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            # Create a temporary zip file first for safe replacement
            temp_zip = target_path.with_suffix(".tmp.zip")
            with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path in out_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(out_path)
                        zf.write(file_path, arcname=arcname)
            temp_zip.replace(target_path)
            return target_path
        return out_path
    finally:
        if is_zip and 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)


MAX_ZIP_MEMBERS = 1000
MAX_ZIP_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # 100 MiB


def unpack_and_verify_crate(
    crate_source: str | Path,
    *,
    max_members: int = MAX_ZIP_MEMBERS,
    max_uncompressed_bytes: int = MAX_ZIP_UNCOMPRESSED_BYTES,
) -> dict[str, Any]:
    """Recover and re-validate the carried RCP JSON-LD document from an RO-Crate directory or ZIP."""
    source_path = Path(crate_source)
    is_zip = source_path.is_file() and (source_path.suffix.lower() == ".zip" or zipfile.is_zipfile(source_path))

    if is_zip:
        temp_dir = Path(tempfile.mkdtemp(prefix="ro_crate_extract_"))
        resolved_temp = temp_dir.resolve()
        try:
            with zipfile.ZipFile(source_path, "r") as zf:
                infolist = zf.infolist()
                if len(infolist) > max_members:
                    raise ValueError(f"Zip archive contains too many members ({len(infolist)} > {max_members})")

                total_uncompressed_size = 0
                for member in infolist:
                    total_uncompressed_size += member.file_size
                    if total_uncompressed_size > max_uncompressed_bytes:
                        raise ValueError(
                            f"Zip archive uncompressed size exceeds limit ({total_uncompressed_size} > {max_uncompressed_bytes})"
                        )

                    name = member.filename
                    # Reject absolute paths, drives, UNC, or backslashes
                    if "\\" in name or name.startswith("/") or ":" in name:
                        raise ValueError(f"Insecure zip archive member: {name}")
                    # Check parts for directory traversal
                    parts = [p for p in name.replace("\\", "/").split("/") if p]
                    if ".." in parts:
                        raise ValueError(f"Insecure zip archive member: {name}")
                    # Verify resolved path remains strictly within destination directory
                    target_file = (resolved_temp / Path(*parts)).resolve()
                    if not target_file.is_relative_to(resolved_temp):
                        raise ValueError(f"Insecure zip archive member: {name}")

                # First read and validate metadata directly from archive before extraction
                if METADATA_FILENAME not in zf.namelist():
                    raise ValueError(f"Missing {METADATA_FILENAME} in zip archive")

                try:
                    raw_metadata = zf.read(METADATA_FILENAME).decode("utf-8")
                    metadata = json.loads(raw_metadata)
                except Exception as err:
                    raise ValueError(f"Failed to load RO-Crate metadata from archive: {err}") from err

                validate_against(metadata, PROFILE_SCHEMA)
                from .rdf_validation import validate_crate_shacl

                shacl_res = validate_crate_shacl(metadata)
                if not shacl_res.conforms:
                    raise ValueError(f"RO-Crate metadata failed SHACL shape validation: {shacl_res.report}")

                # Locate carried file entity from metadata
                graph = metadata.get("@graph")
                if not isinstance(graph, list):
                    raise TypeError("RO-Crate metadata has no @graph list")
                action_entities = [
                    entity
                    for entity in graph
                    if isinstance(entity, dict)
                    and any(
                        t in ("CreateAction", "http://schema.org/CreateAction")
                        for t in ([entity.get("@type")] if isinstance(entity.get("@type"), str) else entity.get("@type", []))
                    )
                ]
                if not action_entities:
                    raise ValueError("RO-Crate metadata does not contain a CreateAction entity")
                action_file_refs = _extract_action_file_refs(action_entities)
                carried_file_entry = _locate_carried_file(graph, action_file_refs)

                file_id = carried_file_entry.get("@id")
                if not file_id or not isinstance(file_id, str):
                    raise ValueError("Carried file entry has missing or invalid @id")
                if "\\" in file_id or file_id.startswith("/") or "://" in file_id or ":" in file_id:
                    raise ValueError(f"Path traversal or insecure path detected in carried file reference: {file_id}")
                file_parts = [p for p in file_id.replace("\\", "/").split("/") if p]
                if ".." in file_parts:
                    raise ValueError(f"Path traversal detected in carried file reference: {file_id}")
                normalized_file_name = "/".join(file_parts)

                # Extract only metadata and the carried file
                if normalized_file_name not in zf.namelist():
                    raise ValueError(f"Carried file '{normalized_file_name}' not found in zip archive")
                zf.extract(METADATA_FILENAME, temp_dir)
                zf.extract(normalized_file_name, temp_dir)

            return _unpack_and_verify_directory(temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        return _unpack_and_verify_directory(source_path)


def _unpack_and_verify_directory(path: Path) -> dict[str, Any]:
    resolved_path = path.resolve()
    metadata_unresolved = resolved_path / METADATA_FILENAME
    if not metadata_unresolved.exists():
        raise ValueError(f"Missing {METADATA_FILENAME} in {path}")
    if not metadata_unresolved.is_file() or metadata_unresolved.is_symlink():
        raise ValueError(f"Invalid metadata file (must be regular file, not symlink): {metadata_unresolved}")

    metadata_file = metadata_unresolved.resolve()
    if not metadata_file.is_relative_to(resolved_path) or metadata_file == resolved_path:
        raise ValueError(f"Metadata file path traversal detected: {metadata_file}")

    try:
        metadata = load_json(metadata_file)
    except Exception as err:
        raise ValueError(f"Failed to load RO-Crate metadata: {err}") from err

    # Validate profile schema and carrier SHACL shapes
    validate_against(metadata, PROFILE_SCHEMA)
    from .rdf_validation import validate_crate_shacl

    shacl_res = validate_crate_shacl(metadata)
    if not shacl_res.conforms:
        raise ValueError(f"RO-Crate metadata failed SHACL shape validation: {shacl_res.report}")

    graph = metadata.get("@graph")
    if not isinstance(graph, list):
        raise TypeError("RO-Crate metadata has no @graph list")

    action_entities = [
        entity
        for entity in graph
        if isinstance(entity, dict)
        and any(
            t in ("CreateAction", "http://schema.org/CreateAction")
            for t in ([entity.get("@type")] if isinstance(entity.get("@type"), str) else entity.get("@type", []))
        )
    ]
    if not action_entities:
        raise ValueError("RO-Crate metadata does not contain a CreateAction entity")

    action_file_refs = _extract_action_file_refs(action_entities)
    carried_file_entry = _locate_carried_file(graph, action_file_refs)

    declared_digest = carried_file_entry.get("digest")
    if not declared_digest or not isinstance(declared_digest, str):
        raise ValueError("RO-Crate metadata carried file entity has missing or invalid digest")

    file_id = carried_file_entry.get("@id")
    carried_file_path = _safe_resolve_crate_path(path, file_id)

    try:
        raw_content = carried_file_path.read_text(encoding="utf-8")
        extracted_doc = json.loads(raw_content)
    except Exception as err:
        raise ValueError(f"Failed to parse carried JSON-LD file: {err}") from err

    if not isinstance(extracted_doc, dict):
        raise TypeError("Carried JSON-LD file is not a valid JSON object")

    calculated_digest = document_digest(extracted_doc)
    _verify_carrier_digests(calculated_digest, declared_digest, action_entities, file_id)
    _validate_carried_doc(extracted_doc, carried_file_entry, action_entities, file_id)

    return extracted_doc


to_crate = build_crate
from_crate = unpack_and_verify_crate


class ROCrateBuilder:
    """Builder for Workflow Run RO-Crates carrying RCP messages per ADR 0002."""

    MESSAGE_FILENAME = MESSAGE_FILENAME
    METADATA_FILENAME = METADATA_FILENAME
    PROFILE_ID = PROFILE_ID

    def build_crate(self, rcp_message: dict[str, Any] | str | bytes, output_target: str | Path) -> Path:
        return build_crate(rcp_message, output_target)


def _derive_action_id(msg_id: str) -> str:
    if msg_id:
        hashed_id = hashlib.sha256(msg_id.encode("utf-8")).hexdigest()[:12]
        return f"#action-{hashed_id}"
    return "#action"


def _assemble_action_entity(
    rcp_message: dict[str, Any], msg_id: str, types: set[str], digest: str
) -> tuple[str, dict[str, Any]]:
    is_contribution = "ResearchContribution" in types or f"{RCP}ResearchContribution" in types
    is_task = "ResearchTask" in types or f"{RCP}ResearchTask" in types

    action_id = _derive_action_id(msg_id)
    action_name = f"Execution of {msg_id}" if msg_id else "RCP Workflow Run Execution"

    objects: list[dict[str, str]] = []
    results: list[dict[str, str]] = []

    if is_task:
        objects.append({"@id": MESSAGE_FILENAME})
        for ds in rcp_message.get("usesDataset", []):
            ds_id = ds.get("@id") if isinstance(ds, dict) else ds
            if isinstance(ds_id, str):
                objects.append({"@id": ds_id})
    elif is_contribution:
        results.append({"@id": MESSAGE_FILENAME})
        addresses = rcp_message.get("addresses")
        if isinstance(addresses, str):
            objects.append({"@id": addresses})
        for out in rcp_message.get("hasOutput", []):
            out_id = out.get("@id") if isinstance(out, dict) else out
            if isinstance(out_id, str):
                results.append({"@id": out_id})
    else:
        objects.append({"@id": MESSAGE_FILENAME})

    action_entity: dict[str, Any] = {
        "@id": action_id,
        "@type": "CreateAction",
        "name": action_name,
        "digest": digest,
    }
    if objects:
        action_entity["object"] = objects if len(objects) > 1 else objects[0]
    if results:
        action_entity["result"] = results if len(results) > 1 else results[0]

    agent_info = rcp_message.get("producedBy") or rcp_message.get("requestedBy")
    if isinstance(agent_info, dict) and agent_info.get("@id"):
        action_entity["agent"] = {"@id": agent_info["@id"]}

    return action_id, action_entity


def _extract_action_file_refs(action_entities: list[dict[str, Any]]) -> set[str]:
    action_file_refs: set[str] = set()
    for action in action_entities:
        for slot in ("object", "result"):
            val = action.get(slot)
            items = val if isinstance(val, list) else [val]
            for item in items:
                ref_id = item.get("@id") if isinstance(item, dict) else item
                if isinstance(ref_id, str):
                    action_file_refs.add(ref_id)
    return action_file_refs


def _locate_carried_file(
    graph: list[dict[str, Any]],
    action_file_refs: set[str],
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for entity in graph:
        if not isinstance(entity, dict):
            continue
        entity_id = entity.get("@id", "")
        if not isinstance(entity_id, str):
            continue
        entity_type = entity.get("@type", [])
        types = [entity_type] if isinstance(entity_type, str) else list(entity_type)
        is_file = "File" in types or "http://schema.org/MediaObject" in types
        has_digest = isinstance(entity.get("digest"), str)
        is_jsonld = entity.get("encodingFormat") == "application/ld+json" or entity_id.endswith(".jsonld")
        is_action_ref = entity_id in action_file_refs
        if is_file and has_digest and is_jsonld and is_action_ref:
            candidates.append(entity)

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ValueError(
            f"Ambiguous carried RCP JSON-LD file: found multiple candidates {[c.get('@id') for c in candidates]}"
        )
    raise ValueError(
        "RO-Crate metadata does not contain a valid carried RCP message file entity linked to CreateAction"
    )


def _safe_resolve_crate_path(base_dir: Path, file_id: Any) -> Path:
    if not file_id or not isinstance(file_id, str):
        raise ValueError("Carried file entry has missing or invalid @id")

    # Reject URIs, schemes, Windows drive letters, backslashes, or absolute paths
    if "\\" in file_id or file_id.startswith("/") or "://" in file_id or ":" in file_id:
        raise ValueError(f"Path traversal or insecure path detected in carried file reference: {file_id}")

    # Reject any ".." traversal path component before resolving
    parts = [p for p in file_id.replace("\\", "/").split("/") if p]
    if ".." in parts:
        raise ValueError(f"Path traversal detected in carried file reference: {file_id}")

    resolved_base = base_dir.resolve()
    carried_file_path = (resolved_base / Path(*parts)).resolve()
    if not carried_file_path.is_relative_to(resolved_base) or carried_file_path == resolved_base:
        raise ValueError(f"Path traversal detected in carried file reference: {file_id}")

    if not carried_file_path.is_file():
        raise ValueError(f"Carried file not found at {carried_file_path}")

    return carried_file_path


def _verify_carrier_digests(
    calculated_digest: str,
    declared_digest: str,
    action_entities: list[dict[str, Any]],
    carried_file_id: str,
) -> None:
    if calculated_digest != declared_digest:
        raise ValueError(
            f"Carried JSON-LD digest mismatch: declared {declared_digest}, calculated {calculated_digest}"
        )
    for action in action_entities:
        # Only verify digest on actions that actually reference the carried file
        action_file_refs = _extract_action_file_refs([action])
        if carried_file_id in action_file_refs:
            action_digest = action.get("digest")
            if action_digest and action_digest != calculated_digest:
                raise ValueError(
                    f"CreateAction digest mismatch: action declared {action_digest}, calculated {calculated_digest}"
                )


def _validate_carried_doc(
    extracted_doc: dict[str, Any],
    carried_file_entry: dict[str, Any],
    action_entities: list[dict[str, Any]],
    carried_file_id: str,
) -> None:
    validate_message(extracted_doc)

    doc_types = root_types(extracted_doc)
    if not any(t in VALID_ROOT_TYPES for t in doc_types):
        raise ValueError(f"Carried document has invalid root type: {doc_types}")

    doc_id = extracted_doc.get("@id")
    if not doc_id or not isinstance(doc_id, str):
        raise ValueError("Carried document is missing valid @id")

    about_id = carried_file_entry.get("about")
    if isinstance(about_id, dict):
        about_id = about_id.get("@id")
    if not about_id or about_id != doc_id:
        raise ValueError(
            f"Carried document identifier derivation mismatch: metadata about {about_id}, document @id {doc_id}"
        )

    # Verify that the CreateAction referencing this carried file has the deterministic action @id
    expected_action_id = _derive_action_id(doc_id)
    referencing_actions = [
        action
        for action in action_entities
        if carried_file_id in _extract_action_file_refs([action])
    ]
    if not any(action.get("@id") == expected_action_id for action in referencing_actions):
        actual_ids = [action.get("@id") for action in referencing_actions]
        raise ValueError(
            f"CreateAction identifier derivation mismatch: expected {expected_action_id}, found {actual_ids}"
        )

"""Project RCP messages onto Workflow Run RO-Crates per ADR 0002.

Carries the complete, verbatim RCP JSON-LD document inside an RO-Crate and records
its canonical SHA-256 digest in crate metadata. Recovery verifies crate structural
conformance, carrier SHACL constraints, digest integrity, and message semantics.
"""

import json
from pathlib import Path
from typing import Any

from .constants import RCP
from .ledger import canonical_json, document_digest, root_types
from .rdf_validation import validate_crate_shacl
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


def build_crate(rcp_message: dict[str, Any], output_dir: str | Path) -> Path:
    """Package task inputs and outputs and generate a Workflow Run RO-Crate."""
    validate_message(rcp_message)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    message_file = out_path / MESSAGE_FILENAME
    message_bytes = canonical_json(rcp_message).encode("utf-8")
    message_file.write_bytes(message_bytes)

    digest = document_digest(rcp_message)
    msg_id = rcp_message.get("@id", "")
    types = root_types(rcp_message)

    action_id, action_entity = _assemble_action_entity(rcp_message, msg_id, types, digest)

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

    agent_info = rcp_message.get("producedBy") or rcp_message.get("requestedBy")
    if isinstance(agent_info, dict) and agent_info.get("@id"):
        graph.append(
            {
                "@id": agent_info["@id"],
                "@type": "Person" if "Person" in agent_info.get("@type", "") else "Organization",
                "name": agent_info.get("name", "Agent"),
            }
        )

    crate_metadata: dict[str, Any] = {
        "@context": [
            "https://w3id.org/ro/crate/1.1/context",
            "https://w3id.org/research-commons/v0.1/context.jsonld",
        ],
        "@graph": graph,
    }

    validate_against(crate_metadata, PROFILE_SCHEMA)

    metadata_file = out_path / METADATA_FILENAME
    metadata_file.write_text(json.dumps(crate_metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def unpack_and_verify_crate(crate_dir: str | Path) -> dict[str, Any]:
    """Recover and re-validate the carried RCP JSON-LD document from an RO-Crate."""
    path = Path(crate_dir)
    metadata_file = path / METADATA_FILENAME
    if not metadata_file.exists():
        raise ValueError(f"Missing {METADATA_FILENAME} in {crate_dir}")

    try:
        metadata = load_json(metadata_file)
    except Exception as err:
        raise ValueError(f"Failed to load RO-Crate metadata: {err}") from err

    # Validate profile schema and carrier SHACL shapes
    validate_against(metadata, PROFILE_SCHEMA)
    shacl_res = validate_crate_shacl(metadata)
    if not shacl_res.conforms:
        raise ValueError(f"RO-Crate metadata failed SHACL shape validation: {shacl_res.report}")

    graph = metadata.get("@graph")
    if not isinstance(graph, list):
        raise TypeError("RO-Crate metadata has no @graph list")

    entities_by_id = {entity.get("@id"): entity for entity in graph if isinstance(entity, dict)}
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
    carried_file_entry = _locate_carried_file(graph, entities_by_id, action_file_refs)

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
    _verify_carrier_digests(calculated_digest, declared_digest, action_entities)
    _validate_carried_doc(extracted_doc, carried_file_entry)

    return extracted_doc


to_crate = build_crate
from_crate = unpack_and_verify_crate


class ROCrateBuilder:
    """Builder for Workflow Run RO-Crates carrying RCP messages per ADR 0002."""

    MESSAGE_FILENAME = MESSAGE_FILENAME
    METADATA_FILENAME = METADATA_FILENAME
    PROFILE_ID = PROFILE_ID

    def build_crate(self, rcp_message: dict[str, Any], output_dir: str | Path) -> Path:
        return build_crate(rcp_message, output_dir)


def _assemble_action_entity(
    rcp_message: dict[str, Any], msg_id: str, types: set[str], digest: str
) -> tuple[str, dict[str, Any]]:
    is_contribution = "ResearchContribution" in types or f"{RCP}ResearchContribution" in types
    is_task = "ResearchTask" in types or f"{RCP}ResearchTask" in types

    action_id = f"#action-{msg_id.split(':')[-1]}" if msg_id else "#action"
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
    entities_by_id: dict[str, dict[str, Any]],
    action_file_refs: set[str],
) -> dict[str, Any]:
    carried_file_entry = entities_by_id.get(MESSAGE_FILENAME)
    if carried_file_entry:
        return carried_file_entry

    candidates: list[dict[str, Any]] = []
    for entity in graph:
        if not isinstance(entity, dict):
            continue
        entity_id = entity.get("@id", "")
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

    resolved_base = base_dir.resolve()
    carried_file_path = (resolved_base / file_id).resolve()
    if not carried_file_path.is_relative_to(resolved_base) or carried_file_path == resolved_base:
        raise ValueError(f"Path traversal detected in carried file reference: {file_id}")

    if not carried_file_path.is_file():
        raise ValueError(f"Carried file not found at {carried_file_path}")

    return carried_file_path


def _verify_carrier_digests(
    calculated_digest: str, declared_digest: str, action_entities: list[dict[str, Any]]
) -> None:
    if calculated_digest != declared_digest:
        raise ValueError(
            f"Carried JSON-LD digest mismatch: declared {declared_digest}, calculated {calculated_digest}"
        )
    for action in action_entities:
        action_digest = action.get("digest")
        if action_digest and action_digest != calculated_digest:
            raise ValueError(
                f"CreateAction digest mismatch: action declared {action_digest}, calculated {calculated_digest}"
            )


def _validate_carried_doc(extracted_doc: dict[str, Any], carried_file_entry: dict[str, Any]) -> None:
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
    if about_id and about_id != doc_id:
        raise ValueError(
            f"Carried document identifier derivation mismatch: metadata about {about_id}, document @id {doc_id}"
        )

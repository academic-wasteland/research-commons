"""Project RCP messages onto Beads issues (`bd import` JSONL).

A bead is a coordination record, not a semantic object. The RCP document is
carried verbatim in `metadata.rcp.document`; every other field is derived and
may be regenerated. Identifiers are deterministic hashes of the RCP `@id` so
repeated imports upsert instead of duplicating.
"""

import json
from datetime import UTC, datetime
from typing import Any

from .ledger import (
    PROFILE_CONTRIBUTION,
    PROFILE_REQUEST,
    PROFILE_TASK,
    digest_id,
    display_name,
    document_digest,
    document_kind,
    local_name,
    title_for,
)
from .schema import validate_message

BEAD_SCHEMA_VERSION = 1
DEFAULT_PREFIX = "rcp"
LABEL_REQUEST = "rcp-request"
LABEL_TASK = "rcp-task"
LABEL_CONTRIBUTION = "rcp-contribution"
SOURCE_SYSTEM = "rcp"

_PROFILES = {
    "request": PROFILE_REQUEST,
    "task": PROFILE_TASK,
    "contribution": PROFILE_CONTRIBUTION,
}
_LABELS = {
    "request": LABEL_REQUEST,
    "task": LABEL_TASK,
    "contribution": LABEL_CONTRIBUTION,
}
_TYPES = {"request": "epic", "task": "task", "contribution": "task"}


def bead_id(iri: str, prefix: str = DEFAULT_PREFIX) -> str:
    return f"{prefix}-{digest_id(iri, 8)}"


def to_bead(
    document: dict[str, Any],
    *,
    prefix: str = DEFAULT_PREFIX,
    priority: int = 2,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Convert one validated RCP message into a `bd import` record."""
    validate_message(document)
    kind = document_kind(document)
    iri = document["@id"]
    timestamp = (now or datetime.now(UTC)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    actor = _actor(document, kind)

    bead: dict[str, Any] = {
        "_type": "issue",
        "schema_version": BEAD_SCHEMA_VERSION,
        "id": bead_id(iri, prefix),
        "title": title_for(document)[:200],
        "description": _description(document, kind),
        "status": "closed" if kind == "contribution" else "open",
        "priority": priority,
        "issue_type": _TYPES[kind],
        "external_ref": iri,
        "source_system": SOURCE_SYSTEM,
        "spec_id": document.get("semanticContract"),
        "created_at": timestamp,
        "updated_at": timestamp,
        "labels": _labels(document, kind),
        "metadata": {
            "rcp": {
                "profile": _PROFILES[kind],
                "id": iri,
                "semanticContract": document.get("semanticContract"),
                "ontologyProfile": document.get("ontologyProfile"),
                "digest": document_digest(document),
                "document": document,
            }
        },
        "dependencies": _dependencies(document, kind, prefix),
    }
    if actor:
        bead["created_by"] = actor
    if kind == "contribution":
        bead["closed_at"] = document.get("generatedAtTime", timestamp)
        bead["close_reason"] = "RCP contribution received; semantic validation pending"
    return bead


def from_bead(bead: dict[str, Any]) -> dict[str, Any]:
    """Recover and re-validate the RCP document carried by a bead."""
    try:
        carried = bead["metadata"]["rcp"]
    except (KeyError, TypeError) as error:
        raise ValueError("bead carries no metadata.rcp block") from error
    document = carried.get("document")
    if not isinstance(document, dict):
        raise TypeError("metadata.rcp.document is missing or not an object")
    if document_digest(document) != carried.get("digest"):
        raise ValueError("metadata.rcp.digest does not match the carried document")
    if bead.get("external_ref") not in (None, document.get("@id")):
        raise ValueError("bead external_ref disagrees with the carried document @id")
    validate_message(document)
    return document


def to_jsonl(beads: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(bead, sort_keys=True, ensure_ascii=False) + "\n" for bead in beads)


def _actor(document: dict[str, Any], kind: str) -> str | None:
    if kind == "contribution":
        return display_name(document.get("producedBy"))
    return display_name(document.get("onBehalfOf")) or display_name(document.get("requestedBy"))


def _description(document: dict[str, Any], kind: str) -> str:
    lines = [f"RCP {kind} {document['@id']}"]
    contract = document.get("semanticContract")
    if contract:
        lines.append(f"Semantic contract: {contract}")
    if kind == "request":
        question = document.get("question")
        if question:
            lines.append("")
            lines.append(str(question))
    if kind == "task":
        for dataset in document.get("usesDataset") or []:
            name = display_name(dataset)
            if name:
                lines.append(f"Dataset: {name}")
    if kind == "contribution":
        lines.append(f"Addresses task: {document.get('addresses')}")
        for claim in document.get("hasClaim") or []:
            if isinstance(claim, dict) and claim.get("statement"):
                lines.append(f"Claim: {claim['statement']}")
    lines.append("")
    lines.append("The authoritative JSON-LD message is stored in metadata.rcp.document.")
    return "\n".join(lines)


def _labels(document: dict[str, Any], kind: str) -> list[str]:
    labels = [_LABELS[kind]]
    task_type = document.get("taskType")
    if isinstance(task_type, str):
        labels.append(f"rcp-class:{local_name(task_type)}")
    if any(isinstance(item, dict) and "RestrictedDataset" in _types(item) for item in document.get("usesDataset") or []):
        labels.append("rcp-restricted-data")
    return labels


def _types(value: dict[str, Any]) -> list[str]:
    types = value.get("@type", [])
    return [types] if isinstance(types, str) else list(types)


def _dependencies(document: dict[str, Any], kind: str, prefix: str) -> list[dict[str, str]]:
    own = bead_id(document["@id"], prefix)
    dependencies: list[dict[str, str]] = []
    if kind == "task" and isinstance(document.get("partOfRequest"), str):
        dependencies.append(
            {"issue_id": own, "depends_on_id": bead_id(document["partOfRequest"], prefix), "type": "parent-child"}
        )
    if kind == "contribution" and isinstance(document.get("addresses"), str):
        dependencies.append(
            {"issue_id": own, "depends_on_id": bead_id(document["addresses"], prefix), "type": "relates-to"}
        )
    return dependencies

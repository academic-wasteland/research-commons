"""Shared helpers for projecting RCP documents onto external work ledgers.

RCP documents stay authoritative. Ledger rows (beads, wasteland wanted items)
are derived views that carry the full JSON-LD document verbatim so the
receiving side can re-run structural, SHACL, and semantic validation.
"""

import hashlib
import json
from typing import Any

from .constants import RCP

PROFILE_TASK = f"{RCP}task"
PROFILE_CONTRIBUTION = f"{RCP}contribution"
PROFILE_REQUEST = f"{RCP}request"


def local_name(iri: str) -> str:
    """Return the fragment or last path segment of an IRI."""
    if "#" in iri:
        return iri.rsplit("#", 1)[1]
    return iri.rstrip("/").rsplit("/", 1)[-1]


def digest_id(iri: str, length: int) -> str:
    """Deterministic hexadecimal identifier derived from an RCP `@id`."""
    return hashlib.sha256(iri.encode("utf-8")).hexdigest()[:length]


def canonical_json(document: dict[str, Any]) -> str:
    """Compact, key-sorted JSON so digests of the carried document are stable."""
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def document_digest(document: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(document).encode("utf-8")).hexdigest()


def root_types(document: dict[str, Any]) -> list[str]:
    value = document.get("@type", [])
    if isinstance(value, str):
        return [value]
    return [item for item in value if isinstance(item, str)]


def document_kind(document: dict[str, Any]) -> str:
    """Classify a message as request, task, or contribution by its root type."""
    types = set(root_types(document))
    if "ResearchTask" in types or f"{RCP}ResearchTask" in types:
        return "task"
    if "ResearchContribution" in types or f"{RCP}ResearchContribution" in types:
        return "contribution"
    if "ResearchRequest" in types or f"{RCP}ResearchRequest" in types:
        return "request"
    raise ValueError("document root type is not ResearchRequest, ResearchTask, or ResearchContribution")


def display_name(value: Any) -> str | None:
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str) and name:
            return name
        identifier = value.get("@id")
        if isinstance(identifier, str):
            return identifier
    if isinstance(value, str):
        return value
    return None


def title_for(document: dict[str, Any]) -> str:
    kind = document_kind(document)
    if kind == "request":
        question = document.get("question")
        if isinstance(question, str) and question:
            return question
        return f"Research request {document['@id']}"
    if kind == "task":
        task_type = document.get("taskType")
        head = local_name(task_type) if isinstance(task_type, str) else "ResearchTask"
        datasets = document.get("usesDataset") or []
        if datasets:
            first = display_name(datasets[0])
            if first:
                return f"{head}: {first}"
        return head
    claims = document.get("hasClaim") or []
    if claims:
        statement = claims[0].get("statement") if isinstance(claims[0], dict) else None
        if isinstance(statement, str) and statement:
            return statement
    return f"Contribution to {document.get('addresses', document['@id'])}"

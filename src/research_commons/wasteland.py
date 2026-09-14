"""Project RCP messages onto the Wasteland commons schema (schema_version 1.2).

Wasteland federates Gas Town rigs through a shared Dolt database whose tables
are defined in `schema/commons.sql` of github.com/gastownhall/wasteland. There
is no message protocol: participants write rows and propagate them with Dolt
fork/pull/merge. This module produces those rows.

Profile:

- A `ResearchTask` becomes a `wanted` row with `type = 'rcp-task'` and the
  full JSON-LD task in `description`.
- A `ResearchContribution` becomes a `completions` row with the JSON-LD
  contribution in `evidence`.
- A `SemanticValidationReport` becomes a `stamps` row whose `valence` records
  the per-layer outcome.

The `wl post` CLI restricts `type` to its own vocabulary, so the `type` column
is written with raw SQL. Rows generated here embed hostile message content;
all string values are escaped for MySQL/Dolt string literals and the schema
has no DDL surface, but consumers must still re-validate the carried document.
"""

import json
from datetime import UTC, datetime
from typing import Any

from .ledger import (
    PROFILE_CONTRIBUTION,
    PROFILE_TASK,
    canonical_json,
    digest_id,
    document_digest,
    document_kind,
    local_name,
    title_for,
)
from .schema import validate_against, validate_message

WANTED_TYPE = "rcp-task"
DEFAULT_PROJECT = "research-commons"
BASE_TAGS = ["rcp", WANTED_TYPE]
DESCRIPTION_LIMIT = 1_048_576

_STATUS_TO_VALENCE = {"entailed": 1.0, "unknown": 0.5, "contradicted": 0.0, "invalid": 0.0, "indeterminate": 0.0}


def wanted_id(task_iri: str) -> str:
    return f"w-{digest_id(task_iri, 10)}"


def completion_id(contribution_iri: str) -> str:
    return f"c-{digest_id(contribution_iri, 10)}"


def stamp_id(subject: str, context_id: str) -> str:
    return "s-" + digest_id(subject + "\x00" + context_id, 10)


def task_to_wanted(
    task: dict[str, Any],
    *,
    posted_by: str,
    project: str = DEFAULT_PROJECT,
    priority: int = 2,
    effort_level: str = "medium",
    now: datetime | None = None,
) -> dict[str, Any]:
    validate_message(task)
    if document_kind(task) != "task":
        raise ValueError("wanted rows are derived from ResearchTask messages only")
    description = canonical_json(task)
    if len(description.encode("utf-8")) > DESCRIPTION_LIMIT:
        raise ValueError("task exceeds the wanted.description size limit")
    timestamp = _timestamp(now)
    tags = list(BASE_TAGS)
    task_type = task.get("taskType")
    if isinstance(task_type, str):
        tags.append(f"rcp-class:{local_name(task_type)}")
    contract = task.get("semanticContract")
    if isinstance(contract, str):
        tags.append(f"rcp-contract:{contract}")
    restricted = any(
        isinstance(item, dict) and "RestrictedDataset" in _types(item) for item in task.get("usesDataset") or []
    )
    return {
        "id": wanted_id(task["@id"]),
        "title": title_for(task)[:1000],
        "description": description,
        "project": project[:64],
        "type": WANTED_TYPE,
        "priority": priority,
        "tags": tags,
        "posted_by": posted_by,
        "claimed_by": None,
        "status": "open",
        "effort_level": effort_level,
        "evidence_url": None,
        "sandbox_required": 1 if restricted else 0,
        "sandbox_scope": {"profile": PROFILE_TASK, "digest": document_digest(task)},
        "sandbox_min_tier": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def contribution_to_completion(
    contribution: dict[str, Any],
    *,
    completed_by: str,
    hop_uri: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    validate_message(contribution)
    if document_kind(contribution) != "contribution":
        raise ValueError("completion rows are derived from ResearchContribution messages only")
    addresses = contribution.get("addresses")
    if not isinstance(addresses, str):
        raise TypeError("contribution must address exactly one task IRI")
    return {
        "id": completion_id(contribution["@id"]),
        "wanted_id": wanted_id(addresses),
        "completed_by": completed_by,
        "evidence": canonical_json(contribution),
        "validated_by": None,
        "stamp_id": None,
        "parent_completion_id": None,
        "block_hash": None,
        "hop_uri": hop_uri,
        "completed_at": contribution.get("generatedAtTime") or _timestamp(now),
        "validated_at": None,
    }


def report_to_stamp(
    report: dict[str, Any],
    *,
    author: str,
    subject: str,
    completion: str,
    hop_uri: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Turn a SemanticValidationReport into a reputation stamp on a completion.

    Only `entailed` counts as full credit. `unknown` is recorded as 0.5 so the
    scoreboard distinguishes an unproven contribution from a rejected one.
    """
    validate_against(report, "semantic-validation-report.schema.json")
    if author == subject:
        raise ValueError("wasteland forbids self-stamps (author must differ from subject)")
    status = report["status"]
    valence = {
        "semantic": _STATUS_TO_VALENCE[status],
        "quality": _STATUS_TO_VALENCE[status],
        "rcp_status": status,
        "message": report["message"],
        "contract": report["contract"],
        "bundleDigest": report["bundleDigest"],
        "checker": report["checker"],
        "checks": [{"kind": check["kind"], "status": check["status"]} for check in report["checks"]],
    }
    diagnostics = [check["diagnostic"] for check in report["checks"] if check.get("diagnostic")]
    return {
        "id": stamp_id(subject, completion),
        "author": author,
        "subject": subject,
        "valence": valence,
        "confidence": 1.0 if status in {"entailed", "contradicted", "invalid"} else 0.5,
        "severity": "leaf",
        "context_id": completion,
        "context_type": "completion",
        "skill_tags": ["rcp", PROFILE_CONTRIBUTION],
        "message": diagnostics[0] if diagnostics else f"RCP semantic validation: {status}",
        "prev_stamp_hash": None,
        "block_hash": None,
        "hop_uri": hop_uri,
        "created_at": _timestamp(now),
    }


def wanted_to_task(row: dict[str, Any]) -> dict[str, Any]:
    """Recover and re-validate the task carried by a wanted row."""
    if row.get("type") != WANTED_TYPE:
        raise ValueError(f"wanted row type is {row.get('type')!r}, expected {WANTED_TYPE!r}")
    description = row.get("description")
    if not isinstance(description, str):
        raise TypeError("wanted.description is missing")
    task = json.loads(description)
    if not isinstance(task, dict):
        raise TypeError("wanted.description is not a JSON object")
    validate_message(task)
    if document_kind(task) != "task":
        raise ValueError("carried document is not a ResearchTask")
    if wanted_id(task["@id"]) != row.get("id"):
        raise ValueError("wanted.id does not match the carried task @id")
    return task


def insert_sql(table: str, row: dict[str, Any]) -> str:
    """Render one `INSERT ... ON DUPLICATE KEY UPDATE` statement for Dolt."""
    if table not in {"wanted", "completions", "stamps"}:
        raise ValueError(f"unsupported wasteland table {table!r}")
    columns = list(row)
    values = ", ".join(_literal(row[column]) for column in columns)
    updates = ", ".join(f"`{column}` = VALUES(`{column}`)" for column in columns if column != "id")
    return (
        f"INSERT INTO `{table}` ({', '.join(f'`{column}`' for column in columns)}) "
        f"VALUES ({values}) ON DUPLICATE KEY UPDATE {updates};"
    )


def _literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if not isinstance(value, str):
        raise TypeError(f"cannot render {type(value).__name__} as a SQL literal")
    escaped = (
        value.replace("\\", "\\\\")
        .replace("'", "''")
        .replace("\x00", "\\0")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\x1a", "\\Z")
    )
    return f"'{escaped}'"


def _types(value: dict[str, Any]) -> list[str]:
    types = value.get("@type", [])
    return [types] if isinstance(types, str) else list(types)


def _timestamp(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

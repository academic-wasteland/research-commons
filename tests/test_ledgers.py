import json
from datetime import UTC, datetime

import pytest

from research_commons import beads, wasteland
from research_commons.cli import main
from research_commons.schema import StructuralValidationError, load_json

FIXED = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


@pytest.fixture
def task(repository_root):
    return load_json(repository_root / "examples/metagenomics/task.jsonld")


@pytest.fixture
def request_document(repository_root):
    return load_json(repository_root / "examples/metagenomics/request.jsonld")


@pytest.fixture
def contribution(repository_root):
    return load_json(repository_root / "examples/metagenomics/contribution.jsonld")


@pytest.fixture
def report(task):
    return {
        "status": "entailed",
        "message": task["@id"],
        "contract": task["semanticContract"],
        "bundleDigest": task["ontologyProfile"],
        "checker": {"name": "km", "version": "0.0.0"},
        "checks": [{"kind": "instance", "status": "entailed", "durationMs": 12}],
    }


def test_task_bead_carries_document_and_parent_link(task):
    bead = beads.to_bead(task, now=FIXED)
    assert bead["id"] == beads.bead_id(task["@id"])
    assert bead["issue_type"] == "task"
    assert bead["external_ref"] == task["@id"]
    assert bead["metadata"]["rcp"]["document"] == task
    assert "rcp-task" in bead["labels"]
    assert "rcp-class:ProteinFunctionPredictionTask" in bead["labels"]
    assert bead["dependencies"] == [
        {
            "issue_id": bead["id"],
            "depends_on_id": beads.bead_id(task["partOfRequest"]),
            "type": "parent-child",
        }
    ]
    assert bead["created_by"] == "Robert Hoehndorf"


def test_request_and_contribution_bead_kinds(request_document, contribution):
    epic = beads.to_bead(request_document, now=FIXED)
    assert epic["issue_type"] == "epic"
    assert epic["title"] == request_document["question"]
    closed = beads.to_bead(contribution, now=FIXED)
    assert closed["status"] == "closed"
    assert closed["closed_at"] == contribution["generatedAtTime"]
    assert closed["dependencies"][0]["depends_on_id"] == beads.bead_id(contribution["addresses"])


def test_bead_ids_are_deterministic(task):
    assert beads.to_bead(task, now=FIXED)["id"] == beads.to_bead(task)["id"]
    assert beads.to_bead(task, prefix="lab")["id"].startswith("lab-")


def test_bead_round_trip(task):
    bead = beads.to_bead(task, now=FIXED)
    line = beads.to_jsonl([bead])
    assert beads.from_bead(json.loads(line)) == task


def test_tampered_bead_is_rejected(task):
    bead = beads.to_bead(task, now=FIXED)
    bead["metadata"]["rcp"]["document"]["usesDataset"][0]["@type"] = "PublicDataset"
    bead["metadata"]["rcp"]["document"]["usesDataset"][0]["name"] = "changed"
    with pytest.raises(ValueError, match="digest"):
        beads.from_bead(bead)
    bead = beads.to_bead(task, now=FIXED)
    bead["external_ref"] = "urn:uuid:00000000-0000-0000-0000-000000000000"
    with pytest.raises(ValueError, match="external_ref"):
        beads.from_bead(bead)


def test_invalid_document_is_not_projected(task):
    del task["requestedBy"]
    with pytest.raises(StructuralValidationError):
        beads.to_bead(task)
    with pytest.raises(StructuralValidationError):
        wasteland.task_to_wanted(task, posted_by="lab")


def test_wanted_row_round_trip(task):
    row = wasteland.task_to_wanted(task, posted_by="borg", now=FIXED)
    assert row["type"] == "rcp-task"
    assert row["id"] == wasteland.wanted_id(task["@id"])
    assert row["sandbox_required"] == 0
    assert "rcp-class:ProteinFunctionPredictionTask" in row["tags"]
    assert wasteland.wanted_to_task(row) == task


def test_restricted_dataset_requires_sandbox(repository_root):
    restricted = load_json(repository_root / "examples/messaging/restricted-task.jsonld")
    row = wasteland.task_to_wanted(restricted, posted_by="borg", now=FIXED)
    assert row["sandbox_required"] == 1


def test_wanted_row_rejects_foreign_type_and_id(task):
    row = wasteland.task_to_wanted(task, posted_by="borg", now=FIXED)
    row["id"] = "w-0000000000"
    with pytest.raises(ValueError, match="wanted.id"):
        wasteland.wanted_to_task(row)
    row = wasteland.task_to_wanted(task, posted_by="borg", now=FIXED)
    row["type"] = "feature"
    with pytest.raises(ValueError, match="type"):
        wasteland.wanted_to_task(row)


def test_completion_links_to_wanted(contribution, task):
    row = wasteland.contribution_to_completion(contribution, completed_by="agent-1", now=FIXED)
    assert row["wanted_id"] == wasteland.wanted_id(task["@id"])
    assert json.loads(row["evidence"]) == contribution
    assert row["completed_at"] == contribution["generatedAtTime"]
    with pytest.raises(ValueError):
        wasteland.contribution_to_completion(task, completed_by="agent-1")


def test_stamp_from_report(report):
    stamp = wasteland.report_to_stamp(report, author="validator", subject="agent-1", completion="c-1", now=FIXED)
    assert stamp["valence"]["semantic"] == 1.0
    assert stamp["valence"]["rcp_status"] == "entailed"
    assert stamp["context_type"] == "completion"
    report["status"] = "unknown"
    report["checks"][0]["status"] = "unknown"
    report["checks"][0]["diagnostic"] = "dataset access status not entailed"
    stamp = wasteland.report_to_stamp(report, author="validator", subject="agent-1", completion="c-1", now=FIXED)
    assert stamp["valence"]["semantic"] == 0.5
    assert stamp["message"] == "dataset access status not entailed"
    with pytest.raises(ValueError, match="self-stamps"):
        wasteland.report_to_stamp(report, author="agent-1", subject="agent-1", completion="c-1")


def _unescape(literal: str) -> str:
    assert literal[0] == literal[-1] == "'"
    body = literal[1:-1].replace("''", "'")
    out, i = [], 0
    while i < len(body):
        if body[i] == "\\":
            out.append({"\\": "\\", "n": "\n", "r": "\r", "0": "\x00", "Z": "\x1a"}[body[i + 1]])
            i += 2
        else:
            out.append(body[i])
            i += 1
    return "".join(out)


def test_insert_sql_escapes_hostile_strings(task):
    hostile = "x'); DROP TABLE wanted; -- \\ \n \x00 \x1a"
    assert _unescape(wasteland._literal(hostile)) == hostile
    task["usesDataset"][0]["name"] = hostile
    row = wasteland.task_to_wanted(task, posted_by="borg", now=FIXED)
    sql = wasteland.insert_sql("wanted", row)
    assert sql.startswith("INSERT INTO `wanted` (`id`, `title`")
    assert sql.endswith("ON DUPLICATE KEY UPDATE " + ", ".join(
        f"`{column}` = VALUES(`{column}`)" for column in row if column != "id"
    ) + ";")
    assert _unescape(wasteland._literal(row["title"])) == row["title"]
    assert wasteland._literal(None) == "NULL"
    assert wasteland._literal(["a", "b"]) == "'[\"a\",\"b\"]'"
    with pytest.raises(ValueError):
        wasteland.insert_sql("rigs", {"handle": "x"})


def test_cli_to_bead_and_from_bead(repository_root, tmp_path, capsys):
    task_path = repository_root / "examples/metagenomics/task.jsonld"
    assert main(["to-bead", str(task_path), str(repository_root / "examples/metagenomics/request.jsonld")]) == 0
    jsonl = tmp_path / "issues.jsonl"
    jsonl.write_text(capsys.readouterr().out, encoding="utf-8")
    assert len(jsonl.read_text().splitlines()) == 2
    assert main(["from-bead", str(jsonl)]) == 0
    documents = json.loads(capsys.readouterr().out)
    assert {document["@id"] for document in documents} == {
        load_json(task_path)["@id"],
        load_json(repository_root / "examples/metagenomics/request.jsonld")["@id"],
    }


def test_cli_wasteland_rows(repository_root, capsys):
    task_path = repository_root / "examples/metagenomics/task.jsonld"
    assert main(["to-wanted", str(task_path), "--posted-by", "borg", "--sql"]) == 0
    assert capsys.readouterr().out.startswith("INSERT INTO `wanted`")
    contribution_path = repository_root / "examples/metagenomics/contribution.jsonld"
    assert main(["to-completion", str(contribution_path), "--completed-by", "agent-1"]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["wanted_id"] == wasteland.wanted_id(load_json(task_path)["@id"])
    assert main(["to-wanted", str(contribution_path), "--posted-by", "borg"]) == 2

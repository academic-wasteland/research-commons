import argparse
import json
import sys
from pathlib import Path

from . import beads, wasteland
from .contracts import ContractManifest
from .km import KMRunner
from .rdf_validation import validate_shacl
from .ro_crate import from_crate, to_crate
from .schema import (
    StructuralValidationError,
    load_json,
    validate_against,
    validate_message,
)
from .semantic import SemanticValidator


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="research-commons")
    commands = root.add_subparsers(dest="command", required=True)

    structure = commands.add_parser("validate-structure")
    structure.add_argument("document", type=Path)
    structure.add_argument("--schema", default="message.schema.json")

    shacl = commands.add_parser("validate-shacl")
    shacl.add_argument("document", type=Path)

    semantic = commands.add_parser("validate-semantics")
    semantic.add_argument("document", type=Path)
    _reasoner_arguments(semantic)

    capability = commands.add_parser("check-capability")
    _reasoner_arguments(capability)

    composition = commands.add_parser("check-composition")
    composition.add_argument("--produced", required=True)
    composition.add_argument("--accepted", required=True)
    _reasoner_arguments(composition)

    contribution = commands.add_parser("check-contribution")
    contribution.add_argument("document", type=Path)
    _reasoner_arguments(contribution)

    instance = commands.add_parser("check-instance")
    instance.add_argument("document", type=Path)
    instance.add_argument("--class", dest="class_iri", required=True)
    _reasoner_arguments(instance)

    joint = commands.add_parser("check-joint-consistency")
    joint.add_argument("documents", type=Path, nargs="+")
    _reasoner_arguments(joint)

    classify = commands.add_parser("classify-protocol")
    _reasoner_arguments(classify)

    to_bead = commands.add_parser("to-bead", help="Project RCP messages onto Beads `bd import` JSONL")
    to_bead.add_argument("documents", type=Path, nargs="+")
    to_bead.add_argument("--prefix", default=beads.DEFAULT_PREFIX)
    to_bead.add_argument("--priority", type=int, default=2)

    from_bead = commands.add_parser("from-bead", help="Recover RCP messages from a `bd export` JSONL file")
    from_bead.add_argument("jsonl", type=Path)

    to_wanted = commands.add_parser("to-wanted", help="Render a ResearchTask as a Wasteland `wanted` row")
    to_wanted.add_argument("document", type=Path)
    to_wanted.add_argument("--posted-by", required=True, help="Wasteland rig handle of the poster")
    to_wanted.add_argument("--project", default=wasteland.DEFAULT_PROJECT)
    to_wanted.add_argument("--priority", type=int, default=2)
    to_wanted.add_argument("--sql", action="store_true", help="Emit an INSERT statement instead of JSON")

    to_completion = commands.add_parser(
        "to-completion", help="Render a ResearchContribution as a Wasteland `completions` row"
    )
    to_completion.add_argument("document", type=Path)
    to_completion.add_argument("--completed-by", required=True, help="Wasteland rig handle of the contributor")
    to_completion.add_argument("--hop-uri")
    to_completion.add_argument(
        "--crate-out",
        type=Path,
        help="Target directory or .zip archive to automatically emit an RO-Crate carrier",
    )
    to_completion.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing archive or directory target when creating a crate",
    )
    to_completion.add_argument("--sql", action="store_true")

    to_stamp = commands.add_parser("to-stamp", help="Render a semantic validation report as a Wasteland stamp")
    to_stamp.add_argument("report", type=Path)
    to_stamp.add_argument("--author", required=True, help="Validating rig handle")
    to_stamp.add_argument("--subject", required=True, help="Contributing rig handle being stamped")
    to_stamp.add_argument("--completion", required=True, help="Wasteland completion id being stamped")
    to_stamp.add_argument("--hop-uri")
    to_stamp.add_argument("--sql", action="store_true")

    to_crate_cmd = commands.add_parser("to-crate", help="Package an RCP message into an RO-Crate carrier")
    to_crate_cmd.add_argument("document", type=Path)
    to_crate_cmd.add_argument("output", type=Path, help="Target directory or .zip archive path")
    to_crate_cmd.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing archive or directory target",
    )

    from_crate_cmd = commands.add_parser("from-crate", help="Recover and verify an RCP message from an RO-Crate")
    from_crate_cmd.add_argument("crate", type=Path, help="Source directory or .zip archive path")
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "validate-structure":
            document = load_json(arguments.document)
            validate_against(document, arguments.schema)
            _print({"status": "entailed", "check": "structure"})
            return 0
        if arguments.command == "validate-shacl":
            document = load_json(arguments.document)
            validate_message(document)
            result = validate_shacl(document)
            _print({"status": "entailed" if result.conforms else "invalid", "report": result.report})
            return 0 if result.conforms else 1
        if arguments.command in _LEDGER_COMMANDS:
            return _ledger(arguments)

        manifest = ContractManifest.load(arguments.manifest)
        runner = KMRunner(
            arguments.km_bin,
            timeout_seconds=manifest.timeout_seconds,
            max_memory_mb=arguments.max_memory_mb,
            version=arguments.km_version,
        )
        validator = SemanticValidator(manifest, runner)
        if arguments.command in {"validate-semantics", "check-contribution"}:
            report = validator.validate(load_json(arguments.document))
        elif arguments.command == "check-instance":
            report = validator.check_instance(load_json(arguments.document), arguments.class_iri)
        elif arguments.command == "check-joint-consistency":
            report = validator.check_joint_consistency(
                [load_json(document) for document in arguments.documents]
            ).as_dict()
        elif arguments.command == "check-composition":
            check = validator.check_composition(arguments.produced, arguments.accepted)
            report = check.as_dict()
        else:
            checks = validator.check_contract()
            report = {
                "status": "entailed" if all(check.status == "entailed" for check in checks) else next(
                    check.status for check in checks if check.status != "entailed"
                ),
                "checks": [check.as_dict() for check in checks],
            }
        _print(report)
        return 0 if report["status"] == "entailed" else 1
    except (OSError, TypeError, ValueError, StructuralValidationError) as error:
        _print({"status": "invalid", "diagnostic": str(error)})
        return 2


_LEDGER_COMMANDS = {"to-bead", "from-bead", "to-wanted", "to-completion", "to-stamp", "to-crate", "from-crate"}


def _ledger(arguments: argparse.Namespace) -> int:
    if arguments.command == "to-bead":
        records = [
            beads.to_bead(load_json(path), prefix=arguments.prefix, priority=arguments.priority)
            for path in arguments.documents
        ]
        sys.stdout.write(beads.to_jsonl(records))
        return 0
    if arguments.command == "from-bead":
        documents = []
        with arguments.jsonl.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                record = json.loads(line)
                if isinstance(record, dict) and record.get("source_system") == beads.SOURCE_SYSTEM:
                    documents.append(beads.from_bead(record))
        _print(documents)
        return 0
    if arguments.command == "to-wanted":
        row = wasteland.task_to_wanted(
            load_json(arguments.document),
            posted_by=arguments.posted_by,
            project=arguments.project,
            priority=arguments.priority,
        )
        return _emit_row("wanted", row, arguments.sql)
    if arguments.command == "to-completion":
        raw_bytes = arguments.document.read_bytes()
        doc = json.loads(raw_bytes.decode("utf-8"))
        row = wasteland.contribution_to_completion(
            doc, completed_by=arguments.completed_by, hop_uri=arguments.hop_uri
        )
        if arguments.crate_out:
            to_crate(raw_bytes, arguments.crate_out, overwrite=arguments.force)
        return _emit_row("completions", row, arguments.sql)
    if arguments.command == "to-crate":
        out_path = to_crate(
            arguments.document.read_bytes(),
            arguments.output,
            overwrite=arguments.force,
        )
        _print({"status": "created", "crate": str(out_path)})
        return 0
    if arguments.command == "from-crate":
        recovered_doc = from_crate(arguments.crate)
        _print(recovered_doc)
        return 0
    row = wasteland.report_to_stamp(
        load_json(arguments.report),
        author=arguments.author,
        subject=arguments.subject,
        completion=arguments.completion,
        hop_uri=arguments.hop_uri,
    )
    return _emit_row("stamps", row, arguments.sql)


def _emit_row(table: str, row: dict[str, object], as_sql: bool) -> int:
    if as_sql:
        sys.stdout.write(wasteland.insert_sql(table, row) + "\n")
    else:
        _print(row)
    return 0


def _reasoner_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--manifest", required=True, type=Path)
    command.add_argument("--km-bin", default="km")
    command.add_argument("--km-version")
    command.add_argument("--max-memory-mb", type=int, default=2048)


def _print(value: object) -> None:
    json.dump(value, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import json
import sys
from pathlib import Path

from .contracts import ContractManifest
from .km import KMRunner
from .rdf_validation import validate_shacl
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
    except (OSError, ValueError, StructuralValidationError) as error:
        _print({"status": "invalid", "diagnostic": str(error)})
        return 2


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

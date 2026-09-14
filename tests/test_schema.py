import json

import pytest

from research_commons.schema import (
    StructuralValidationError,
    load_json,
    validate_against,
    validate_message,
)


@pytest.mark.parametrize(
    "relative_path",
    [
        "examples/metagenomics/request.jsonld",
        "examples/metagenomics/task.jsonld",
        "examples/metagenomics/contribution.jsonld",
        "examples/messaging/restricted-task.jsonld",
        "examples/messaging/unknown-task.jsonld",
        "examples/messaging/delegated-task.jsonld",
        "examples/messaging/delegation-denial-task.jsonld",
    ],
)
def test_messages_validate(repository_root, relative_path):
    validate_message(load_json(repository_root / relative_path))


def test_contract_manifest_validates(repository_root):
    document = load_json(repository_root / "examples/contracts/public-research.contract.json")
    validate_against(document, "contract-manifest.schema.json")


def test_agent_card_extension_validates(repository_root):
    document = load_json(repository_root / "examples/messaging/agent-card-extension.json")
    validate_against(document, "agent-card-extension.schema.json")


def test_missing_requested_by_is_rejected(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    del document["requestedBy"]
    with pytest.raises(StructuralValidationError):
        validate_message(document)


def test_axiom_bearing_message_field_is_rejected(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    document["imports"] = ["https://attacker.invalid/ontology"]
    with pytest.raises(StructuralValidationError):
        validate_message(document)


def test_root_message_type_cannot_be_spoofed(repository_root):
    document = load_json(repository_root / "examples/metagenomics/request.jsonld")
    document["@type"] = "Agent"
    with pytest.raises(StructuralValidationError):
        validate_message(document)


def test_all_json_examples_are_parseable(repository_root):
    for path in repository_root.glob("examples/**/*.json*"):
        json.loads(path.read_text(encoding="utf-8"))

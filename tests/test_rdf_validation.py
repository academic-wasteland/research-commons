from research_commons.rdf_validation import message_graph, validate_shacl
from research_commons.schema import load_json


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

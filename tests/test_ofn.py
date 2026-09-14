import pytest

from research_commons.ofn import (
    FunctionalSyntaxError,
    compose_ontologies,
    message_axioms,
    subsumption_probe_axiom,
)
from research_commons.schema import load_json


def test_message_is_projected_to_abox(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    axioms = message_axioms(document)
    assert any("ClassAssertion" in axiom and "ResearchTask" in axiom for axiom in axioms)
    assert any("ClassAssertion" in axiom and "ProteinFunctionPredictionTask" in axiom for axiom in axioms)
    assert any("ObjectPropertyAssertion" in axiom and "usesDataset" in axiom for axiom in axioms)
    assert all("Import(" not in axiom for axiom in axioms)


def test_unsafe_iri_is_rejected(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    document["@id"] = "https://example.org/> Injection("
    with pytest.raises(FunctionalSyntaxError):
        message_axioms(document)


def test_contract_ontologies_compose(repository_root):
    source = (repository_root / "examples/contracts/public-research.ofn").read_text(encoding="utf-8")
    result = compose_ontologies([source], "urn:uuid:e1a654c2-ceef-4fe7-9c17-cabbe460a2a5")
    assert result.count("Ontology(") == 1
    assert "ObjectExactCardinality" in result
    assert "ObjectInverseOf" in result
    assert "ObjectPropertyChain" in result
    assert "ObjectHasValue" in result


def test_subsumption_probe_uses_complement():
    probe = subsumption_probe_axiom("urn:probe", "https://example.org/A", "https://example.org/B")
    assert "ObjectIntersectionOf" in probe
    assert "ObjectComplementOf" in probe

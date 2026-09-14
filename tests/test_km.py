import sys

import pytest

from research_commons.km import KMRunner, ReasonerError, _classification_from_json


def test_classification_accepts_orchestrator_output():
    result = _classification_from_json(
        {"consistent": True, "unsatisfiable": ["urn:NothingLike"], "subsumptions": {"A": ["B"]}},
        7,
    )
    assert result.consistent
    assert "urn:NothingLike" in result.unsatisfiable
    assert result.subsumptions["A"] == {"B"}


def test_classification_accepts_engine_output():
    result = _classification_from_json({"inconsistent": True, "subsumptions": {}}, 2)
    assert not result.consistent


def test_classification_rejects_missing_status():
    with pytest.raises(ReasonerError):
        _classification_from_json({"subsumptions": {}}, 1)


def test_runner_invokes_machine_readable_cli(tmp_path):
    executable = tmp_path / "fake-km"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json\n"
        "print(json.dumps({'consistent': True, 'unsatisfiable': [], 'subsumptions': {}}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    result = KMRunner(str(executable), timeout_seconds=1).classify("Ontology(<urn:test>\n)\n")
    assert result.consistent


def test_runner_kills_timed_out_process_group(tmp_path):
    executable = tmp_path / "slow-km"
    executable.write_text(
        f"#!{sys.executable}\nimport time\ntime.sleep(5)\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    with pytest.raises(ReasonerError, match="timeout"):
        KMRunner(str(executable), timeout_seconds=0.05).classify("Ontology(<urn:test>\n)\n")


def test_km_pair_subsumptions_and_prefixes_are_normalised():
    from research_commons.km import _classification_from_json, ontology_prefixes

    ontology = "Prefix(:=<https://w3id.org/research-commons/v0.1/>)\nPrefix(pg:=<https://example.org/pg/>)\nOntology(<x>\n)"
    prefixes = ontology_prefixes(ontology)
    assert prefixes == {"": "https://w3id.org/research-commons/v0.1/", "pg": "https://example.org/pg/"}
    result = _classification_from_json(
        {"consistent": True, "subsumptions": [["pg:Basic", ":ResearchTask"], ["pg:Basic", "owl:Nothing"]],
         "unsatisfiable": ["pg:Basic", "urn:uuid:1"], "dropped": 0},
        5,
        prefixes=prefixes,
    )
    supers = result.subsumptions["https://example.org/pg/Basic"]
    assert "https://w3id.org/research-commons/v0.1/ResearchTask" in supers and "owl:Nothing" in supers
    assert result.subsumptions["pg:Basic"] == supers
    assert {"https://example.org/pg/Basic", "urn:uuid:1"} <= result.unsatisfiable


def test_prefixed_names_are_expanded_uniformly():
    from research_commons.km import expand_prefixed_names

    ontology = (
        "Prefix(:=<https://w3id.org/research-commons/v0.1/>)\n"
        "Prefix(pg:=<https://example.org/pg/>)\n"
        "Ontology(<https://example.org/pg/onto>\n"
        " Declaration(Class(pg:Basic))\n"
        " SubClassOf(pg:Basic :ResearchTask)\n"
        " ClassAssertion(ObjectComplementOf(pg:Basic) <urn:uuid:1>)\n"
        " ClassAssertion(<https://example.org/pg/Basic> <urn:uuid:1>)\n"
        ")\n"
    )
    expanded = expand_prefixed_names(ontology)
    assert "Prefix(pg:=<https://example.org/pg/>)" in expanded
    assert " Declaration(Class(<https://example.org/pg/Basic>))" in expanded
    assert " SubClassOf(<https://example.org/pg/Basic> <https://w3id.org/research-commons/v0.1/ResearchTask>)" in expanded
    assert " ClassAssertion(ObjectComplementOf(<https://example.org/pg/Basic>) <urn:uuid:1>)" in expanded
    assert "<https://example.org/pg/Basic> <urn:uuid:1>)" in expanded
    assert "pg:" not in expanded.split("Ontology(", 1)[1]

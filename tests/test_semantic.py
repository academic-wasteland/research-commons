import re

from research_commons.contracts import ContractManifest
from research_commons.km import Classification, ReasonerError
from research_commons.schema import load_json
from research_commons.semantic import SemanticValidator


class FixtureReasoner:
    name = "Fixture SROIQ reasoner"
    version = "test"

    def classify(self, ontology: str) -> Classification:
        consistent = True
        if (
            "ClassAssertion(<https://w3id.org/research-commons/v0.1/PublicDataset> "
            "<https://www.ebi.ac.uk/metagenomics/proteins/MGYP000261684433>)" in ontology
            and "ClassAssertion(<https://w3id.org/research-commons/v0.1/RestrictedDataset> "
            "<https://www.ebi.ac.uk/metagenomics/proteins/MGYP000261684433>)" in ontology
        ):
            consistent = False
        elif "ObjectComplementOf(<https://example.org/research-commons/contracts/public/AcceptedPublicTask>)" in ontology:
            consistent = "ClassAssertion(<https://w3id.org/research-commons/v0.1/PublicDataset>" not in ontology
        elif (
            "ObjectComplementOf(<https://example.org/research-commons/contracts/public/RejectedRestrictedTask>)"
            in ontology
            or "ObjectComplementOf(<https://example.org/research-commons/contracts/public/PermissionRequiredTask>)"
            in ontology
        ):
            consistent = "ClassAssertion(<https://w3id.org/research-commons/v0.1/RestrictedDataset>" not in ontology
        elif "ObjectComplementOf(<https://example.org/research-commons/contracts/public/ConformingContribution>)" in ontology:
            consistent = not ("ResearchArtifact" in ontology and "Agent" in ontology)
        elif "ObjectComplementOf(<https://example.org/research-commons/contracts/public/DelegatedExampleTask>)" in ontology:
            consistent = "ObjectPropertyAssertion(<https://w3id.org/research-commons/v0.1/delegatesTo>" not in ontology
        unsatisfiable = set()
        match = re.search(r"EquivalentClasses\(<(urn:uuid:[^>]+)> ObjectIntersectionOf", ontology)
        if match and "ConformingContribution" in ontology and "ResearchContribution" in ontology:
            unsatisfiable.add(match.group(1))
        return Classification(consistent, frozenset(unsatisfiable), {}, 1)


class FailedReasoner(FixtureReasoner):
    def classify(self, ontology: str) -> Classification:
        raise ReasonerError("bounded failure")


def validator(repository_root, reasoner=None):
    manifest = ContractManifest.load(repository_root / "examples/contracts/public-research.contract.json")
    return SemanticValidator(manifest, reasoner or FixtureReasoner())


def test_public_task_is_entailed(repository_root):
    report = validator(repository_root).validate(
        load_json(repository_root / "examples/metagenomics/task.jsonld")
    )
    assert report["status"] == "entailed"


def test_restricted_task_is_contradicted(repository_root):
    report = validator(repository_root).validate(
        load_json(repository_root / "examples/messaging/restricted-task.jsonld")
    )
    assert report["status"] == "contradicted"
    assert next(check for check in report["checks"] if check["kind"] == "permission-requirement")["status"] == "entailed"


def test_unclassified_dataset_produces_unknown(repository_root):
    report = validator(repository_root).validate(
        load_json(repository_root / "examples/messaging/unknown-task.jsonld")
    )
    assert report["status"] == "unknown"


def test_conforming_contribution_is_entailed(repository_root):
    report = validator(repository_root).validate(
        load_json(repository_root / "examples/metagenomics/contribution.jsonld")
    )
    assert report["status"] == "entailed"


def test_reasoner_failure_is_indeterminate(repository_root):
    report = validator(repository_root, FailedReasoner()).validate(
        load_json(repository_root / "examples/metagenomics/task.jsonld")
    )
    assert report["status"] == "indeterminate"


def test_wrong_profile_is_invalid(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    document["ontologyProfile"] = "sha256:" + "0" * 64
    report = validator(repository_root).validate(document)
    assert report["status"] == "invalid"


def test_sender_cannot_assert_acceptance_class(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    document["@type"].append(
        "https://example.org/research-commons/contracts/public/AcceptedPublicTask"
    )
    report = validator(repository_root).validate(document)
    assert report["status"] == "invalid"
    assert "non-allowlisted class" in report["checks"][-1]["diagnostic"]


def test_role_chain_delegation_can_be_checked(repository_root):
    document = load_json(repository_root / "examples/messaging/delegated-task.jsonld")
    report = validator(repository_root).check_instance(
        document,
        "https://example.org/research-commons/contracts/public/DelegatedExampleTask",
    )
    assert report["status"] == "entailed"


def test_conflicting_message_graphs_are_jointly_inconsistent(repository_root):
    documents = [
        load_json(repository_root / "examples/messaging/delegated-task.jsonld"),
        load_json(repository_root / "examples/messaging/delegation-denial-task.jsonld"),
    ]
    check = validator(repository_root).check_joint_consistency(documents)
    assert check.status == "contradicted"


def test_report_conforms_to_schema(repository_root):
    report = validator(repository_root).validate(
        load_json(repository_root / "examples/metagenomics/task.jsonld")
    )
    from research_commons.schema import validate_against

    validate_against(report, "semantic-validation-report.schema.json")


def test_composition_uses_subsumption_probe(repository_root):
    check = validator(repository_root).check_composition(
        "https://example.org/research-commons/contracts/public/ConformingContribution",
        "https://w3id.org/research-commons/v0.1/ResearchContribution",
    )
    assert check.status == "entailed"


class RecordingReasoner(FixtureReasoner):
    def __init__(self):
        self.ontologies = []

    def classify(self, ontology: str) -> Classification:
        self.ontologies.append(ontology)
        return super().classify(ontology)


REPUTABLE = "https://example.org/research-commons/contracts/public/ReputableRequester"
REQUESTER = "urn:uuid:f9f898ab-7501-4db7-a5f2-52d9968fbe6f"


def test_receiver_assertions_reach_the_reasoner_and_the_report(repository_root):
    reasoner = RecordingReasoner()
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    report = validator(repository_root, reasoner).validate(document, receiver_assertions=[(REPUTABLE, REQUESTER)])
    assert report["status"] == "entailed"
    axiom = f"ClassAssertion(<{REPUTABLE}> <{REQUESTER}>)"
    assert all(axiom in ontology for ontology in reasoner.ontologies)
    receiver_checks = [check for check in report["checks"] if check["kind"] == "receiver-assertions"]
    assert receiver_checks and REPUTABLE in receiver_checks[0]["diagnostic"]


def test_receiver_assertions_bypass_the_sender_allowlist_but_senders_cannot(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    manifest = ContractManifest.load(repository_root / "examples/contracts/public-research.contract.json")
    assert REPUTABLE not in manifest.data["assertionPolicy"]["allowedClasses"]
    assert validator(repository_root).validate(document, receiver_assertions=[(REPUTABLE, REQUESTER)])["status"] == "entailed"
    document["semanticAssertions"] = [
        {"assertionType": "ClassAssertion", "individual": REQUESTER, "class": REPUTABLE}
    ]
    assert validator(repository_root).validate(document)["status"] == "invalid"


def test_receiver_assertions_are_rendered_through_the_checked_serializer(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    report = validator(repository_root).validate(
        document, receiver_assertions=[("https://example.org/Reputable>) Ontology(", REQUESTER)]
    )
    assert report["status"] == "invalid"
    assert any(check["kind"] == "semantic-assertions" for check in report["checks"])


def test_receiver_assertions_apply_to_instance_and_joint_checks(repository_root):
    reasoner = RecordingReasoner()
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    check_validator = validator(repository_root, reasoner)
    check_validator.check_instance(
        document,
        "https://example.org/research-commons/contracts/public/AcceptedPublicTask",
        receiver_assertions=[(REPUTABLE, REQUESTER)],
    )
    joint = check_validator.check_joint_consistency([document], receiver_assertions=[(REPUTABLE, REQUESTER)])
    assert joint.status == "entailed"
    axiom = f"ClassAssertion(<{REPUTABLE}> <{REQUESTER}>)"
    assert all(axiom in ontology for ontology in reasoner.ontologies)


CREDENTIAL = "https://example.org/credentials/c1"
COVERED_BY = "https://example.org/credentials/coveredBy"
SCOPE = "https://example.org/scopes/AggregateScope"


def test_receiver_axiom_strings_reach_the_reasoner_and_the_report(repository_root):
    from research_commons import axioms

    reasoner = RecordingReasoner()
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    closure = axioms.class_assertion(axioms.only(COVERED_BY, axioms.one_of(CREDENTIAL)), document["@id"])
    scope = axioms.subclass_of(axioms.some(COVERED_BY, axioms.one_of(CREDENTIAL)), SCOPE)
    report = validator(repository_root, reasoner).validate(document, receiver_assertions=[closure, scope, (REPUTABLE, REQUESTER)])
    assert report["status"] == "entailed"
    assert all(closure in ontology and scope in ontology for ontology in reasoner.ontologies)
    diagnostic = next(check for check in report["checks"] if check["kind"] == "receiver-assertions")["diagnostic"]
    assert closure in diagnostic and REPUTABLE in diagnostic


def test_receiver_axiom_strings_are_checked(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    hostile = [
        "ClassAssertion(<https://e.org/A> <https://e.org/b>)) Ontology(<https://e.org/x>",
        "Import(<https://e.org/evil>)",
        'ClassAssertion(<https://e.org/A> "literal")',
        "ClassAssertion(ex:A <https://e.org/b>)",
        "SubClassOf(<https://e.org/A> ObjectMinCardinality(1 <https://e.org/p>))",
        "ClassAssertion(<https://e.org/A> <https://e.org/b>) ClassAssertion(<https://e.org/A> <https://e.org/c>)",
        "ClassAssertion(<https://e.org/A> <https://e.org/b>",
    ]
    for axiom in hostile:
        report = validator(repository_root).validate(document, receiver_assertions=[axiom])
        assert report["status"] == "invalid", axiom
        assert any(check["kind"] == "semantic-assertions" and check["status"] == "invalid" for check in report["checks"])


def test_axiom_builders_render_iris_through_the_checked_serializer():
    import pytest

    from research_commons import axioms
    from research_commons.ofn import FunctionalSyntaxError

    assert axioms.one_of() == axioms.NOTHING
    assert axioms.only(COVERED_BY, axioms.NOTHING) == f"ObjectAllValuesFrom(<{COVERED_BY}> owl:Nothing)"
    assert axioms.complement(SCOPE) == f"ObjectComplementOf(<{SCOPE}>)"
    with pytest.raises(FunctionalSyntaxError):
        axioms.one_of("https://e.org/a> <https://e.org/b")
    assert axioms.check_axiom(axioms.class_assertion(axioms.union(SCOPE, axioms.complement(SCOPE)), CREDENTIAL))


def test_probes_are_reported_without_changing_the_status(repository_root):
    document = load_json(repository_root / "examples/metagenomics/task.jsonld")
    plain = validator(repository_root).validate(document)
    probed = validator(repository_root).validate(document, probes=[("scope:c1", SCOPE), ("vetted:c1", REPUTABLE)])
    assert probed["status"] == plain["status"] == "entailed"
    kinds = [check["kind"] for check in probed["checks"]]
    assert kinds[-2:] == ["scope:c1", "vetted:c1"]
    assert {check["status"] for check in probed["checks"][-2:]} <= {"entailed", "contradicted", "unknown"}
    from research_commons.schema import validate_against

    validate_against(probed, "semantic-validation-report.schema.json")

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

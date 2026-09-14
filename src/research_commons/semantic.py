import json
import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .axioms import check_axiom
from .contracts import ContractManifest
from .km import Reasoner, ReasonerError
from .ofn import (
    FunctionalSyntaxError,
    add_axioms,
    instance_probe_axiom,
    message_axioms,
    render_iri,
    subsumption_probe_axiom,
)
from .rdf_validation import validate_shacl
from .schema import StructuralValidationError, validate_message

Status = str


@dataclass(frozen=True)
class Check:
    kind: str
    status: Status
    duration_ms: int
    diagnostic: str = ""

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "kind": self.kind,
            "status": self.status,
            "durationMs": self.duration_ms,
        }
        if self.diagnostic:
            value["diagnostic"] = self.diagnostic
        return value


ReceiverAssertion = tuple[str, str] | str
"""A (class IRI, individual IRI) pair asserted by the receiving node itself.

Receiver assertions carry facts the receiver trusts from its own sources (a
reputation ledger, an access-control list, a local registry). They bypass the
sender allowlist because the sender never wrote them, but they are still
rendered through the checked serializer and recorded in the report so a
decision can be audited and repeated.

A receiver assertion is either a (class IRI, individual IRI) pair or one
complete axiom string built with `research_commons.axioms` (closures, scope
axioms, negated facts about the receiver's own holdings). Axiom strings are
re-checked by `axioms.check_axiom` before they reach the reasoner.
"""

Probe = tuple[str, str]
"""A (check kind, class IRI or class expression) instance check the receiver wants reported.

Probes run on the same asserted ontology as the decision checks and are listed
in the report, but they never change the report status. Nodes use them to
explain a decision (which credential covered a task, why a scope failed).
"""


def receiver_axioms(assertions: Iterable[ReceiverAssertion]) -> list[str]:
    axioms = []
    for assertion in assertions:
        if isinstance(assertion, str):
            axioms.append(check_axiom(assertion))
            continue
        class_iri, individual = assertion
        axioms.append(f"ClassAssertion({render_iri(class_iri)} {render_iri(individual)})")
    return axioms


def _probe_axiom(individual: str, class_expression: str, *, negated: bool) -> str:
    """Instance probe for a class IRI or a checked class expression (for example ObjectSomeValuesFrom(...))."""
    if class_expression.startswith("Object") and class_expression.endswith(")"):
        expression = f"ObjectComplementOf({class_expression})" if negated else class_expression
        return check_axiom(f"ClassAssertion({expression} {render_iri(individual)})")
    return instance_probe_axiom(individual, class_expression, negated=negated)


def _describe(assertion: ReceiverAssertion) -> str:
    if isinstance(assertion, str):
        return assertion
    class_iri, individual = assertion
    return f"{individual} : {class_iri}"


class SemanticValidator:
    def __init__(self, manifest: ContractManifest, reasoner: Reasoner) -> None:
        self.manifest = manifest
        self.reasoner = reasoner
        self.base_ontology = manifest.ontology_paths()[0].read_text(encoding="utf-8")

    def _message_axioms(self, document: dict[str, Any], receiver_assertions: Iterable[ReceiverAssertion]) -> list[str]:
        axioms = message_axioms(
            document,
            allowed_classes=set(self.manifest.data["assertionPolicy"]["allowedClasses"]),
            allowed_object_properties=set(self.manifest.data["assertionPolicy"]["allowedObjectProperties"]),
        )
        axioms.extend(receiver_axioms(receiver_assertions))
        return axioms

    def validate(
        self,
        document: dict[str, Any],
        *,
        receiver_assertions: Iterable[ReceiverAssertion] = (),
        probes: Iterable[Probe] = (),
    ) -> dict[str, Any]:
        receiver_assertions = list(receiver_assertions)
        probes = list(probes)
        checks: list[Check] = []
        started = time.monotonic()
        try:
            validate_message(document)
            self._validate_profile(document)
            checks.append(Check("structure", "entailed", _elapsed(started)))
        except (StructuralValidationError, ValueError) as error:
            checks.append(Check("structure", "invalid", _elapsed(started), str(error)))
            return self._report(document, "invalid", checks)

        shacl_started = time.monotonic()
        shacl = validate_shacl(document)
        checks.append(
            Check(
                "shacl",
                "entailed" if shacl.conforms else "invalid",
                _elapsed(shacl_started),
                "" if shacl.conforms else shacl.report,
            )
        )
        if not shacl.conforms:
            return self._report(document, "invalid", checks)

        projection_started = time.monotonic()
        try:
            asserted = add_axioms(self.base_ontology, self._message_axioms(document, receiver_assertions))
        except FunctionalSyntaxError as error:
            checks.append(Check("semantic-assertions", "invalid", _elapsed(projection_started), str(error)))
            return self._report(document, "invalid", checks)
        checks.append(Check("semantic-assertions", "entailed", _elapsed(projection_started)))
        if receiver_assertions:
            checks.append(
                Check(
                    "receiver-assertions",
                    "entailed",
                    0,
                    "; ".join(_describe(assertion) for assertion in receiver_assertions),
                )
            )
        consistency = self._consistency_check(asserted)
        checks.append(consistency)
        if consistency.status != "entailed":
            status = "invalid" if consistency.status == "contradicted" else consistency.status
            return self._report(document, status, checks)

        message_types = _types(document)
        if "ResearchTask" in message_types:
            accepted = self._instance_check(
                asserted, document["@id"], self.manifest.data["acceptedTaskClass"], "task-admissibility"
            )
            rejected = self._instance_check(
                asserted, document["@id"], self.manifest.data["rejectedTaskClass"], "task-prohibition"
            )
            permission = self._instance_check(
                asserted,
                document["@id"],
                self.manifest.data["permissionRequiredClass"],
                "permission-requirement",
            )
            checks.extend([accepted, rejected, permission])
            status = _task_status(accepted, rejected, permission)
        elif "ResearchContribution" in message_types:
            output = self._instance_check(
                asserted,
                document["@id"],
                self.manifest.data["guaranteedOutputClass"],
                "result-conformance",
            )
            checks.append(output)
            status = output.status
        else:
            status = "entailed"
        for kind, class_iri in probes:
            checks.append(self._instance_check(asserted, document["@id"], class_iri, kind))
        return self._report(document, status, checks)

    def check_composition(self, produced_class: str, accepted_class: str) -> Check:
        probe = f"urn:uuid:{uuid.uuid4()}"
        axiom = subsumption_probe_axiom(probe, produced_class, accepted_class)
        ontology = add_axioms(self.base_ontology, [axiom])
        started = time.monotonic()
        try:
            result = self.reasoner.classify(ontology)
        except ReasonerError as error:
            return Check("pipeline-compatibility", "indeterminate", _elapsed(started), str(error))
        unsatisfiable = probe in result.unsatisfiable or "owl:Nothing" in result.subsumptions.get(probe, ())
        if unsatisfiable:
            return Check("pipeline-compatibility", "entailed", result.duration_ms)
        contrary_probe = f"urn:uuid:{uuid.uuid4()}"
        contrary_axiom = (
            f"EquivalentClasses({render_iri(contrary_probe)} "
            f"ObjectIntersectionOf({render_iri(produced_class)} {render_iri(accepted_class)}))"
        )
        contrary_ontology = add_axioms(
            self.base_ontology,
            [contrary_axiom],
        )
        try:
            contrary = self.reasoner.classify(contrary_ontology)
        except ReasonerError as error:
            return Check("pipeline-compatibility", "indeterminate", _elapsed(started), str(error))
        contradicted = contrary_probe in contrary.unsatisfiable or "owl:Nothing" in contrary.subsumptions.get(
            contrary_probe, ()
        )
        return Check(
            "pipeline-compatibility",
            "contradicted" if contradicted else "unknown",
            _elapsed(started),
        )

    def check_instance(
        self,
        document: dict[str, Any],
        class_iri: str,
        *,
        receiver_assertions: Iterable[ReceiverAssertion] = (),
    ) -> dict[str, Any]:
        receiver_assertions = list(receiver_assertions)
        report = self.validate(document, receiver_assertions=receiver_assertions)
        if report["status"] in {"invalid", "indeterminate"}:
            return report
        asserted = add_axioms(self.base_ontology, self._message_axioms(document, receiver_assertions))
        check = self._instance_check(asserted, document["@id"], class_iri, "requested-instance-check")
        report["checks"].append(check.as_dict())
        report["status"] = check.status
        return report

    def check_joint_consistency(
        self, documents: list[dict[str, Any]], *, receiver_assertions: Iterable[ReceiverAssertion] = ()
    ) -> Check:
        started = time.monotonic()
        axioms: list[str] = []
        try:
            for document in documents:
                validate_message(document)
                self._validate_profile(document)
                shacl = validate_shacl(document)
                if not shacl.conforms:
                    return Check("joint-consistency", "invalid", _elapsed(started), shacl.report)
                axioms.extend(self._message_axioms(document, ()))
            axioms.extend(receiver_axioms(receiver_assertions))
        except (StructuralValidationError, FunctionalSyntaxError, ValueError) as error:
            return Check("joint-consistency", "invalid", _elapsed(started), str(error))
        result = self._consistency_check(add_axioms(self.base_ontology, axioms))
        return Check(
            "joint-consistency",
            result.status,
            _elapsed(started),
            result.diagnostic,
        )

    def check_contract(self) -> list[Check]:
        checks = [self._consistency_check(self.base_ontology)]
        if checks[0].status != "entailed":
            return checks
        for key in (
            "acceptedTaskClass",
            "guaranteedOutputClass",
            "rejectedTaskClass",
            "permissionRequiredClass",
        ):
            checks.append(self._class_satisfiability_check(self.manifest.data[key], key))
        return checks

    def _validate_profile(self, document: dict[str, Any]) -> None:
        if document["semanticContract"] != self.manifest.id:
            raise ValueError("message semanticContract does not match the selected manifest")
        if document["ontologyProfile"] != self.manifest.bundle_digest:
            raise ValueError("message ontologyProfile does not match the verified ontology bundle")
        encoded_size = len(
            json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        if encoded_size > self.manifest.data["limits"]["maxMessageBytes"]:
            raise ValueError("message exceeds the contract size limit")
        if _individual_count(document) > self.manifest.data["limits"]["maxIndividuals"]:
            raise ValueError("message exceeds the contract individual limit")

    def _consistency_check(self, ontology: str) -> Check:
        started = time.monotonic()
        try:
            result = self.reasoner.classify(ontology)
        except ReasonerError as error:
            return Check("consistency", "indeterminate", _elapsed(started), str(error))
        return Check(
            "consistency",
            "entailed" if result.consistent else "contradicted",
            result.duration_ms,
        )

    def _instance_check(self, ontology: str, individual: str, class_iri: str, kind: str) -> Check:
        started = time.monotonic()
        try:
            negative = add_axioms(
                ontology,
                [_probe_axiom(individual, class_iri, negated=True)],
            )
            negative_result = self.reasoner.classify(negative)
            if not negative_result.consistent:
                return Check(kind, "entailed", _elapsed(started))
            positive = add_axioms(
                ontology,
                [_probe_axiom(individual, class_iri, negated=False)],
            )
            positive_result = self.reasoner.classify(positive)
            if not positive_result.consistent:
                return Check(kind, "contradicted", _elapsed(started))
            return Check(kind, "unknown", _elapsed(started))
        except ReasonerError as error:
            return Check(kind, "indeterminate", _elapsed(started), str(error))
        except FunctionalSyntaxError as error:
            return Check(kind, "invalid", _elapsed(started), str(error))

    def _class_satisfiability_check(self, class_iri: str, kind: str) -> Check:
        probe = f"urn:uuid:{uuid.uuid4()}"
        ontology = add_axioms(
            self.base_ontology,
            [f"EquivalentClasses({render_iri(probe)} {render_iri(class_iri)})"],
        )
        started = time.monotonic()
        try:
            result = self.reasoner.classify(ontology)
        except ReasonerError as error:
            return Check(f"class-satisfiability:{kind}", "indeterminate", _elapsed(started), str(error))
        unsatisfiable = probe in result.unsatisfiable or "owl:Nothing" in result.subsumptions.get(probe, ())
        return Check(
            f"class-satisfiability:{kind}",
            "contradicted" if unsatisfiable else "entailed",
            result.duration_ms,
        )

    def _report(self, document: dict[str, Any], status: Status, checks: list[Check]) -> dict[str, Any]:
        return {
            "status": status,
            "message": document.get("@id", "urn:uuid:00000000-0000-0000-0000-000000000000"),
            "contract": self.manifest.id,
            "bundleDigest": self.manifest.bundle_digest,
            "checker": {"name": self.reasoner.name, "version": self.reasoner.version},
            "checks": [check.as_dict() for check in checks],
        }


def _types(document: dict[str, Any]) -> set[str]:
    values = document.get("@type", [])
    if isinstance(values, str):
        values = [values]
    return {value.rsplit("/", 1)[-1] for value in values}


def _task_status(accepted: Check, rejected: Check, permission: Check) -> Status:
    if "indeterminate" in {accepted.status, rejected.status, permission.status}:
        return "indeterminate"
    if rejected.status == "entailed" or accepted.status == "contradicted":
        return "contradicted"
    if accepted.status == "entailed":
        return "entailed"
    return "unknown"


def _elapsed(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def _individual_count(document: dict[str, Any]) -> int:
    identifiers: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            identifier = value.get("@id")
            if isinstance(identifier, str):
                identifiers.add(identifier)
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(document)
    return len(identifiers)

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from .constants import COMPACT_IRIS, OBJECT_PROPERTIES


class FunctionalSyntaxError(ValueError):
    pass


def compose_ontologies(documents: Iterable[str], ontology_iri: str) -> str:
    prefixes: list[str] = []
    axioms: list[str] = []
    for document in documents:
        document_prefixes, document_axioms = split_ontology(document)
        for prefix in document_prefixes:
            if prefix not in prefixes:
                prefixes.append(prefix)
        axioms.extend(document_axioms)
    return render_ontology(prefixes, ontology_iri, axioms)


def split_ontology(document: str) -> tuple[list[str], list[str]]:
    lines = [line.rstrip() for line in document.splitlines() if line.strip()]
    prefixes = [line.strip() for line in lines if line.lstrip().startswith("Prefix(")]
    start = next((index for index, line in enumerate(lines) if line.lstrip().startswith("Ontology(")), None)
    if start is None or lines[-1].strip() != ")":
        raise FunctionalSyntaxError("expected a line-oriented OWL Functional Syntax ontology")
    axioms = [line.strip() for line in lines[start + 1 : -1]]
    return prefixes, axioms


def render_ontology(prefixes: Iterable[str], ontology_iri: str, axioms: Iterable[str]) -> str:
    iri = render_iri(ontology_iri)
    body = "\n".join(f" {axiom}" for axiom in axioms)
    prefix_text = "\n".join(prefixes)
    return f"{prefix_text}\nOntology({iri}\n{body}\n)\n"


def add_axioms(document: str, axioms: Iterable[str]) -> str:
    closing = document.rfind(")")
    if closing < 0 or "Ontology(" not in document[:closing]:
        raise FunctionalSyntaxError("expected an OWL Functional Syntax ontology")
    insertion = "".join(f"\n {axiom}" for axiom in axioms)
    return f"{document[:closing].rstrip()}{insertion}\n{document[closing:]}"


def message_axioms(
    document: dict[str, Any],
    *,
    allowed_classes: set[str] | None = None,
    allowed_object_properties: set[str] | None = None,
) -> list[str]:
    axioms: list[str] = []
    visited: set[str] = set()

    def add_entity(entity: dict[str, Any]) -> str:
        identifier = require_iri(entity.get("@id"), "@id")
        if identifier in visited:
            return identifier
        visited.add(identifier)
        for class_name in _as_list(entity.get("@type", [])):
            class_iri = expand_class(class_name)
            _require_allowed(class_iri, allowed_classes, "class")
            axioms.append(f"ClassAssertion({render_iri(class_iri)} {render_iri(identifier)})")
        if "taskType" in entity:
            task_class = require_iri(entity["taskType"], "taskType")
            _require_allowed(task_class, allowed_classes, "class")
            axioms.append(f"ClassAssertion({render_iri(task_class)} {render_iri(identifier)})")
        for field, property_iri in OBJECT_PROPERTIES.items():
            if field not in entity:
                continue
            for value in _as_list(entity[field]):
                if isinstance(value, dict):
                    target = add_entity(value)
                elif isinstance(value, str):
                    target = require_iri(value, field)
                else:
                    continue
                _require_allowed(property_iri, allowed_object_properties, "object property")
                axioms.append(
                    f"ObjectPropertyAssertion({render_iri(property_iri)} "
                    f"{render_iri(identifier)} {render_iri(target)})"
                )
        return identifier

    add_entity(document)
    for assertion in document.get("semanticAssertions", []):
        assertion_type = assertion["assertionType"]
        if assertion_type == "ClassAssertion":
            class_iri = require_iri(assertion["class"], "class")
            _require_allowed(class_iri, allowed_classes, "class")
            axioms.append(
                f"ClassAssertion({render_iri(class_iri)} {render_iri(assertion['individual'])})"
            )
            continue
        property_iri = require_iri(assertion["property"], "property")
        _require_allowed(property_iri, allowed_object_properties, "object property")
        axioms.append(
            f"{assertion_type}({render_iri(property_iri)} {render_iri(assertion['subject'])} "
            f"{render_iri(assertion['object'])})"
        )
    return axioms


def instance_probe_axiom(individual: str, class_iri: str, *, negated: bool) -> str:
    expression = render_iri(require_iri(class_iri, "class IRI"))
    if negated:
        expression = f"ObjectComplementOf({expression})"
    return f"ClassAssertion({expression} {render_iri(require_iri(individual, 'individual IRI'))})"


def subsumption_probe_axiom(probe_iri: str, subclass_iri: str, superclass_iri: str) -> str:
    return (
        f"EquivalentClasses({render_iri(probe_iri)} "
        f"ObjectIntersectionOf({render_iri(subclass_iri)} "
        f"ObjectComplementOf({render_iri(superclass_iri)})))"
    )


def expand_class(value: str) -> str:
    if value in COMPACT_IRIS:
        return COMPACT_IRIS[value]
    return require_iri(value, "@type")


def require_iri(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise FunctionalSyntaxError(f"{field} must be an absolute IRI")
    parsed = urlparse(value)
    if not parsed.scheme or any(character in value for character in '<>"{}|\\^`'):
        raise FunctionalSyntaxError(f"{field} must be a safe absolute IRI: {value!r}")
    return value


def render_iri(value: str) -> str:
    return f"<{require_iri(value, 'IRI')}>"


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value]


def _require_allowed(value: str, allowed: set[str] | None, kind: str) -> None:
    if allowed is not None and value not in allowed:
        raise FunctionalSyntaxError(f"message asserts a non-allowlisted {kind}: {value}")

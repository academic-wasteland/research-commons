"""Checked builders and a checker for receiver-authored OWL axioms.

A receiving node sometimes needs to tell the reasoner more than "this
individual is in that class": a closure over the credentials it verified, a
scope axiom that ties coverage to one credential, the negation of a fact it
knows about its own holdings. Those axioms are written by the receiver, never
by the sender, but they still pass through this module: builders render every
IRI through the checked serializer, and `check_axiom` accepts only a small,
import-free fragment (no prefixes, no literals, no annotations, one axiom per
string) so a bug or a hostile value cannot smuggle ontology structure in.
"""

import re

from .ofn import FunctionalSyntaxError, render_iri

NOTHING = "owl:Nothing"
THING = "owl:Thing"

AXIOM_FUNCTIONS = frozenset(
    {
        "ClassAssertion",
        "ObjectPropertyAssertion",
        "NegativeObjectPropertyAssertion",
        "SubClassOf",
        "EquivalentClasses",
        "DisjointClasses",
        "DifferentIndividuals",
    }
)
EXPRESSION_FUNCTIONS = frozenset(
    {
        "ObjectIntersectionOf",
        "ObjectUnionOf",
        "ObjectComplementOf",
        "ObjectOneOf",
        "ObjectSomeValuesFrom",
        "ObjectAllValuesFrom",
        "ObjectHasValue",
        "ObjectInverseOf",
    }
)
_TOKEN = re.compile(r"<[^<>\s]*>|owl:Nothing|owl:Thing|[A-Za-z]+\(|\)|\s+")
MAX_AXIOM_CHARS = 20000


def _ref(value: str) -> str:
    if value in (NOTHING, THING):
        return value
    if value.startswith("<") and value.endswith(">"):
        return render_iri(value[1:-1])
    if _is_expression(value):
        return value
    return render_iri(value)


def _is_expression(value: str) -> bool:
    name = value.split("(", 1)[0]
    return "(" in value and name in EXPRESSION_FUNCTIONS


def iri(value: str) -> str:
    return render_iri(value)


def one_of(*individuals: str) -> str:
    if not individuals:
        return NOTHING
    return f"ObjectOneOf({' '.join(render_iri(item) for item in individuals)})"


def some(prop: str, filler: str) -> str:
    return f"ObjectSomeValuesFrom({render_iri(prop)} {_ref(filler)})"


def only(prop: str, filler: str) -> str:
    return f"ObjectAllValuesFrom({render_iri(prop)} {_ref(filler)})"


def has_value(prop: str, individual: str) -> str:
    return f"ObjectHasValue({render_iri(prop)} {render_iri(individual)})"


def intersection(*classes: str) -> str:
    if len(classes) == 1:
        return _ref(classes[0])
    return f"ObjectIntersectionOf({' '.join(_ref(item) for item in classes)})"


def union(*classes: str) -> str:
    if len(classes) == 1:
        return _ref(classes[0])
    return f"ObjectUnionOf({' '.join(_ref(item) for item in classes)})"


def complement(expression: str) -> str:
    return f"ObjectComplementOf({_ref(expression)})"


def class_assertion(expression: str, individual: str) -> str:
    return f"ClassAssertion({_ref(expression)} {render_iri(individual)})"


def property_assertion(prop: str, subject: str, obj: str) -> str:
    return f"ObjectPropertyAssertion({render_iri(prop)} {render_iri(subject)} {render_iri(obj)})"


def subclass_of(sub: str, sup: str) -> str:
    return f"SubClassOf({_ref(sub)} {_ref(sup)})"


def check_axiom(axiom: str) -> str:
    """Return `axiom` stripped if it is one axiom of the accepted fragment, else raise."""
    if not isinstance(axiom, str):
        raise FunctionalSyntaxError("receiver axiom must be a string")
    text = axiom.strip()
    if not text or len(text) > MAX_AXIOM_CHARS:
        raise FunctionalSyntaxError("receiver axiom is empty or too long")
    position = 0
    depth = 0
    closed_top = False
    first = True
    for match in _TOKEN.finditer(text):
        if match.start() != position:
            raise FunctionalSyntaxError(f"receiver axiom has unexpected text at {position}: {text[position:position + 40]!r}")
        token = match.group(0)
        position = match.end()
        if token.isspace():
            continue
        if closed_top:
            raise FunctionalSyntaxError("receiver axiom must contain exactly one axiom")
        if token.endswith("("):
            name = token[:-1]
            if first:
                if name not in AXIOM_FUNCTIONS:
                    raise FunctionalSyntaxError(f"receiver axiom kind {name} is not allowed")
            elif name not in EXPRESSION_FUNCTIONS:
                raise FunctionalSyntaxError(f"construct {name} is not allowed inside a receiver axiom")
            depth += 1
        elif token == ")":
            depth -= 1
            if depth < 0:
                raise FunctionalSyntaxError("receiver axiom has unbalanced parentheses")
            if depth == 0:
                closed_top = True
        elif token.startswith("<"):
            if depth == 0:
                raise FunctionalSyntaxError("receiver axiom must start with an axiom function")
            render_iri(token[1:-1])
        elif depth == 0:
            raise FunctionalSyntaxError("receiver axiom must start with an axiom function")
        first = False
    if position != len(text):
        raise FunctionalSyntaxError(f"receiver axiom has unexpected text at {position}")
    if depth != 0 or not closed_top:
        raise FunctionalSyntaxError("receiver axiom has unbalanced parentheses")
    return text

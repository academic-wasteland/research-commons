import copy
import json
from dataclasses import dataclass
from typing import Any

from pyshacl import validate
from rdflib import Graph

from .constants import SPEC_ROOT
from .schema import load_json


@dataclass(frozen=True)
class ShaclResult:
    conforms: bool
    report: str


def message_graph(document: dict[str, Any]) -> Graph:
    expanded = copy.deepcopy(document)
    local_context = load_json(SPEC_ROOT / "context.jsonld")["@context"]
    expanded["@context"] = local_context
    graph = Graph()
    graph.parse(data=json.dumps(expanded), format="json-ld")
    return graph


def validate_shacl(document: dict[str, Any]) -> ShaclResult:
    data_graph = message_graph(document)
    shapes_graph = Graph().parse(SPEC_ROOT / "shapes.ttl", format="turtle")
    ontology_graph = Graph().parse(SPEC_ROOT / "vocabulary.ttl", format="turtle")
    conforms, _, report = validate(
        data_graph,
        shacl_graph=shapes_graph,
        ont_graph=ontology_graph,
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
    )
    return ShaclResult(bool(conforms), str(report))

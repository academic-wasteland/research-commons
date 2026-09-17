"""RDF and SHACL validation for Research Commons Protocol messages and carriers."""

import copy
import json
from dataclasses import dataclass
from typing import Any

from pyshacl import validate
from rdflib import Graph

from .constants import RO_CRATE_BASE_CONTEXT, SPEC_ROOT
from .schema import load_json


@dataclass(frozen=True)
class ShaclResult:
    conforms: bool
    report: str


def message_graph(document: dict[str, Any]) -> Graph:
    """Build RDF Graph for an RCP message document."""
    expanded = copy.deepcopy(document)
    local_context = load_json(SPEC_ROOT / "context.jsonld")["@context"]
    expanded["@context"] = local_context
    graph = Graph()
    graph.parse(data=json.dumps(expanded), format="json-ld")
    return graph


def validate_shacl(document: dict[str, Any]) -> ShaclResult:
    """Validate RCP message graph against RCP SHACL shapes."""
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


def ro_crate_graph(metadata: dict[str, Any]) -> Graph:
    """Build RDF Graph for an RO-Crate metadata document using local context definitions."""
    expanded = copy.deepcopy(metadata)
    local_rcp_context = load_json(SPEC_ROOT / "context.jsonld")["@context"]
    # Preserve standard JSON-LD semantics by following the serialized context array:
    # RO-Crate base context, then RCP context, then explicit preservation of schema:object.
    crate_context: list[Any] = [
        RO_CRATE_BASE_CONTEXT,
        local_rcp_context,
        {"object": {"@id": "schema:object", "@type": "@id"}},
    ]
    expanded["@context"] = crate_context
    graph = Graph()
    graph.parse(data=json.dumps(expanded), format="json-ld")
    return graph


def validate_crate_shacl(metadata: dict[str, Any]) -> ShaclResult:
    """Validate RO-Crate carrier graph against carrier SHACL shapes."""
    data_graph = ro_crate_graph(metadata)
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


# Backwards compatibility re-exports for RO-Crate carrier functions
from .ro_crate import (
    ROCrateBuilder,
    build_crate,
    from_crate,
    to_crate,
    unpack_and_verify_crate,
)

__all__ = [
    "ROCrateBuilder",
    "ShaclResult",
    "build_crate",
    "from_crate",
    "message_graph",
    "ro_crate_graph",
    "to_crate",
    "unpack_and_verify_crate",
    "validate_crate_shacl",
    "validate_shacl",
]

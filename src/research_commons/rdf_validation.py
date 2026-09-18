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


def _validate_and_resolve_context_element(
    ctx: Any,
    expected_iris: set[str],
    local_rcp_context: dict[str, Any],
) -> Any:
    if isinstance(ctx, str):
        if ctx not in expected_iris:
            raise ValueError(f"Unsupported external context in RO-Crate metadata: {ctx}")
        if ctx == "https://w3id.org/ro/crate/1.1/context":
            return RO_CRATE_BASE_CONTEXT
        if ctx == "https://w3id.org/research-commons/v0.1/context.jsonld":
            return local_rcp_context
        return ctx
    if isinstance(ctx, dict):
        expected_overrides = {
            "object": {"@id": "http://schema.org/object", "@type": "@id"},
            "name": "http://schema.org/name",
            "license": {"@id": "http://schema.org/license", "@type": "@id"},
        }
        for key, val in ctx.items():
            if key not in expected_overrides or val != expected_overrides[key]:
                raise ValueError(f"Unsupported context term override in RO-Crate metadata: {key}={val}")
        return ctx
    raise TypeError(f"Unsupported context entry in RO-Crate metadata: {ctx!r}")


def _recursively_sanitize_contexts(
    node: Any,
    expected_iris: set[str],
    local_rcp_context: dict[str, Any],
) -> Any:
    if isinstance(node, dict):
        sanitized = {}
        for key, val in node.items():
            if key == "@context":
                if isinstance(val, list):
                    sanitized[key] = [
                        _validate_and_resolve_context_element(elem, expected_iris, local_rcp_context)
                        for elem in val
                    ]
                else:
                    sanitized[key] = _validate_and_resolve_context_element(
                        val, expected_iris, local_rcp_context
                    )
            else:
                sanitized[key] = _recursively_sanitize_contexts(val, expected_iris, local_rcp_context)
        return sanitized
    if isinstance(node, list):
        return [
            _recursively_sanitize_contexts(item, expected_iris, local_rcp_context)
            for item in node
        ]
    return node


def ro_crate_graph(metadata: dict[str, Any]) -> Graph:
    """Build RDF Graph for an RO-Crate metadata document using local context definitions."""
    # Ensure declared top-level @context does not contain unsupported or overriding external contexts
    declared_context = metadata.get("@context")
    if not isinstance(declared_context, list):
        raise TypeError("RO-Crate metadata must have a list @context")

    expected_iris = {
        "https://w3id.org/ro/crate/1.1/context",
        "https://w3id.org/research-commons/v0.1/context.jsonld",
    }
    local_rcp_context = load_json(SPEC_ROOT / "context.jsonld")["@context"]

    # Recursively validate and resolve @context at top level and any nested entities
    expanded = _recursively_sanitize_contexts(metadata, expected_iris, local_rcp_context)
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
        advanced=True,
    )
    return ShaclResult(bool(conforms), str(report))


# Backwards compatibility re-exports for RO-Crate carrier functions
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ro_crate import (
        ROCrateBuilder,
        build_crate,
        from_crate,
        to_crate,
        unpack_and_verify_crate,
    )


def __getattr__(name: str) -> Any:
    if name in {"ROCrateBuilder", "build_crate", "from_crate", "to_crate", "unpack_and_verify_crate"}:
        from . import ro_crate

        return getattr(ro_crate, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)


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

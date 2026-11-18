"""RDF and SHACL validation for Research Commons Protocol messages and carriers."""

import copy
import json
from dataclasses import dataclass
from typing import Any

from pyshacl import validate
from rdflib import Graph

from .constants import (
    CARRIER_CONTEXT,
    RO_CRATE_BASE_CONTEXT,
    RO_CRATE_CONTEXT_IRI,
    SPEC_ROOT,
)
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


def _validate_and_resolve_context_element(ctx: Any) -> Any:
    if isinstance(ctx, str):
        if ctx != RO_CRATE_CONTEXT_IRI:
            raise ValueError(f"Unsupported external context in RO-Crate metadata: {ctx}")
        # The vendored copy is the RO-Crate 1.1 context document itself; using it avoids
        # a network lookup without changing any term definition.
        return RO_CRATE_BASE_CONTEXT
    if isinstance(ctx, dict):
        if ctx != CARRIER_CONTEXT:
            raise ValueError(f"Unsupported inline context in RO-Crate metadata: {ctx!r}")
        return ctx
    raise TypeError(f"Unsupported context entry in RO-Crate metadata: {ctx!r}")


def _reject_nested_contexts(node: Any) -> None:
    if isinstance(node, dict):
        if "@context" in node:
            raise ValueError("Nested @context is not allowed in RO-Crate carrier metadata")
        for val in node.values():
            _reject_nested_contexts(val)
    elif isinstance(node, list):
        for item in node:
            _reject_nested_contexts(item)


def ro_crate_graph(metadata: dict[str, Any]) -> Graph:
    """Build RDF Graph for an RO-Crate metadata document.

    Only a top-level @context made of the RO-Crate 1.1 context IRI (resolved from its
    vendored copy) and the inline carrier context is accepted; nested @context entries
    and any other context are rejected. Parsing therefore never fetches remote contexts,
    cannot be inflated by repeated context expansion, and uses the same term definitions
    a standard JSON-LD processor would use.
    """
    declared_context = metadata.get("@context")
    if not isinstance(declared_context, list):
        raise TypeError("RO-Crate metadata must have a list @context")

    for key, val in metadata.items():
        if key != "@context":
            _reject_nested_contexts(val)
    expanded = {
        **metadata,
        "@context": [_validate_and_resolve_context_element(elem) for elem in declared_context],
    }
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

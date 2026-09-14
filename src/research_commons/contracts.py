import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import load_json, validate_against


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class ContractManifest:
    path: Path
    data: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "ContractManifest":
        resolved = path.resolve()
        data = load_json(resolved)
        validate_against(data, "contract-manifest.schema.json")
        manifest = cls(resolved, data)
        manifest.verify()
        return manifest

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def bundle_digest(self) -> str:
        return self.data["bundleDigest"]

    @property
    def timeout_seconds(self) -> int:
        return self.data["limits"]["timeoutSeconds"]

    def ontology_paths(self) -> list[Path]:
        base = self.path.parent.resolve()
        paths: list[Path] = []
        for ontology in self.data["ontologies"]:
            candidate = (base / ontology["path"]).resolve()
            if not candidate.is_relative_to(base):
                raise ContractError(f"ontology path escapes manifest directory: {candidate}")
            paths.append(candidate)
        return paths

    def verify(self) -> None:
        entries: list[tuple[str, str]] = []
        paths = self.ontology_paths()
        for ontology, path in zip(self.data["ontologies"], paths, strict=True):
            if not path.is_file():
                raise ContractError(f"ontology file not found: {path}")
            if "Import(" in path.read_text(encoding="utf-8"):
                raise ContractError(f"contract ontology must be flattened and import-free: {path.name}")
            digest = sha256_file(path)
            if digest != ontology["digest"]:
                raise ContractError(f"digest mismatch for {path.name}: {digest}")
            entries.append((ontology["id"], digest))
        actual_bundle = bundle_digest(entries)
        if actual_bundle != self.bundle_digest:
            raise ContractError(
                f"bundle digest mismatch: expected {self.bundle_digest}, got {actual_bundle}"
            )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def bundle_digest(entries: list[tuple[str, str]]) -> str:
    canonical = "".join(f"{identifier}\0{digest}\n" for identifier, digest in sorted(entries))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

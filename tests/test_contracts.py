import json

import pytest

from research_commons.contracts import ContractError, ContractManifest


def test_manifest_verifies_digest(repository_root):
    manifest = ContractManifest.load(repository_root / "examples/contracts/public-research.contract.json")
    assert manifest.bundle_digest.startswith("sha256:")


def test_manifest_rejects_tampered_ontology(repository_root, tmp_path):
    source_manifest = repository_root / "examples/contracts/public-research.contract.json"
    source_ontology = repository_root / "examples/contracts/public-research.ofn"
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    (tmp_path / "public-research.ofn").write_text(
        source_ontology.read_text(encoding="utf-8") + "\n# tampered\n",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ContractError, match="digest mismatch"):
        ContractManifest.load(manifest_path)


def test_manifest_rejects_path_escape(repository_root, tmp_path):
    manifest = json.loads(
        (repository_root / "examples/contracts/public-research.contract.json").read_text(encoding="utf-8")
    )
    manifest["ontologies"][0]["path"] = "../outside.ofn"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ContractError, match="escapes"):
        ContractManifest.load(manifest_path)

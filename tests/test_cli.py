"""Tests of the command-line interface."""

import json
import subprocess
import sys

import pytest


@pytest.mark.parametrize("document", ["[1, 2]", '{"@type": [1]}', '"text"', "{"])
def test_to_completion_reports_malformed_input(tmp_path, document):
    source = tmp_path / "doc.jsonld"
    source.write_text(document, encoding="utf-8")
    crate_out = tmp_path / "crate.zip"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "research_commons.cli",
            "to-completion",
            str(source),
            "--completed-by",
            "rig-1",
            "--crate-out",
            str(crate_out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout)["status"] == "invalid"
    assert "Traceback" not in result.stderr
    assert not crate_out.exists()

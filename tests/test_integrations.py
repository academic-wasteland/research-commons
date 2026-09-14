import tomllib
from itertools import pairwise

from research_commons.schema import load_json, validate_against

REQUIRED_STEP_ORDER = [
    "recover-task",
    "validate-shape",
    "semantic-gate",
    "execute",
    "package-contribution",
    "independent-validation",
    "publish",
]


def test_integration_toml_files_parse(repository_root):
    files = list((repository_root / "integrations").rglob("*.toml"))
    assert files
    for path in files:
        with path.open("rb") as stream:
            tomllib.load(stream)


def test_beads_formula_orders_gate_before_execution(repository_root):
    path = repository_root / "integrations/beads/formulas/rcp-task.formula.toml"
    with path.open("rb") as stream:
        formula = tomllib.load(stream)
    assert formula["formula"] == "rcp-task"
    steps = {step["id"]: step for step in formula["steps"]}
    assert list(steps) == REQUIRED_STEP_ORDER
    for previous, current in pairwise(REQUIRED_STEP_ORDER):
        assert steps[current]["needs"] == [previous]
    assert steps["independent-validation"]["gate"]["type"] == "human"
    assert formula["vars"]["task_bead"]["required"] is True
    assert formula["vars"]["manifest"]["required"] is True


def test_gascity_pack_declares_checked_gate(repository_root):
    pack_root = repository_root / "integrations/gascity/rcp-pack"
    with (pack_root / "pack.toml").open("rb") as stream:
        pack = tomllib.load(stream)
    assert pack["pack"]["schema"] == 2
    assert pack["pack"]["requires"][0]["agent"] == "rcp-worker"
    assert (pack_root / "agents/rcp-worker/prompt.template.md").exists()
    with (pack_root / "formulas/rcp-task.formula.toml").open("rb") as stream:
        formula = tomllib.load(stream)
    gate = next(step for step in formula["steps"] if step["id"] == "gate")
    assert gate["check"]["check"]["mode"] == "exec"
    assert (pack_root / gate["check"]["check"]["path"]).exists()
    execute = next(step for step in formula["steps"] if step["id"] == "execute")
    assert execute["needs"] == ["gate"]
    for script in pack_root.rglob("*.sh"):
        assert script.stat().st_mode & 0o111, f"{script} is not executable"


def test_bdp_type_descriptors_reference_shipped_schemas(repository_root):
    descriptors = load_json(repository_root / "integrations/bdp/rcp-types.json")["types"]
    message_schema = load_json(repository_root / "spec/message.schema.json")
    for descriptor in descriptors:
        assert descriptor["describes"] in {"bead", "link"}
        schema_ref = descriptor.get("propertiesSchema")
        if schema_ref and "#/$defs/" in schema_ref:
            assert schema_ref.rsplit("/", 1)[1] in message_schema["$defs"]


def test_validation_report_example_validates(repository_root):
    validate_against(
        load_json(repository_root / "examples/messaging/validation-report.json"),
        "semantic-validation-report.schema.json",
    )


def test_wasteland_example_sql_has_three_upserts(repository_root):
    statements = [
        line
        for line in (repository_root / "integrations/wasteland/example.sql").read_text().splitlines()
        if line.startswith("INSERT INTO")
    ]
    assert [line.split("`")[1] for line in statements] == ["wanted", "completions", "stamps"]
    assert all("ON DUPLICATE KEY UPDATE" in line for line in statements)

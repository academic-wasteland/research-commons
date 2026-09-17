import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .constants import SPEC_ROOT

_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("date-time")
def _check_datetime(instance: Any) -> bool:
    if not isinstance(instance, str):
        return True
    try:
        # ISO-8601 / RFC-3339 datetime
        datetime.fromisoformat(instance)
        return True
    except (ValueError, TypeError):
        return False


@_FORMAT_CHECKER.checks("date")
def _check_date(instance: Any) -> bool:
    if not isinstance(instance, str):
        return True
    try:
        date.fromisoformat(instance)
        return True
    except (ValueError, TypeError):
        return False


class StructuralValidationError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise StructuralValidationError(f"{path} must contain a JSON object")
    return value


def validate_against(document: dict[str, Any], schema_name: str) -> None:
    schema = load_json(SPEC_ROOT / schema_name)
    validator = Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(_format_error(error) for error in errors)
        raise StructuralValidationError(details)


def validate_message(document: dict[str, Any]) -> None:
    validate_against(document, "message.schema.json")


def _format_error(error: Any) -> str:
    location = ".".join(str(part) for part in error.absolute_path) or "$"
    if error.context:
        alternatives = " | ".join(child.message for child in error.context[:3])
        return f"{location}: {alternatives}"
    return f"{location}: {error.message}"

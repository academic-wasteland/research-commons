import json
import os
import re
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

try:
    import resource
except ImportError:  # pragma: no cover - KM currently targets Unix-like systems
    resource = None


class ReasonerError(RuntimeError):
    pass


@dataclass(frozen=True)
class Classification:
    consistent: bool
    unsatisfiable: frozenset[str]
    subsumptions: dict[str, frozenset[str]]
    duration_ms: int


class Reasoner(Protocol):
    name: str
    version: str

    def classify(self, ontology: str) -> Classification: ...


class KMRunner:
    name = "Kobayashi-MaRust"

    def __init__(
        self,
        executable: str = "km",
        *,
        timeout_seconds: int = 30,
        max_memory_mb: int = 2048,
        version: str | None = None,
    ) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.version = version or os.environ.get("KM_VERSION", "unreported")

    def classify(self, ontology: str) -> Classification:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="rcp-km-") as directory:
            ontology_path = Path(directory) / "query.ofn"
            ontology_path.write_text(ontology, encoding="utf-8")
            try:
                process = subprocess.Popen(
                    [self.executable, "classify", str(ontology_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=os.name == "posix",
                )
            except FileNotFoundError as error:
                raise ReasonerError(f"KM executable not found: {self.executable}") from error
            if resource is not None and hasattr(resource, "prlimit"):
                try:
                    memory_bytes = self.max_memory_mb * 1024 * 1024
                    resource.prlimit(process.pid, resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                except ProcessLookupError:
                    pass
            try:
                stdout, stderr = process.communicate(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired as error:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:  # pragma: no cover - KM currently targets Unix-like systems
                    process.kill()
                process.communicate()
                raise ReasonerError(f"KM exceeded {self.timeout_seconds}s timeout") from error
        duration_ms = round((time.monotonic() - started) * 1000)
        if process.returncode != 0:
            diagnostic = stderr.strip() or f"exit status {process.returncode}"
            raise ReasonerError(f"KM failed: {diagnostic}")
        try:
            output = json.loads(stdout)
        except json.JSONDecodeError as error:
            raise ReasonerError("KM returned malformed JSON") from error
        return _classification_from_json(output, duration_ms, prefixes=ontology_prefixes(ontology))

_PREFIX_LINE = re.compile(r"^\s*Prefix\(\s*([A-Za-z0-9_.-]*):=<([^>]+)>\s*\)", re.MULTILINE)


def ontology_prefixes(ontology: str) -> dict[str, str]:
    """Prefix declarations of a Functional Syntax document, used to expand KM's prefixed names."""
    return {match.group(1): match.group(2) for match in _PREFIX_LINE.finditer(ontology)}


def expand_name(name: str, prefixes: dict[str, str]) -> str:
    """Expand `pg:Class` with a declared prefix; leave full IRIs and undeclared names untouched."""
    if name.startswith("<") and name.endswith(">"):
        return name[1:-1]
    prefix, separator, local = name.partition(":")
    if separator and prefix in prefixes and "/" not in prefix:
        return prefixes[prefix] + local
    return name


def _classification_from_json(
    output: object, duration_ms: int, *, prefixes: dict[str, str] | None = None
) -> Classification:
    if not isinstance(output, dict):
        raise ReasonerError("KM output must be a JSON object")
    if "consistent" in output:
        consistent = output["consistent"]
    elif "inconsistent" in output:
        consistent = not output["inconsistent"]
    else:
        raise ReasonerError("KM output lacks consistency status")
    if not isinstance(consistent, bool):
        raise ReasonerError("KM consistency status must be Boolean")
    prefixes = prefixes or {}
    unsatisfiable = output.get("unsatisfiable", [])
    subsumptions = output.get("subsumptions", {})
    if not isinstance(unsatisfiable, list) or not isinstance(subsumptions, dict | list):
        raise ReasonerError("KM output has invalid classification collections")
    if isinstance(subsumptions, list):
        # KM >= 1.3 emits [sub, super] pairs; older builds emitted {sub: [supers]}.
        pairs: dict[str, list[str]] = {}
        for pair in subsumptions:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ReasonerError("KM subsumption pairs must be [sub, super] arrays")
            pairs.setdefault(str(pair[0]), []).append(str(pair[1]))
        subsumptions = pairs
    normalized: dict[str, frozenset[str]] = {}
    for subject, supers in subsumptions.items():
        if not isinstance(subject, str) or not isinstance(supers, list):
            raise ReasonerError("KM subsumptions must map strings to string arrays")
        names = {str(value) for value in supers}
        names |= {expand_name(value, prefixes) for value in list(names)}
        expanded_subject = expand_name(subject, prefixes)
        normalized[expanded_subject] = frozenset(names)
        if expanded_subject != subject:
            normalized[subject] = normalized[expanded_subject]
    unsatisfiable_names = {str(value) for value in unsatisfiable}
    unsatisfiable_names |= {expand_name(value, prefixes) for value in list(unsatisfiable_names)}
    return Classification(
        consistent=consistent,
        unsatisfiable=frozenset(unsatisfiable_names),
        subsumptions=normalized,
        duration_ms=duration_ms,
    )

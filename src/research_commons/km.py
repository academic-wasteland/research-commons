import json
import os
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
        return _classification_from_json(output, duration_ms)

def _classification_from_json(output: object, duration_ms: int) -> Classification:
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
    unsatisfiable = output.get("unsatisfiable", [])
    subsumptions = output.get("subsumptions", {})
    if not isinstance(unsatisfiable, list) or not isinstance(subsumptions, dict):
        raise ReasonerError("KM output has invalid classification collections")
    normalized: dict[str, frozenset[str]] = {}
    for subject, supers in subsumptions.items():
        if not isinstance(subject, str) or not isinstance(supers, list):
            raise ReasonerError("KM subsumptions must map strings to string arrays")
        normalized[subject] = frozenset(str(value) for value in supers)
    return Classification(
        consistent=consistent,
        unsatisfiable=frozenset(str(value) for value in unsatisfiable),
        subsumptions=normalized,
        duration_ms=duration_ms,
    )

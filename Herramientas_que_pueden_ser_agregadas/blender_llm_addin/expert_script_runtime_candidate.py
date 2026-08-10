"""Candidate expert-script runtime derived from ideas in mac999/blender-llm-addin.

This file is intentionally NOT wired into MCP or the active Blender bridge.
It is a staging candidate for a future privileged Expert Execution Lane.

Responsibilities kept from the upstream concept:
- extract generated Python;
- parse/compile before execution;
- execute only when explicitly marked trusted;
- capture stdout/stderr/traceback;
- support bounded retry through a caller-provided fixer callback.

Responsibilities deliberately excluded:
- model/API clients;
- Blender UI;
- API keys;
- transport/authentication;
- automatic enablement of arbitrary Python execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import ast
from contextlib import redirect_stderr, redirect_stdout
import io
import re
import traceback as traceback_module
from types import CodeType
from typing import Callable, Mapping, MutableMapping


PYTHON_FENCE_RE = re.compile(
    r"```(?:python|py)?\s*\n(?P<code>.*?)```",
    re.IGNORECASE | re.DOTALL,
)


class ExpertExecutionDisabled(PermissionError):
    """Raised when arbitrary Python execution was not explicitly enabled."""


@dataclass(slots=True)
class ScriptAttemptResult:
    attempt: int
    ok: bool
    source: str
    stdout: str = ""
    stderr: str = ""
    exception_type: str | None = None
    exception_message: str | None = None
    traceback: str | None = None


@dataclass(slots=True)
class ScriptExecutionResult:
    ok: bool
    attempts: list[ScriptAttemptResult] = field(default_factory=list)

    @property
    def final(self) -> ScriptAttemptResult | None:
        return self.attempts[-1] if self.attempts else None


Fixer = Callable[[str, ScriptAttemptResult], str]


def extract_python_source(text: str) -> str:
    """Extract the first fenced Python block, otherwise treat the input as source.

    Unlike the upstream regex, this accepts ```python, ```py and an unfenced script.
    It never executes the returned text.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    match = PYTHON_FENCE_RE.search(text)
    source = match.group("code") if match else text
    source = source.replace("\t", "    ").strip()
    if not source:
        raise ValueError("No Python source was found")
    return source


def parse_python_source(source: str) -> ast.Module:
    """Parse source and fail before execution when syntax is invalid."""
    return ast.parse(source, mode="exec")


def compile_python_source(source: str, *, filename: str = "<harness-expert-script>") -> CodeType:
    """Parse and compile source without executing it."""
    tree = parse_python_source(source)
    return compile(tree, filename, "exec")


def execute_trusted_python(
    source: str,
    *,
    trusted: bool = False,
    attempt: int = 1,
    filename: str = "<harness-expert-script>",
    globals_ns: MutableMapping[str, object] | None = None,
    locals_ns: MutableMapping[str, object] | None = None,
) -> ScriptAttemptResult:
    """Execute Python only when the caller explicitly enables trusted mode.

    This is deliberately a sharp tool. It provides no sandbox and must never be
    exposed as a normal unauthenticated MCP operation. In a future integration,
    the Harness should call it only after its own authentication, workspace,
    policy and main-thread checks.
    """
    if not trusted:
        raise ExpertExecutionDisabled(
            "Arbitrary Python execution is disabled; pass trusted=True only from a privileged harness path"
        )

    code = compile_python_source(source, filename=filename)

    if globals_ns is None:
        globals_ns = {"__name__": "__harness_expert_script__"}
    if locals_ns is None:
        locals_ns = globals_ns

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    try:
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(code, globals_ns, locals_ns)
        return ScriptAttemptResult(
            attempt=attempt,
            ok=True,
            source=source,
            stdout=stdout_buffer.getvalue(),
            stderr=stderr_buffer.getvalue(),
        )
    except BaseException as exc:  # capture Blender/Python runtime failures for the agent
        return ScriptAttemptResult(
            attempt=attempt,
            ok=False,
            source=source,
            stdout=stdout_buffer.getvalue(),
            stderr=stderr_buffer.getvalue(),
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            traceback="".join(
                traceback_module.format_exception(type(exc), exc, exc.__traceback__)
            ),
        )


def execute_with_fixer(
    generated_text: str,
    *,
    fixer: Fixer,
    trusted: bool = False,
    max_attempts: int = 3,
    filename: str = "<harness-expert-script>",
    globals_ns: MutableMapping[str, object] | None = None,
    locals_ns: MutableMapping[str, object] | None = None,
) -> ScriptExecutionResult:
    """Execute generated Python and ask a caller-provided fixer for corrections.

    `fixer` is intentionally model-agnostic. Codex, Claude, Kimi or another agent
    can implement it outside Blender. The runtime itself makes no network calls.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    source = extract_python_source(generated_text)
    result = ScriptExecutionResult(ok=False)

    for attempt_number in range(1, max_attempts + 1):
        attempt = execute_trusted_python(
            source,
            trusted=trusted,
            attempt=attempt_number,
            filename=filename,
            globals_ns=globals_ns,
            locals_ns=locals_ns,
        )
        result.attempts.append(attempt)

        if attempt.ok:
            result.ok = True
            return result

        if attempt_number >= max_attempts:
            break

        replacement = fixer(source, attempt)
        source = extract_python_source(replacement)

    return result


def blender_default_namespace() -> dict[str, object]:
    """Build a useful namespace when this candidate is evaluated inside Blender.

    Imports are local so this staging module remains importable outside Blender.
    """
    try:
        import bpy  # type: ignore
        import bmesh  # type: ignore
        import mathutils  # type: ignore
    except ImportError as exc:
        raise RuntimeError("blender_default_namespace() must run inside Blender") from exc

    return {
        "__name__": "__harness_expert_script__",
        "bpy": bpy,
        "bmesh": bmesh,
        "mathutils": mathutils,
    }


# Integration contract intentionally absent:
# - no MCP registration
# - no socket transport
# - no filesystem access policy
# - no automatic retries against an LLM provider
# - no auto-save / auto-undo
# - no claim that successful execution implies a visually correct 3D result

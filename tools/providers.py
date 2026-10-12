"""CLI adapters. Task contracts and integration gates do not depend on a model SDK."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _toml(value: Any) -> str:
    """Encode our validated stdio server config as a TOML CLI override."""
    if isinstance(value, dict):
        fields = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("TOML table keys must be strings")
            encoded_key = key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else json.dumps(key, ensure_ascii=True)
            fields.append(f"{encoded_key} = {_toml(item)}")
        return "{ " + ", ".join(fields) + " }"
    if isinstance(value, list):
        return "[" + ",".join(_toml(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=True)


def build_command(settings: dict[str, Any], model: str, role: str,
                  workspace: Path, schema: Path, output: Path,
                  analysis_output: Path | None = None,
                  rea: dict[str, Any] | None = None) -> list[str]:
    command = settings.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(s, str) for s in command):
        raise ValueError("provider command must be a nonempty argv array")
    if role not in {"worker", "reviewer"} or not model.strip():
        raise ValueError("a role and explicit model are required")
    kind = settings["kind"]
    rea_tools = list(rea["tools"]) if rea else []
    if role == "reviewer" and "export_evidence_bundle" in rea_tools:
        rea_tools.remove("export_evidence_bundle")
    if kind == "codex":
        extra = ["--add-dir", str(analysis_output)] if role == "worker" and analysis_output else []
        windows_sandbox = settings.get("windows_sandbox")
        if windows_sandbox is not None:
            if not isinstance(windows_sandbox, str) or windows_sandbox not in {"mxc", "elevated", "unelevated"}:
                raise ValueError("windows_sandbox must select a supported bounded Windows sandbox")
            extra += ["-c", "windows.sandbox=" + _toml(windows_sandbox)]
        if rea:
            server = {**rea["server"], "enabled_tools": rea_tools,
                      "startup_timeout_sec": 60, "tool_timeout_sec": 300}
            extra += ["-c", "mcp_servers.rea=" + _toml(server)]
        return command + ["--ask-for-approval", "never", "exec", "--ephemeral", "--ignore-user-config",
                          "--cd", str(workspace), "--model", model,
                          "-c", 'default_permissions=":read-only"' if role == "reviewer" else 'default_permissions=":workspace"',
                          "-c", "agents.enabled=false", "--output-schema", str(schema),
                          "--output-last-message", str(output), *extra, "-"]
    if kind == "claude":
        tools = "Read,Glob,Grep" if role == "reviewer" else "Read,Glob,Grep,Edit,Write,Bash"
        allowed = tools + "".join(",mcp__rea__" + name for name in rea_tools)
        extra = ["--add-dir", str(analysis_output)] if role == "worker" and analysis_output else []
        return command + ["--print", "--output-format", "json", "--model", model,
                          "--json-schema", schema.read_text(encoding="utf-8"),
                          "--permission-mode", "dontAsk", "--tools", tools,
                          "--allowedTools", allowed, "--no-session-persistence",
                          "--strict-mcp-config", "--mcp-config",
                          json.dumps({"mcpServers": {"rea": rea["server"]} if rea else {}}), *extra]
    if kind == "command":
        # A custom adapter receives the prompt on stdin and writes contract JSON
        # to {output}. argv substitution never invokes a shell.
        values = {"model": model, "role": role, "workspace": str(workspace),
                  "schema": str(schema), "output": str(output),
                  "analysis": str(analysis_output) if analysis_output else "",
                  "rea_context": str(rea["evidence_path"]) if rea else ""}
        return [item.format_map(values) for item in command]
    raise ValueError(f"unknown provider kind: {kind}")


def validate_result(result: Any, role: str) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("provider result must be an object")
    if role == "worker":
        expected = {"status", "summary", "tests", "risks"}
        if set(result) != expected or result["status"] not in {"completed", "blocked"}:
            raise ValueError("invalid worker result")
        arrays = ("tests", "risks")
    else:
        expected = {"verdict", "summary", "findings"}
        if set(result) != expected or result["verdict"] not in {"approve", "request_changes"}:
            raise ValueError("invalid review result")
        arrays = ("findings",)
    if not isinstance(result["summary"], str) or not result["summary"].strip():
        raise ValueError("provider summary must be nonempty text")
    for name in arrays:
        if not isinstance(result[name], list) or not all(isinstance(s, str) for s in result[name]):
            raise ValueError(f"provider {name} must be a string array")
    return result


def run_provider(settings: dict[str, Any], model: str, role: str, workspace: Path,
                 schema: Path, directory: Path, prompt: str, timeout: int,
                 analysis_output: Path | None = None,
                 rea: dict[str, Any] | None = None) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False)
    output = directory / "result.json"
    command = build_command(settings, model, role, workspace, schema, output, analysis_output, rea)
    executable = shutil.which(command[0])
    if executable is None:
        raise RuntimeError(f"provider CLI is missing: {command[0]}")
    command[0] = executable
    (directory / "prompt.txt").write_text(prompt, encoding="utf-8")
    with (directory / "stdout.log").open("w", encoding="utf-8") as stdout, \
            (directory / "stderr.log").open("w", encoding="utf-8") as stderr:
        environment = os.environ.copy()
        if settings["kind"] == "codex":
            environment["CODEX_PERMISSION_PROFILE"] = ":read-only" if role == "reviewer" else ":workspace"
        completed = subprocess.run(command, cwd=workspace, input=prompt, text=True,
                                   encoding="utf-8", stdout=stdout, stderr=stderr,
                                   timeout=timeout, check=False, env=environment)
    if completed.returncode:
        raise RuntimeError(f"{role} provider failed ({completed.returncode}); inspect local {directory}")
    if settings["kind"] == "claude":
        envelope = json.loads((directory / "stdout.log").read_text(encoding="utf-8"))
        if envelope.get("is_error"):
            raise RuntimeError(f"Claude reported failure; inspect local {directory}")
        result = envelope.get("structured_output")
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else:
        result = json.loads(output.read_text(encoding="utf-8"))
    return validate_result(result, role)

"""Prepare private, static-only REA context for an explicitly opted-in task."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any


REA_TOOLS = [
    "open_binary", "close_binary", "binary_session", "binary_overview",
    "search_procedures", "list_procedures", "procedure_info", "procedure_assembly",
    "procedure_pseudo_code", "procedure_callers", "procedure_callees",
    "procedure_references", "search_strings", "list_strings", "read_bytes",
    "address_to_file_offset", "xrefs", "get_call_graph", "analyze_function",
    "export_evidence_bundle",
]
MANIFEST_TARGET = "PR2.exe"


def _is_reparse(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _check_path_components(path: Path, label: str) -> Path:
    cursor = Path(path.anchor)
    for part in path.parts[1:]:
        cursor = cursor / part
        if not cursor.exists() and not cursor.is_symlink():
            break
        if _is_reparse(cursor.lstat()):
            raise ValueError(f"REA blocked: {label} contains a symlink or reparse point")
    return path


def _load_server(root: Path, config: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    raw_path = config.get("rea_mcp_config", "local/rea.mcp.json")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("REA blocked: rea_mcp_config must be a local config path")
    path = Path(raw_path)
    path = path if path.is_absolute() else root / path
    path = Path(os.path.abspath(path))
    _check_path_components(path, "MCP config path")
    local = (root / "local").resolve(strict=False)
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(local)
    except ValueError as exc:
        raise ValueError("REA blocked: MCP config must stay under local/") from exc
    try:
        info = path.lstat()
        if _is_reparse(info) or not stat.S_ISREG(info.st_mode):
            raise ValueError("REA blocked: MCP config must be a regular local file")
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"REA blocked: local MCP config is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("REA blocked: local MCP config is not valid JSON") from exc
    if not isinstance(document, dict) or set(document) != {"mcpServers"}:
        raise ValueError("REA blocked: MCP config must contain only mcpServers")
    servers = document["mcpServers"]
    if not isinstance(servers, dict) or set(servers) != {"rea"}:
        raise ValueError("REA blocked: configure exactly one local stdio server named rea")
    server = servers["rea"]
    allowed = {"command", "args", "env"}
    if not isinstance(server, dict) or not set(server).issubset(allowed) or "command" not in server:
        raise ValueError("REA blocked: rea server accepts only command, args, and env")
    command, args, env = server["command"], server.get("args", []), server.get("env", {})
    if not isinstance(command, str) or not command.strip() or _looks_like_url(command):
        raise ValueError("REA blocked: rea command must be a local executable, not a URL")
    if not isinstance(args, list) or any(not isinstance(arg, str) or _looks_like_url(arg) for arg in args):
        raise ValueError("REA blocked: rea args must be a string array without URLs")
    if not isinstance(env, dict) or any(
        not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
        or not isinstance(value, str) or _looks_like_url(value)
        for key, value in env.items()
    ):
        raise ValueError("REA blocked: rea env must map variable names to local string values")
    return {"command": command, "args": args, "env": env}, path


def _looks_like_url(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value))


def _target_info(root: Path, baseline: dict[str, Any]) -> dict[str, Any]:
    files = baseline.get("files") if isinstance(baseline, dict) else None
    if not isinstance(baseline, dict) or baseline.get("version") != 1 or not isinstance(files, dict):
        raise ValueError("REA blocked: invalid reference baseline")
    record = files.get(MANIFEST_TARGET)
    expected = record.get("sha256") if isinstance(record, dict) else None
    expected_size = record.get("size") if isinstance(record, dict) else None
    if (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)
            or type(expected_size) is not int or expected_size < 0):
        raise ValueError("REA blocked: baseline has no valid PR2.exe hash")
    install = root / "pr2"
    executable = install / MANIFEST_TARGET
    try:
        install_info = install.lstat()
        executable_info = executable.lstat()
    except OSError as exc:
        raise ValueError("REA blocked: fresh pr2/PR2.exe is unavailable") from exc
    if (_is_reparse(install_info) or not stat.S_ISDIR(install_info.st_mode)
            or _is_reparse(executable_info) or not stat.S_ISREG(executable_info.st_mode)):
        raise ValueError("REA blocked: pr2/PR2.exe must be a regular file in a real pr2 directory")
    digest = hashlib.sha256()
    with executable.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("REA blocked: fresh pr2/PR2.exe does not match the baseline")
    if expected_size != executable_info.st_size:
        raise ValueError("REA blocked: fresh pr2/PR2.exe size does not match the baseline")
    return {"path": str(executable.resolve(strict=True)), "relative_path": MANIFEST_TARGET,
            "size": executable_info.st_size, "baseline_verified": True, "sha256": expected}


def _write_evidence(run_dir: Path, evidence: dict[str, Any]) -> Path:
    run_dir = Path(os.path.abspath(run_dir))
    _check_path_components(run_dir, "run directory")
    if run_dir.exists():
        info = run_dir.lstat()
        if _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("REA blocked: run directory must be a real directory")
    else:
        run_dir.mkdir(parents=True)
    output = run_dir / "analysis"
    _check_path_components(output, "analysis output path")
    if output.exists():
        info = output.lstat()
        if _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("REA blocked: private analysis output must be a real directory")
    else:
        output.mkdir()
    _check_path_components(output, "analysis output path")
    target = output / "rea-context.json"
    with target.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    return target


def prepare_rea(root: Path, config: dict[str, Any], run_dir: Path,
                baseline: dict[str, Any]) -> dict[str, Any]:
    """Return the local REA stdio spec and private static-analysis task context."""
    root = Path(root).resolve(strict=True)
    run_raw = _check_path_components(Path(os.path.abspath(run_dir)), "run directory")
    run_dir = run_raw.resolve(strict=False)
    analysis_root = (root / "analysis").resolve(strict=False)
    if not run_dir.is_relative_to(analysis_root):
        raise ValueError("REA blocked: run output must stay under checkout-root analysis/")
    server, config_path = _load_server(root, config)
    target = _target_info(root, baseline)
    prompt = (
        "This task explicitly opted into local REA static analysis. Connect only to the configured local "
        "stdio server and use only the whitelisted tools in this context. Open the target executable read-only; "
        "do not execute it, extract files, request runtime data, annotate or mutate the program. Preserve raw "
        "tool output only under the supplied run directory's analysis/ folder. In findings, label each statement "
        "as an observation, inference, or unknown, and keep observations separate from interpretation. Public "
        "findings must be independently written summaries; do not publish raw decompiler output, strings, addresses, "
        "or evidence bundles. If Ghidra's native decompiler AppControl blocks an operation, report it blocked and "
        "stop that operation; do not bypass the block."
    )
    prompt += (f"\nOpen only this target with provider_id=ghidra, without importing a prior snapshot: "
               f"{json.dumps(target)}\nAll retained raw evidence goes to {run_dir / 'analysis'}.\n"
               "Verify the REA open_binary SHA-256 matches the supplied identity before inspecting code.\n")
    context = {"server": server, "tools": list(REA_TOOLS), "target": target,
               "config_path": str(config_path), "run_dir": str(Path(run_dir).resolve(strict=False)),
               "prompt": prompt}
    context["evidence_path"] = str(Path(run_dir).resolve(strict=False) / "analysis" / "rea-context.json")
    _write_evidence(Path(run_dir), context)
    return context


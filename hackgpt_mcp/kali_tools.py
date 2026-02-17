#!/usr/bin/env python3
"""
HackGPT – Kali Linux Tool Wrappers
====================================
Thin Python wrappers around Kali Linux CLI tools.
Each function runs the tool as a subprocess and returns structured output.

These wrappers are consumed by the MCP server (server.py) but can also be
used directly from any Python code:

    from mcp.kali_tools import nmap, nikto, sqlmap
    result = nmap("10.0.0.1", scan_type="-sV")
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("hackgpt.mcp.tools")

# ── Tunables (overridable via config / env) ──────────────────────────────────
COMMAND_TIMEOUT = int(os.getenv("MCP_COMMAND_TIMEOUT", "300"))
MAX_OUTPUT_BYTES = int(os.getenv("MCP_MAX_OUTPUT_BYTES", str(512 * 1024)))
RESULTS_DIR = Path(os.getenv("MCP_RESULTS_DIR", "/tmp/hackgpt-mcp-results"))
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ═════════════════════════════════════════════════════════════════════════════
# CORE RUNNER
# ═════════════════════════════════════════════════════════════════════════════


def run_shell(
    cmd: str | list[str],
    timeout: int = COMMAND_TIMEOUT,
    cwd: str | None = None,
) -> dict[str, Any]:
    """Execute a shell command and return structured output.

    Returns
    -------
    dict with keys: command, exit_code, stdout, stderr, elapsed_seconds
    """
    if isinstance(cmd, str):
        shell = True
        display_cmd = cmd
    else:
        shell = False
        display_cmd = " ".join(cmd)

    logger.info("exec ▸ %s", display_cmd)
    start = time.monotonic()

    try:
        proc = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        elapsed = round(time.monotonic() - start, 2)
        return {
            "command": display_cmd,
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "")[:MAX_OUTPUT_BYTES],
            "stderr": (proc.stderr or "")[:MAX_OUTPUT_BYTES],
            "elapsed_seconds": elapsed,
        }
    except subprocess.TimeoutExpired:
        return {
            "command": display_cmd,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "elapsed_seconds": timeout,
        }
    except FileNotFoundError:
        return {
            "command": display_cmd,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Tool not found. Ensure Kali tools are installed (apt install <tool>).",
            "elapsed_seconds": 0,
        }
    except Exception as exc:
        return {
            "command": display_cmd,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(exc),
            "elapsed_seconds": round(time.monotonic() - start, 2),
        }


def format_result(result: dict[str, Any]) -> str:
    """Format a run_shell result for human / AI consumption."""
    parts: list[str] = [
        f"$ {result['command']}",
        f"exit code: {result['exit_code']}  ({result['elapsed_seconds']}s)",
    ]
    if result["stdout"]:
        parts.append(f"\n─── stdout ───\n{result['stdout']}")
    if result["stderr"]:
        parts.append(f"\n─── stderr ───\n{result['stderr']}")
    return "\n".join(parts)


# ═════════════════════════════════════════════════════════════════════════════
# TOOL-SPECIFIC WRAPPERS
# ═════════════════════════════════════════════════════════════════════════════


def nmap(
    target: str,
    scan_type: str = "-sV -sC",
    ports: str = "",
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, Any]:
    """Run Nmap scan."""
    port_flag = f"-p {ports}" if ports else ""
    cmd = f"nmap {scan_type} {port_flag} {extra_args} {target}".strip()
    return run_shell(cmd, timeout=timeout)


def nikto(
    target: str,
    port: int = 80,
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, Any]:
    """Run Nikto web vulnerability scan."""
    cmd = f"nikto -h {target} -p {port} {extra_args}".strip()
    return run_shell(cmd, timeout=timeout)


def sqlmap(
    target_url: str,
    data: str = "",
    extra_args: str = "--batch --random-agent",
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, Any]:
    """Run SQLMap SQL-injection scan."""
    data_flag = f"--data={shlex.quote(data)}" if data else ""
    cmd = f"sqlmap -u {shlex.quote(target_url)} {data_flag} {extra_args}".strip()
    return run_shell(cmd, timeout=timeout)


def gobuster(
    target_url: str,
    mode: str = "dir",
    wordlist: str = "/usr/share/seclists/Discovery/Web-Content/common.txt",
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, Any]:
    """Run Gobuster directory / DNS / vhost brute-force."""
    cmd = f"gobuster {mode} -u {shlex.quote(target_url)} -w {wordlist} {extra_args}".strip()
    return run_shell(cmd, timeout=timeout)


def hydra(
    target: str,
    service: str,
    username: str = "",
    username_list: str = "",
    password_list: str = "/usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt",  # noqa: S107
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, Any]:
    """Run Hydra online brute-force."""
    user_flag = f"-L {username_list}" if username_list else f"-l {shlex.quote(username)}"
    cmd = f"hydra {user_flag} -P {password_list} {extra_args} {target} {service}".strip()
    return run_shell(cmd, timeout=timeout)


def metasploit(
    module: str,
    options: dict[str, str] | None = None,
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, Any]:
    """Run a Metasploit module via msfconsole resource script."""
    options = options or {}
    rc_lines = [f"use {module}"]
    for k, v in options.items():
        rc_lines.append(f"set {k} {v}")
    rc_lines += ["run", "exit"]

    rc_path = RESULTS_DIR / "msf_script.rc"
    rc_path.write_text("\n".join(rc_lines))
    return run_shell(f"msfconsole -q -r {rc_path}", timeout=timeout)


def whatweb(
    target: str,
    aggression: int = 3,
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, Any]:
    """Run WhatWeb fingerprinting."""
    cmd = f"whatweb -a {aggression} {extra_args} {target}".strip()
    return run_shell(cmd, timeout=timeout)


def whois_lookup(target: str) -> dict[str, Any]:
    """Run WHOIS lookup."""
    return run_shell(f"whois {shlex.quote(target)}")


def hashcat(
    hash_value: str,
    hash_type: int = 0,
    wordlist: str = "/usr/share/wordlists/rockyou.txt",
    extra_args: str = "--force",
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, Any]:
    """Run Hashcat offline hash cracking."""
    hash_file = RESULTS_DIR / "target_hash.txt"
    hash_file.write_text(hash_value.strip())
    cmd = f"hashcat -m {hash_type} {hash_file} {wordlist} {extra_args}".strip()
    return run_shell(cmd, timeout=timeout)


def amass(
    domain: str,
    passive: bool = True,
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, Any]:
    """Run Amass subdomain enumeration."""
    mode = "-passive" if passive else ""
    cmd = f"amass enum {mode} -d {shlex.quote(domain)} {extra_args}".strip()
    return run_shell(cmd, timeout=timeout)


def searchsploit(query: str, exact: bool = False) -> dict[str, Any]:
    """Search ExploitDB."""
    exact_flag = "-e" if exact else ""
    cmd = f"searchsploit {exact_flag} {shlex.quote(query)}".strip()
    return run_shell(cmd)


def list_installed_packages(limit: int = 200) -> dict[str, Any]:
    """List installed Kali packages."""
    return run_shell(f"dpkg --get-selections | grep -v deinstall | awk '{{print $1}}' | head -{limit}")


def list_wordlists(limit: int = 100) -> dict[str, Any]:
    """List available wordlists."""
    return run_shell(f"find /usr/share/wordlists /usr/share/seclists -maxdepth 2 -type f 2>/dev/null | head -{limit}")

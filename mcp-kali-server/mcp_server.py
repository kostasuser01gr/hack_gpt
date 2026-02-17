#!/usr/bin/env python3
"""
HackGPT – Kali Linux MCP Server
================================
Exposes Kali Linux offensive-security tools to AI assistants (e.g. Claude)
through the Model Context Protocol (MCP).

The server runs *inside* a disposable Docker container that starts on demand
and can be destroyed afterward, leaving zero footprint on the host.

Capabilities exposed via MCP tools
-----------------------------------
* run_command        – execute any shell command in the Kali container
* nmap_scan          – network / port scanning
* nikto_scan         – web-server vulnerability scanning
* sqlmap_scan        – SQL-injection detection & exploitation
* gobuster_scan      – directory / DNS brute-forcing
* hydra_attack       – online password brute-forcing
* metasploit_run     – run Metasploit modules
* whatweb_scan       – web-technology fingerprinting
* whois_lookup       – domain / IP WHOIS queries
* hashcat_crack      – offline hash cracking
* amass_enum         – subdomain enumeration
* exploit_search     – search ExploitDB for known exploits

Transport: Streamable-HTTP (SSE fallback) on 0.0.0.0:8811
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any

# ── MCP SDK ──────────────────────────────────────────────────────────────────
from mcp.server.fastmcp import FastMCP

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mcp-kali")

# ── Constants ────────────────────────────────────────────────────────────────
MCP_PORT = int(os.getenv("MCP_PORT", "8811"))
COMMAND_TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", "300"))  # 5 min default
MAX_OUTPUT_BYTES = int(os.getenv("MAX_OUTPUT_BYTES", str(512 * 1024)))  # 512 KB
RESULTS_DIR = Path("/tmp/hackgpt-results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Load the system prompt that guides AI behaviour
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "kali_system_prompt.md"
SYSTEM_PROMPT = (
    SYSTEM_PROMPT_PATH.read_text()
    if SYSTEM_PROMPT_PATH.exists()
    else "You are HackGPT, an AI penetration-testing assistant with access to Kali Linux tools."
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _run(cmd: str | list[str], timeout: int = COMMAND_TIMEOUT, cwd: str | None = None) -> dict[str, Any]:
    """Run a shell command and return structured output."""
    if isinstance(cmd, str):
        shell = True
        display_cmd = cmd
    else:
        shell = False
        display_cmd = " ".join(cmd)

    logger.info("exec  ▸ %s", display_cmd)
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
        stdout = proc.stdout[:MAX_OUTPUT_BYTES] if proc.stdout else ""
        stderr = proc.stderr[:MAX_OUTPUT_BYTES] if proc.stderr else ""
        return {
            "command": display_cmd,
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
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
    except Exception as exc:
        return {
            "command": display_cmd,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(exc),
            "elapsed_seconds": round(time.monotonic() - start, 2),
        }


def _fmt(result: dict[str, Any]) -> str:
    """Format a command result as human-readable text for the AI."""
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
# MCP SERVER DEFINITION
# ═════════════════════════════════════════════════════════════════════════════

mcp = FastMCP(
    "HackGPT Kali Linux",
    instructions=SYSTEM_PROMPT,
)


# ── Generic shell execution ─────────────────────────────────────────────────


@mcp.tool()
async def run_command(
    command: str,
    timeout: int = COMMAND_TIMEOUT,
    working_directory: str = "/tmp",
) -> str:
    """Execute an arbitrary shell command inside the Kali Linux container.

    Use this when no specialised tool covers the task, or to chain multiple
    commands together.

    Args:
        command: The shell command to run (e.g. 'ls -la', 'cat /etc/passwd').
        timeout: Maximum seconds to wait (default 300).
        working_directory: Directory to run the command in.
    """
    return _fmt(_run(command, timeout=timeout, cwd=working_directory))


# ── Nmap ─────────────────────────────────────────────────────────────────────


@mcp.tool()
async def nmap_scan(
    target: str,
    scan_type: str = "-sV -sC",
    ports: str = "",
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Run an Nmap scan against a target host or network.

    Args:
        target:     IP, hostname, or CIDR range to scan.
        scan_type:  Nmap scan flags (default: '-sV -sC' for version + scripts).
                    Common options: '-sS' (SYN), '-sU' (UDP), '-A' (aggressive),
                    '-O' (OS detect), '-Pn' (skip ping).
        ports:      Port specification (e.g. '80,443', '1-1024', '-' for all).
        extra_args: Any additional Nmap arguments.
        timeout:    Max seconds.
    """
    port_flag = f"-p {ports}" if ports else ""
    cmd = f"nmap {scan_type} {port_flag} {extra_args} {target}"
    return _fmt(_run(cmd.strip(), timeout=timeout))


# ── Nikto ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def nikto_scan(
    target: str,
    port: int = 80,
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Run a Nikto web-server vulnerability scan.

    Args:
        target:     URL or IP of the web server.
        port:       Port to scan (default 80).
        extra_args: Additional Nikto flags.
        timeout:    Max seconds.
    """
    cmd = f"nikto -h {target} -p {port} {extra_args}"
    return _fmt(_run(cmd.strip(), timeout=timeout))


# ── SQLMap ───────────────────────────────────────────────────────────────────


@mcp.tool()
async def sqlmap_scan(
    target_url: str,
    data: str = "",
    extra_args: str = "--batch --random-agent",
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Run SQLMap to detect and exploit SQL injection vulnerabilities.

    Args:
        target_url: The URL to test (use '*' to mark injection points).
        data:       POST data string (optional).
        extra_args: Additional flags (default: '--batch --random-agent').
        timeout:    Max seconds.
    """
    data_flag = f"--data={shlex.quote(data)}" if data else ""
    cmd = f"sqlmap -u {shlex.quote(target_url)} {data_flag} {extra_args}"
    return _fmt(_run(cmd.strip(), timeout=timeout))


# ── Gobuster ─────────────────────────────────────────────────────────────────


@mcp.tool()
async def gobuster_scan(
    target_url: str,
    mode: str = "dir",
    wordlist: str = "/usr/share/seclists/Discovery/Web-Content/common.txt",
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Brute-force directories, DNS subdomains, or virtual hosts with Gobuster.

    Args:
        target_url: The base URL to scan.
        mode:       'dir' (directories), 'dns' (subdomains), 'vhost'.
        wordlist:   Path to wordlist inside the container.
        extra_args: Additional Gobuster flags.
        timeout:    Max seconds.
    """
    cmd = f"gobuster {mode} -u {shlex.quote(target_url)} -w {wordlist} {extra_args}"
    return _fmt(_run(cmd.strip(), timeout=timeout))


# ── Hydra ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def hydra_attack(
    target: str,
    service: str,
    username: str = "",
    username_list: str = "",
    password_list: str = "/usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt",  # noqa: S107
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Run Hydra for online password brute-forcing.

    Args:
        target:        IP or hostname.
        service:       Protocol to attack (ssh, ftp, http-get, http-post-form, …).
        username:      Single username to try.
        username_list: Path to username wordlist (overrides username).
        password_list: Path to password wordlist.
        extra_args:    Additional Hydra flags.
        timeout:       Max seconds.
    """
    user_flag = f"-L {username_list}" if username_list else f"-l {shlex.quote(username)}"
    cmd = f"hydra {user_flag} -P {password_list} {extra_args} {target} {service}"
    return _fmt(_run(cmd.strip(), timeout=timeout))


# ── Metasploit ───────────────────────────────────────────────────────────────


@mcp.tool()
async def metasploit_run(
    module: str,
    options: dict[str, str] | None = None,
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Run a Metasploit Framework module (exploit, auxiliary, or post).

    Args:
        module:  Full module path (e.g. 'auxiliary/scanner/http/http_version').
        options: Dict of module options, e.g. {"RHOSTS": "10.0.0.1", "RPORT": "80"}.
        timeout: Max seconds.
    """
    if options is None:
        options = {}
    rc_lines = [f"use {module}"]
    for k, v in options.items():
        rc_lines.append(f"set {k} {v}")
    rc_lines.append("run")
    rc_lines.append("exit")

    rc_content = "\n".join(rc_lines)
    rc_path = RESULTS_DIR / "msf_script.rc"
    rc_path.write_text(rc_content)

    cmd = f"msfconsole -q -r {rc_path}"
    return _fmt(_run(cmd, timeout=timeout))


# ── WhatWeb ──────────────────────────────────────────────────────────────────


@mcp.tool()
async def whatweb_scan(
    target: str,
    aggression: int = 3,
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Fingerprint web technologies with WhatWeb.

    Args:
        target:     URL or IP.
        aggression: Aggression level 1-4 (default 3).
        extra_args: Additional flags.
        timeout:    Max seconds.
    """
    cmd = f"whatweb -a {aggression} {extra_args} {target}"
    return _fmt(_run(cmd.strip(), timeout=timeout))


# ── WHOIS ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def whois_lookup(
    target: str,
) -> str:
    """Perform a WHOIS lookup on a domain or IP address.

    Args:
        target: Domain name or IP address.
    """
    return _fmt(_run(f"whois {shlex.quote(target)}"))


# ── Hashcat ──────────────────────────────────────────────────────────────────


@mcp.tool()
async def hashcat_crack(
    hash_value: str,
    hash_type: int = 0,
    wordlist: str = "/usr/share/wordlists/rockyou.txt",
    extra_args: str = "--force",
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Crack password hashes offline with Hashcat.

    Args:
        hash_value: The hash to crack (or path to hash file).
        hash_type:  Hashcat mode number (0=MD5, 100=SHA1, 1000=NTLM, …).
        wordlist:   Path to wordlist.
        extra_args: Additional flags (default: '--force' for CPU-only).
        timeout:    Max seconds.
    """
    hash_file = RESULTS_DIR / "target_hash.txt"
    hash_file.write_text(hash_value.strip())
    cmd = f"hashcat -m {hash_type} {hash_file} {wordlist} {extra_args}"
    return _fmt(_run(cmd.strip(), timeout=timeout))


# ── Amass ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def amass_enum(
    domain: str,
    passive: bool = True,
    extra_args: str = "",
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Enumerate subdomains with Amass.

    Args:
        domain:  Target domain.
        passive: If True, passive-only enumeration; otherwise active.
        extra_args: Additional flags.
        timeout: Max seconds.
    """
    mode = "-passive" if passive else ""
    cmd = f"amass enum {mode} -d {shlex.quote(domain)} {extra_args}"
    return _fmt(_run(cmd.strip(), timeout=timeout))


# ── ExploitDB search ────────────────────────────────────────────────────────


@mcp.tool()
async def exploit_search(
    query: str,
    exact: bool = False,
) -> str:
    """Search the local ExploitDB database (searchsploit).

    Args:
        query: Search term (e.g. 'Apache 2.4', 'WordPress 6').
        exact: If True, match exact title.
    """
    exact_flag = "-e" if exact else ""
    cmd = f"searchsploit {exact_flag} {shlex.quote(query)}"
    return _fmt(_run(cmd.strip()))


# ── Resource: list available tools ───────────────────────────────────────────


@mcp.resource("kali://tools")
async def list_tools() -> str:
    """Return a list of pre-installed Kali Linux tools available in this container."""
    result = _run("dpkg --get-selections | grep -v deinstall | awk '{print $1}' | head -200")
    return result["stdout"]


@mcp.resource("kali://wordlists")
async def list_wordlists() -> str:
    """List available wordlists in the container."""
    result = _run("find /usr/share/wordlists /usr/share/seclists -maxdepth 2 -type f 2>/dev/null | head -100")
    return result["stdout"]


# ── Prompt: penetration-testing workflow ─────────────────────────────────────


@mcp.prompt()
async def pentest_workflow(target: str, scope: str = "full") -> str:
    """Return a structured penetration-testing workflow prompt for the AI.

    Args:
        target: The target to test.
        scope:  'full', 'web', 'network', or 'recon'.
    """
    return textwrap.dedent(f"""\
        You are HackGPT, an expert AI penetration tester.
        You have access to a full Kali Linux environment via MCP tools.

        **Target**: {target}
        **Scope** : {scope}

        Follow this structured methodology:

        1. **Reconnaissance**
           - WHOIS lookup (`whois_lookup`)
           - Subdomain enumeration (`amass_enum`)
           - Port scanning (`nmap_scan`)
           - Web-technology fingerprinting (`whatweb_scan`)

        2. **Vulnerability Assessment**
           - Web vulnerability scan (`nikto_scan`)
           - Directory brute-force (`gobuster_scan`)
           - SQL injection testing (`sqlmap_scan`)
           - ExploitDB search (`exploit_search`)

        3. **Exploitation** (only if authorised)
           - Metasploit modules (`metasploit_run`)
           - Password attacks (`hydra_attack`)
           - Hash cracking (`hashcat_crack`)

        4. **Post-Exploitation**
           - Privilege escalation checks
           - Lateral movement assessment
           - Data exfiltration risks

        5. **Reporting**
           - Summarise findings with CVSS scores
           - Recommend remediations
           - Generate executive summary

        Always confirm authorisation before running exploits.
        Use `run_command` for any tool not covered by specialised MCP tools.
    """)


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════


def main():
    logger.info("Starting HackGPT Kali Linux MCP Server on port %d", MCP_PORT)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=MCP_PORT)


if __name__ == "__main__":
    main()

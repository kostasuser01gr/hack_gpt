#!/usr/bin/env python3
"""
HackGPT – Integrated MCP Kali Linux Server
============================================
Runs as part of the HackGPT application (same process / container).

Start via the main app menu (option 16), CLI flag (--mcp), or programmatically:

    from mcp import MCPKaliServer
    server = MCPKaliServer(config)
    server.start()            # blocking (runs uvicorn)
    server.start_background() # non-blocking (new thread)

The server exposes Kali Linux tools over MCP (Streamable-HTTP) on the
configured host:port (default 0.0.0.0:8811).
"""

from __future__ import annotations

import logging
import os
import textwrap
import threading
from pathlib import Path

from hackgpt_mcp.kali_tools import (
    amass,
    format_result,
    gobuster,
    hashcat,
    hydra,
    list_installed_packages,
    list_wordlists,
    metasploit,
    nikto,
    nmap,
    run_shell,
    searchsploit,
    sqlmap,
    whatweb,
    whois_lookup,
)

logger = logging.getLogger("hackgpt.mcp.server")

# ── System prompt ────────────────────────────────────────────────────────────
_PROMPT_PATH = Path(__file__).parent / "prompts" / "kali_system_prompt.md"
_SYSTEM_PROMPT = (
    _PROMPT_PATH.read_text()
    if _PROMPT_PATH.exists()
    else "You are HackGPT, an AI penetration-testing assistant with access to Kali Linux tools."
)


class MCPKaliServer:
    """Integrated MCP server for Kali Linux tools.

    Parameters
    ----------
    config : object, optional
        HackGPT Config instance (reads MCP settings from [mcp] section).
        If None, falls back to environment variables / defaults.
    """

    def __init__(self, config=None):
        self.host = "0.0.0.0"
        self.port = 8811
        self.command_timeout = 300
        self._thread: threading.Thread | None = None
        self._running = False

        # Read settings from config.ini [mcp] section if available
        if config is not None:
            cfg = getattr(config, "config", None)
            if cfg is not None:
                self.host = cfg.get("mcp", "host", fallback=self.host)
                self.port = cfg.getint("mcp", "port", fallback=self.port)
                self.command_timeout = cfg.getint("mcp", "command_timeout", fallback=self.command_timeout)

        # Env-var overrides
        self.host = os.getenv("MCP_HOST", self.host)
        self.port = int(os.getenv("MCP_PORT", str(self.port)))
        self.command_timeout = int(os.getenv("MCP_COMMAND_TIMEOUT", str(self.command_timeout)))

        self._mcp = self._build_mcp_app()

    # ─────────────────────────────────────────────────────────────────────────
    # FastMCP application definition
    # ─────────────────────────────────────────────────────────────────────────

    def _build_mcp_app(self):
        """Build and return a configured FastMCP instance."""
        from mcp.server.fastmcp import FastMCP  # MCP SDK import

        mcp = FastMCP("HackGPT Kali Linux", instructions=_SYSTEM_PROMPT)
        timeout = self.command_timeout

        # ── Generic shell ────────────────────────────────────────────────────

        @mcp.tool()
        async def run_command(
            command: str,
            timeout: int = timeout,
            working_directory: str = "/tmp",
        ) -> str:
            """Execute an arbitrary shell command inside the Kali Linux environment.

            Use this when no specialised tool covers the task, or to chain
            multiple commands together.

            Args:
                command: The shell command to run.
                timeout: Maximum seconds to wait (default 300).
                working_directory: Directory to run the command in.
            """
            return format_result(run_shell(command, timeout=timeout, cwd=working_directory))

        # ── Nmap ─────────────────────────────────────────────────────────────

        @mcp.tool()
        async def nmap_scan(
            target: str,
            scan_type: str = "-sV -sC",
            ports: str = "",
            extra_args: str = "",
            timeout: int = timeout,
        ) -> str:
            """Run an Nmap scan against a target host or network.

            Args:
                target:     IP, hostname, or CIDR range to scan.
                scan_type:  Nmap scan flags (default '-sV -sC').
                ports:      Port specification (e.g. '80,443', '1-1024').
                extra_args: Additional Nmap arguments.
                timeout:    Maximum seconds.
            """
            return format_result(nmap(target, scan_type, ports, extra_args, timeout))

        # ── Nikto ────────────────────────────────────────────────────────────

        @mcp.tool()
        async def nikto_scan(
            target: str,
            port: int = 80,
            extra_args: str = "",
            timeout: int = timeout,
        ) -> str:
            """Run Nikto web-server vulnerability scan.

            Args:
                target:     URL or IP of the web server.
                port:       Port to scan (default 80).
                extra_args: Additional Nikto flags.
                timeout:    Maximum seconds.
            """
            return format_result(nikto(target, port, extra_args, timeout))

        # ── SQLMap ───────────────────────────────────────────────────────────

        @mcp.tool()
        async def sqlmap_scan(
            target_url: str,
            data: str = "",
            extra_args: str = "--batch --random-agent",
            timeout: int = timeout,
        ) -> str:
            """Run SQLMap to detect and exploit SQL injection vulnerabilities.

            Args:
                target_url: The URL to test (use '*' to mark injection points).
                data:       POST data string (optional).
                extra_args: Additional flags (default '--batch --random-agent').
                timeout:    Maximum seconds.
            """
            return format_result(sqlmap(target_url, data, extra_args, timeout))

        # ── Gobuster ─────────────────────────────────────────────────────────

        @mcp.tool()
        async def gobuster_scan(
            target_url: str,
            mode: str = "dir",
            wordlist: str = "/usr/share/seclists/Discovery/Web-Content/common.txt",
            extra_args: str = "",
            timeout: int = timeout,
        ) -> str:
            """Brute-force directories, DNS subdomains, or virtual hosts.

            Args:
                target_url: The base URL to scan.
                mode:       'dir', 'dns', or 'vhost'.
                wordlist:   Path to wordlist inside the container.
                extra_args: Additional Gobuster flags.
                timeout:    Maximum seconds.
            """
            return format_result(gobuster(target_url, mode, wordlist, extra_args, timeout))

        # ── Hydra ────────────────────────────────────────────────────────────

        @mcp.tool()
        async def hydra_attack(
            target: str,
            service: str,
            username: str = "",
            username_list: str = "",
            password_list: str = "/usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt",  # noqa: S107
            extra_args: str = "",
            timeout: int = timeout,
        ) -> str:
            """Run Hydra for online password brute-forcing.

            Args:
                target:        IP or hostname.
                service:       Protocol (ssh, ftp, http-get, http-post-form, …).
                username:      Single username to try.
                username_list: Path to username wordlist (overrides username).
                password_list: Path to password wordlist.
                extra_args:    Additional Hydra flags.
                timeout:       Maximum seconds.
            """
            return format_result(
                hydra(
                    target,
                    service,
                    username,
                    username_list,
                    password_list,
                    extra_args,
                    timeout,
                )
            )

        # ── Metasploit ───────────────────────────────────────────────────────

        @mcp.tool()
        async def metasploit_run(
            module: str,
            options: dict[str, str] | None = None,
            timeout: int = timeout,
        ) -> str:
            """Run a Metasploit Framework module.

            Args:
                module:  Full module path (e.g. 'auxiliary/scanner/http/http_version').
                options: Module options dict, e.g. {"RHOSTS": "10.0.0.1"}.
                timeout: Maximum seconds.
            """
            if options is None:
                options = {}
            return format_result(metasploit(module, options, timeout))

        # ── WhatWeb ──────────────────────────────────────────────────────────

        @mcp.tool()
        async def whatweb_scan(
            target: str,
            aggression: int = 3,
            extra_args: str = "",
            timeout: int = timeout,
        ) -> str:
            """Fingerprint web technologies with WhatWeb.

            Args:
                target:     URL or IP.
                aggression: Aggression level 1-4 (default 3).
                extra_args: Additional flags.
                timeout:    Maximum seconds.
            """
            return format_result(whatweb(target, aggression, extra_args, timeout))

        # ── WHOIS ────────────────────────────────────────────────────────────

        @mcp.tool()
        async def whois(target: str) -> str:
            """Perform a WHOIS lookup on a domain or IP address.

            Args:
                target: Domain name or IP address.
            """
            return format_result(whois_lookup(target))

        # ── Hashcat ──────────────────────────────────────────────────────────

        @mcp.tool()
        async def hashcat_crack(
            hash_value: str,
            hash_type: int = 0,
            wordlist: str = "/usr/share/wordlists/rockyou.txt",
            extra_args: str = "--force",
            timeout: int = timeout,
        ) -> str:
            """Crack password hashes offline with Hashcat.

            Args:
                hash_value: The hash (or path to hash file).
                hash_type:  Hashcat mode (0=MD5, 100=SHA1, 1000=NTLM, …).
                wordlist:   Path to wordlist.
                extra_args: Additional flags.
                timeout:    Maximum seconds.
            """
            return format_result(hashcat(hash_value, hash_type, wordlist, extra_args, timeout))

        # ── Amass ────────────────────────────────────────────────────────────

        @mcp.tool()
        async def amass_enum(
            domain: str,
            passive: bool = True,
            extra_args: str = "",
            timeout: int = timeout,
        ) -> str:
            """Enumerate subdomains with Amass.

            Args:
                domain:     Target domain.
                passive:    Passive-only enumeration if True.
                extra_args: Additional flags.
                timeout:    Maximum seconds.
            """
            return format_result(amass(domain, passive, extra_args, timeout))

        # ── ExploitDB ────────────────────────────────────────────────────────

        @mcp.tool()
        async def exploit_search(query: str, exact: bool = False) -> str:
            """Search the local ExploitDB database (searchsploit).

            Args:
                query: Search term (e.g. 'Apache 2.4', 'WordPress 6').
                exact: Match exact title if True.
            """
            return format_result(searchsploit(query, exact))

        # ── Resources ────────────────────────────────────────────────────────

        @mcp.resource("kali://tools")
        async def resource_tools() -> str:
            """List installed Kali Linux security packages."""
            return list_installed_packages()["stdout"]

        @mcp.resource("kali://wordlists")
        async def resource_wordlists() -> str:
            """List available wordlists."""
            return list_wordlists()["stdout"]

        # ── Prompt ───────────────────────────────────────────────────────────

        @mcp.prompt()
        async def pentest_workflow(target: str, scope: str = "full") -> str:
            """Return a structured penetration-testing workflow for the AI.

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
                   - WHOIS lookup (whois)
                   - Subdomain enumeration (amass_enum)
                   - Port scanning (nmap_scan)
                   - Web-technology fingerprinting (whatweb_scan)

                2. **Vulnerability Assessment**
                   - Web vulnerability scan (nikto_scan)
                   - Directory brute-force (gobuster_scan)
                   - SQL injection testing (sqlmap_scan)
                   - ExploitDB search (exploit_search)

                3. **Exploitation** (only if authorised)
                   - Metasploit modules (metasploit_run)
                   - Password attacks (hydra_attack)
                   - Hash cracking (hashcat_crack)

                4. **Post-Exploitation**
                   - Privilege escalation checks
                   - Lateral movement assessment
                   - Data exfiltration risks

                5. **Reporting**
                   - Summarise findings with CVSS scores
                   - Recommend remediations
                   - Generate executive summary

                Always confirm authorisation before running exploits.
                Use run_command for any tool not covered by specialised MCP tools.
            """)

        return mcp

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    def start(self):
        """Start the MCP server (blocking)."""
        logger.info("Starting HackGPT MCP server on %s:%d", self.host, self.port)
        self._running = True
        self._mcp.run(transport="streamable-http", host=self.host, port=self.port)

    def start_background(self) -> threading.Thread:
        """Start the MCP server in a background thread."""
        self._thread = threading.Thread(target=self.start, daemon=True, name="mcp-server")
        self._thread.start()
        logger.info("MCP server started in background thread")
        return self._thread

    def stop(self):
        """Mark the server for shutdown."""
        self._running = False
        logger.info("MCP server stop requested")

    @property
    def is_running(self) -> bool:
        return self._running and (self._thread is not None and self._thread.is_alive())

    @property
    def endpoint_url(self) -> str:
        return f"http://{self.host}:{self.port}/mcp"

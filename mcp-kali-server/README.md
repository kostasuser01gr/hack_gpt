# HackGPT – Kali Linux MCP Server

> **AI-Powered Hacking with Docker & MCP**
>
> Turn Claude (or any MCP-compatible AI) into a penetration-testing assistant
> backed by a full Kali Linux toolset — running on demand inside an isolated
> Docker container.

---

## What Is This?

This directory contains everything needed to build and run a **Kali Linux MCP
Server** — a Docker container that:

1. Boots a full **Kali Linux** environment with pre-installed offensive
   security tools (Nmap, Nikto, SQLMap, Metasploit, Hydra, Hashcat, …).
2. Exposes those tools to an AI assistant through the **Model Context Protocol
   (MCP)** over HTTP.
3. Runs **on demand** — starts when you need it, disappears when you're done.
   No resource waste, no permanent system changes.

```
┌──────────────┐       MCP (HTTP)       ┌──────────────────────┐
│  Claude AI   │ ◄───────────────────► │  Kali Linux          │
│  (Desktop /  │                       │  MCP Server          │
│   Codespace) │                       │  (Docker container)  │
└──────────────┘                       └──────────────────────┘
                                          │ nmap, nikto, sqlmap
                                          │ metasploit, hydra …
```

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the Kali Linux container with all tools + MCP server |
| `mcp_server.py` | Python MCP server exposing 12+ security tools as MCP tools |
| `requirements.txt` | Python dependencies (MCP SDK, uvicorn, etc.) |
| `prompts/kali_system_prompt.md` | System prompt guiding AI behaviour |

## Quick Start

### 1. Build the Container

```bash
cd mcp-kali-server
docker build -t hackgpt-kali-mcp .
```

### 2. Run It

```bash
# Start the MCP server (runs on port 8811)
docker run -d --name hackgpt-kali \
  -p 8811:8811 \
  --rm \
  hackgpt-kali-mcp

# Verify it's running
curl http://localhost:8811/health
```

### 3. Connect Claude Desktop

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hackgpt-kali": {
      "url": "http://localhost:8811/mcp"
    }
  }
}
```

Restart Claude Desktop. You should see the Kali Linux tools appear in the
tool-use panel.

### 4. Start Hacking (with authorisation!)

Example prompts:

```
Scan example.com for open ports and identify running services.

Run a Nikto scan against http://testsite.local to find web vulnerabilities.

Search ExploitDB for Apache 2.4 exploits.

Enumerate subdomains of example.com using Amass.

Fingerprint the technologies behind https://target.com with WhatWeb.
```

## Using with Docker Compose

From the HackGPT root directory:

```bash
# Start the full stack including the MCP server
docker-compose up -d hackgpt-kali-mcp

# Or start just the MCP server
docker-compose up -d hackgpt-kali-mcp
```

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `run_command` | Execute any shell command in Kali |
| `nmap_scan` | Network/port scanning with Nmap |
| `nikto_scan` | Web-server vulnerability scanning |
| `sqlmap_scan` | SQL-injection detection & exploitation |
| `gobuster_scan` | Directory/DNS brute-forcing |
| `hydra_attack` | Online password brute-forcing |
| `metasploit_run` | Run Metasploit Framework modules |
| `whatweb_scan` | Web-technology fingerprinting |
| `whois_lookup` | Domain/IP WHOIS queries |
| `hashcat_crack` | Offline hash cracking |
| `amass_enum` | Subdomain enumeration |
| `exploit_search` | Search ExploitDB for known exploits |

## MCP Resources

| URI | Description |
|-----|-------------|
| `kali://tools` | List all installed security packages |
| `kali://wordlists` | List available wordlists |

## Architecture

```
mcp-kali-server/
├── Dockerfile                 # Kali Linux + tools + MCP server
├── mcp_server.py              # FastMCP server (12 tools, 2 resources, 1 prompt)
├── requirements.txt           # Python deps
├── prompts/
│   └── kali_system_prompt.md  # System prompt for AI behaviour
└── README.md                  # This file
```

### How It Works

1. **Docker container** boots Kali Linux with curated security tools.
2. **`mcp_server.py`** starts a FastMCP server on port 8811.
3. The AI connects via MCP (Streamable HTTP transport).
4. Each MCP tool call executes the corresponding Kali tool inside the container.
5. Results stream back to the AI for analysis and reporting.

### Security Model

- **Isolation**: Everything runs inside a Docker container. The host is untouched.
- **Ephemeral**: Use `--rm` to auto-destroy the container when stopped.
- **Non-root**: The MCP server runs as a non-root user (`hackgpt`) inside the container.
- **No host networking**: The container only exposes port 8811 by default.
- **Authorisation prompts**: The AI system prompt requires authorisation before exploitation.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_PORT` | `8811` | Port the MCP server listens on |
| `COMMAND_TIMEOUT` | `300` | Default command timeout (seconds) |
| `MAX_OUTPUT_BYTES` | `524288` | Max output size (512 KB) |

## Troubleshooting

### Container won't start

```bash
# Check Docker is running
docker info

# Check build logs
docker build -t hackgpt-kali-mcp . 2>&1 | tail -50
```

### Claude doesn't see the tools

1. Verify the container is running: `docker ps | grep hackgpt-kali`
2. Verify the MCP endpoint: `curl http://localhost:8811/health`
3. Check the Claude Desktop config file for typos.
4. Restart Claude Desktop after config changes.

### Command times out

Increase the timeout via the tool's `timeout` parameter or set the
`COMMAND_TIMEOUT` environment variable when starting the container:

```bash
docker run -d --name hackgpt-kali \
  -p 8811:8811 \
  -e COMMAND_TIMEOUT=600 \
  --rm \
  hackgpt-kali-mcp
```

## Legal Notice

⚠️ **Use only against systems you own or have explicit written permission to
test.** Unauthorised access to computer systems is illegal. The developers are
not responsible for misuse.

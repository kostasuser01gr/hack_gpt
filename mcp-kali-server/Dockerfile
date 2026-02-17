# =============================================================================
# HackGPT – Kali Linux MCP Server
# Isolated container with offensive-security tools exposed via MCP
# =============================================================================
FROM kalilinux/kali-rolling

LABEL maintainer="HackGPT Enterprise <security@zehrasec.com>"
LABEL description="Kali Linux MCP server for AI-powered penetration testing"

# ── Environment ──────────────────────────────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    MCP_PORT=8811 \
    TERM=xterm-256color

# ── Base packages + Kali meta-packages (curated, not kali-linux-everything) ─
RUN apt-get update && apt-get full-upgrade -y && apt-get install -y \
    # ---------- core ----------
    python3 python3-pip python3-venv \
    git curl wget sudo jq dnsutils net-tools iputils-ping iproute2 \
    # ---------- recon ----------
    nmap masscan amass subfinder dnsrecon whois \
    # ---------- web ----------
    nikto dirb gobuster whatweb wfuzz sqlmap \
    # ---------- exploitation ----------
    metasploit-framework hydra john hashcat \
    # ---------- wireless / network ----------
    aircrack-ng netcat-openbsd tcpdump tshark arpwatch \
    # ---------- misc ----------
    seclists wordlists exploitdb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Python dependencies for the MCP server ───────────────────────────────────
WORKDIR /mcp-server
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# ── Copy server code ─────────────────────────────────────────────────────────
COPY mcp_server.py .
COPY prompts/ ./prompts/

# ── Non-root user (principle of least privilege inside container) ─────────────
RUN useradd -m -s /bin/bash hackgpt && \
    echo "hackgpt ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    chown -R hackgpt:hackgpt /mcp-server
USER hackgpt

# ── Expose MCP transport port ────────────────────────────────────────────────
EXPOSE ${MCP_PORT}

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:${MCP_PORT}/health || exit 1

# ── Entrypoint ───────────────────────────────────────────────────────────────
ENTRYPOINT ["python3", "mcp_server.py"]

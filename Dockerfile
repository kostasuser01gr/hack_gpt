# ============================================================
# Stage 1: System tools & Python dependencies (builder)
# ============================================================
FROM kalilinux/kali-rolling AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies + Kali security tools
RUN apt-get update && apt-get full-upgrade -y && apt-get install -y \
    # ── build / runtime ──
    python3 \
    python3-pip \
    python3-venv \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    portaudio19-dev \
    git \
    curl \
    wget \
    sudo \
    jq \
    dnsutils \
    net-tools \
    iputils-ping \
    iproute2 \
    # ── recon ──
    nmap \
    masscan \
    amass \
    subfinder \
    dnsrecon \
    whois \
    # ── web ──
    nikto \
    dirb \
    gobuster \
    whatweb \
    wfuzz \
    sqlmap \
    # ── exploitation ──
    metasploit-framework \
    hydra \
    john \
    hashcat \
    # ── network ──
    aircrack-ng \
    netcat-openbsd \
    tcpdump \
    tshark \
    arpwatch \
    # ── wordlists / exploit-db ──
    seclists \
    wordlists \
    exploitdb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /hackgpt

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies (--ignore-installed avoids conflicts with system packages)
RUN pip3 install --no-cache-dir --ignore-installed -r requirements.txt --break-system-packages

# ============================================================
# Stage 2: Runtime image
# ============================================================
FROM builder AS runtime

WORKDIR /hackgpt

# Create non-root user for running the application
RUN groupadd -r hackgpt && useradd -r -g hackgpt -m -s /bin/bash hackgpt

# Copy application code
COPY --chown=hackgpt:hackgpt . .

# Run installation script (as root, before switching user)
RUN chmod +x install.sh && ./install.sh

# Create reports & logs directories with correct ownership
RUN mkdir -p /reports /hackgpt/logs \
    && chown -R hackgpt:hackgpt /reports /hackgpt/logs

# Metadata
LABEL maintainer="HackGPT Team <yashabalam707@gmail.com>" \
      version="2.1.0" \
      description="HackGPT Enterprise AI-Powered Penetration Testing Platform"

# Expose ports: web dashboard, API, MCP server
EXPOSE 5000 8000 8080 8811

# Health check — lightweight HTTP probe against the API
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

# Switch to non-root user
USER hackgpt

ENTRYPOINT ["python3", "hackgpt.py"]

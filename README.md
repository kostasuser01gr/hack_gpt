<div align="center">
  <img src="public/hackgpt-logo.png" alt="HackGPT Enterprise Logo" width="400" height="auto">
  
  <h1>🚀 HackGPT Enterprise</h1>
  <h3>AI-Powered Penetration Testing Platform</h3>
  
  <p>
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+">
    <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-orange.svg" alt="Multi-Platform">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License">
    <img src="https://img.shields.io/badge/AI-GPT%20%7C%20Local%20LLM%20%7C%20ML-purple.svg" alt="AI Powered">
  </p>
  <p>
    <img src="https://img.shields.io/badge/Architecture-Microservices-red.svg" alt="Microservices">
    <img src="https://img.shields.io/badge/Cloud-Docker%20%7C%20Kubernetes-lightblue.svg" alt="Cloud Native">
    <img src="https://img.shields.io/badge/Version-2.0.0-success.svg" alt="Version 2.0.0">
    <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg" alt="Production Ready">
  </p>
</div>

**HackGPT Enterprise** is a production-ready, cloud-native AI-powered penetration testing platform designed for enterprise security teams. It combines advanced AI, machine learning, microservices architecture, and comprehensive security frameworks to deliver professional-grade cybersecurity assessments.

**Created by [Yashab Alam](https://github.com/yashab-cyber), Founder & CEO of [ZehraSec](https://www.zehrasec.com)**

> 💰 **Support the Project**: [Donate to HackGPT Development](DONATE.md) | Help us build the future of AI-powered penetration testing!

## 🏢 Enterprise Features

### 🤖 Advanced AI Engine
- **Multi-Model Support**: OpenAI GPT-4, Local LLM (Ollama), TensorFlow, PyTorch
- **Machine Learning**: Pattern recognition, anomaly detection, behavioral analysis
- **Zero-Day Detection**: ML-powered vulnerability discovery and correlation
- **Risk Intelligence**: CVSS scoring, impact assessment, exploit prioritization
- **Automated Reporting**: Executive summaries, technical details, compliance mapping

### 🛡️ Enterprise Security & Compliance
- **Authentication**: RBAC + LDAP/Active Directory integration
- **Authorization**: Role-based permissions (Admin, Lead, Senior, Pentester, Analyst)
- **Compliance**: OWASP, NIST, ISO27001, SOC2, PCI-DSS frameworks
- **Audit Logging**: Comprehensive activity tracking and forensics
- **Data Protection**: AES-256-GCM encryption, JWT tokens, secure sessions

### 🏗️ Cloud-Native Architecture
- **Microservices**: Docker containers with Kubernetes orchestration
- **Service Discovery**: Consul-based service registry
- **Load Balancing**: Nginx reverse proxy with auto-scaling
- **Multi-Cloud**: AWS, Azure, GCP deployment support
- **High Availability**: Circuit breakers, health checks, failover

### ⚡ Performance & Scalability
- **Parallel Processing**: Celery-based distributed task execution
- **Multi-Layer Caching**: Redis + memory caching with TTL management
- **Database**: PostgreSQL with connection pooling and replication
- **Real-Time**: WebSocket dashboards with live updates
- **Auto-Scaling**: Worker pools adapt to workload demands

### 📊 Enterprise Reporting & Analytics
- **Dynamic Reports**: HTML, PDF, JSON, XML, CSV export formats
- **Real-Time Dashboards**: Prometheus + Grafana monitoring stack
- **Log Analytics**: ELK stack (Elasticsearch + Kibana) integration
- **Executive Summaries**: AI-generated business impact assessments
- **Compliance Reports**: Framework-specific compliance documentation

## 🚀 Quick Start

### Prerequisites
- **Operating System**: Linux (Ubuntu/Debian/RHEL/CentOS), macOS, or Windows WSL2
- **Python**: 3.8+ with pip and virtual environment support
- **Docker**: For containerized deployment (recommended)
- **Resources**: Minimum 4GB RAM, 20GB disk space

### Enterprise Installation

```bash
# Clone the repository
git clone https://github.com/yashab-cyber/HackGPT.git
cd HackGPT

# Run enterprise installer (sets up all services)
chmod +x install.sh
./install.sh

# Configure environment
cp .env.example .env
# Edit .env with your API keys and settings
nano .env

# Verify installation
python3 test_installation.py
```

### Deployment Options

#### 1. Standalone Enterprise Mode
```bash
# Activate virtual environment
source venv/bin/activate

# Run enterprise application
python3 hackgpt_v2.py
```

#### 2. API Server Mode
```bash
# Start REST API server
python3 hackgpt_v2.py --api

# API available at: http://localhost:8000
# Health check: http://localhost:8000/api/health
```

#### 3. Web Dashboard Mode
```bash
# Start web dashboard
python3 hackgpt_v2.py --web

# Dashboard available at: http://localhost:8080
```

#### 4. Full Enterprise Stack (Recommended)
```bash
# Deploy complete microservices stack
docker-compose up -d

# Services:
# - API Server: http://localhost:8000
# - Web Dashboard: http://localhost:8080  
# - Monitoring: http://localhost:9090 (Prometheus)
# - Analytics: http://localhost:3000 (Grafana)
# - Logs: http://localhost:5601 (Kibana)
```

#### 5. Direct Assessment Mode
```bash
# Run immediate assessment
python3 hackgpt_v2.py \
  --target example.com \
  --scope "Web application and API" \
  --auth-key "ENTERPRISE-2025-AUTH" \
  --assessment-type black-box \
  --compliance OWASP
```

## 🏗️ Enterprise Architecture

### Core Components

```mermaid
graph TD
    A[Load Balancer/Nginx] --> B[HackGPT API Gateway]
    B --> C[Authentication Service]
    B --> D[AI Engine Service] 
    B --> E[Exploitation Service]
    B --> F[Reporting Service]
    
    C --> G[LDAP/AD]
    D --> H[OpenAI API]
    D --> I[Local LLM]
    D --> J[ML Models]
    
    E --> K[Parallel Processor]
    F --> L[Report Generator]
    
    K --> M[Celery Workers]
    M --> N[Redis Queue]
    
    B --> O[PostgreSQL]
    B --> P[Redis Cache]
    
    Q[Prometheus] --> R[Grafana]
    S[Elasticsearch] --> T[Kibana]
```

### Service Stack

| Service | Purpose | Port | Technology |
|---------|---------|------|------------|
| **hackgpt-app** | Main application | 8000, 8080 | Python/Flask |
| **hackgpt-worker** | Background tasks | - | Celery |
| **hackgpt-database** | Data persistence | 5432 | PostgreSQL 15 |
| **hackgpt-redis** | Cache & queues | 6379 | Redis 7 |
| **prometheus** | Metrics collection | 9090 | Prometheus |
| **grafana** | Monitoring dashboard | 3000 | Grafana |
| **elasticsearch** | Log aggregation | 9200 | Elasticsearch |
| **kibana** | Log visualization | 5601 | Kibana |
| **consul** | Service discovery | 8500 | Consul |
| **nginx** | Load balancer | 80, 443 | Nginx |
| **hackgpt-kali-mcp** | AI hacking via MCP | 8811 | Kali Linux / FastMCP |

## 🔧 Configuration

### Enterprise Configuration (`config.ini`)

The configuration file supports 200+ options across multiple categories:

```ini
[app]
debug = false
environment = production
max_sessions = 100

[database]
url = postgresql://hackgpt:hackgpt123@localhost:5432/hackgpt
pool_size = 20
backup_enabled = true

[ai]
openai_api_key = your_key_here
openai_model = gpt-4
enable_local_fallback = true
confidence_threshold = 0.8

[security]
secret_key = your_secret_here
jwt_algorithm = HS256
rate_limit_enabled = true

[ldap]
server = ldaps://your-ldap-server.com:636
bind_dn = cn=admin,dc=example,dc=com

[compliance]
frameworks = OWASP,NIST,ISO27001,SOC2,PCI-DSS
auto_compliance_check = true

[cloud]
docker_host = unix:///var/run/docker.sock
service_registry_backend = consul
```

### Environment Variables (`.env`)

Over 100 environment variables for enterprise deployment:

```bash
# Core Services
DATABASE_URL=postgresql://hackgpt:hackgpt123@localhost:5432/hackgpt
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your_openai_api_key

# Security
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret
LDAP_SERVER=ldaps://your-ldap.com:636

# Cloud Providers
AWS_ACCESS_KEY_ID=your_aws_key
AZURE_SUBSCRIPTION_ID=your_azure_id
GCP_PROJECT_ID=your_gcp_project

# Monitoring
PROMETHEUS_ENDPOINT=http://localhost:9090
GRAFANA_API_KEY=your_grafana_key
ELASTICSEARCH_ENDPOINT=http://localhost:9200
```

## 🎯 Enterprise Penetration Testing

### Enhanced 6-Phase Methodology

#### Phase 1: Intelligence Gathering & Reconnaissance
**Enterprise Features**:
- AI-powered OSINT automation
- Multi-source data aggregation
- Threat intelligence correlation
- Cloud asset discovery (AWS, Azure, GCP)
- **Tools**: theHarvester, Amass, Subfinder, Shodan API

#### Phase 2: Advanced Scanning & Enumeration  
**Enterprise Features**:
- Parallel distributed scanning
- Service fingerprinting with ML classification
- Vulnerability correlation across assets
- Zero-day pattern detection
- **Tools**: Nmap, Masscan, Nuclei, HTTPx, Naabu

#### Phase 3: Vulnerability Assessment
**Enterprise Features**:
- CVSS v3.1 automated scoring
- Business impact analysis
- Exploit availability assessment  
- Compliance framework mapping
- **Tools**: OpenVAS, Nexpose integration, custom scanners

#### Phase 4: Exploitation & Post-Exploitation
**Enterprise Features**:
- Safe-mode exploitation with approval workflows
- Privilege escalation enumeration
- Lateral movement mapping
- Data exfiltration simulation
- **Tools**: Metasploit, CrackMapExec, BloodHound, custom exploits

#### Phase 5: Enterprise Reporting & Analytics
**Enterprise Features**:
- Executive dashboard with KPIs
- Technical vulnerability details
- Compliance gap analysis
- Risk prioritization matrix
- **Outputs**: HTML, PDF, JSON, XML, compliance reports

#### Phase 6: Verification & Retesting
**Enterprise Features**:
- Automated remediation verification
- Regression testing for fixes
- Continuous security monitoring
- Trend analysis and metrics
- **Features**: Scheduled retests, delta reporting

## 📊 Enterprise Interfaces

### 1. Command Line Interface (CLI)
```bash
# Interactive enterprise mode
python3 hackgpt_v2.py

# Available options:
# 1. Full Enterprise Pentest (All 6 Phases)
# 2. Run Specific Phase
# 3. Custom Assessment Workflow
# 4. View Reports & Analytics
# 5. Real-time Dashboard
# 6. User & Permission Management
# 7. System Configuration
# 8. Compliance Management
# 9. Cloud & Container Management
# 10. AI Engine Configuration
```

### 2. REST API Server
```bash
# Start API server
python3 hackgpt_v2.py --api

# Available endpoints:
# GET  /api/health - Health check
# POST /api/pentest/start - Start assessment
# GET  /api/sessions - List sessions
# GET  /api/reports/{id} - Get report
# POST /api/users - User management
# GET  /api/compliance - Compliance status
```

### 3. Web Dashboard
```bash
# Start web dashboard
python3 hackgpt_v2.py --web

# Features:
# - Real-time assessment monitoring
# - Interactive vulnerability management
# - Executive summary dashboard
# - User and role management
# - System configuration
# - Compliance reporting
```

### 4. Voice Commands (Enterprise)
```bash
# Voice command mode
python3 hackgpt_v2.py --voice

# Supported commands:
# "Start enterprise assessment of example.com"
# "Show compliance dashboard"
# "Generate executive report"
# "Scale worker pool to 10"
```

## 🔐 Enterprise Security

### Authentication & Authorization
- **Multi-Factor Authentication**: LDAP/AD + JWT tokens
- **Role-Based Access Control**: Granular permissions matrix
- **Session Management**: Secure session handling with timeout
- **API Security**: Rate limiting, CORS, input validation

### Data Protection
- **Encryption**: AES-256-GCM for data at rest
- **Transport Security**: TLS 1.3 for data in transit  
- **Key Management**: Automated key rotation
- **Audit Logging**: Comprehensive activity tracking

### Compliance Frameworks
| Framework | Coverage | Reports | Automation |
|-----------|----------|---------|------------|
| **OWASP Top 10** | ✅ Full | ✅ Yes | ✅ Automated |
| **NIST Cybersecurity Framework** | ✅ Full | ✅ Yes | ✅ Automated |
| **ISO 27001** | ✅ Partial | ✅ Yes | ✅ Semi-automated |
| **SOC 2** | ✅ Partial | ✅ Yes | ✅ Semi-automated |
| **PCI DSS** | ✅ Partial | ✅ Yes | ✅ Manual |

## 📈 Monitoring & Analytics

### Real-Time Monitoring
- **System Metrics**: CPU, memory, disk, network utilization
- **Application Metrics**: Request rates, response times, error rates
- **Security Metrics**: Vulnerability counts, risk scores, remediation rates
- **Business Metrics**: Assessment coverage, compliance scores

### Alerting
- **Email Alerts**: Critical vulnerabilities, system issues
- **Slack Integration**: Real-time notifications to security teams
- **Webhook Support**: Custom integrations with SIEM systems
- **Dashboard Alerts**: Visual indicators and notifications

### Analytics Dashboard
```bash
# Access Grafana dashboard
http://localhost:3000
# Login: admin / hackgpt123

# Pre-configured dashboards:
# - HackGPT System Overview
# - Assessment Performance Metrics  
# - Vulnerability Trend Analysis
# - User Activity Dashboard
# - Compliance Status Overview
```

## 🛠️ Advanced Usage

### Custom AI Models
```python
# Configure custom AI endpoints
config['ai']['custom_model_endpoint'] = 'http://your-llm:8000'
config['ai']['model_type'] = 'custom'
```

### Custom Compliance Frameworks
```python
# Add custom compliance framework
from security.compliance import ComplianceFrameworkMapper

mapper = ComplianceFrameworkMapper()
mapper.add_framework('CUSTOM', {
    'sql_injection': 'SEC-01',
    'xss': 'SEC-02',
    # ... custom mappings
})
```

### Kubernetes Deployment
```yaml
# Deploy to Kubernetes cluster
kubectl apply -f k8s/
```

### Multi-Cloud Deployment
```bash
# Deploy to AWS
python3 hackgpt_v2.py --deploy aws

# Deploy to Azure  
python3 hackgpt_v2.py --deploy azure

# Deploy to GCP
python3 hackgpt_v2.py --deploy gcp
```

## 🧪 Testing & Development

### Running Tests
```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# Security tests
bandit -r .
safety check
```

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Code formatting
black .
flake8 .
mypy .
```

## 📦 Enterprise Deployment

### Docker Swarm
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml hackgpt
```

### Kubernetes
```bash
# Create namespace
kubectl create namespace hackgpt

# Deploy applications
kubectl apply -f k8s/

# Scale workers
kubectl scale deployment hackgpt-worker --replicas=10
```

### Cloud Platforms

#### AWS Deployment
```bash
# ECS deployment
aws ecs create-cluster --cluster-name hackgpt
aws ecs create-service --service-name hackgpt-api
```

#### Azure Deployment  
```bash
# ACI deployment
az container create --resource-group hackgpt --name hackgpt-api
```

#### GCP Deployment
```bash
# GKE deployment
gcloud container clusters create hackgpt-cluster
kubectl apply -f k8s/
```

## 🔧 Troubleshooting

### Common Enterprise Issues

#### Database Connection Issues
```bash
# Check PostgreSQL status
systemctl status postgresql
docker logs hackgpt-database

# Test connection
python3 -c "from database import get_db_manager; print(get_db_manager().test_connection())"
```

#### Redis Cache Issues
```bash
# Check Redis status
redis-cli ping
docker logs hackgpt-redis

# Clear cache
redis-cli FLUSHALL
```

#### AI Engine Issues
```bash
# Test OpenAI connectivity
python3 -c "import openai; print(openai.Model.list())"

# Check local LLM
ollama list
ollama run llama2:7b
```

#### Worker Pool Issues
```bash
# Check Celery workers
celery -A performance.parallel_processor inspect active

# Restart workers
docker-compose restart hackgpt-worker
```

### Performance Optimization
```bash
# Database optimization
python3 -c "from database import optimize_database; optimize_database()"

# Cache warming
python3 -c "from performance.cache_manager import warm_cache; warm_cache()"

# Worker scaling
docker-compose up --scale hackgpt-worker=10
```

## � AI-Powered Hacking with Docker & MCP

HackGPT includes a **Kali Linux MCP Server** that turns any MCP-compatible AI
assistant (Claude Desktop, Codespaces Copilot, etc.) into a full-fledged
penetration-testing operator — with zero setup on the host.

### How It Works

```
┌──────────────┐       MCP (HTTP)       ┌──────────────────────┐
│  Claude AI   │ ◄───────────────────► │  HackGPT             │
│  (Desktop /  │                       │  MCP Server           │
│   Codespace) │                       │  (integrated module)  │
└──────────────┘                       └──────────────────────┘
                                          │ nmap, nikto, sqlmap
                                          │ metasploit, hydra …
```

The MCP server is built into HackGPT — same application, same container.
Start it from the menu (option **16**), the CLI flag `--mcp`, or via Docker Compose.

### Quick Start

```bash
# Option A: Run directly (Kali Linux host or container)
python3 hackgpt_v2.py --mcp

# Option B: Use docker-compose
docker-compose up -d hackgpt-kali-mcp

# Option C: From the interactive menu → option 16
python3 hackgpt_v2.py
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "hackgpt-kali": {
      "url": "http://localhost:8811/mcp"
    }
  }
}
```

### Available MCP Tools

| Tool | Purpose |
|------|---------|
| `run_command` | Execute any shell command in Kali |
| `nmap_scan` | Port scanning & service detection |
| `nikto_scan` | Web-server vulnerability scanning |
| `sqlmap_scan` | SQL-injection detection & exploitation |
| `gobuster_scan` | Directory / DNS brute-forcing |
| `hydra_attack` | Online password cracking |
| `metasploit_run` | Metasploit modules |
| `whatweb_scan` | Web-technology fingerprinting |
| `whois_lookup` | Domain / IP WHOIS |
| `hashcat_crack` | Offline hash cracking |
| `amass_enum` | Subdomain enumeration |
| `exploit_search` | ExploitDB search |

### Example Prompts

```
Scan 10.0.0.0/24 for open ports and running services.

Run a Nikto scan against http://testsite.local.

Search ExploitDB for Apache 2.4 vulnerabilities.

Enumerate subdomains of example.com with Amass.

Use Metasploit to check if host 10.0.0.5 is vulnerable to EternalBlue.
```

> 📖 MCP module source: [`hackgpt_mcp/`](hackgpt_mcp/) | Standalone reference: [`mcp-kali-server/`](mcp-kali-server/)

## 🖥️ Native macOS App

HackGPT ships as a **native Swift/SwiftUI macOS application** optimized for Apple Silicon (M4).

### Install & Launch

```bash
cd HackGPTApp
chmod +x build_and_install.sh
./build_and_install.sh
```

Then launch from **Finder**, **Launchpad**, or **Spotlight** (Cmd+Space → "HackGPT").

### Auto-Launch Services

When HackGPT opens, it **automatically starts all services**:

| Service | Port | Description |
|---------|------|-------------|
| API Backend | 8000 | REST API server |
| MCP Kali Server | 8811 | Model Context Protocol tools |
| Web Dashboard | 8080 | Browser-based dashboard |
| Realtime Dashboard | 5000 | Live monitoring |

All services **shut down automatically** when you quit the app.

### iPhone / iPad

HackGPT also supports iOS in **remote mode** — the iPhone app connects to your Mac's servers over WiFi.

```bash
# Generate Xcode project for iOS
cd HackGPTApp && xcodegen generate && open HackGPT.xcodeproj
```

See [HackGPTApp/IOS_SETUP.md](HackGPTApp/IOS_SETUP.md) for full iOS deployment guide.

## 🤖 Agent Mode (ChatGPT-like Interface)

HackGPT includes a built-in **Agent Mode** — a ChatGPT-like conversational interface powered by the OpenAI Responses API with tool-calling capabilities.

### Features

| Capability | Description |
|---|---|
| **Tool Calling** | Web search, code interpreter, file search, image generation — all via OpenAI built-in tools |
| **Streaming** | SSE-based real-time token streaming for responsive chat |
| **Conversation Memory** | Persistent conversations with pin, archive, and history |
| **Project Workspaces** | Per-project vector stores for RAG-powered file search |
| **Usage Metering** | Per-user rate limiting, token budgets, and cost tracking |
| **ChatGPT-like UI** | Full single-page chat interface at `/agent` |

### Quick Start

1. **Set your OpenAI API key** in `.env`:

```bash
cp .env.example .env
# Edit .env and set:
OPENAI_API_KEY=sk-...
AGENT_ENABLE_WEB_SEARCH=true
AGENT_ENABLE_CODE_INTERPRETER=true
```

2. **Access the Agent UI** at `http://localhost:5000/agent` when running the Flask app.

3. **Or use the REST API** directly:

```bash
# Chat (blocking)
curl -X POST http://localhost:5000/api/agent/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user1" \
  -d '{"message": "Scan example.com for open ports"}'

# Chat (streaming via SSE)
curl -N -X POST http://localhost:5000/api/agent/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user1" \
  -d '{"message": "Explain SQL injection", "tool_overrides": {"web_search": true}}'

# List conversations
curl http://localhost:5000/api/agent/conversations -H "X-User-ID: user1"

# Create a workspace with file search
curl -X POST http://localhost:5000/api/agent/workspaces \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user1" \
  -d '{"name": "pentest-acme"}'

# Check usage & rate limits
curl http://localhost:5000/api/agent/usage -H "X-User-ID: user1"
```

### Configuration (Environment Variables)

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required. Your OpenAI API key |
| `AGENT_MODEL` | `gpt-4o` | Default model for chat |
| `AGENT_ENABLE_WEB_SEARCH` | `false` | Enable web search tool |
| `AGENT_ENABLE_CODE_INTERPRETER` | `false` | Enable code interpreter |
| `AGENT_ENABLE_FILE_SEARCH` | `false` | Enable file search (RAG) |
| `AGENT_ENABLE_IMAGE_GENERATION` | `false` | Enable image generation |
| `AGENT_RATE_LIMIT_RPM` | `20` | Max requests per minute per user |
| `AGENT_RATE_LIMIT_RPD` | `500` | Max requests per day per user |
| `AGENT_MAX_TOKENS_REQUEST` | `16384` | Max tokens per single request |
| `AGENT_MAX_TOKENS_DAY` | `500000` | Daily token budget per user |
| `AGENT_MAX_IMAGES_DAY` | `20` | Max image generations per day |

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/agent/health` | Health check & feature flags |
| `POST` | `/api/agent/chat` | Send message (blocking response) |
| `POST` | `/api/agent/chat/stream` | Send message (SSE streaming) |
| `GET` | `/api/agent/conversations` | List user conversations |
| `GET` | `/api/agent/conversations/:id` | Get conversation details |
| `DELETE` | `/api/agent/conversations/:id` | Delete conversation |
| `POST` | `/api/agent/conversations/:id/pin` | Pin/unpin conversation |
| `POST` | `/api/agent/conversations/:id/archive` | Archive/unarchive |
| `GET` | `/api/agent/workspaces` | List user workspaces |
| `POST` | `/api/agent/workspaces` | Create workspace |
| `DELETE` | `/api/agent/workspaces/:id` | Delete workspace |
| `POST` | `/api/agent/workspaces/:id/files` | Upload file to workspace |
| `GET` | `/api/agent/workspaces/:id/files` | List workspace files |
| `DELETE` | `/api/agent/workspaces/:id/files/:fid` | Delete file |
| `GET` | `/api/agent/usage` | Usage stats & limits |

### Architecture

```
agent/
├── config.py          # AgentConfig & AgentLimits dataclasses
├── schemas.py         # Message, Conversation, Workspace, UsageRecord models
├── openai_client.py   # OpenAI Responses API wrapper
├── metering.py        # Per-user rate limiting & token budgets
├── orchestrator.py    # Multi-turn agent loop with tool dispatch
├── vector_store.py    # Workspace-scoped vector stores for RAG
├── api.py             # Flask Blueprint with 15 REST endpoints
└── tools/
    └── __init__.py    # Tool registry (web search, code interpreter, etc.)
```

## 🛡️ Quality Gates & Autofix

### TL;DR — Automated Safety Net

Every pull request runs **five automated gates** before it can merge:

| Gate | Tool | What it checks |
|------|------|---------------|
| **Lint & Format** | ruff | Code style, import ordering, common bugs |
| **Type Check** | mypy | Type annotation correctness |
| **Unit Tests** | pytest | Functional correctness across Python 3.9–3.12 |
| **Security Scan** | bandit + pip-audit | Vulnerable code patterns + dependency CVEs |
| **CodeQL** | GitHub Code Scanning | Injection, XSS, path traversal, insecure crypto |

All configuration lives in [`pyproject.toml`](pyproject.toml).

### CodeQL Code Scanning

Every PR and weekly schedule runs **GitHub CodeQL** analysis for JavaScript/TypeScript and Python:

- Workflow: [`.github/workflows/codeql.yml`](.github/workflows/codeql.yml)
- Alerts appear as PR annotations and under Security → Code scanning
- **Copilot Autofix** suggests patches directly on alerts — always review before merging

#### Enable Default Setup (UI)

1. Go to **Settings → Security → Code security and analysis**
2. Under **Code scanning** → **CodeQL analysis** → click **Default**
3. Select languages and enable

#### Enable via CLI

```bash
gh api -X PUT -H "Accept: application/vnd.github+json" \
  /repos/<OWNER>/<REPO>/branches/main/protection \
  -f required_status_checks[strict]=true \
  -f 'required_status_checks[contexts][]=code-scanning' \
  -f 'required_status_checks[contexts][]=lint' \
  -f 'required_status_checks[contexts][]=test' \
  -f enforce_admins=true \
  -f restrictions=null -f required_pull_request_reviews=null
```

### Running Quality Checks Locally

```bash
# Install tools
pip install ruff mypy bandit pip-audit pytest pytest-cov

# Lint
ruff check .
ruff format --check .

# Type check
mypy hackgpt.py hackgpt_v2.py --ignore-missing-imports

# Security scan
bandit -r hackgpt.py hackgpt_v2.py -s B101,B603,B602,B607
pip-audit -r requirements.txt --desc

# Tests
pytest tests/ -v
```

### Input Validation & Rate Limiting

HackGPT now includes built-in protections:

- **Input validation**: Target IPs/domains and scope text are validated against strict patterns and length limits before processing
- **Rate limiting**: AI API calls are rate-limited to 30 requests per minute per session to prevent abuse and runaway costs
- **Ethical disclaimers**: The exploitation phase displays a mandatory legal disclaimer requiring explicit confirmation

### Sentry Copilot Extension

1. Install [Sentry for GitHub Copilot](https://github.com/marketplace/sentry-copilot) from the Marketplace
2. Connect your Sentry project in VS Code/Codespaces
3. In PRs, use prompts like:
   - `@sentry What errors occurred in the last 24 hours?`
   - `@sentry Suggest a minimal fix and generate tests for commit XYZ`
   - `@sentry Show unresolved issues for this file`

### Docker Copilot

1. Install [Docker for GitHub Copilot](https://github.com/marketplace/docker-for-github-copilot)
2. Use prompts like:
   - `@docker Optimize this Dockerfile for production`
   - `@docker Add healthcheck to my compose services`
   - `@docker Scan my image for vulnerabilities`
   - `@docker Convert to multi-stage build`

### Branch Protection (Required Checks)

Set up required status checks before merging:

1. **Settings → Branches → Add rule** → pattern: `main`
2. Enable **Require status checks to pass**
3. Add checks: `code-scanning`, `lint`, `test`, `security`
4. Enable **Require branches to be up to date**
5. Enable **Enforce for administrators**

### Docker Hardening

The Dockerfile follows security best practices:

- **Multi-stage build**: Builder and runtime stages to minimize attack surface
- **Non-root user**: Application runs as `hackgpt` user, not root
- **Health check**: Built-in HTTP health probe against `/api/health`
- **No cache**: `--no-cache-dir` prevents pip cache from inflating image size
- **Localhost binding**: `docker-compose.yml` binds all infrastructure ports to `127.0.0.1`

### Org-Wide Reusable Workflow

Place `org/reusable-codeql.yml` in `<OWNER>/.github/.github/workflows/` then call from any repo:

```yaml
jobs:
  security:
    uses: <OWNER>/.github/.github/workflows/reusable-codeql.yml@main
    secrets: inherit
```

See [`org/_org_checklist.md`](org/_org_checklist.md) for full org setup guide.

## 📄 Enterprise License

This project is licensed under the MIT License with additional enterprise terms:

- **Commercial Use**: Permitted with attribution
- **Enterprise Support**: Available through support channels
- **Compliance**: Tool usage must comply with applicable laws
- **Liability**: Limited liability for enterprise deployments

## 🆘 Enterprise Support

### Support Channels
- **Enterprise Support**: yashabalam707@gmail.com
- **Technical Issues**: https://github.com/yashab-cyber/HackGPT/issues
- **Feature Requests**: https://github.com/yashab-cyber/HackGPT/discussions
- **Security Issues**: yashabalam707@gmail.com
- **WhatsApp Business**: [Join Channel](https://whatsapp.com/channel/0029Vaoa1GfKLaHlL0Kc8k1q)

### Professional Services
- **Implementation**: Custom deployment and configuration
- **Training**: Security team training and certification  
- **Custom Development**: Feature development and integration
- **24/7 Support**: Enterprise support packages available

### Connect with the Team
- **Yashab Alam**: [GitHub](https://github.com/yashab-cyber) | [Instagram](https://www.instagram.com/yashab.alam) | [LinkedIn](https://www.linkedin.com/in/yashab-alam)
- **ZehraSec**: [Website](https://www.zehrasec.com) | [Instagram](https://www.instagram.com/_zehrasec) | [LinkedIn](https://www.linkedin.com/company/zehrasec)

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Total Lines of Code** | 15,000+ |
| **Enterprise Dependencies** | 90+ |
| **Configuration Options** | 200+ |
| **Environment Variables** | 100+ |
| **Docker Services** | 13 |
| **Supported Compliance Frameworks** | 5 |
| **Penetration Testing Tools** | 50+ |
| **API Endpoints** | 25+ |
| **Deployment Platforms** | 6+ |

## 🗺️ Roadmap

### Version 2.1 (Q3 2025)
- [ ] Advanced threat hunting capabilities
- [ ] ML-based false positive reduction
- [ ] Integration with popular SIEM systems
- [ ] Mobile application for executives

### Version 2.2 (Q4 2025) 
- [ ] Automated penetration testing workflows
- [ ] Advanced cloud security assessments
- [ ] Integration with CI/CD pipelines
- [ ] Enhanced compliance reporting

### Version 3.0 (Q1 2026)
- [ ] Fully autonomous security assessments
- [ ] Advanced AI attack simulation
- [ ] Quantum-safe cryptography
- [ ] Next-generation threat detection

## 🙏 Contributors

### Core Development Team
- **Lead Developer & Founder**: [Yashab Alam](https://github.com/yashab-cyber) - [@yashab.alam](https://www.instagram.com/yashab.alam) | [LinkedIn](https://www.linkedin.com/in/yashab-alam)
- **Company**: [ZehraSec](https://www.zehrasec.com) - Cybersecurity Solutions & Research
- **AI/ML Engineer**: Enterprise AI Team
- **Security Engineer**: Enterprise Security Team
- **DevOps Engineer**: Enterprise Infrastructure Team

### ZehraSec Social Media
- 🌐 **Website**: [www.zehrasec.com](https://www.zehrasec.com)
- 📸 **Instagram**: [@_zehrasec](https://www.instagram.com/_zehrasec?igsh=bXM0cWl1ejdoNHM4)
- 📘 **Facebook**: [ZehraSec Official](https://www.facebook.com/profile.php?id=61575580721849)
- 🐦 **X (Twitter)**: [@zehrasec](https://x.com/zehrasec?t=Tp9LOesZw2d2yTZLVo0_GA&s=08)
- 💼 **LinkedIn**: [ZehraSec Company](https://www.linkedin.com/company/zehrasec)
- 💬 **WhatsApp**: [Business Channel](https://whatsapp.com/channel/0029Vaoa1GfKLaHlL0Kc8k1q)

### Acknowledgments
- OpenAI for GPT-4 API access
- Ollama team for local LLM support
- Docker & Kubernetes communities
- Security research community
- Open source tool developers

### 💰 Support HackGPT Development
Your donations help accelerate development and support the growing cybersecurity community:

**Cryptocurrency Donations (Recommended):**
- **Solana (SOL)**: `5pEwP9JN8tRCXL5Vc9gQrxRyHHyn7J6P2DCC8cSQKDKT`
- **Bitcoin (BTC)**: `bc1qmkptg6wqn9sjlx6wf7dk0px0yq4ynr4ukj2x8c`

**Traditional Payment:**
- **PayPal**: [yashabalam707@gmail.com](https://paypal.me/yashab07)
- **Email**: yashabalam707@gmail.com

**📄 Full Donation Information**: [DONATE.md](DONATE.md) - Support tiers, funding goals, and recognition programs

## ⚖️ Legal & Compliance

**⚠️ IMPORTANT LEGAL NOTICE**

HackGPT Enterprise is designed for authorized security testing only:

- ✅ **Authorized Use**: Only use against systems you own or have explicit written permission
- ✅ **Compliance**: Follow all applicable laws, regulations, and industry standards
- ✅ **Responsible Disclosure**: Report vulnerabilities through proper channels
- ✅ **Documentation**: Maintain audit trails and documentation
- ❌ **Unauthorized Use**: Never use against systems without permission
- ❌ **Malicious Activity**: Not for criminal or malicious purposes

**The developers and contributors are not liable for misuse of this platform.**

---

---

<div align="center">
  <img src="public/hackgpt-logo.png" alt="HackGPT Enterprise" width="150" height="auto">
  
  <h3>🚀 HackGPT Enterprise - Transforming Cybersecurity Through AI 🚀</h3>
  <p><em>Made with ❤️ by Yashab Alam & ZehraSec for enterprise security teams worldwide</em></p>
  
  <p>
    <a href="https://github.com/yashab-cyber/HackGPT">⭐ Star us on GitHub</a> |
    <a href="DONATE.md">💰 Support Development</a> |
    <a href="#-enterprise-support">📞 Get Support</a> |
    <a href="#-contributors">🤝 Contribute</a> |
    <a href="LICENSE">📄 License</a>
  </p>
</div>

### 🔗 Connect with ZehraSec & Yashab Alam

<div align="center">
  <p>
    <a href="https://www.zehrasec.com">🌐 ZehraSec Website</a> |
    <a href="https://www.instagram.com/_zehrasec">📸 ZehraSec Instagram</a> |
    <a href="https://www.linkedin.com/company/zehrasec">💼 ZehraSec LinkedIn</a> |
    <a href="https://whatsapp.com/channel/0029Vaoa1GfKLaHlL0Kc8k1q">💬 WhatsApp Business</a>
  </p>
  
  <p>
    <strong>Founder & Lead Developer:</strong><br>
    <a href="https://github.com/yashab-cyber">🔧 Yashab Alam GitHub</a> |
    <a href="https://www.instagram.com/yashab.alam">📸 Personal Instagram</a> |
    <a href="https://www.linkedin.com/in/yashab-alam">💼 LinkedIn Profile</a>
  </p>
</div>
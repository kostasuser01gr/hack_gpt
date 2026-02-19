#!/bin/bash

# HackGPT Enterprise - Unrestricted Mode Launcher
# Launches HackGPT with all security restrictions bypassed

echo "🔥 HackGPT Enterprise - UNRESTRICTED MODE 🔥"
echo "=========================================="
echo ""

# Set unrestricted environment variables
export UNRESTRICTED_MODE=true
export ADMIN_BYPASS_MODE=true
export UNRESTRICTED_TOOLS=true
export FILESYSTEM_BYPASS=true
export DANGEROUS_OPERATIONS=true
export STEALTH_MODE=true
export COMPLIANCE_BYPASS=true
export BYPASS_SECRET="hackgpt-unrestricted"

# Navigate to HackGPT directory
cd "$(dirname "$0")"

echo "✅ Environment variables set for unrestricted mode"
echo ""
echo "📋 Configuration:"
echo "  - Authentication: BYPASSED"
echo "  - Permissions: ALL GRANTED"
echo "  - Network Access: UNRESTRICTED"
echo "  - API Limits: DISABLED"
echo "  - Audit Logging: DISABLED"
echo "  - Compliance: BYPASSED"
echo "  - File System: FULL ACCESS"
echo "  - Offensive Tools: ENABLED"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
echo "🐍 Python Version: $PYTHON_VERSION"

# Install required packages if not present
echo "🔧 Checking dependencies..."
if ! python3 -c "import rich" 2>/dev/null; then
    echo "📦 Installing required packages..."
    pip install rich bcrypt jwt flask requests --quiet
fi

# Check for offensive security tools
echo "🔍 Checking offensive security tools..."
MISSING_TOOLS=()

for tool in nmap metasploit msfrpc sqlmapapi hydra scapy impacket crackmapexec aircrack pwntools; do
    if ! python3 -c "import $tool" 2>&1 | grep -q "ModuleNotFoundError"; then
        echo "  ✅ $tool - Available"
    else
        echo "  ⚠️  $tool - Not installed"
        MISSING_TOOLS+=("$tool")
    fi
done

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo ""
    echo "💡 Tip: Install missing offensive tools for full functionality:"
    echo "   pip install python-nmap python-metasploit sqlmapapi python-hydra scapy impacket crackmapexec aircrack-ng pwntools"
fi

echo ""
echo "🚀 Launching HackGPT in UNRESTRICTED MODE..."
echo "=========================================="
echo ""

# Run HackGPT with unrestricted mode
python3 hackgpt_v2.py "$@"

echo ""
echo "💥 HackGPT session completed"

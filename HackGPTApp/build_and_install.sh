#!/bin/bash
#
# HackGPT Enterprise — Build & Install Script
# Builds the native macOS app, packages it as a .app bundle,
# and installs it to /Applications with the icon visible in Finder.
#
# Usage:
#   chmod +x build_and_install.sh
#   ./build_and_install.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
APP_NAME="HackGPT"
APP_BUNDLE="${APP_NAME}.app"
BUILD_DIR="${SCRIPT_DIR}/.build"
RELEASE_BIN="${BUILD_DIR}/release/HackGPTApp"
DEST_APP="/Applications/${APP_BUNDLE}"
TEMPLATE_APP="${SCRIPT_DIR}/${APP_BUNDLE}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  HackGPT Enterprise — Build & Install"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Project Root: ${PROJECT_ROOT}"
echo "  App Bundle:   ${DEST_APP}"
echo ""

# Step 1: Build release binary
echo "▸ [1/5] Building release binary (Apple Silicon optimized)..."
cd "${SCRIPT_DIR}"
swift build -c release --arch arm64 2>&1 | tail -5

if [ ! -f "${RELEASE_BIN}" ]; then
    echo "❌ Build failed — binary not found at ${RELEASE_BIN}"
    exit 1
fi
echo "  ✅ Binary built: $(du -h "${RELEASE_BIN}" | cut -f1) (arm64)"

# Step 2: Prepare .app bundle
echo ""
echo "▸ [2/5] Preparing .app bundle..."

# Create fresh staging area
STAGING="/tmp/HackGPT-staging"
rm -rf "${STAGING}"
mkdir -p "${STAGING}/${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${STAGING}/${APP_BUNDLE}/Contents/Resources"

# Copy binary
cp "${RELEASE_BIN}" "${STAGING}/${APP_BUNDLE}/Contents/MacOS/${APP_NAME}"
chmod +x "${STAGING}/${APP_BUNDLE}/Contents/MacOS/${APP_NAME}"

# Copy Info.plist
cp "${TEMPLATE_APP}/Contents/Info.plist" "${STAGING}/${APP_BUNDLE}/Contents/"

# Copy icon
if [ -f "${TEMPLATE_APP}/Contents/Resources/AppIcon.icns" ]; then
    cp "${TEMPLATE_APP}/Contents/Resources/AppIcon.icns" "${STAGING}/${APP_BUNDLE}/Contents/Resources/"
    echo "  ✅ Icon copied"
else
    echo "  ⚠️  No AppIcon.icns found — Finder will show generic icon"
fi

# Embed project root path for auto-discovery
defaults write "${STAGING}/${APP_BUNDLE}/Contents/Info" HackGPTProjectRoot -string "${PROJECT_ROOT}"

echo "  ✅ App bundle prepared"

# Step 3: Store project root for the app to discover
echo ""
echo "▸ [3/5] Configuring project root..."
defaults write com.hackgpt.enterprise HackGPTProjectRoot -string "${PROJECT_ROOT}"
echo "  ✅ Project root stored: ${PROJECT_ROOT}"

# Step 4: Install to /Applications
echo ""
echo "▸ [4/5] Installing to /Applications..."

if [ -d "${DEST_APP}" ]; then
    echo "  Removing existing installation..."
    rm -rf "${DEST_APP}"
fi

cp -R "${STAGING}/${APP_BUNDLE}" "${DEST_APP}"
rm -rf "${STAGING}"

# Touch to update Finder/LaunchServices
touch "${DEST_APP}"

echo "  ✅ Installed: ${DEST_APP}"

# Step 5: Register with LaunchServices & update Finder
echo ""
echo "▸ [5/5] Registering with macOS..."

# Register app with Launch Services so icon shows properly
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "${DEST_APP}" 2>/dev/null || true

# Clear icon cache
killall Finder 2>/dev/null || true
sleep 1

echo "  ✅ Registered with LaunchServices"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ HackGPT Enterprise installed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  📍 Location: /Applications/HackGPT.app"
echo "  🚀 Launch:   open /Applications/HackGPT.app"
echo "  🔍 Finder:   Cmd+Space → 'HackGPT'"
echo ""
echo "  When launched, HackGPT will automatically start:"
echo "    • API Backend (port 8000)"
echo "    • MCP Kali Server (port 8811)"
echo "    • Web Dashboard (port 8080)"
echo "    • Realtime Dashboard (port 5000)"
echo ""
echo "  All services shut down automatically when you quit the app."
echo ""

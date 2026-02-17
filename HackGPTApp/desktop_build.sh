#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# HackGPT Desktop – Build & Package Script
# Outputs: HackGPT.app (macOS .app bundle) + optional DMG installer
#
# Usage:
#   ./desktop_build.sh dev        # Debug build + run (hot reload via rebuild)
#   ./desktop_build.sh build      # Release build, create .app bundle
#   ./desktop_build.sh dist       # Release build + .app + DMG installer
#   ./desktop_build.sh clean      # Remove build artifacts
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$SCRIPT_DIR"
APP_NAME="HackGPT"
BUNDLE_ID="com.hackgpt.enterprise"
VERSION="2.1.0"
BUILD_NUMBER="$(date +%Y%m%d%H%M)"

# Paths
APP_BUNDLE="$APP_DIR/$APP_NAME.app"
DIST_DIR="$REPO_ROOT/dist"
DMG_NAME="${APP_NAME}-${VERSION}-arm64.dmg"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${BLUE}[BUILD]${NC} $*"; }
ok()    { echo -e "${GREEN}[  OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN ]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ============================================================================
# Pre-flight checks
# ============================================================================
preflight() {
    log "Checking prerequisites..."

    # Swift compiler
    if ! command -v swift &>/dev/null; then
        err "Swift not found. Install Xcode Command Line Tools: xcode-select --install"
        exit 1
    fi
    ok "Swift $(swift --version 2>&1 | head -1 | sed 's/.*version //' | cut -d' ' -f1)"

    # Python 3
    local python=""
    for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
        if [[ -x "$p" ]]; then python="$p"; break; fi
    done
    if [[ -z "$python" ]]; then
        warn "Python 3 not found. The app will prompt for setup on first run."
    else
        ok "Python $($python --version 2>&1 | cut -d' ' -f2) at $python"
    fi

    # Check that project files exist
    if [[ ! -f "$REPO_ROOT/hackgpt_v2.py" ]]; then
        err "hackgpt_v2.py not found at $REPO_ROOT"
        exit 1
    fi
    ok "Project root: $REPO_ROOT"
}

# ============================================================================
# Build
# ============================================================================
build_debug() {
    log "Building debug..."
    cd "$APP_DIR"
    swift build 2>&1
    ok "Debug build complete"
}

build_release() {
    log "Building release (arm64)..."
    cd "$APP_DIR"
    swift build -c release 2>&1
    ok "Release build complete"
}

# ============================================================================
# Create .app bundle
# ============================================================================
create_app_bundle() {
    log "Creating .app bundle..."

    # Clean previous
    rm -rf "$APP_BUNDLE"

    # Structure
    mkdir -p "$APP_BUNDLE/Contents/MacOS"
    mkdir -p "$APP_BUNDLE/Contents/Resources"
    mkdir -p "$APP_BUNDLE/Contents/Resources/python-app"

    # Copy binary
    cp "$APP_DIR/.build/release/HackGPTApp" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
    ok "Binary copied"

    # Copy Python project files (only what's needed, skip heavy/temp dirs)
    local rsync_excludes=(
        --exclude='.git'
        --exclude='__pycache__'
        --exclude='*.pyc'
        --exclude='.pytest_cache'
        --exclude='node_modules'
        --exclude='dist'
        --exclude='.build'
        --exclude='*.app'
        --exclude='*.bak.*'
        --exclude='HackGPTApp'
        --exclude='logs/*.log'
        --exclude='logs/'
        --exclude='*.db'
        --exclude='.env'
        --exclude='.env.local'
        --exclude='.ruff_cache'
        --exclude='.mypy_cache'
        --exclude='*.egg-info'
        --exclude='htmlcov'
        --exclude='public/*.png'
        --exclude='.venv'
        --exclude='venv'
        --exclude='env'
        --exclude='.tox'
        --exclude='*.dmg'
        --exclude='*.iso'
        --exclude='config.ini.bak.*'
        --exclude='hackgpt_v2.py.bak.*'
    )
    rsync -a "${rsync_excludes[@]}" "$REPO_ROOT/" "$APP_BUNDLE/Contents/Resources/python-app/"
    ok "Python source bundled"

    # Info.plist
    cat > "$APP_BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>${BUNDLE_ID}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>HackGPT Enterprise</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>${BUILD_NUMBER}</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>CFBundleSupportedPlatforms</key>
    <array>
        <string>MacOSX</string>
    </array>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIconName</key>
    <string>AppIcon</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.developer-tools</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2026 HackGPT Team. All rights reserved.</string>
    <key>LSArchitecturePriority</key>
    <array>
        <string>arm64</string>
    </array>
</dict>
</plist>
PLIST
    ok "Info.plist generated"

    # Copy entitlements
    if [[ -f "$APP_DIR/HackGPT.entitlements" ]]; then
        cp "$APP_DIR/HackGPT.entitlements" "$APP_BUNDLE/Contents/Resources/"
        ok "Entitlements copied"
    fi

    # Generate icon if .icns exists; otherwise create a placeholder
    if [[ -f "$APP_DIR/HackGPT.app.bak/Contents/Resources/AppIcon.icns" ]]; then
        cp "$APP_DIR/HackGPT.app.bak/Contents/Resources/AppIcon.icns" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
    elif [[ -f "$REPO_ROOT/public/hackgpt-logo.png" ]]; then
        generate_icns "$REPO_ROOT/public/hackgpt-logo.png" "$APP_BUNDLE/Contents/Resources/AppIcon.icns" 2>/dev/null || true
    fi

    # Calculate bundle size
    local size
    size=$(du -sh "$APP_BUNDLE" | cut -f1)
    ok ".app bundle created: $APP_BUNDLE ($size)"
}

# ============================================================================
# Icon generation (from PNG)
# ============================================================================
generate_icns() {
    local src_png="$1"
    local dst_icns="$2"

    if ! command -v sips &>/dev/null; then
        warn "sips not available, skipping icon generation"
        return 1
    fi

    local iconset_dir
    iconset_dir=$(mktemp -d)/AppIcon.iconset
    mkdir -p "$iconset_dir"

    for size in 16 32 64 128 256 512; do
        sips -z "$size" "$size" "$src_png" --out "$iconset_dir/icon_${size}x${size}.png" &>/dev/null
        local double=$((size * 2))
        sips -z "$double" "$double" "$src_png" --out "$iconset_dir/icon_${size}x${size}@2x.png" &>/dev/null
    done

    iconutil -c icns -o "$dst_icns" "$iconset_dir" 2>/dev/null
    rm -rf "$(dirname "$iconset_dir")"
    ok "App icon generated"
}

# ============================================================================
# Create DMG installer
# ============================================================================
create_dmg() {
    log "Creating DMG installer..."

    mkdir -p "$DIST_DIR"
    local dmg_path="$DIST_DIR/$DMG_NAME"
    rm -f "$dmg_path"

    # Create a temporary directory for DMG contents
    local dmg_tmp
    dmg_tmp=$(mktemp -d)
    cp -R "$APP_BUNDLE" "$dmg_tmp/"

    # Create a symlink to /Applications for drag-and-drop install
    ln -s /Applications "$dmg_tmp/Applications"

    # Create DMG
    hdiutil create -volname "$APP_NAME" \
        -srcfolder "$dmg_tmp" \
        -ov -format UDZO \
        "$dmg_path" 2>/dev/null

    rm -rf "$dmg_tmp"

    local size
    size=$(du -sh "$dmg_path" | cut -f1)
    ok "DMG created: $dmg_path ($size)"
    echo ""
    echo -e "${GREEN}=== Distribution Ready ===${NC}"
    echo -e "  .app:  $APP_BUNDLE"
    echo -e "  .dmg:  $dmg_path"
    echo ""
    echo -e "${YELLOW}Note: This app is unsigned. Users must right-click → Open on first launch.${NC}"
    echo -e "${YELLOW}For proper signing, see: README.md → Signing & Notarization${NC}"
}

# ============================================================================
# Clean
# ============================================================================
clean() {
    log "Cleaning build artifacts..."
    cd "$APP_DIR"
    rm -rf .build
    rm -rf "$APP_BUNDLE"
    rm -rf "$DIST_DIR"
    ok "Clean complete"
}

# ============================================================================
# Main
# ============================================================================
MODE="${1:-dev}"

case "$MODE" in
    dev)
        preflight
        build_debug
        log "Launching in development mode..."
        cd "$APP_DIR"
        exec .build/debug/HackGPTApp
        ;;
    build)
        preflight
        build_release
        create_app_bundle
        ;;
    dist)
        preflight
        build_release
        create_app_bundle
        create_dmg
        ;;
    clean)
        clean
        ;;
    *)
        echo "Usage: $0 {dev|build|dist|clean}"
        echo ""
        echo "  dev    – Debug build + run"
        echo "  build  – Release build + .app bundle"
        echo "  dist   – Release build + .app + DMG installer"
        echo "  clean  – Remove build artifacts"
        exit 1
        ;;
esac

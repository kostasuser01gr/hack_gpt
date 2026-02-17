#!/usr/bin/env bash
set -euo pipefail

# HackGPT – build & run the native macOS Swift app
# Usage:
#   ./run_app.sh          # build debug + run
#   ./run_app.sh release  # build release + run
#   ./run_app.sh bundle   # build release + create .app bundle + open

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/HackGPTApp"

cd "$APP_DIR"

MODE="${1:-debug}"

echo "🔨 Building HackGPT (${MODE})..."

case "$MODE" in
  release)
    swift build -c release 2>&1
    echo "✅ Release build complete"
    echo "🚀 Launching..."
    exec .build/release/HackGPTApp
    ;;
  bundle)
    swift build -c release 2>&1
    mkdir -p HackGPT.app/Contents/MacOS
    cp .build/release/HackGPTApp HackGPT.app/Contents/MacOS/HackGPT
    echo "✅ App bundle ready at: $APP_DIR/HackGPT.app"
    echo "🚀 Opening..."
    open HackGPT.app
    ;;
  *)
    swift build 2>&1
    echo "✅ Debug build complete"
    echo "🚀 Launching..."
    exec .build/debug/HackGPTApp
    ;;
esac

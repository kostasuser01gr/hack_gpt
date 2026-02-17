# HackGPT — iOS Setup Guide

## Prerequisites

1. **Xcode 16+** installed from the Mac App Store
2. **Apple Developer Account** (free or paid)
3. **iPhone** running iOS 16+ or **iPad** running iPadOS 16+

## Building for iPhone/iPad

### Option 1: Xcode (Recommended)

```bash
# Navigate to HackGPTApp
cd ~/HackGPT/HackGPTApp

# Generate Xcode project (if not already generated)
xcodegen generate

# Open in Xcode
open HackGPT.xcodeproj
```

In Xcode:
1. Select the **HackGPT-iOS** scheme in the toolbar
2. Select your connected iPhone or a simulator
3. Go to **Signing & Capabilities** → select your Team
4. Press **Cmd+R** to build & run

### Option 2: Command Line

```bash
# Set Xcode as active developer directory
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer

# Build for iOS Simulator
xcodebuild -project HackGPT.xcodeproj \
  -scheme HackGPT-iOS \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  -configuration Debug \
  build

# Build for physical device (requires signing)
xcodebuild -project HackGPT.xcodeproj \
  -scheme HackGPT-iOS \
  -destination 'generic/platform=iOS' \
  -configuration Release \
  CODE_SIGN_IDENTITY="Apple Development" \
  DEVELOPMENT_TEAM="YOUR_TEAM_ID" \
  build
```

## How iOS Mode Works

On iOS, HackGPT operates in **remote mode**:

- **No local shell execution** — iOS apps can't run terminal commands
- **Connects to your Mac's HackGPT server** over the local network
- **AI Chat works fully** — Ollama/OpenAI streaming works directly
- **MCP tools are accessed** through your Mac's MCP server endpoint

### Setting Up the Connection

1. Launch HackGPT on your Mac (it auto-starts all servers)
2. Note your Mac's local IP address (e.g., `192.168.1.100`)
3. On the iPhone app, go to **Config** tab
4. Set the API server URL to `http://192.168.1.100:8000`
5. MCP endpoint will be `http://192.168.1.100:8811/mcp`

### iOS Tab Layout

The iPhone app uses a bottom tab bar with:
- **Chat** — Full AI chat with Ollama/OpenAI
- **Dashboard** — Service status overview
- **MCP** — MCP server status and tools
- **Tools** — Available security tools
- **Config** — Settings and connection

## Deploying to Your iPhone

### Without Paid Developer Account (Free)

1. Connect iPhone via USB
2. In Xcode: select your iPhone as destination
3. Sign with your personal Apple ID
4. Build & run — app installs on your phone
5. On iPhone: Settings → General → VPN & Device Management → Trust your certificate
6. Note: Free provisioning profiles expire after 7 days — rebuild when needed

### With Paid Developer Account ($99/year)

1. Same as above but profiles last 1 year
2. Can also use TestFlight for distribution
3. Can create Ad Hoc profiles for multiple devices

## Architecture

```
┌─────────────────────────────────────┐
│          iPhone (iOS App)           │
│  ┌──────────┐  ┌────────────────┐  │
│  │ Chat UI  │  │   Dashboard    │  │
│  │ (SwiftUI)│  │   (SwiftUI)    │  │
│  └────┬─────┘  └───────┬────────┘  │
│       │                │           │
│       ▼                ▼           │
│  ┌──────────────────────────────┐  │
│  │   Remote API Client (HTTP)   │  │
│  └──────────────┬───────────────┘  │
└─────────────────┼──────────────────┘
                  │ WiFi/Network
┌─────────────────┼──────────────────┐
│    MacBook Air M4 (macOS App)      │
│  ┌──────────────┴───────────────┐  │
│  │     API Backend :8000        │  │
│  │     MCP Server  :8811        │  │
│  │     Web Dashboard :8080      │  │
│  │     Python/Kali Tools        │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

## Troubleshooting

**"Untrusted Developer" on iPhone:**
Settings → General → VPN & Device Management → Trust the developer

**Can't connect to Mac servers from iPhone:**
- Ensure both devices are on the same WiFi network
- Check Mac firewall allows incoming connections on ports 8000, 8811
- Try `http://<mac-ip>:8000/health` from iPhone Safari

**xcodebuild requires Xcode:**
```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

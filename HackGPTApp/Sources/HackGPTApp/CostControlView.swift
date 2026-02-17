// CostControlView.swift – Settings UI for OpenAI API cost controls
// Part of HackGPT Enterprise Desktop

import SwiftUI

struct CostControlView: View {
    @StateObject private var costManager = CostControlManager.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Cost Controls")
                    .font(.title2.bold())

                // Master toggle
                GroupBox {
                    VStack(alignment: .leading, spacing: 12) {
                        Toggle("Enable Cost Controls", isOn: $costManager.enabled)
                            .onChange(of: costManager.enabled) { _ in save() }

                        Toggle(isOn: $costManager.aiDisabled) {
                            HStack {
                                Image(systemName: "exclamationmark.octagon.fill")
                                    .foregroundStyle(.red)
                                Text("Disable AI Completely")
                            }
                        }
                        .onChange(of: costManager.aiDisabled) { _ in save() }

                        if costManager.aiDisabled {
                            Text("All OpenAI API calls are blocked. Chat and AI features will not work.")
                                .font(.caption)
                                .foregroundStyle(.red)
                        }
                    }
                    .padding(8)
                }

                // Limits
                if costManager.enabled && !costManager.aiDisabled {
                    GroupBox("Daily Limits") {
                        VStack(alignment: .leading, spacing: 16) {
                            LabeledContent("Max Requests / Day") {
                                TextField("100", value: $costManager.dailyRequestLimit, format: .number)
                                    .textFieldStyle(.roundedBorder)
                                    .frame(maxWidth: 100)
                                    .onSubmit { save() }
                            }

                            LabeledContent("Max Tokens / Day") {
                                TextField("500000", value: $costManager.dailyTokenBudget, format: .number)
                                    .textFieldStyle(.roundedBorder)
                                    .frame(maxWidth: 120)
                                    .onSubmit { save() }
                            }

                            LabeledContent("Max Cost / Day (USD)") {
                                TextField("5.00", value: $costManager.dailyCostCapUSD, format: .currency(code: "USD"))
                                    .textFieldStyle(.roundedBorder)
                                    .frame(maxWidth: 100)
                                    .onSubmit { save() }
                            }
                        }
                        .padding(8)
                    }
                }

                // Today's usage
                GroupBox("Today's Usage") {
                    VStack(alignment: .leading, spacing: 8) {
                        usageBar(label: "Requests", current: costManager.todayRequests, max: costManager.dailyRequestLimit)
                        usageBar(label: "Tokens", current: costManager.todayTokens, max: costManager.dailyTokenBudget)
                        HStack {
                            Text("Est. Cost")
                                .frame(width: 80, alignment: .leading)
                            Text(String(format: "$%.4f / $%.2f", costManager.todayEstimatedCostUSD, costManager.dailyCostCapUSD))
                                .font(.system(.body, design: .monospaced))
                        }

                        if costManager.limitReached {
                            HStack {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundStyle(.red)
                                Text(costManager.limitMessage)
                                    .font(.caption)
                                    .foregroundStyle(.red)
                            }
                            .padding(.top, 4)
                        }

                        HStack {
                            Button("Reset Today's Counters") {
                                costManager.resetTodayCounters()
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                        }
                        .padding(.top, 4)
                    }
                    .padding(8)
                }

                Spacer()
            }
            .padding(24)
        }
    }

    @ViewBuilder
    func usageBar(label: String, current: Int, max: Int) -> some View {
        let fraction = max > 0 ? min(Double(current) / Double(max), 1.0) : 0.0
        let barColor: Color = fraction >= 1.0 ? .red : (fraction >= 0.8 ? .orange : .green)

        HStack {
            Text(label)
                .frame(width: 80, alignment: .leading)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.secondary.opacity(0.15))
                    RoundedRectangle(cornerRadius: 4)
                        .fill(barColor)
                        .frame(width: geo.size.width * fraction)
                }
            }
            .frame(height: 12)
            Text("\(current) / \(max)")
                .font(.system(.caption, design: .monospaced))
                .frame(width: 120, alignment: .trailing)
        }
    }

    private func save() {
        // CostControlManager auto-saves, but force a sync
        costManager.resetTodayCounters()
    }
}

// MARK: - Keychain Settings View

struct KeychainSettingsView: View {
    @State private var openAIKey = ""
    @State private var hasKey = false
    @State private var showKey = false
    @State private var saveMessage = ""
    @State private var validated = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("API Keys & Secrets")
                    .font(.title2.bold())

                Text("Keys are stored securely in your macOS Keychain, encrypted at rest.")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                GroupBox("OpenAI API Key") {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Image(systemName: hasKey ? "checkmark.shield.fill" : "xmark.shield")
                                .foregroundStyle(hasKey ? .green : .orange)
                            Text(hasKey ? "Key stored in Keychain" : "No key configured")
                        }

                        HStack {
                            if showKey {
                                TextField("sk-...", text: $openAIKey)
                                    .textFieldStyle(.roundedBorder)
                            } else {
                                SecureField("sk-...", text: $openAIKey)
                                    .textFieldStyle(.roundedBorder)
                            }
                            Button {
                                showKey.toggle()
                            } label: {
                                Image(systemName: showKey ? "eye.slash" : "eye")
                            }
                            .buttonStyle(.borderless)
                        }

                        HStack(spacing: 12) {
                            Button("Save to Keychain") {
                                let trimmed = openAIKey.trimmingCharacters(in: .whitespacesAndNewlines)
                                if KeychainManager.shared.set(trimmed, forKey: .openAIAPIKey) {
                                    hasKey = true
                                    saveMessage = "✅ Saved to Keychain"
                                    openAIKey = ""
                                } else {
                                    saveMessage = "❌ Failed to save"
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(!KeychainManager.isValidOpenAIKeyFormat(openAIKey))

                            if hasKey {
                                Button("Remove", role: .destructive) {
                                    _ = KeychainManager.shared.delete(forKey: .openAIAPIKey)
                                    hasKey = false
                                    saveMessage = "Key removed"
                                }
                            }

                            if !saveMessage.isEmpty {
                                Text(saveMessage)
                                    .font(.caption)
                                    .foregroundStyle(saveMessage.hasPrefix("✅") ? .green : .red)
                            }
                        }

                        if !openAIKey.isEmpty && !KeychainManager.isValidOpenAIKeyFormat(openAIKey) {
                            Text("Key must start with \"sk-\" and be at least 20 characters")
                                .font(.caption2)
                                .foregroundStyle(.orange)
                        }
                    }
                    .padding(8)
                }

                GroupBox("Security Note") {
                    VStack(alignment: .leading, spacing: 6) {
                        Label("Keys never leave your device", systemImage: "lock.shield")
                        Label("Stored in macOS Keychain (encrypted)", systemImage: "key")
                        Label("Backend server binds to 127.0.0.1 only", systemImage: "network.badge.shield.half.filled")
                        Label("No secrets are committed to source control", systemImage: "checkmark.circle")
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(8)
                }

                Spacer()
            }
            .padding(24)
        }
        .onAppear {
            hasKey = KeychainManager.shared.exists(forKey: .openAIAPIKey)
        }
    }
}

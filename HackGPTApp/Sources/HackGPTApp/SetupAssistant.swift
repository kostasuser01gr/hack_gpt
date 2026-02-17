// SetupAssistant.swift – First-run setup wizard
// Part of HackGPT Enterprise Desktop

import SwiftUI

/// Checks system prerequisites and guides the user through first-run setup.
@MainActor
final class SetupChecker: ObservableObject {

    @Published var pythonOK = false
    @Published var pythonVersion = ""
    @Published var projectOK = false
    @Published var depsOK = false
    @Published var keychainKeyExists = false
    @Published var isChecking = false
    @Published var setupLog: [String] = []
    @Published var needsSetup = false

    let projectRoot: String

    init(projectRoot: String) {
        self.projectRoot = projectRoot
    }

    // MARK: - Full check

    func runAllChecks() {
        isChecking = true
        setupLog = []

        checkPython()
        checkProject()
        checkKeychain()

        // If Python + project OK, check deps
        if pythonOK && projectOK {
            checkDependencies()
        }

        needsSetup = !pythonOK || !projectOK || !keychainKeyExists
        isChecking = false
    }

    // MARK: - Python

    func checkPython() {
        let candidates = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        for path in candidates {
            if FileManager.default.fileExists(atPath: path) {
                let version = runCommand(path, args: ["--version"])
                if !version.isEmpty {
                    pythonVersion = version.trimmingCharacters(in: .whitespacesAndNewlines)
                    pythonOK = true
                    log("✅ Python found: \(pythonVersion) at \(path)")
                    return
                }
            }
        }
        pythonOK = false
        log("❌ Python 3 not found. Install via: brew install python@3.12")
    }

    // MARK: - Project files

    func checkProject() {
        let requiredFiles = ["hackgpt_v2.py", "config.ini", "requirements.txt"]
        var allFound = true
        for file in requiredFiles {
            let path = (projectRoot as NSString).appendingPathComponent(file)
            if FileManager.default.fileExists(atPath: path) {
                log("✅ Found \(file)")
            } else {
                log("❌ Missing \(file) at \(path)")
                allFound = false
            }
        }
        projectOK = allFound
    }

    // MARK: - Dependencies

    func checkDependencies() {
        let python = findPython()
        let result = runCommand(python, args: ["-c", "import flask; import sqlalchemy; print('ok')"])
        if result.contains("ok") {
            depsOK = true
            log("✅ Core Python dependencies available")
        } else {
            depsOK = false
            log("⚠️  Some Python dependencies missing. Run: pip3 install -r requirements.txt")
        }
    }

    /// Install dependencies from requirements.txt into the current Python environment.
    func installDependencies() {
        let python = findPython()
        let reqPath = (projectRoot as NSString).appendingPathComponent("requirements.txt")
        log("📦 Installing dependencies from requirements.txt...")
        let output = runCommand(python, args: ["-m", "pip", "install", "-r", reqPath, "--break-system-packages", "-q"])
        if !output.isEmpty {
            for line in output.components(separatedBy: .newlines) where !line.isEmpty {
                log("  " + line)
            }
        }
        // Re-check
        checkDependencies()
    }

    // MARK: - Keychain

    func checkKeychain() {
        keychainKeyExists = KeychainManager.shared.exists(forKey: .openAIAPIKey)
        if keychainKeyExists {
            log("✅ OpenAI API key found in Keychain")
        } else {
            log("⚠️  No OpenAI API key in Keychain (optional, can be set in Settings)")
        }
    }

    // MARK: - Helpers

    private func findPython() -> String {
        for c in ["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"] {
            if FileManager.default.fileExists(atPath: c) { return c }
        }
        return "python3"
    }

    private func log(_ msg: String) {
        setupLog.append(msg)
    }

    private func runCommand(_ command: String, args: [String]) -> String {
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: command)
        proc.arguments = args
        proc.currentDirectoryURL = URL(fileURLWithPath: projectRoot)
        let pipe = Pipe()
        proc.standardOutput = pipe
        proc.standardError = pipe
        do {
            try proc.run()
            proc.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            return String(data: data, encoding: .utf8) ?? ""
        } catch {
            return ""
        }
    }
}

// MARK: - Setup Assistant View

struct SetupAssistantView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var checker: SetupChecker
    @State private var apiKey = ""
    @State private var showKeyField = false
    @State private var isInstalling = false
    @Binding var isPresented: Bool

    init(projectRoot: String, isPresented: Binding<Bool>) {
        _checker = StateObject(wrappedValue: SetupChecker(projectRoot: projectRoot))
        _isPresented = isPresented
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "shield.checkered")
                    .font(.largeTitle)
                    .foregroundStyle(.red)
                VStack(alignment: .leading) {
                    Text("HackGPT Setup")
                        .font(.title2.bold())
                    Text("First-run environment check")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
            .padding()

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    // Python
                    checkRow(
                        title: "Python 3",
                        detail: checker.pythonOK ? checker.pythonVersion : "Not found",
                        ok: checker.pythonOK,
                        action: nil
                    )

                    // Project files
                    checkRow(
                        title: "Project Files",
                        detail: checker.projectOK ? "All found at \(checker.projectRoot)" : "Missing files",
                        ok: checker.projectOK,
                        action: nil
                    )

                    // Dependencies
                    checkRow(
                        title: "Python Dependencies",
                        detail: checker.depsOK ? "Core packages available" : "Missing packages",
                        ok: checker.depsOK,
                        action: !checker.depsOK && checker.pythonOK && checker.projectOK ? {
                            isInstalling = true
                            Task {
                                checker.installDependencies()
                                isInstalling = false
                            }
                        } : nil
                    )

                    // Keychain
                    checkRow(
                        title: "OpenAI API Key",
                        detail: checker.keychainKeyExists ? "Stored in Keychain" : "Not configured (optional)",
                        ok: checker.keychainKeyExists,
                        action: { showKeyField.toggle() }
                    )

                    if showKeyField {
                        GroupBox {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Paste your OpenAI API key (stored securely in macOS Keychain)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                HStack {
                                    SecureField("sk-...", text: $apiKey)
                                        .textFieldStyle(.roundedBorder)
                                    Button("Save") {
                                        let trimmed = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
                                        if KeychainManager.isValidOpenAIKeyFormat(trimmed) {
                                            _ = KeychainManager.shared.set(trimmed, forKey: .openAIAPIKey)
                                            checker.checkKeychain()
                                            showKeyField = false
                                            apiKey = ""
                                        }
                                    }
                                    .disabled(!KeychainManager.isValidOpenAIKeyFormat(apiKey))
                                    .buttonStyle(.borderedProminent)
                                }
                                if !apiKey.isEmpty && !KeychainManager.isValidOpenAIKeyFormat(apiKey) {
                                    Text("Key must start with \"sk-\" and be at least 20 characters")
                                        .font(.caption2)
                                        .foregroundStyle(.red)
                                }
                            }
                        }
                    }

                    // Log output
                    if !checker.setupLog.isEmpty {
                        Divider()
                        DisclosureGroup("Setup Log") {
                            ScrollView {
                                VStack(alignment: .leading, spacing: 2) {
                                    ForEach(checker.setupLog.indices, id: \.self) { i in
                                        Text(checker.setupLog[i])
                                            .font(.system(.caption, design: .monospaced))
                                            .textSelection(.enabled)
                                    }
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .frame(maxHeight: 200)
                        }
                    }
                }
                .padding()
            }

            Divider()

            // Footer
            HStack {
                Button("Re-check") {
                    checker.runAllChecks()
                }

                Spacer()

                if isInstalling {
                    ProgressView()
                        .scaleEffect(0.7)
                    Text("Installing...")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Button("Continue") {
                    isPresented = false
                }
                .buttonStyle(.borderedProminent)
                .tint(.red)
                .disabled(!checker.pythonOK || !checker.projectOK)
            }
            .padding()
        }
        .frame(width: 600, height: 520)
        .onAppear {
            checker.runAllChecks()
        }
    }

    @ViewBuilder
    func checkRow(title: String, detail: String, ok: Bool, action: (() -> Void)?) -> some View {
        HStack {
            Image(systemName: ok ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .foregroundStyle(ok ? .green : .orange)
            VStack(alignment: .leading) {
                Text(title).font(.headline)
                Text(detail).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            if let action = action {
                Button(ok ? "Change" : "Fix") { action() }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
            }
        }
    }
}

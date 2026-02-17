import SwiftUI
#if canImport(AppKit)
import AppKit
#endif
#if canImport(UIKit)
import UIKit
#endif

// MARK: - App Entry Point

@main
struct HackGPTApp: App {
    @StateObject private var appState = AppState()
    #if os(macOS)
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    #endif

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                #if os(macOS)
                .frame(minWidth: 960, minHeight: 640)
                #endif
                .onAppear {
                    appState.autoLaunchAllServices()
                }
        }
        #if os(macOS)
        .windowStyle(.titleBar)
        .defaultSize(width: 1100, height: 720)
        #endif

        #if os(macOS)
        Settings {
            SettingsView()
                .environmentObject(appState)
        }
        #endif
    }
}

#if os(macOS)
// MARK: - AppDelegate for cleanup on quit
class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationWillTerminate(_ notification: Notification) {
        // Gracefully shut down all background services
        Task { @MainActor in
            AppState.shared?.shutdownAllServices()
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}
#endif

// MARK: - Data Models

enum ServiceStatus: String, Identifiable {
    case ready = "Ready"
    case unavailable = "Unavailable"
    case disabled = "Disabled"
    case error = "Error"
    case running = "Running"

    var id: String { rawValue }

    var color: Color {
        switch self {
        case .ready, .running: return .green
        case .unavailable, .disabled: return .orange
        case .error: return .red
        }
    }

    var icon: String {
        switch self {
        case .ready, .running: return "checkmark.circle.fill"
        case .unavailable, .disabled: return "exclamationmark.triangle.fill"
        case .error: return "xmark.circle.fill"
        }
    }
}

struct ComponentInfo: Identifiable {
    let id = UUID()
    let name: String
    var status: ServiceStatus
    let detail: String
}

struct LogEntry: Identifiable {
    let id = UUID()
    let timestamp: Date
    let level: LogLevel
    let message: String

    enum LogLevel: String {
        case info = "INFO"
        case warning = "WARN"
        case error = "ERROR"
        case debug = "DEBUG"

        var color: Color {
            switch self {
            case .info: return .primary
            case .warning: return .orange
            case .error: return .red
            case .debug: return .secondary
            }
        }
    }
}

struct PentestSession: Identifiable {
    let id: String
    let target: String
    let scope: String
    let assessmentType: String
    let complianceFramework: String
    var status: String
    let startedAt: Date
    var completedAt: Date?
    var findings: Int
    var riskScore: Double
}

// MARK: - Python Backend Bridge

#if os(macOS)
@MainActor
final class PythonBridge: ObservableObject {
    @Published var isRunning = false
    @Published var output: [LogEntry] = []
    @Published var lastError: String?

    private var process: Process?
    private var outputPipe: Pipe?
    private var errorPipe: Pipe?
    let projectRoot: String

    init() {
        // Resolve project root: parent of HackGPTApp/
        let appDir = Bundle.main.bundlePath
        if appDir.contains("HackGPTApp") {
            projectRoot = (appDir as NSString)
                .deletingLastPathComponent
                .replacingOccurrences(of: "/HackGPTApp", with: "")
        } else {
            // When running from /Applications, check for stored project path
            let storedPath = UserDefaults.standard.string(forKey: "HackGPTProjectRoot") ?? ""
            if !storedPath.isEmpty && FileManager.default.fileExists(atPath: (storedPath as NSString).appendingPathComponent("hackgpt_v2.py")) {
                projectRoot = storedPath
            } else {
                // Try common locations
                let candidates = [
                    NSHomeDirectory() + "/HackGPT",
                    NSHomeDirectory() + "/Documents/HackGPT",
                    NSHomeDirectory() + "/Projects/HackGPT",
                    NSHomeDirectory() + "/Developer/HackGPT",
                    FileManager.default.currentDirectoryPath
                ]
                projectRoot = candidates.first { path in
                    FileManager.default.fileExists(atPath: (path as NSString).appendingPathComponent("hackgpt_v2.py"))
                } ?? candidates[0]
            }
        }
        // Persist for next launch
        UserDefaults.standard.set(projectRoot, forKey: "HackGPTProjectRoot")
    }

    func findPython() -> String {
        // Check Homebrew arm64 first, then system
        let candidates = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        for c in candidates {
            if FileManager.default.fileExists(atPath: c) { return c }
        }
        return "python3"
    }

    func runScript(_ scriptName: String, args: [String] = []) {
        guard !isRunning else {
            appendLog(.warning, "A process is already running")
            return
        }

        let python = findPython()
        let scriptPath = (projectRoot as NSString).appendingPathComponent(scriptName)

        guard FileManager.default.fileExists(atPath: scriptPath) else {
            appendLog(.error, "Script not found: \(scriptPath)")
            return
        }

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: python)
        proc.arguments = [scriptPath] + args
        proc.currentDirectoryURL = URL(fileURLWithPath: projectRoot)

        // Forward important env vars
        var env = ProcessInfo.processInfo.environment
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        // Ensure the project root is in PYTHONPATH so our modules resolve
        let existingPP = env["PYTHONPATH"] ?? ""
        env["PYTHONPATH"] = existingPP.isEmpty ? projectRoot : "\(projectRoot):\(existingPP)"
        proc.environment = env

        let outPipe = Pipe()
        let errPipe = Pipe()
        proc.standardOutput = outPipe
        proc.standardError = errPipe

        outputPipe = outPipe
        errorPipe = errPipe
        process = proc

        // Read stdout
        outPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            Task { @MainActor [weak self] in
                for line in text.components(separatedBy: .newlines) where !line.isEmpty {
                    self?.appendLog(.info, line)
                }
            }
        }

        // Read stderr
        errPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            Task { @MainActor [weak self] in
                for line in text.components(separatedBy: .newlines) where !line.isEmpty {
                    self?.appendLog(.warning, line)
                }
            }
        }

        proc.terminationHandler = { [weak self] p in
            Task { @MainActor [weak self] in
                self?.isRunning = false
                let code = p.terminationStatus
                if code == 0 {
                    self?.appendLog(.info, "Process finished successfully (exit 0)")
                } else {
                    self?.appendLog(.error, "Process exited with code \(code)")
                }
            }
        }

        do {
            try proc.run()
            isRunning = true
            appendLog(.info, "Started \(scriptName) with PID \(proc.processIdentifier)")
        } catch {
            appendLog(.error, "Failed to start: \(error.localizedDescription)")
            lastError = error.localizedDescription
        }
    }

    func stop() {
        guard let proc = process, proc.isRunning else { return }
        proc.terminate()
        appendLog(.info, "Sent SIGTERM to process")
    }

    func sendInput(_ text: String) {
        // For future interactive use via stdin pipe
    }

    private func appendLog(_ level: LogEntry.LogLevel, _ message: String) {
        let entry = LogEntry(timestamp: Date(), level: level, message: message)
        output.append(entry)
        // Keep buffer bounded
        if output.count > 5000 {
            output.removeFirst(output.count - 4000)
        }
    }
}
#else
// iOS stub — PythonBridge is not available on iOS, use remote API
@MainActor
final class PythonBridge: ObservableObject {
    @Published var isRunning = false
    @Published var output: [LogEntry] = []
    @Published var lastError: String?
    let projectRoot: String

    init() {
        projectRoot = UserDefaults.standard.string(forKey: "HackGPTProjectRoot") ?? ""
    }

    func findPython() -> String { return "python3" }
    func runScript(_ scriptName: String, args: [String] = []) {
        appendLog(.warning, "Direct script execution not available on iOS. Use the API server.")
    }
    func stop() {}
    func sendInput(_ text: String) {}
    private func appendLog(_ level: LogEntry.LogLevel, _ message: String) {
        output.append(LogEntry(timestamp: Date(), level: level, message: message))
    }
}
#endif

// MARK: - Service Manager (manages multiple background processes)

#if os(macOS)
@MainActor
final class ServiceManager: ObservableObject {
    @Published var services: [ManagedService] = []

    struct ManagedService: Identifiable {
        let id: String
        let name: String
        let command: String
        let args: [String]
        let port: Int?
        var process: Process?
        var isRunning: Bool = false
        var logs: [LogEntry] = []
        var pid: Int32? = nil
    }

    let projectRoot: String

    init(projectRoot: String) {
        self.projectRoot = projectRoot
    }

    func startService(id: String, name: String, command: String, args: [String], port: Int? = nil, env: [String: String] = [:]) {
        // Don't double-start
        if let idx = services.firstIndex(where: { $0.id == id }), services[idx].isRunning { return }

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: command)
        proc.arguments = args
        proc.currentDirectoryURL = URL(fileURLWithPath: projectRoot)

        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        let existingPP = environment["PYTHONPATH"] ?? ""
        environment["PYTHONPATH"] = existingPP.isEmpty ? projectRoot : "\(projectRoot):\(existingPP)"
        for (k, v) in env { environment[k] = v }
        proc.environment = environment

        let outPipe = Pipe()
        let errPipe = Pipe()
        proc.standardOutput = outPipe
        proc.standardError = errPipe

        var service = ManagedService(id: id, name: name, command: command, args: args, port: port)

        outPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            Task { @MainActor [weak self] in
                guard let self = self, let idx = self.services.firstIndex(where: { $0.id == id }) else { return }
                for line in text.components(separatedBy: .newlines) where !line.isEmpty {
                    self.services[idx].logs.append(LogEntry(timestamp: Date(), level: .info, message: line))
                    if self.services[idx].logs.count > 2000 {
                        self.services[idx].logs.removeFirst(self.services[idx].logs.count - 1500)
                    }
                }
            }
        }

        errPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            Task { @MainActor [weak self] in
                guard let self = self, let idx = self.services.firstIndex(where: { $0.id == id }) else { return }
                for line in text.components(separatedBy: .newlines) where !line.isEmpty {
                    self.services[idx].logs.append(LogEntry(timestamp: Date(), level: .warning, message: line))
                }
            }
        }

        proc.terminationHandler = { [weak self] p in
            Task { @MainActor [weak self] in
                guard let self = self, let idx = self.services.firstIndex(where: { $0.id == id }) else { return }
                self.services[idx].isRunning = false
                self.services[idx].process = nil
                self.services[idx].logs.append(LogEntry(timestamp: Date(), level: p.terminationStatus == 0 ? .info : .error,
                    message: "\(name) exited with code \(p.terminationStatus)"))
            }
        }

        do {
            try proc.run()
            service.process = proc
            service.isRunning = true
            service.pid = proc.processIdentifier
            service.logs.append(LogEntry(timestamp: Date(), level: .info, message: "\(name) started (PID \(proc.processIdentifier))"))

            if let idx = services.firstIndex(where: { $0.id == id }) {
                services[idx] = service
            } else {
                services.append(service)
            }
        } catch {
            service.logs.append(LogEntry(timestamp: Date(), level: .error, message: "Failed to start: \(error.localizedDescription)"))
            if let idx = services.firstIndex(where: { $0.id == id }) {
                services[idx] = service
            } else {
                services.append(service)
            }
        }
    }

    func stopService(id: String) {
        guard let idx = services.firstIndex(where: { $0.id == id }),
              let proc = services[idx].process, proc.isRunning else { return }
        proc.terminate()
        services[idx].logs.append(LogEntry(timestamp: Date(), level: .info, message: "Sent SIGTERM to \(services[idx].name)"))
    }

    func stopAll() {
        for service in services {
            if let proc = service.process, proc.isRunning {
                proc.terminate()
            }
        }
    }

    func isServiceRunning(_ id: String) -> Bool {
        services.first(where: { $0.id == id })?.isRunning ?? false
    }

    func findPython() -> String {
        let candidates = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        for c in candidates {
            if FileManager.default.fileExists(atPath: c) { return c }
        }
        return "python3"
    }
}
#endif

// MARK: - App State

@MainActor
final class AppState: ObservableObject {
    static weak var shared: AppState?

    @Published var components: [ComponentInfo] = []
    @Published var sessions: [PentestSession] = []
    @Published var selectedTab: SidebarItem = .chat
    @Published var backendRunning = false
    @Published var apiBaseURL = "http://localhost:8000"

    @Published var pythonBridge = PythonBridge()
    #if os(macOS)
    @Published var serviceManager: ServiceManager!
    #endif

    // MCP state
    @Published var mcpRunning = false
    @Published var mcpPort: Int = 8811
    @Published var enableMCP = true

    // Config mirrors
    @Published var enableDocker = false
    @Published var enableKubernetes = false
    @Published var enableVoice = true
    @Published var enableWebDashboard = true
    @Published var enableRealtimeDashboard = true
    @Published var openAIKey = ""

    // Auto-launch state
    @Published var autoLaunchCompleted = false
    @Published var launchStatus: String = "Initializing..."

    init() {
        AppState.shared = self
        #if os(macOS)
        serviceManager = ServiceManager(projectRoot: pythonBridge.projectRoot)
        #endif
        loadConfigFromINI()
        refreshComponents()
    }

    /// Auto-launches all configured services when app opens
    func autoLaunchAllServices() {
        guard !autoLaunchCompleted else { return }
        autoLaunchCompleted = true

        #if os(macOS)
        let python = serviceManager.findPython()
        let root = projectRoot()

        // Verify project root exists
        guard FileManager.default.fileExists(atPath: (root as NSString).appendingPathComponent("hackgpt_v2.py")) else {
            launchStatus = "Project files not found at \(root)"
            return
        }

        launchStatus = "Starting services..."

        // 1. Start API backend
        serviceManager.startService(
            id: "api-backend",
            name: "HackGPT API Server",
            command: python,
            args: [(root as NSString).appendingPathComponent("hackgpt_v2.py"), "--api"],
            port: 8000
        )
        backendRunning = true

        // 2. Start MCP Kali server (if enabled)
        if enableMCP {
            let mcpScript = (root as NSString).appendingPathComponent("hackgpt_v2.py")
            serviceManager.startService(
                id: "mcp-server",
                name: "MCP Kali Server",
                command: python,
                args: [mcpScript, "--mcp"],
                port: mcpPort
            )
            mcpRunning = true
        }

        // 3. Start Web Dashboard (if enabled)
        if enableWebDashboard {
            serviceManager.startService(
                id: "web-dashboard",
                name: "Web Dashboard",
                command: python,
                args: [(root as NSString).appendingPathComponent("hackgpt_v2.py"), "--web"],
                port: 8080
            )
        }

        // 4. Start Realtime Dashboard (if enabled)
        if enableRealtimeDashboard {
            serviceManager.startService(
                id: "realtime-dashboard",
                name: "Realtime Dashboard",
                command: python,
                args: [(root as NSString).appendingPathComponent("hackgpt_v2.py"), "--realtime"],
                port: 5000
            )
        }

        // 5. Start Ollama check
        Task {
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            launchStatus = "All services started"
            refreshServiceStatuses()
        }
        #else
        // iOS: connect to remote server
        launchStatus = "Ready (remote mode)"
        #endif
    }

    func shutdownAllServices() {
        #if os(macOS)
        serviceManager.stopAll()
        pythonBridge.stop()
        #endif
        backendRunning = false
        mcpRunning = false
        launchStatus = "Shutdown"
    }

    func refreshServiceStatuses() {
        #if os(macOS)
        mcpRunning = serviceManager.isServiceRunning("mcp-server")
        backendRunning = serviceManager.isServiceRunning("api-backend")
        refreshComponents()
        #endif
    }

    func loadConfigFromINI() {
        let root = projectRoot()
        let configPath = (root as NSString).appendingPathComponent("config.ini")
        guard FileManager.default.fileExists(atPath: configPath),
              let contents = try? String(contentsOfFile: configPath, encoding: .utf8) else { return }

        // Simple INI parser
        for line in contents.components(separatedBy: .newlines) {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            guard !trimmed.hasPrefix("#"), !trimmed.hasPrefix("["), trimmed.contains("=") else { continue }
            let parts = trimmed.split(separator: "=", maxSplits: 1).map { $0.trimmingCharacters(in: .whitespaces) }
            guard parts.count == 2 else { continue }
            let key = parts[0].lowercased()
            let val = parts[1].lowercased()
            switch key {
            case "enable_docker": enableDocker = (val == "true")
            case "enable_kubernetes": enableKubernetes = (val == "true")
            case "enable_voice": enableVoice = (val == "true")
            case "enable_web_dashboard": enableWebDashboard = (val == "true")
            case "enable_realtime_dashboard": enableRealtimeDashboard = (val == "true")
            case "enable_mcp": enableMCP = (val == "true")
            case "openai_api_key": openAIKey = parts[1] // preserve case
            case "port" where val.count <= 5:
                if let p = Int(val) { mcpPort = p }
            default: break
            }
        }
    }

    func saveConfigToINI() {
        let root = projectRoot()
        let configPath = (root as NSString).appendingPathComponent("config.ini")
        guard FileManager.default.fileExists(atPath: configPath),
              var contents = try? String(contentsOfFile: configPath, encoding: .utf8) else { return }

        func setVal(_ key: String, _ value: String) {
            // Replace "key = oldval" with "key = newval"
            let pattern = "(?m)^(\\s*\(key)\\s*=\\s*)(.*)$"
            if let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) {
                let range = NSRange(contents.startIndex..., in: contents)
                contents = regex.stringByReplacingMatches(in: contents, range: range,
                                                         withTemplate: "$1\(value)")
            }
        }

        setVal("enable_docker", enableDocker ? "true" : "false")
        setVal("enable_kubernetes", enableKubernetes ? "true" : "false")
        setVal("enable_voice", enableVoice ? "true" : "false")
        setVal("enable_web_dashboard", enableWebDashboard ? "true" : "false")
        setVal("enable_realtime_dashboard", enableRealtimeDashboard ? "true" : "false")
        setVal("enable_mcp", enableMCP ? "true" : "false")
        if !openAIKey.isEmpty {
            setVal("openai_api_key", openAIKey)
        }

        try? contents.write(toFile: configPath, atomically: true, encoding: .utf8)
    }

    func projectRoot() -> String {
        // Walk up from CWD until we find hackgpt_v2.py
        var dir = FileManager.default.currentDirectoryPath
        if dir.contains("HackGPTApp") {
            dir = dir.replacingOccurrences(of: "/HackGPTApp", with: "")
        }
        // Also try parent until hackgpt_v2.py found
        var check = dir
        for _ in 0..<5 {
            let candidate = (check as NSString).appendingPathComponent("hackgpt_v2.py")
            if FileManager.default.fileExists(atPath: candidate) { return check }
            check = (check as NSString).deletingLastPathComponent
        }
        return dir
    }

    func refreshComponents() {
        components = [
            ComponentInfo(name: "API Backend", status: backendRunning ? .running : .unavailable, detail: backendRunning ? "Port 8000" : "Stopped"),
            ComponentInfo(name: "MCP Server", status: mcpRunning ? .running : (enableMCP ? .unavailable : .disabled), detail: mcpRunning ? "Port \(mcpPort)" : (enableMCP ? "Starting..." : "Disabled")),
            ComponentInfo(name: "AI Engine", status: .unavailable, detail: "ML-Enhanced"),
            ComponentInfo(name: "Database", status: .unavailable, detail: "PostgreSQL"),
            ComponentInfo(name: "Authentication", status: .unavailable, detail: "RBAC+LDAP"),
            ComponentInfo(name: "Cache", status: .unavailable, detail: "Redis+Memory"),
            ComponentInfo(name: "Parallel Processing", status: .unavailable, detail: "\(ProcessInfo.processInfo.activeProcessorCount) cores"),
            ComponentInfo(name: "Docker", status: enableDocker ? .ready : .disabled, detail: enableDocker ? "Enabled" : "Disabled"),
            ComponentInfo(name: "Kubernetes", status: enableKubernetes ? .ready : .disabled, detail: enableKubernetes ? "Enabled" : "Disabled"),
            ComponentInfo(name: "Compliance", status: .unavailable, detail: "OWASP+NIST"),
            ComponentInfo(name: "Voice Interface", status: enableVoice ? .ready : .disabled, detail: enableVoice ? "Enabled" : "Disabled"),
            ComponentInfo(name: "Web Dashboard", status: enableWebDashboard ? .ready : .disabled, detail: enableWebDashboard ? "Enabled" : "Disabled"),
        ]
    }

    func startBackend(mode: BackendMode = .interactive) {
        #if os(macOS)
        let python = serviceManager.findPython()
        let root = projectRoot()
        var args: [String] = [(root as NSString).appendingPathComponent("hackgpt_v2.py")]
        switch mode {
        case .interactive: break
        case .api: args.append("--api")
        case .web: args.append("--web")
        case .realtime: args.append("--realtime")
        }
        serviceManager.startService(
            id: "api-backend",
            name: "HackGPT Backend (\(mode))",
            command: python,
            args: args,
            port: mode == .web ? 8080 : 8000
        )
        #else
        pythonBridge.runScript("hackgpt_v2.py", args: [])
        #endif
        backendRunning = true
    }

    func stopBackend() {
        #if os(macOS)
        serviceManager.stopService(id: "api-backend")
        #else
        pythonBridge.stop()
        #endif
        backendRunning = false
    }

    enum BackendMode {
        case interactive, api, web, realtime
    }
}

// MARK: - Sidebar

enum SidebarItem: String, CaseIterable, Identifiable {
    case chat = "AI Chat"
    case dashboard = "Dashboard"
    case mcp = "MCP Server"
    case assessment = "Assessment"
    case sessions = "Sessions"
    case cloud = "Cloud Services"
    case compliance = "Compliance"
    case reports = "Reports"
    case tools = "Tools"
    case logs = "Logs"
    case configuration = "Configuration"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .chat: return "bubble.left.and.bubble.right.fill"
        case .dashboard: return "gauge.with.dots.needle.bottom.50percent"
        case .mcp: return "server.rack"
        case .assessment: return "shield.checkered"
        case .sessions: return "list.bullet.clipboard"
        case .cloud: return "cloud"
        case .compliance: return "checkmark.seal"
        case .reports: return "doc.richtext"
        case .tools: return "wrench.and.screwdriver"
        case .logs: return "terminal"
        case .configuration: return "gearshape"
        }
    }
}

// MARK: - Content View

struct ContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        #if os(macOS)
        HStack(spacing: 0) {
            // Sidebar
            SidebarView()
                .frame(width: 200)

            Divider()

            // Detail
            detailView
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        #else
        TabView(selection: $appState.selectedTab) {
            ChatView()
                .tabItem { Label("Chat", systemImage: "bubble.left.and.bubble.right.fill") }
                .tag(SidebarItem.chat)
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "gauge.with.dots.needle.bottom.50percent") }
                .tag(SidebarItem.dashboard)
            MCPView()
                .tabItem { Label("MCP", systemImage: "server.rack") }
                .tag(SidebarItem.mcp)
            ToolsView()
                .tabItem { Label("Tools", systemImage: "wrench.and.screwdriver") }
                .tag(SidebarItem.tools)
            ConfigurationView()
                .tabItem { Label("Config", systemImage: "gearshape") }
                .tag(SidebarItem.configuration)
        }
        .tint(.red)
        #endif
    }

    @ViewBuilder
    var detailView: some View {
        switch appState.selectedTab {
        case .chat: ChatView()
        case .dashboard: DashboardView()
        case .mcp: MCPView()
        case .assessment: AssessmentView()
        case .sessions: SessionsView()
        case .cloud: CloudView()
        case .compliance: ComplianceView()
        case .reports: ReportsView()
        case .tools: ToolsView()
        case .logs: LogsView()
        case .configuration: ConfigurationView()
        }
    }
}

// MARK: - Sidebar View (manual List, no NavigationSplitView)

struct SidebarView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(spacing: 0) {
            // App title
            HStack(spacing: 8) {
                Image(systemName: "shield.checkered")
                    .foregroundColor(.red)
                    .font(.title3)
                Text("HackGPT")
                    .font(.headline)
                    .fontWeight(.bold)
            }
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity)

            Divider()

            // Navigation items
            ScrollView {
                VStack(spacing: 2) {
                    ForEach(SidebarItem.allCases) { item in
                        Button {
                            appState.selectedTab = item
                        } label: {
                            HStack(spacing: 10) {
                                Image(systemName: item.icon)
                                    .font(.body)
                                    .frame(width: 22)
                                Text(item.rawValue)
                                    .font(.callout)
                                Spacer()
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(
                                RoundedRectangle(cornerRadius: 6)
                                    .fill(appState.selectedTab == item ? Color.accentColor.opacity(0.2) : Color.clear)
                            )
                            .foregroundColor(appState.selectedTab == item ? .accentColor : .primary)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 8)
                .padding(.top, 8)
            }

            Spacer()

            Divider()

            // Status
            HStack(spacing: 6) {
                Circle()
                    .fill(appState.backendRunning ? Color.green : Color.red)
                    .frame(width: 8, height: 8)
                Text(appState.backendRunning ? "Backend Running" : "Backend Stopped")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
        }
        #if os(macOS)
        .background(Color(nsColor: .windowBackgroundColor))
        #else
        .background(Color(uiColor: .systemBackground))
        #endif
    }
}

// MARK: - Dashboard View

struct DashboardView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Banner
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("HackGPT Enterprise")
                            .font(.largeTitle.bold())
                        Text("AI-Powered Penetration Testing Platform v2.0")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        // Launch status
                        HStack(spacing: 6) {
                            Circle()
                                .fill(appState.backendRunning ? Color.green : Color.orange)
                                .frame(width: 8, height: 8)
                            Text(appState.launchStatus)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    Spacer()
                    backendControls
                }
                .padding(.bottom, 8)

                // System Status Grid
                Text("System Status")
                    .font(.title2.bold())

                LazyVGrid(columns: [
                    GridItem(.adaptive(minimum: 200, maximum: 280))
                ], spacing: 12) {
                    ForEach(appState.components) { comp in
                        ComponentCard(component: comp)
                    }
                }

                // Quick Actions
                Text("Quick Actions")
                    .font(.title2.bold())
                    .padding(.top, 8)

                LazyVGrid(columns: [
                    GridItem(.adaptive(minimum: 200, maximum: 280))
                ], spacing: 12) {
                    QuickActionCard(title: "Full Pentest", icon: "shield.checkered", color: .red) {
                        appState.selectedTab = .assessment
                    }
                    QuickActionCard(title: "MCP Server", icon: "server.rack", color: .orange) {
                        appState.selectedTab = .mcp
                    }
                    QuickActionCard(title: "Start API Server", icon: "play.circle.fill", color: .blue) {
                        appState.startBackend(mode: .api)
                    }
                    QuickActionCard(title: "Web Dashboard", icon: "globe", color: .purple) {
                        appState.startBackend(mode: .web)
                    }
                    QuickActionCard(title: "View Reports", icon: "doc.richtext", color: .green) {
                        appState.selectedTab = .reports
                    }
                }

                Spacer()
            }
            .padding(24)
        }
    }

    var backendControls: some View {
        HStack(spacing: 12) {
            if appState.backendRunning {
                Button(role: .destructive) {
                    appState.stopBackend()
                } label: {
                    Label("Stop Backend", systemImage: "stop.circle.fill")
                }
                .buttonStyle(.bordered)
                .tint(.red)
            } else {
                Button {
                    appState.startBackend(mode: .api)
                } label: {
                    Label("Start API", systemImage: "play.circle.fill")
                }
                .buttonStyle(.borderedProminent)
            }

            Button {
                appState.refreshComponents()
            } label: {
                Label("Refresh", systemImage: "arrow.clockwise")
            }
            .buttonStyle(.bordered)
        }
    }
}

struct ComponentCard: View {
    let component: ComponentInfo

    var body: some View {
        HStack {
            Image(systemName: component.status.icon)
                .foregroundStyle(component.status.color)
                .font(.title2)
            VStack(alignment: .leading, spacing: 2) {
                Text(component.name)
                    .font(.headline)
                Text(component.detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(component.status.rawValue)
                .font(.caption)
                .padding(.horizontal, 8)
                .padding(.vertical, 3)
                .background(component.status.color.opacity(0.15))
                .clipShape(Capsule())
        }
        .padding(12)
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

struct QuickActionCard: View {
    let title: String
    let icon: String
    let color: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .font(.title3)
                    .foregroundStyle(color)
                Text(title)
                    .font(.headline)
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundStyle(.secondary)
            }
            .padding(12)
            .background(.regularMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 10))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - MCP Server View

struct MCPView: View {
    @EnvironmentObject var appState: AppState
    @State private var mcpLogs: [LogEntry] = []
    @State private var selectedTool: String? = nil

    let mcpTools = [
        ("nmap_scan", "Network port scanning & service detection", "network"),
        ("nikto_scan", "Web server vulnerability scanning", "globe"),
        ("sqlmap_scan", "SQL injection detection & exploitation", "cylinder"),
        ("gobuster_scan", "Directory/file brute-force discovery", "folder"),
        ("hydra_attack", "Network login brute-force", "lock.open"),
        ("metasploit_scan", "Exploit framework integration", "ant"),
        ("whatweb_scan", "Web technology fingerprinting", "magnifyingglass"),
        ("whois_lookup", "Domain registration lookup", "doc.text"),
        ("hashcat_crack", "Password hash cracking", "key"),
        ("amass_enum", "Subdomain enumeration", "point.3.connected.trianglepath.dotted"),
        ("searchsploit", "Exploit database search", "magnifyingglass.circle"),
        ("full_recon", "Complete reconnaissance pipeline", "shield.checkered"),
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Header
                HStack {
                    Image(systemName: "server.rack")
                        .font(.title)
                        .foregroundColor(.red)
                    VStack(alignment: .leading) {
                        Text("MCP Kali Linux Server")
                            .font(.title2)
                            .fontWeight(.bold)
                        Text("Model Context Protocol — AI-powered security tools")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    Spacer()

                    // Status badge
                    HStack(spacing: 6) {
                        Circle()
                            .fill(appState.mcpRunning ? Color.green : Color.red)
                            .frame(width: 10, height: 10)
                        Text(appState.mcpRunning ? "Running on port \(appState.mcpPort)" : "Stopped")
                            .font(.callout)
                            .fontWeight(.medium)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(appState.mcpRunning ? Color.green.opacity(0.15) : Color.red.opacity(0.15))
                    )
                }
                .padding()

                Divider()

                // Controls
                HStack(spacing: 12) {
                    #if os(macOS)
                    Button {
                        if appState.mcpRunning {
                            appState.serviceManager.stopService(id: "mcp-server")
                            appState.mcpRunning = false
                        } else {
                            let python = appState.serviceManager.findPython()
                            let root = appState.projectRoot()
                            appState.serviceManager.startService(
                                id: "mcp-server",
                                name: "MCP Kali Server",
                                command: python,
                                args: [(root as NSString).appendingPathComponent("hackgpt_v2.py"), "--mcp"],
                                port: appState.mcpPort
                            )
                            appState.mcpRunning = true
                        }
                        appState.refreshComponents()
                    } label: {
                        Label(appState.mcpRunning ? "Stop MCP Server" : "Start MCP Server",
                              systemImage: appState.mcpRunning ? "stop.circle.fill" : "play.circle.fill")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(appState.mcpRunning ? .red : .green)
                    #endif

                    Button {
                        appState.refreshServiceStatuses()
                    } label: {
                        Label("Refresh Status", systemImage: "arrow.clockwise")
                    }
                    .buttonStyle(.bordered)

                    Spacer()

                    // Connection info
                    VStack(alignment: .trailing, spacing: 2) {
                        Text("Endpoint: http://localhost:\(appState.mcpPort)/mcp")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text("Transport: Streamable HTTP")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                .padding(.horizontal)

                // Tools grid
                VStack(alignment: .leading, spacing: 10) {
                    Text("Available Tools (\(mcpTools.count))")
                        .font(.headline)
                        .padding(.horizontal)

                    LazyVGrid(columns: [
                        GridItem(.flexible(), spacing: 12),
                        GridItem(.flexible(), spacing: 12),
                        GridItem(.flexible(), spacing: 12)
                    ], spacing: 12) {
                        ForEach(mcpTools, id: \.0) { tool in
                            mcpToolCard(name: tool.0, description: tool.1, icon: tool.2)
                        }
                    }
                    .padding(.horizontal)
                }

                // Claude Desktop config
                VStack(alignment: .leading, spacing: 8) {
                    Text("Claude Desktop Configuration")
                        .font(.headline)
                    Text("Add this to your Claude Desktop config to connect:")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    let configJSON = """
                    {
                      "mcpServers": {
                        "hackgpt-kali": {
                          "url": "http://localhost:\(appState.mcpPort)/mcp"
                        }
                      }
                    }
                    """

                    Text(configJSON)
                        .font(.system(.caption, design: .monospaced))
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.black.opacity(0.3))
                        .cornerRadius(8)
                        .textSelection(.enabled)
                }
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.primary.opacity(0.05))
                )
                .padding(.horizontal)

                // Service Logs
                #if os(macOS)
                VStack(alignment: .leading, spacing: 8) {
                    Text("MCP Server Logs")
                        .font(.headline)

                    let logs = appState.serviceManager.services.first(where: { $0.id == "mcp-server" })?.logs ?? []

                    if logs.isEmpty {
                        Text("No logs yet")
                            .foregroundColor(.secondary)
                            .padding()
                    } else {
                        ScrollView {
                            VStack(alignment: .leading, spacing: 2) {
                                ForEach(logs.suffix(50)) { entry in
                                    HStack(alignment: .top, spacing: 8) {
                                        Text(entry.timestamp, style: .time)
                                            .font(.system(.caption2, design: .monospaced))
                                            .foregroundColor(.secondary)
                                        Text(entry.message)
                                            .font(.system(.caption, design: .monospaced))
                                            .foregroundColor(entry.level.color)
                                            .textSelection(.enabled)
                                    }
                                }
                            }
                            .padding(8)
                        }
                        .frame(maxHeight: 200)
                        .background(Color.black.opacity(0.3))
                        .cornerRadius(8)
                    }
                }
                .padding(.horizontal)
                #endif

                Spacer().frame(height: 20)
            }
        }
    }

    func mcpToolCard(name: String, description: String, icon: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: icon)
                    .font(.title3)
                    .foregroundColor(.red)
                Spacer()
            }
            Text(name)
                .font(.callout)
                .fontWeight(.semibold)
            Text(description)
                .font(.caption)
                .foregroundColor(.secondary)
                .lineLimit(2)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.primary.opacity(0.05))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(Color.primary.opacity(0.1), lineWidth: 1)
        )
    }
}

// MARK: - Assessment View

struct AssessmentView: View {
    @EnvironmentObject var appState: AppState
    @State private var target = ""
    @State private var scope = ""
    @State private var assessmentType = "black-box"
    @State private var complianceFramework = "OWASP"
    @State private var parallelExecution = true
    @State private var aiEnhanced = true
    @State private var isRunning = false

    let assessmentTypes = ["black-box", "white-box", "gray-box"]
    let frameworks = ["OWASP", "NIST", "ISO27001", "SOC2", "PCI-DSS"]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Penetration Test Assessment")
                    .font(.largeTitle.bold())

                GroupBox("Target Information") {
                    VStack(alignment: .leading, spacing: 12) {
                        LabeledContent("Target (IP/domain/CIDR)") {
                            TextField("e.g. 192.168.1.0/24", text: $target)
                                .textFieldStyle(.roundedBorder)
                                .frame(maxWidth: 400)
                        }
                        LabeledContent("Scope") {
                            TextField("Describe scope", text: $scope)
                                .textFieldStyle(.roundedBorder)
                                .frame(maxWidth: 400)
                        }
                        LabeledContent("Assessment Type") {
                            Picker("", selection: $assessmentType) {
                                ForEach(assessmentTypes, id: \.self) { Text($0) }
                            }
                            .frame(width: 180)
                        }
                        LabeledContent("Compliance Framework") {
                            Picker("", selection: $complianceFramework) {
                                ForEach(frameworks, id: \.self) { Text($0) }
                            }
                            .frame(width: 180)
                        }

                        Divider()

                        Toggle("Parallel Execution", isOn: $parallelExecution)
                        Toggle("AI-Enhanced Analysis", isOn: $aiEnhanced)
                    }
                    .padding(8)
                }

                HStack {
                    Button {
                        startPentest()
                    } label: {
                        Label("Start Full Pentest", systemImage: "play.fill")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.red)
                    .disabled(target.isEmpty || isRunning)

                    if isRunning {
                        ProgressView()
                            .controlSize(.small)
                        Text("Running...")
                            .foregroundStyle(.secondary)
                    }
                }

                // Phases
                GroupBox("Pentest Phases") {
                    VStack(alignment: .leading, spacing: 8) {
                        PhaseRow(number: 1, name: "Intelligence Gathering & Reconnaissance", icon: "magnifyingglass")
                        PhaseRow(number: 2, name: "Advanced Scanning & Enumeration", icon: "antenna.radiowaves.left.and.right")
                        PhaseRow(number: 3, name: "Vulnerability Assessment", icon: "exclamationmark.shield")
                        PhaseRow(number: 4, name: "Exploitation & Post-Exploitation", icon: "bolt.shield")
                        PhaseRow(number: 5, name: "Enterprise Reporting & Analytics", icon: "chart.bar.doc.horizontal")
                        PhaseRow(number: 6, name: "Verification & Retesting", icon: "checkmark.shield")
                    }
                    .padding(8)
                }

                Spacer()
            }
            .padding(24)
        }
    }

    func startPentest() {
        isRunning = true
        let args = ["--target", target, "--scope", scope, "--auth-key", "native-app",
                     "--assessment-type", assessmentType, "--compliance", complianceFramework]
        if !args.isEmpty {
            appState.pythonBridge.runScript("hackgpt_v2.py", args: args)
        }
        // Add session locally
        let session = PentestSession(
            id: UUID().uuidString,
            target: target,
            scope: scope,
            assessmentType: assessmentType,
            complianceFramework: complianceFramework,
            status: "running",
            startedAt: Date(),
            findings: 0,
            riskScore: 0
        )
        appState.sessions.insert(session, at: 0)
    }
}

struct PhaseRow: View {
    let number: Int
    let name: String
    let icon: String

    var body: some View {
        HStack {
            Image(systemName: icon)
                .frame(width: 24)
                .foregroundStyle(.blue)
            Text("Phase \(number):")
                .fontWeight(.semibold)
            Text(name)
            Spacer()
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Sessions View

struct SessionsView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Pentest Sessions")
                .font(.largeTitle.bold())
                .padding(.horizontal, 24)
                .padding(.top, 24)

            if appState.sessions.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "tray")
                        .font(.system(size: 48))
                        .foregroundStyle(.secondary)
                    Text("No sessions yet")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                    Text("Start a pentest from the Assessment tab")
                        .font(.subheadline)
                        .foregroundStyle(.tertiary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Table(appState.sessions) {
                    TableColumn("Target") { s in Text(s.target) }
                    TableColumn("Type") { s in Text(s.assessmentType) }
                    TableColumn("Framework") { s in Text(s.complianceFramework) }
                    TableColumn("Status") { s in
                        HStack {
                            Circle()
                                .fill(s.status == "running" ? Color.green :
                                      s.status == "completed" ? Color.blue : Color.orange)
                                .frame(width: 8, height: 8)
                            Text(s.status)
                        }
                    }
                    TableColumn("Risk") { s in Text(String(format: "%.1f", s.riskScore)) }
                    TableColumn("Findings") { s in Text("\(s.findings)") }
                    TableColumn("Started") { s in Text(s.startedAt, style: .relative) }
                }
            }
        }
    }
}

// MARK: - Cloud View

struct CloudView: View {
    @EnvironmentObject var appState: AppState
    @State private var dockerAvailable = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Cloud & Container Management")
                    .font(.largeTitle.bold())

                HStack(spacing: 16) {
                    StatusBadge(label: "Docker", enabled: appState.enableDocker)
                    StatusBadge(label: "Kubernetes", enabled: appState.enableKubernetes)
                }

                if !appState.enableDocker && !appState.enableKubernetes {
                    GroupBox {
                        VStack(spacing: 8) {
                            Image(systemName: "exclamationmark.triangle")
                                .font(.title)
                                .foregroundStyle(.orange)
                            Text("Docker and Kubernetes are disabled")
                                .font(.headline)
                            Text("Enable them in Configuration to use cloud features.")
                                .foregroundStyle(.secondary)
                            Button("Go to Configuration") {
                                appState.selectedTab = .configuration
                            }
                            .buttonStyle(.borderedProminent)
                        }
                        .padding()
                        .frame(maxWidth: .infinity)
                    }
                }

                if appState.enableDocker {
                    GroupBox("Docker") {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Label("Docker Engine", systemImage: "shippingbox")
                                Spacer()
                                Text(dockerAvailable ? "Connected" : "Not Connected")
                                    .foregroundStyle(dockerAvailable ? .green : .red)
                            }
                            Button("Deploy HackGPT Stack") {
                                appState.pythonBridge.runScript("hackgpt_v2.py", args: ["--api"])
                            }
                            .buttonStyle(.bordered)
                        }
                        .padding(8)
                    }
                }

                if appState.enableKubernetes {
                    GroupBox("Kubernetes") {
                        VStack(alignment: .leading, spacing: 12) {
                            Label("Cluster Management", systemImage: "server.rack")
                            Text("Manage Kubernetes deployments, pods, and services")
                                .foregroundStyle(.secondary)
                        }
                        .padding(8)
                    }
                }

                Spacer()
            }
            .padding(24)
        }
        .onAppear { checkDocker() }
    }

    func checkDocker() {
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        proc.arguments = ["docker", "info"]
        proc.standardOutput = FileHandle.nullDevice
        proc.standardError = FileHandle.nullDevice
        do {
            try proc.run()
            proc.waitUntilExit()
            dockerAvailable = proc.terminationStatus == 0
        } catch {
            dockerAvailable = false
        }
    }
}

struct StatusBadge: View {
    let label: String
    let enabled: Bool

    var body: some View {
        HStack {
            Image(systemName: enabled ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundStyle(enabled ? .green : .red)
            Text(label)
                .fontWeight(.medium)
            Text(enabled ? "Enabled" : "Disabled")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(.regularMaterial)
        .clipShape(Capsule())
    }
}

// MARK: - Compliance View

struct ComplianceView: View {
    let frameworks = [
        ("OWASP", "Open Web Application Security Project", "globe.americas"),
        ("NIST", "National Institute of Standards and Technology", "building.columns"),
        ("ISO 27001", "Information Security Management", "lock.shield"),
        ("SOC 2", "Service Organization Control Type 2", "checkmark.seal"),
        ("PCI-DSS", "Payment Card Industry Data Security Standard", "creditcard"),
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Compliance Management")
                    .font(.largeTitle.bold())

                ForEach(frameworks, id: \.0) { fw in
                    GroupBox {
                        HStack {
                            Image(systemName: fw.2)
                                .font(.title2)
                                .foregroundStyle(.blue)
                                .frame(width: 40)
                            VStack(alignment: .leading) {
                                Text(fw.0).font(.headline)
                                Text(fw.1).font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Button("Run Audit") {}
                                .buttonStyle(.bordered)
                        }
                    }
                }

                Spacer()
            }
            .padding(24)
        }
    }
}

// MARK: - Reports View

struct ReportsView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Reports & Analytics")
                    .font(.largeTitle.bold())

                GroupBox("Report Generation") {
                    VStack(alignment: .leading, spacing: 12) {
                        Button {
                        } label: {
                            Label("Generate Executive Summary", systemImage: "doc.text")
                        }
                        .buttonStyle(.bordered)

                        Button {
                        } label: {
                            Label("Export Full Report (PDF)", systemImage: "arrow.down.doc")
                        }
                        .buttonStyle(.bordered)

                        Button {
                        } label: {
                            Label("Export JSON Data", systemImage: "curlybraces")
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding(8)
                }

                Spacer()
            }
            .padding(24)
        }
    }
}

// MARK: - Tools View

struct ToolsView: View {
    let tools = [
        ("nmap", "Network scanner"),
        ("nikto", "Web server scanner"),
        ("sqlmap", "SQL injection tool"),
        ("gobuster", "Directory brute-forcer"),
        ("hydra", "Password cracker"),
        ("metasploit", "Exploitation framework"),
        ("burpsuite", "Web proxy"),
        ("wireshark", "Packet analyzer"),
    ]

    @State private var statuses: [String: Bool] = [:]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Tool Management")
                    .font(.largeTitle.bold())

                HStack {
                    Button {
                        checkAllTools()
                    } label: {
                        Label("Check All Tools", systemImage: "arrow.clockwise")
                    }
                    .buttonStyle(.borderedProminent)
                }

                LazyVGrid(columns: [GridItem(.adaptive(minimum: 250))], spacing: 10) {
                    ForEach(tools, id: \.0) { tool in
                        HStack {
                            Image(systemName: statuses[tool.0] == true ? "checkmark.circle.fill" : "xmark.circle")
                                .foregroundStyle(statuses[tool.0] == true ? .green : .red)
                            VStack(alignment: .leading) {
                                Text(tool.0).font(.headline)
                                Text(tool.1).font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                        }
                        .padding(10)
                        .background(.regularMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                }

                Spacer()
            }
            .padding(24)
        }
        .onAppear { checkAllTools() }
    }

    func checkAllTools() {
        for tool in tools {
            let proc = Process()
            proc.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            proc.arguments = ["which", tool.0]
            proc.standardOutput = FileHandle.nullDevice
            proc.standardError = FileHandle.nullDevice
            do {
                try proc.run()
                proc.waitUntilExit()
                statuses[tool.0] = proc.terminationStatus == 0
            } catch {
                statuses[tool.0] = false
            }
        }
    }
}

// MARK: - Logs View

struct LogsView: View {
    @EnvironmentObject var appState: AppState
    @State private var filterText = ""
    @State private var autoScroll = true

    var filteredLogs: [LogEntry] {
        if filterText.isEmpty { return appState.pythonBridge.output }
        return appState.pythonBridge.output.filter { $0.message.localizedCaseInsensitiveContains(filterText) }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Logs")
                    .font(.largeTitle.bold())
                Spacer()
                TextField("Filter...", text: $filterText)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 200)
                Toggle("Auto-scroll", isOn: $autoScroll)
                Button {
                    appState.pythonBridge.output.removeAll()
                } label: {
                    Label("Clear", systemImage: "trash")
                }
                .buttonStyle(.bordered)
            }
            .padding(16)

            Divider()

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 1) {
                        ForEach(filteredLogs) { entry in
                            HStack(alignment: .top, spacing: 8) {
                                Text(entry.timestamp, format: .dateTime.hour().minute().second())
                                    .font(.system(.caption, design: .monospaced))
                                    .foregroundStyle(.secondary)
                                    .frame(width: 80, alignment: .leading)
                                Text(entry.level.rawValue)
                                    .font(.system(.caption, design: .monospaced))
                                    .fontWeight(.bold)
                                    .foregroundStyle(entry.level.color)
                                    .frame(width: 40, alignment: .leading)
                                Text(entry.message)
                                    .font(.system(.caption, design: .monospaced))
                                    .textSelection(.enabled)
                            }
                            .padding(.horizontal, 16)
                            .padding(.vertical, 2)
                            .id(entry.id)
                        }
                    }
                }
                .onChange(of: appState.pythonBridge.output.count) { _ in
                    if autoScroll, let last = filteredLogs.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
        }
    }
}

// MARK: - Configuration View

struct ConfigurationView: View {
    @EnvironmentObject var appState: AppState
    @State private var showSaved = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Configuration")
                    .font(.largeTitle.bold())

                GroupBox("Feature Flags") {
                    VStack(alignment: .leading, spacing: 12) {
                        Toggle("Enable MCP Server (Kali Tools)", isOn: $appState.enableMCP)
                        Toggle("Enable Docker", isOn: $appState.enableDocker)
                        Toggle("Enable Kubernetes", isOn: $appState.enableKubernetes)
                        Toggle("Enable Voice Interface", isOn: $appState.enableVoice)
                        Toggle("Enable Web Dashboard", isOn: $appState.enableWebDashboard)
                        Toggle("Enable Realtime Dashboard", isOn: $appState.enableRealtimeDashboard)
                    }
                    .padding(8)
                }

                GroupBox("MCP Configuration") {
                    VStack(alignment: .leading, spacing: 12) {
                        LabeledContent("MCP Port") {
                            TextField("8811", value: $appState.mcpPort, format: .number)
                                .textFieldStyle(.roundedBorder)
                                .frame(maxWidth: 100)
                        }
                        HStack(spacing: 6) {
                            Circle()
                                .fill(appState.mcpRunning ? Color.green : Color.red)
                                .frame(width: 8, height: 8)
                            Text(appState.mcpRunning ? "MCP Server running" : "MCP Server stopped")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(8)
                }

                GroupBox("AI Configuration") {
                    VStack(alignment: .leading, spacing: 12) {
                        LabeledContent("OpenAI API Key") {
                            SecureField("sk-...", text: $appState.openAIKey)
                                .textFieldStyle(.roundedBorder)
                                .frame(maxWidth: 400)
                        }
                    }
                    .padding(8)
                }

                GroupBox("System Info") {
                    VStack(alignment: .leading, spacing: 8) {
                        InfoRow(label: "Platform", value: "macOS (Apple Silicon M4)")
                        InfoRow(label: "Swift", value: "6.2.3")
                        InfoRow(label: "Python", value: "3.14.3")
                        InfoRow(label: "Architecture", value: "arm64")
                        InfoRow(label: "Cores", value: "\(ProcessInfo.processInfo.activeProcessorCount)")
                        InfoRow(label: "Project Root", value: appState.projectRoot())
                    }
                    .padding(8)
                }

                HStack {
                    Button {
                        appState.saveConfigToINI()
                        appState.refreshComponents()
                        showSaved = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { showSaved = false }
                    } label: {
                        Label("Save Configuration", systemImage: "externaldrive")
                    }
                    .buttonStyle(.borderedProminent)

                    if showSaved {
                        Text("Saved!")
                            .foregroundStyle(.green)
                            .transition(.opacity)
                    }
                }

                Spacer()
            }
            .padding(24)
        }
    }
}

struct InfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .foregroundStyle(.secondary)
                .frame(width: 120, alignment: .leading)
            Text(value)
                .textSelection(.enabled)
        }
    }
}

// MARK: - Settings View

struct SettingsView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        TabView {
            ConfigurationView()
                .tabItem { Label("General", systemImage: "gearshape") }
        }
        .frame(width: 600, height: 500)
    }
}

// MARK: - Chat AI Bot (ChatGPT-style)

struct ChatMessage: Identifiable, Equatable {
    let id: UUID
    let role: Role
    var content: String
    let timestamp: Date
    var isStreaming: Bool
    var toolOutput: String?
    var toolName: String?

    enum Role: String { case user, assistant, system, tool }

    init(role: Role, content: String, isStreaming: Bool = false, toolOutput: String? = nil, toolName: String? = nil) {
        self.id = UUID()
        self.role = role
        self.content = content
        self.timestamp = Date()
        self.isStreaming = isStreaming
        self.toolOutput = toolOutput
        self.toolName = toolName
    }

    static func == (lhs: ChatMessage, rhs: ChatMessage) -> Bool { lhs.id == rhs.id }
}

// Conversation thread for sidebar
struct ChatThread: Identifiable, Codable {
    let id: UUID
    var title: String
    var lastUpdated: Date
    var preview: String

    init(title: String, preview: String = "") {
        self.id = UUID()
        self.title = title
        self.lastUpdated = Date()
        self.preview = preview
    }
}

// MARK: - Chat View Model

@MainActor
final class ChatViewModel: ObservableObject {
    // Messages & threads
    @Published var messages: [ChatMessage] = []
    @Published var threads: [ChatThread] = []
    @Published var activeThreadId: UUID?
    private var threadMessages: [UUID: [ChatMessage]] = [:]

    // Input
    @Published var inputText = ""
    @Published var isLoading = false
    @Published var statusText = ""

    // Model selection
    @Published var selectedModel = "auto"
    @Published var availableModels: [String] = ["auto"]
    @Published var ollamaConnected = false

    // Config
    private var ollamaURL = "http://localhost:11434"
    private var openAIKey = ""
    private var openAIModel = "gpt-4"
    private var localModel = "llama3.2:3b"
    private var projectRoot = ""
    private var currentTask: Task<Void, Never>?
    private weak var appState: AppState?

    // NLP intent patterns — natural language ➜ platform actions
    private let intentPatterns: [(pattern: String, action: String)] = [
        // Scanning & recon
        ("(scan|pentest|penetration test|hack|attack|test)\\s+(the\\s+)?(target|host|server|network|ip|site|website|domain|url|machine|system)\\s*:?\\s*(.+)", "scan"),
        ("(scan|pentest|test|hack|probe|attack)\\s+(.+\\..+)", "scan"),
        ("(scan|pentest|test|hack|probe|attack)\\s+(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\S*)", "scan"),
        ("run\\s+(a\\s+)?(full\\s+)?(pentest|scan|assessment|security test)\\s+(on|against|for)\\s+(.+)", "scan"),
        ("(recon|reconnaissance|enumerate|discover|footprint|osint)\\s+(on\\s+|for\\s+|against\\s+)?(.+)", "recon"),
        // Nmap
        ("(nmap|port\\s*scan|port\\s*check|open\\s+ports?)\\s+(on\\s+|for\\s+|against\\s+)?(.+)", "nmap"),
        ("(which|what|find|show|list|check)\\s+(ports?|services?)\\s+(are\\s+)?(open|running|listening)\\s+(on|for|at)\\s+(.+)", "nmap"),
        // Network lookups
        ("(whois|who\\s+is|who\\s+owns?)\\s+(.+)", "whois"),
        ("(dns|dig|nslookup|resolve|lookup)\\s+(for\\s+|of\\s+)?(.+)", "dig"),
        ("(curl|fetch|http|get|request|headers?)\\s+(from\\s+|to\\s+|for\\s+)?(.+)", "curl"),
        // Tools
        ("(show|list|check|what|which)\\s+(my\\s+)?(installed\\s+)?(tools?|security\\s+tools?|hacking\\s+tools?)", "tools"),
        ("(are|is|do i have)\\s+(my\\s+)?(tools?|nmap|sqlmap|metasploit|hydra|burp|nikto)\\s+(installed|available|ready)", "tools"),
        // Docker
        ("(show|list|check|what|docker|containers?).*?(docker|containers?|images?|running)", "docker"),
        ("(what|which|show|list).*?(containers?|docker).*?(running|active|up)", "docker"),
        // Status
        ("(system|status|health|info|system info|what.s running|components?)", "status"),
        // Config
        ("(show|display|print|read|open|cat)\\s+(the\\s+)?(config|configuration|settings|config\\.ini)", "config"),
        // Compliance
        ("(compliance|audit|owasp|nist|pci|iso\\s*27001|soc\\s*2|gdpr|hipaa)\\s*(audit|check|scan|test|report|assessment)?", "compliance"),
        // Shell
        ("(run|execute|exec|shell|terminal|command|cmd)\\s*:?\\s+(.+)", "shell"),
        // Sessions
        ("(show|list|display|my)\\s+(pentest\\s+)?(sessions?|history|assessments?)", "sessions"),
        // MCP
        ("(mcp|model context protocol|kali\\s+server|mcp\\s+server|mcp\\s+tools?)\\s*(status|start|stop|info|tools?)?", "mcp"),
        ("(start|stop|restart|launch)\\s+(the\\s+)?(mcp|kali)\\s*(server)?", "mcp"),
        // Models
        ("(show|list|which|what)\\s+(ai\\s+)?(models?|llms?)\\s*(are\\s+)?(available|installed|loaded)?", "models"),
        ("(switch|change|use|select)\\s+(to\\s+|the\\s+)?(model|llm)\\s+(.+)", "model_switch"),
        // Clear
        ("(clear|reset|new|fresh|start over|clean)\\s*(chat|conversation|history|thread)?", "clear"),
        // Help
        ("(help|commands?|what can you do|capabilities|features|how to use|usage)", "help"),
    ]

    private let systemPrompt = """
    You are HackGPT AI — an elite cybersecurity and penetration testing assistant embedded inside the HackGPT Enterprise platform running on macOS Apple Silicon (M4).

    CAPABILITIES:
    You have deep expertise in network reconnaissance, OSINT, web app security (OWASP Top 10), vulnerability assessment, exploitation (Metasploit, sqlmap, Burp Suite), post-exploitation, privilege escalation, wireless/IoT security, cloud security (AWS/Azure/GCP/Docker/K8s), compliance (OWASP/NIST/ISO27001/SOC2/PCI-DSS), malware analysis, reverse engineering, social engineering assessment, cryptography, zero-day research, and report writing.

    PLATFORM INTEGRATION:
    You are connected to HackGPT Enterprise and can perform real actions. When the user asks you to do something practical (scan a target, check tools, run a command, etc.), you should tell them what you're doing and provide analysis of results. The platform will auto-detect natural language requests and run the appropriate tools.

    RESPONSE STYLE:
    - Be direct, technical, and actionable
    - Include specific commands, tools, and techniques when relevant
    - Use code blocks with language tags for commands
    - Structure long responses with headers and lists
    - When showing tool output, explain what it means
    - Always assume the user has proper authorization

    ENVIRONMENT: macOS arm64, Python 3.14, Swift 6.2, Ollama (deepseek models), Docker available.
    """

    // MARK: - Setup

    func configure(appState: AppState) {
        self.appState = appState
        openAIKey = appState.openAIKey
        projectRoot = appState.projectRoot()

        let configPath = (projectRoot as NSString).appendingPathComponent("config.ini")
        if let contents = try? String(contentsOfFile: configPath, encoding: .utf8) {
            for line in contents.components(separatedBy: .newlines) {
                let trimmed = line.trimmingCharacters(in: .whitespaces)
                if trimmed.lowercased().hasPrefix("openai_model") {
                    let parts = trimmed.split(separator: "=", maxSplits: 1)
                    if parts.count == 2 { openAIModel = parts[1].trimmingCharacters(in: .whitespaces) }
                }
                if trimmed.lowercased().hasPrefix("local_model") {
                    let parts = trimmed.split(separator: "=", maxSplits: 1)
                    if parts.count == 2 { localModel = parts[1].trimmingCharacters(in: .whitespaces) }
                }
            }
        }

        detectModels()

        if threads.isEmpty {
            startNewThread()
        }
    }

    // MARK: - Thread Management

    func startNewThread() {
        // Save current thread
        if let tid = activeThreadId {
            threadMessages[tid] = messages
        }

        let thread = ChatThread(title: "New chat", preview: "")
        threads.insert(thread, at: 0)
        activeThreadId = thread.id
        messages = []

        // Welcome message
        messages.append(ChatMessage(role: .assistant, content: """
        What can I help you with?

        You can ask me anything in natural language — or use commands:

        **Examples:**
        • "Scan 192.168.1.0/24 for open ports"
        • "Check what security tools are installed"
        • "Run nmap on example.com"
        • "Show me the docker containers"
        • "Do a compliance audit for OWASP"
        • "Whois google.com"

        Type naturally — I'll figure out what to do.
        """))
    }

    func switchToThread(_ id: UUID) {
        guard id != activeThreadId else { return }
        // Save current
        if let tid = activeThreadId {
            threadMessages[tid] = messages
        }
        activeThreadId = id
        messages = threadMessages[id] ?? []
    }

    func deleteThread(_ id: UUID) {
        threads.removeAll { $0.id == id }
        threadMessages.removeValue(forKey: id)
        if activeThreadId == id {
            if let first = threads.first {
                switchToThread(first.id)
            } else {
                startNewThread()
            }
        }
    }

    func updateThreadTitle() {
        guard let tid = activeThreadId,
              let idx = threads.firstIndex(where: { $0.id == tid }) else { return }
        // Use first user message as title
        if let firstUser = messages.first(where: { $0.role == .user }) {
            let title = String(firstUser.content.prefix(50))
            threads[idx].title = title
            threads[idx].preview = String(firstUser.content.prefix(80))
        }
        threads[idx].lastUpdated = Date()
    }

    // MARK: - Model Detection

    func detectModels() {
        availableModels = ["auto"]
        Task {
            if let models = await fetchOllamaModels() {
                ollamaConnected = true
                availableModels.append(contentsOf: models.map { "ollama:\($0)" })
            } else {
                ollamaConnected = false
            }
            if !openAIKey.isEmpty {
                availableModels.append("openai:\(openAIModel)")
            }
        }
    }

    func fetchOllamaModels() async -> [String]? {
        guard let url = URL(string: "\(ollamaURL)/api/tags") else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let models = json["models"] as? [[String: Any]] {
                return models.compactMap { $0["name"] as? String }
            }
        } catch { }
        return nil
    }

    // MARK: - Send Message

    func send() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        messages.append(ChatMessage(role: .user, content: text))
        inputText = ""

        // Update thread
        updateThreadTitle()

        // 1. Slash commands — explicit
        if text.hasPrefix("/") {
            handleSlashCommand(text)
            return
        }

        // 2. Natural language intent detection — execute platform actions
        if let action = detectIntent(text) {
            executeIntent(action, text: text)
            return
        }

        // 3. General AI conversation
        requestAIResponse(prompt: text)
    }

    func stopGenerating() {
        currentTask?.cancel()
        isLoading = false
        statusText = ""
        if let last = messages.last, last.isStreaming {
            messages[messages.count - 1].isStreaming = false
            if messages[messages.count - 1].content.isEmpty {
                messages[messages.count - 1].content = "*Stopped.*"
            }
        }
    }

    // MARK: - Natural Language Intent Detection

    struct DetectedIntent {
        let action: String
        let target: String
        let fullMatch: String
    }

    func detectIntent(_ text: String) -> DetectedIntent? {
        let lower = text.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)

        for (pattern, action) in intentPatterns {
            guard let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) else { continue }
            let range = NSRange(lower.startIndex..., in: lower)
            if let match = regex.firstMatch(in: lower, range: range) {
                // Extract the last capture group as target
                var target = ""
                for g in stride(from: match.numberOfRanges - 1, through: 1, by: -1) {
                    let r = match.range(at: g)
                    if r.location != NSNotFound, let swiftRange = Range(r, in: lower) {
                        let captured = String(lower[swiftRange]).trimmingCharacters(in: .whitespacesAndNewlines)
                        if !captured.isEmpty && captured.count > 1 {
                            target = captured
                            break
                        }
                    }
                }
                // Use original text for target to preserve case
                if !target.isEmpty {
                    // Find target in original text
                    if let tRange = text.range(of: target, options: .caseInsensitive) {
                        target = String(text[tRange])
                    }
                }
                return DetectedIntent(action: action, target: target, fullMatch: String(lower))
            }
        }
        return nil
    }

    func executeIntent(_ intent: DetectedIntent, text: String) {
        switch intent.action {
        case "scan":
            let target = cleanTarget(intent.target)
            if target.isEmpty {
                requestAIResponse(prompt: text)
            } else {
                messages.append(ChatMessage(role: .assistant, content: "🔍 **Launching full penetration test** on `\(target)` ..."))
                isLoading = true
                statusText = "Scanning \(target)..."
                Task {
                    let output = await runShell("cd '\(shellEscape(projectRoot))' && python3 hackgpt_v2.py --target '\(shellEscape(target))' --scope 'AI Chat scan' --auth-key chat-session 2>&1 | head -100")
                    isLoading = false
                    statusText = ""
                    let trimmed = output.count > 4000 ? String(output.prefix(4000)) + "\n... (truncated)" : output
                    messages.append(ChatMessage(role: .tool, content: trimmed, toolName: "pentest"))
                    // Ask AI to analyze
                    requestAIResponse(prompt: "Analyze this pentest scan output and provide a security assessment summary:\n\n\(trimmed)")
                }
            }

        case "recon":
            let target = cleanTarget(intent.target)
            if target.isEmpty { requestAIResponse(prompt: text); return }
            messages.append(ChatMessage(role: .assistant, content: "🔎 **Reconnaissance** on `\(target)` ..."))
            isLoading = true; statusText = "Recon \(target)..."
            Task {
                let output = await runShell("nmap -sn -PE '\(shellEscape(target))' 2>&1")
                isLoading = false; statusText = ""
                messages.append(ChatMessage(role: .tool, content: output.isEmpty ? "No output" : output, toolName: "nmap"))
                requestAIResponse(prompt: "Analyze this reconnaissance result:\n\n\(output)")
            }

        case "nmap":
            let target = cleanTarget(intent.target)
            if target.isEmpty { requestAIResponse(prompt: text); return }
            messages.append(ChatMessage(role: .assistant, content: "🔍 **Port scanning** `\(target)` ..."))
            isLoading = true; statusText = "Scanning ports on \(target)..."
            Task {
                let output = await runShell("nmap -sV '\(shellEscape(target))' 2>&1")
                isLoading = false; statusText = ""
                messages.append(ChatMessage(role: .tool, content: output.isEmpty ? "No output" : output, toolName: "nmap"))
                requestAIResponse(prompt: "Analyze this nmap scan and identify potential vulnerabilities:\n\n\(output)")
            }

        case "whois":
            let target = cleanTarget(intent.target)
            if target.isEmpty { requestAIResponse(prompt: text); return }
            messages.append(ChatMessage(role: .assistant, content: "🌐 **WHOIS lookup** for `\(target)` ..."))
            isLoading = true; statusText = "WHOIS..."
            Task {
                let output = await runShell("whois '\(shellEscape(target))' 2>&1 | head -60")
                isLoading = false; statusText = ""
                messages.append(ChatMessage(role: .tool, content: output.isEmpty ? "No output" : output, toolName: "whois"))
            }

        case "dig":
            let target = cleanTarget(intent.target)
            if target.isEmpty { requestAIResponse(prompt: text); return }
            messages.append(ChatMessage(role: .assistant, content: "📡 **DNS lookup** for `\(target)` ..."))
            isLoading = true; statusText = "DNS..."
            Task {
                let output = await runShell("dig '\(shellEscape(target))' 2>&1")
                isLoading = false; statusText = ""
                messages.append(ChatMessage(role: .tool, content: output.isEmpty ? "No output" : output, toolName: "dig"))
            }

        case "curl":
            let target = cleanTarget(intent.target)
            if target.isEmpty { requestAIResponse(prompt: text); return }
            let url = target.hasPrefix("http") ? target : "https://\(target)"
            messages.append(ChatMessage(role: .assistant, content: "📥 **HTTP headers** for `\(url)` ..."))
            isLoading = true; statusText = "Fetching..."
            Task {
                let output = await runShell("curl -sI '\(shellEscape(url))' 2>&1")
                isLoading = false; statusText = ""
                messages.append(ChatMessage(role: .tool, content: output.isEmpty ? "No output" : output, toolName: "curl"))
                requestAIResponse(prompt: "Analyze these HTTP headers for security issues:\n\n\(output)")
            }

        case "tools":
            messages.append(ChatMessage(role: .assistant, content: "🔧 **Checking installed security tools** ..."))
            isLoading = true; statusText = "Checking tools..."
            Task { await checkTools(); isLoading = false; statusText = "" }

        case "docker":
            messages.append(ChatMessage(role: .assistant, content: "🐳 **Checking Docker** ..."))
            isLoading = true; statusText = "Docker..."
            Task { await checkDocker(); isLoading = false; statusText = "" }

        case "status":
            let s = buildStatusReport()
            messages.append(ChatMessage(role: .assistant, content: s))

        case "config":
            let c = buildConfigReport()
            messages.append(ChatMessage(role: .assistant, content: c))

        case "compliance":
            let fw = extractFramework(intent.target, fallback: "OWASP")
            messages.append(ChatMessage(role: .assistant, content: "📋 **Compliance audit: \(fw)** ..."))
            isLoading = true; statusText = "Auditing..."
            Task {
                _ = await runShell("cd '\(shellEscape(projectRoot))' && python3 -c \"from security.compliance import *; print('Compliance module loaded')\" 2>&1")
                isLoading = false; statusText = ""
                requestAIResponse(prompt: "Run a comprehensive \(fw) compliance audit checklist. List each control, its status, and remediation steps. Include these categories: authentication, authorization, input validation, cryptography, error handling, logging, data protection, and communication security.")
            }

        case "sessions":
            let count = appState?.sessions.count ?? 0
            messages.append(ChatMessage(role: .assistant, content: "📋 **Pentest Sessions:** \(count) total\n\nSwitch to the **Sessions** tab in the sidebar to view details, or say \"scan <target>\" to start a new one."))

        case "mcp":
            let running = appState?.mcpRunning ?? false
            let port = appState?.mcpPort ?? 8811
            var info = "🖧 **MCP Kali Linux Server**\n\n"
            info += "| Status | \(running ? "✅ Running" : "❌ Stopped") |\n"
            info += "|--------|--------|\n"
            info += "| Port | \(port) |\n"
            info += "| Endpoint | http://localhost:\(port)/mcp |\n"
            info += "| Transport | Streamable HTTP |\n\n"
            info += "**Available Tools:** nmap, nikto, sqlmap, gobuster, hydra, metasploit, whatweb, whois, hashcat, amass, searchsploit, full_recon\n\n"
            info += "Switch to the **MCP Server** tab for controls, or say \"start mcp\" / \"stop mcp\"."
            if intent.target.lowercased().contains("start") && !running {
                appState?.selectedTab = .mcp
                info += "\n\n➡️ Opening MCP panel..."
            }
            messages.append(ChatMessage(role: .assistant, content: info))

        case "models":
            let modelList = availableModels.map { m in
                let current = (m == selectedModel) ? " ← active" : ""
                return "• `\(m)`\(current)"
            }.joined(separator: "\n")
            messages.append(ChatMessage(role: .assistant, content: "**Available AI Models:**\n\n\(modelList)\n\nSay \"switch to model <name>\" or use `/model <name>`."))

        case "model_switch":
            let modelName = intent.target.trimmingCharacters(in: .whitespacesAndNewlines)
            if !modelName.isEmpty {
                selectedModel = modelName
                messages.append(ChatMessage(role: .assistant, content: "Switched to model: **\(modelName)**"))
            }

        case "clear":
            startNewThread()

        case "help":
            showHelp()

        case "shell":
            let cmd = intent.target
            if cmd.isEmpty { requestAIResponse(prompt: text); return }
            messages.append(ChatMessage(role: .assistant, content: "⚡ **Executing:** `\(cmd)`"))
            isLoading = true; statusText = "Running..."
            Task {
                let output = await runShell(cmd)
                isLoading = false; statusText = ""
                messages.append(ChatMessage(role: .tool, content: output.isEmpty ? "No output" : output, toolName: "shell"))
            }

        default:
            requestAIResponse(prompt: text)
        }
    }

    func cleanTarget(_ raw: String) -> String {
        var t = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        // Remove common prefixes users might include
        for prefix in ["target ", "host ", "server ", "on ", "for ", "against ", "the ", "is ", "at "] {
            if t.lowercased().hasPrefix(prefix) {
                t = String(t.dropFirst(prefix.count))
            }
        }
        // Remove trailing punctuation
        t = t.trimmingCharacters(in: CharacterSet.punctuationCharacters.union(.whitespaces))
        return t
    }

    func extractFramework(_ raw: String, fallback: String) -> String {
        let l = raw.lowercased()
        if l.contains("nist") { return "NIST" }
        if l.contains("pci") { return "PCI-DSS" }
        if l.contains("iso") { return "ISO 27001" }
        if l.contains("soc") { return "SOC 2" }
        if l.contains("gdpr") { return "GDPR" }
        if l.contains("hipaa") { return "HIPAA" }
        if l.contains("owasp") { return "OWASP" }
        return fallback
    }

    // MARK: - Slash Commands

    func handleSlashCommand(_ input: String) {
        let parts = input.split(separator: " ", maxSplits: 1)
        let cmd = String(parts[0]).lowercased()
        let arg = parts.count > 1 ? String(parts[1]) : ""

        switch cmd {
        case "/help": showHelp()
        case "/clear": startNewThread()
        case "/new": startNewThread()
        case "/status": messages.append(ChatMessage(role: .assistant, content: buildStatusReport()))
        case "/tools":
            messages.append(ChatMessage(role: .assistant, content: "🔧 Checking tools..."))
            isLoading = true; statusText = "Checking tools..."
            Task { await checkTools(); isLoading = false; statusText = "" }
        case "/docker":
            messages.append(ChatMessage(role: .assistant, content: "🐳 Checking Docker..."))
            isLoading = true
            Task { await checkDocker(); isLoading = false; statusText = "" }
        case "/config": messages.append(ChatMessage(role: .assistant, content: buildConfigReport()))
        case "/models":
            let ml = availableModels.map { "• `\($0)`\($0 == selectedModel ? " ← active" : "")" }.joined(separator: "\n")
            messages.append(ChatMessage(role: .assistant, content: "**Models:**\n\n\(ml)"))
        case "/model":
            if !arg.isEmpty { selectedModel = arg; messages.append(ChatMessage(role: .assistant, content: "Switched to **\(arg)**")) }
            else { messages.append(ChatMessage(role: .assistant, content: "Usage: `/model <name>`")) }
        case "/scan":
            if arg.isEmpty { messages.append(ChatMessage(role: .assistant, content: "Usage: `/scan <target>`")); return }
            executeIntent(DetectedIntent(action: "scan", target: arg, fullMatch: input), text: input)
        case "/recon":
            if arg.isEmpty { messages.append(ChatMessage(role: .assistant, content: "Usage: `/recon <target>`")); return }
            executeIntent(DetectedIntent(action: "recon", target: arg, fullMatch: input), text: input)
        case "/nmap":
            if arg.isEmpty { messages.append(ChatMessage(role: .assistant, content: "Usage: `/nmap <target>`")); return }
            executeIntent(DetectedIntent(action: "nmap", target: arg, fullMatch: input), text: input)
        case "/whois":
            if arg.isEmpty { messages.append(ChatMessage(role: .assistant, content: "Usage: `/whois <domain>`")); return }
            executeIntent(DetectedIntent(action: "whois", target: arg, fullMatch: input), text: input)
        case "/dig":
            if arg.isEmpty { messages.append(ChatMessage(role: .assistant, content: "Usage: `/dig <domain>`")); return }
            executeIntent(DetectedIntent(action: "dig", target: arg, fullMatch: input), text: input)
        case "/curl":
            if arg.isEmpty { messages.append(ChatMessage(role: .assistant, content: "Usage: `/curl <url>`")); return }
            executeIntent(DetectedIntent(action: "curl", target: arg, fullMatch: input), text: input)
        case "/shell", "/sh", "/exec", "/run":
            if arg.isEmpty { messages.append(ChatMessage(role: .assistant, content: "Usage: `/shell <command>`")); return }
            executeIntent(DetectedIntent(action: "shell", target: arg, fullMatch: input), text: input)
        case "/compliance":
            executeIntent(DetectedIntent(action: "compliance", target: arg, fullMatch: input), text: input)
        case "/sessions":
            executeIntent(DetectedIntent(action: "sessions", target: "", fullMatch: input), text: input)
        case "/mcp":
            executeIntent(DetectedIntent(action: "mcp", target: arg, fullMatch: input), text: input)
        default:
            messages.append(ChatMessage(role: .assistant, content: "Unknown command: `\(cmd)`. Type `/help` for available commands."))
        }
    }

    func showHelp() {
        messages.append(ChatMessage(role: .assistant, content: """
        **HackGPT AI — Commands & Capabilities**

        **Slash Commands:**
        `/scan <target>` — Full penetration test
        `/recon <target>` — Reconnaissance only
        `/nmap <target>` — Port scan
        `/whois <domain>` — WHOIS lookup
        `/dig <domain>` — DNS lookup
        `/curl <url>` — HTTP headers
        `/shell <cmd>` — Execute shell command
        `/tools` — Check installed tools
        `/docker` — Docker status
        `/status` — System info
        `/config` — Show configuration
        `/compliance [fw]` — Compliance audit
        `/mcp` — MCP Kali server status
        `/models` — List AI models
        `/model <name>` — Switch model
        `/new` — New conversation
        `/clear` — Clear chat

        **Natural Language (just type normally):**
        • "Scan 10.0.0.1 for vulnerabilities"
        • "What ports are open on example.com?"
        • "Check my security tools"
        • "Show docker containers"
        • "Run a NIST compliance audit"
        • "Whois google.com"
        • "How do I exploit SQL injection?"
        • "Write an nmap script for service detection"

        I understand context — ask follow-up questions and I'll remember what we discussed.
        """))
    }

    // MARK: - AI Response

    func requestAIResponse(prompt: String) {
        isLoading = true
        statusText = "Thinking..."
        let placeholder = ChatMessage(role: .assistant, content: "", isStreaming: true)
        messages.append(placeholder)
        let idx = messages.count - 1

        currentTask = Task {
            await generateResponse(prompt: prompt, messageIndex: idx)
            isLoading = false
            statusText = ""
        }
    }

    func generateResponse(prompt: String, messageIndex: Int) async {
        let contextMessages = buildContextMessages(newPrompt: prompt)
        let model = selectedModel == "auto" ? detectBestModel() : selectedModel

        if model.hasPrefix("openai:") {
            await streamOpenAI(messages: contextMessages, messageIndex: messageIndex)
        } else {
            let ollamaModel = model.hasPrefix("ollama:") ? String(model.dropFirst(7)) : localModel
            await streamOllama(model: ollamaModel, messages: contextMessages, messageIndex: messageIndex)
        }

        if messageIndex < messages.count {
            messages[messageIndex].isStreaming = false
            if messages[messageIndex].content.isEmpty {
                messages[messageIndex].content = "I couldn't generate a response. Check that Ollama is running (`ollama serve`) or set an OpenAI API key in Configuration."
            }
        }
    }

    func detectBestModel() -> String {
        if availableModels.contains(where: { $0.hasPrefix("ollama:") }) {
            // Prefer deepseek-hack if available
            if availableModels.contains("ollama:deepseek-hack:latest") { return "ollama:deepseek-hack:latest" }
            return "ollama:\(localModel)"
        }
        if !openAIKey.isEmpty { return "openai:\(openAIModel)" }
        return "ollama:\(localModel)"
    }

    func buildContextMessages(newPrompt: String) -> [[String: String]] {
        var ctx: [[String: String]] = [["role": "system", "content": systemPrompt]]
        let recent = messages.suffix(30)
        for msg in recent {
            if msg.role == .system { continue }
            let role = (msg.role == .tool) ? "user" : msg.role.rawValue
            var content = msg.content
            if msg.role == .tool {
                content = "[Tool output from \(msg.toolName ?? "shell")]:\n\(content)"
            }
            ctx.append(["role": role, "content": content])
        }
        return ctx
    }

    // MARK: - Ollama Streaming

    func streamOllama(model: String, messages: [[String: String]], messageIndex: Int) async {
        guard let url = URL(string: "\(ollamaURL)/api/chat") else { return }
        let body: [String: Any] = ["model": model, "messages": messages, "stream": true]
        guard let jsonData = try? JSONSerialization.data(withJSONObject: body) else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = jsonData
        request.timeoutInterval = 120

        do {
            let (stream, response) = try await URLSession.shared.bytes(for: request)
            guard let httpResp = response as? HTTPURLResponse, httpResp.statusCode == 200 else {
                self.messages[messageIndex].content = "⚠️ Ollama returned an error. Is model `\(model)` pulled?\n\nTry: `ollama pull \(model)`"
                return
            }
            for try await line in stream.lines {
                if Task.isCancelled { break }
                guard let data = line.data(using: .utf8),
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let message = json["message"] as? [String: Any],
                      let content = message["content"] as? String else { continue }
                self.messages[messageIndex].content += content
            }
        } catch {
            if !Task.isCancelled && self.messages[messageIndex].content.isEmpty {
                self.messages[messageIndex].content = "**Connection failed.** Make sure Ollama is running.\n\n```\nollama serve\n```\n\nError: \(error.localizedDescription)"
            }
        }
    }

    // MARK: - OpenAI Streaming

    func streamOpenAI(messages: [[String: String]], messageIndex: Int) async {
        guard !openAIKey.isEmpty else {
            self.messages[messageIndex].content = "OpenAI API key not set. Go to **Configuration** tab or say \"show config\"."
            return
        }
        guard let url = URL(string: "https://api.openai.com/v1/chat/completions") else { return }
        let body: [String: Any] = ["model": openAIModel, "messages": messages, "stream": true, "temperature": 0.7, "max_tokens": 4096]
        guard let jsonData = try? JSONSerialization.data(withJSONObject: body) else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(openAIKey)", forHTTPHeaderField: "Authorization")
        request.httpBody = jsonData
        request.timeoutInterval = 60

        do {
            let (stream, _) = try await URLSession.shared.bytes(for: request)
            for try await line in stream.lines {
                if Task.isCancelled { break }
                guard line.hasPrefix("data: ") else { continue }
                let payload = String(line.dropFirst(6))
                if payload == "[DONE]" { break }
                guard let data = payload.data(using: .utf8),
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let choices = json["choices"] as? [[String: Any]],
                      let delta = choices.first?["delta"] as? [String: Any],
                      let content = delta["content"] as? String else { continue }
                self.messages[messageIndex].content += content
            }
        } catch {
            if !Task.isCancelled && self.messages[messageIndex].content.isEmpty {
                self.messages[messageIndex].content = "OpenAI error: \(error.localizedDescription)"
            }
        }
    }

    // MARK: - Shell Execution

    @discardableResult
    func runShell(_ command: String) async -> String {
        #if os(macOS)
        let root = self.projectRoot
        return await withCheckedContinuation { continuation in
            DispatchQueue.global().async {
                let proc = Process()
                proc.executableURL = URL(fileURLWithPath: "/bin/zsh")
                proc.arguments = ["-c", command]
                proc.currentDirectoryURL = URL(fileURLWithPath: root)
                let pipe = Pipe(); let errPipe = Pipe()
                proc.standardOutput = pipe; proc.standardError = errPipe
                do {
                    try proc.run()
                    proc.waitUntilExit()
                    let data = pipe.fileHandleForReading.readDataToEndOfFile()
                    let errData = errPipe.fileHandleForReading.readDataToEndOfFile()
                    var output = String(data: data, encoding: .utf8) ?? ""
                    if let err = String(data: errData, encoding: .utf8), !err.isEmpty { output += "\n" + err }
                    continuation.resume(returning: output.trimmingCharacters(in: .whitespacesAndNewlines))
                } catch {
                    continuation.resume(returning: "Error: \(error.localizedDescription)")
                }
            }
        }
        #else
        // iOS: run commands via API server
        guard let url = URL(string: "\(appState?.apiBaseURL ?? "http://localhost:8000")/api/shell"),
              let body = try? JSONSerialization.data(withJSONObject: ["command": command]) else {
            return "Shell execution not available on iOS. Connect to your Mac's HackGPT server."
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = body
        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let output = json["output"] as? String {
                return output
            }
            return String(data: data, encoding: .utf8) ?? "No response"
        } catch {
            return "iOS remote execution error: \(error.localizedDescription)"
        }
        #endif
    }

    func shellEscape(_ s: String) -> String {
        s.replacingOccurrences(of: "'", with: "'\\''")
    }

    // MARK: - Tool & System Checks

    func checkTools() async {
        let tools = ["nmap", "nikto", "sqlmap", "gobuster", "hydra", "msfconsole", "wireshark", "curl", "dig", "whois", "john", "hashcat", "aircrack-ng", "masscan", "subfinder", "httpx", "nuclei", "ffuf"]
        var installed: [String] = []
        var missing: [String] = []
        for tool in tools {
            let output = await runShell("which \(tool) 2>/dev/null && echo FOUND || echo MISSING")
            if output.contains("FOUND") { installed.append(tool) } else { missing.append(tool) }
        }
        let installedStr = installed.map { "  ✅ `\($0)`" }.joined(separator: "\n")
        let missingStr = missing.map { "  ❌ `\($0)`" }.joined(separator: "\n")
        messages.append(ChatMessage(role: .assistant, content: """
        **Security Tools Audit**

        **Installed (\(installed.count)):**
        \(installedStr)

        **Missing (\(missing.count)):**
        \(missingStr)

        Install missing tools with `brew install <tool>` or check the Tools tab.
        """))
    }

    func checkDocker() async {
        let output = await runShell("docker ps --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}' 2>&1")
        if output.contains("Cannot connect") || output.contains("command not found") || output.contains("not running") {
            messages.append(ChatMessage(role: .assistant, content: "❌ **Docker is not running.**\n\nStart Docker Desktop or run `open -a Docker`."))
        } else {
            messages.append(ChatMessage(role: .tool, content: output, toolName: "docker"))
        }
    }

    func buildStatusReport() -> String {
        let cores = ProcessInfo.processInfo.activeProcessorCount
        let mem = ProcessInfo.processInfo.physicalMemory / (1024 * 1024 * 1024)
        let ollamaStatus = ollamaConnected ? "✅ Connected" : "❌ Disconnected"
        let modelCount = availableModels.count - 1
        let mcpStatus = appState?.mcpRunning == true ? "✅ Running (port \(appState?.mcpPort ?? 8811))" : "❌ Stopped"
        return """
        **System Status**

        | Component | Status |
        |-----------|--------|
        | Platform | macOS arm64 (Apple Silicon M4) |
        | CPU Cores | \(cores) |
        | Memory | \(mem) GB |
        | Ollama | \(ollamaStatus) (\(modelCount) models) |
        | Active Model | \(selectedModel) |
        | MCP Server | \(mcpStatus) |
        | API Backend | \(appState?.backendRunning == true ? "✅ Running" : "❌ Stopped") |
        | Docker | \(appState?.enableDocker == true ? "✅ Enabled" : "❌ Disabled") |
        | Kubernetes | \(appState?.enableKubernetes == true ? "✅ Enabled" : "❌ Disabled") |
        | Project | `\(projectRoot)` |
        """
    }

    func buildConfigReport() -> String {
        let configPath = (projectRoot as NSString).appendingPathComponent("config.ini")
        if let contents = try? String(contentsOfFile: configPath, encoding: .utf8) {
            let truncated = contents.count > 3000 ? String(contents.prefix(3000)) + "\n..." : contents
            return "**config.ini:**\n\n```ini\n\(truncated)\n```"
        }
        return "Could not read config.ini"
    }
}

// MARK: - Chat View (ChatGPT-style, flat layout)

struct ChatView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = ChatViewModel()
    @State private var showConversations = false

    var body: some View {
        ZStack {
            // Background
            Color(red: 0.13, green: 0.13, blue: 0.14)
                .ignoresSafeArea()

            // Main chat VStack
            VStack(spacing: 0) {
                // Top bar
                chatTopBar
                    .background(Color(red: 0.11, green: 0.11, blue: 0.12))

                Rectangle().fill(Color.gray.opacity(0.2)).frame(height: 1)

                // Messages area
                if viewModel.messages.count <= 1 {
                    chatEmptyState
                } else {
                    chatMessageList
                }

                Rectangle().fill(Color.gray.opacity(0.2)).frame(height: 1)

                // Input bar
                chatInputArea
                    .background(Color(red: 0.11, green: 0.11, blue: 0.12))
            }
        }
        .onAppear {
            viewModel.configure(appState: appState)
        }
        .sheet(isPresented: $showConversations) {
            conversationsSheet
        }
    }

    // MARK: Top Bar

    var chatTopBar: some View {
        HStack(spacing: 12) {
            // Conversations button
            Button {
                showConversations = true
            } label: {
                Image(systemName: "clock.arrow.circlepath")
                    .font(.title3)
                    .foregroundColor(.white.opacity(0.7))
            }
            .buttonStyle(.plain)
            .help("Past conversations")

            Button {
                viewModel.startNewThread()
            } label: {
                Image(systemName: "square.and.pencil")
                    .font(.title3)
                    .foregroundColor(.white.opacity(0.7))
            }
            .buttonStyle(.plain)
            .help("New chat")

            Spacer()

            // Model picker
            HStack(spacing: 6) {
                Text("HackGPT")
                    .font(.headline)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)

                Picker("", selection: $viewModel.selectedModel) {
                    ForEach(viewModel.availableModels, id: \.self) { m in
                        Text(m.replacingOccurrences(of: "ollama:", with: ""))
                            .tag(m)
                    }
                }
                .labelsHidden()
                .controlSize(.small)
                .frame(width: 120)
            }

            Spacer()

            // Status
            HStack(spacing: 6) {
                Circle()
                    .fill(viewModel.ollamaConnected ? Color.green : Color.red)
                    .frame(width: 8, height: 8)
                Text(viewModel.ollamaConnected ? "Online" : "Offline")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.5))
            }

            if viewModel.isLoading {
                Button("Stop") {
                    viewModel.stopGenerating()
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .tint(.red)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    // MARK: Conversations Sheet

    var conversationsSheet: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Conversations")
                    .font(.title2)
                    .fontWeight(.bold)
                Spacer()
                Button("Done") { showConversations = false }
                    .buttonStyle(.bordered)
            }
            .padding()

            Divider()

            if viewModel.threads.isEmpty {
                Text("No conversations yet")
                    .foregroundColor(.secondary)
                    .padding(40)
            } else {
                List {
                    ForEach(viewModel.threads) { thread in
                        Button {
                            viewModel.switchToThread(thread.id)
                            showConversations = false
                        } label: {
                            HStack {
                                Image(systemName: "bubble.left")
                                    .foregroundColor(.secondary)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(thread.title)
                                        .font(.callout)
                                        .fontWeight(thread.id == viewModel.activeThreadId ? .bold : .regular)
                                    Text(thread.lastUpdated, style: .relative)
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                }
                                Spacer()
                                if thread.id == viewModel.activeThreadId {
                                    Image(systemName: "checkmark")
                                        .foregroundColor(.accentColor)
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    }
                    .onDelete { indexSet in
                        for i in indexSet {
                            viewModel.deleteThread(viewModel.threads[i].id)
                        }
                    }
                }
            }
        }
        .frame(width: 400, height: 500)
    }

    // MARK: Empty State (ChatGPT welcome)

    var chatEmptyState: some View {
        ScrollView {
            VStack(spacing: 24) {
                Spacer().frame(height: 60)

                // Logo
                ZStack {
                    Circle()
                        .fill(Color.red.opacity(0.15))
                        .frame(width: 64, height: 64)
                    Image(systemName: "shield.checkered")
                        .font(.system(size: 28))
                        .foregroundColor(.red)
                }

                Text("HackGPT AI")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundColor(.white)

                Text("Your elite cybersecurity AI assistant.\nAsk anything — scan targets, check tools, run commands.")
                    .font(.body)
                    .foregroundColor(.white.opacity(0.5))
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 480)

                // Quick action cards (2x3 grid)
                VStack(spacing: 10) {
                    HStack(spacing: 10) {
                        quickCard(icon: "network", title: "Scan a target", sub: "Full penetration test") {
                            viewModel.inputText = "Scan "
                        }
                        quickCard(icon: "magnifyingglass", title: "Reconnaissance", sub: "OSINT & enumeration") {
                            viewModel.inputText = "Run recon on "
                        }
                    }
                    HStack(spacing: 10) {
                        quickCard(icon: "wrench.and.screwdriver", title: "Check tools", sub: "Security tools audit") {
                            viewModel.inputText = "/tools"
                            viewModel.send()
                        }
                        quickCard(icon: "checklist", title: "Compliance", sub: "OWASP, NIST, PCI") {
                            viewModel.inputText = "Run an OWASP compliance audit"
                        }
                    }
                    HStack(spacing: 10) {
                        quickCard(icon: "terminal", title: "Run command", sub: "Execute shell cmd") {
                            viewModel.inputText = "/shell "
                        }
                        quickCard(icon: "lock.shield", title: "Vuln research", sub: "Exploits & fixes") {
                            viewModel.inputText = "How do I test for "
                        }
                    }
                }
                .frame(maxWidth: 520)

                Spacer().frame(height: 40)
            }
            .frame(maxWidth: .infinity)
            .padding(.horizontal, 20)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    func quickCard(icon: String, title: String, sub: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.title3)
                    .foregroundColor(.red)
                    .frame(width: 24)
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.callout)
                        .fontWeight(.medium)
                        .foregroundColor(.white)
                    Text(sub)
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.4))
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.2))
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.white.opacity(0.06))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color.white.opacity(0.08), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: Message List

    var chatMessageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: 0) {
                    ForEach(viewModel.messages) { msg in
                        if msg.role != .system {
                            ChatMessageBubble(message: msg)
                                .id(msg.id)
                        }
                    }

                    if viewModel.isLoading,
                       let last = viewModel.messages.last,
                       last.isStreaming, last.content.isEmpty {
                        HStack {
                            HStack(spacing: 5) {
                                ForEach(0..<3, id: \.self) { _ in
                                    Circle()
                                        .fill(Color.white.opacity(0.4))
                                        .frame(width: 6, height: 6)
                                }
                            }
                            .padding(.leading, 56)
                            Spacer()
                        }
                        .padding(.vertical, 10)
                        .id("typing")
                    }

                    Color.clear.frame(height: 16).id("chatBottom")
                }
            }
            .onChange(of: viewModel.messages.count) { _ in
                withAnimation(.easeOut(duration: 0.15)) {
                    proxy.scrollTo("chatBottom", anchor: .bottom)
                }
            }
            .onChange(of: viewModel.messages.last?.content ?? "") { _ in
                proxy.scrollTo("chatBottom", anchor: .bottom)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: Input Area

    var chatInputArea: some View {
        VStack(spacing: 6) {
            HStack(spacing: 10) {
                // Commands menu
                Menu {
                    Section("Scanning") {
                        Button { viewModel.inputText = "/scan " } label: { Label("Scan target", systemImage: "network") }
                        Button { viewModel.inputText = "/recon " } label: { Label("Recon target", systemImage: "magnifyingglass") }
                        Button { viewModel.inputText = "/nmap " } label: { Label("Nmap scan", systemImage: "antenna.radiowaves.left.and.right") }
                    }
                    Section("Lookups") {
                        Button { viewModel.inputText = "/whois " } label: { Label("WHOIS", systemImage: "globe") }
                        Button { viewModel.inputText = "/dig " } label: { Label("DNS lookup", systemImage: "point.3.filled.connected.trianglepath.dotted") }
                        Button { viewModel.inputText = "/curl " } label: { Label("HTTP headers", systemImage: "arrow.down.doc") }
                    }
                    Section("System") {
                        Button { viewModel.inputText = "/tools"; viewModel.send() } label: { Label("Check tools", systemImage: "wrench.and.screwdriver") }
                        Button { viewModel.inputText = "/docker"; viewModel.send() } label: { Label("Docker status", systemImage: "shippingbox") }
                        Button { viewModel.inputText = "/status"; viewModel.send() } label: { Label("System status", systemImage: "gauge.with.dots.needle.bottom.50percent") }
                        Button { viewModel.inputText = "/config"; viewModel.send() } label: { Label("Show config", systemImage: "gearshape") }
                    }
                    Section("Other") {
                        Button { viewModel.inputText = "/shell " } label: { Label("Shell command", systemImage: "terminal") }
                        Button { viewModel.inputText = "/compliance " } label: { Label("Compliance audit", systemImage: "checklist") }
                        Button { viewModel.inputText = "/help"; viewModel.send() } label: { Label("Help", systemImage: "questionmark.circle") }
                    }
                } label: {
                    Image(systemName: "plus.circle.fill")
                        .font(.title2)
                        .foregroundColor(.white.opacity(0.5))
                }
                .menuStyle(.borderlessButton)
                .menuIndicator(.hidden)
                .frame(width: 28)

                // Text input — Enter to send
                TextField("Message HackGPT…", text: $viewModel.inputText)
                    .textFieldStyle(.plain)
                    .font(.body)
                    .foregroundColor(.white)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 22)
                            .fill(Color.white.opacity(0.08))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 22)
                            .stroke(Color.white.opacity(0.12), lineWidth: 1)
                    )
                    .onSubmit {
                        viewModel.send()
                    }

                // Send button
                Button {
                    viewModel.send()
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 28))
                        .foregroundColor(
                            viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            ? .white.opacity(0.2) : .white
                        )
                }
                .buttonStyle(.plain)
                .disabled(viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 10)

            Text("HackGPT AI can make mistakes. Verify security-critical output.")
                .font(.caption2)
                .foregroundColor(.white.opacity(0.25))
                .padding(.bottom, 6)
        }
    }
}

// MARK: - Chat Message Bubble (ChatGPT-style)

struct ChatMessageBubble: View {
    let message: ChatMessage
    @State private var isHovering = false

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .top, spacing: 12) {
                // Avatar
                ZStack {
                    RoundedRectangle(cornerRadius: 6)
                        .fill(avatarBg)
                        .frame(width: 30, height: 30)
                    avatarContent
                }

                // Content column
                VStack(alignment: .leading, spacing: 4) {
                    // Role name
                    HStack(spacing: 6) {
                        Text(roleName)
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(roleColor)

                        if message.isStreaming {
                            ProgressView()
                                .controlSize(.mini)
                        }

                        if let tn = message.toolName {
                            Text(tn)
                                .font(.caption2)
                                .padding(.horizontal, 5)
                                .padding(.vertical, 1)
                                .background(Color.green.opacity(0.2))
                                .cornerRadius(3)
                                .foregroundColor(.green)
                        }

                        Spacer()

                        if isHovering && !message.content.isEmpty {
                            Button {
                                #if os(macOS)
                                NSPasteboard.general.clearContents()
                                NSPasteboard.general.setString(message.content, forType: .string)
                                #else
                                UIPasteboard.general.string = message.content
                                #endif
                            } label: {
                                Image(systemName: "doc.on.doc")
                                    .font(.caption)
                                    .foregroundColor(.white.opacity(0.4))
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    // Message body
                    if message.role == .tool {
                        ScrollView {
                            Text(message.content)
                                .font(.system(.caption, design: .monospaced))
                                .foregroundColor(.green)
                                .textSelection(.enabled)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .frame(maxHeight: 250)
                        .padding(10)
                        .background(Color.black.opacity(0.4))
                        .cornerRadius(8)
                    } else {
                        Text(LocalizedStringKey(message.content))
                            .textSelection(.enabled)
                            .font(.body)
                            .foregroundColor(.white.opacity(0.9))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
            .padding(.horizontal, 40)
            .padding(.vertical, 14)
            .background(rowBackground)
        }
        #if os(macOS)
        .onHover { isHovering = $0 }
        #endif
    }

    var rowBackground: Color {
        switch message.role {
        case .user:
            return Color.white.opacity(0.04)
        case .tool:
            return Color.green.opacity(0.03)
        default:
            return Color.clear
        }
    }

    var avatarBg: Color {
        switch message.role {
        case .assistant: return Color.red.opacity(0.2)
        case .user: return Color.blue.opacity(0.2)
        case .tool: return Color.green.opacity(0.2)
        case .system: return Color.gray.opacity(0.2)
        }
    }

    @ViewBuilder
    var avatarContent: some View {
        switch message.role {
        case .assistant:
            Text("H")
                .font(.system(.caption, design: .monospaced))
                .fontWeight(.black)
                .foregroundColor(.red)
        case .user:
            Image(systemName: "person.fill")
                .font(.caption2)
                .foregroundColor(.blue)
        case .tool:
            Image(systemName: "terminal")
                .font(.caption2)
                .foregroundColor(.green)
        case .system:
            Image(systemName: "gear")
                .font(.caption2)
                .foregroundColor(.gray)
        }
    }

    var roleName: String {
        switch message.role {
        case .assistant: return "HackGPT"
        case .user: return "You"
        case .tool: return "Tool Output"
        case .system: return "System"
        }
    }

    var roleColor: Color {
        switch message.role {
        case .assistant: return .red
        case .user: return .blue
        case .tool: return .green
        case .system: return .gray
        }
    }
}

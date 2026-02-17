// DataManager.swift – Local data storage, export, and management
// Part of HackGPT Enterprise Desktop

import SwiftUI
#if canImport(AppKit)
import AppKit
#endif

/// Manages the Application Support directory for HackGPT.
/// Stores: SQLite DB, chat history cache, generated reports, config backups.
final class DataDirectoryManager {
    static let shared = DataDirectoryManager()

    let appSupportURL: URL
    let dataURL: URL
    let logsURL: URL
    let reportsURL: URL
    let cacheURL: URL

    private init() {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        appSupportURL = base.appendingPathComponent("HackGPT", isDirectory: true)
        dataURL = appSupportURL.appendingPathComponent("data", isDirectory: true)
        logsURL = appSupportURL.appendingPathComponent("logs", isDirectory: true)
        reportsURL = appSupportURL.appendingPathComponent("reports", isDirectory: true)
        cacheURL = appSupportURL.appendingPathComponent("cache", isDirectory: true)

        // Create directories
        for url in [appSupportURL, dataURL, logsURL, reportsURL, cacheURL] {
            try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        }
    }

    /// Size of the data directory in bytes.
    var totalSizeBytes: Int64 {
        directorySize(appSupportURL)
    }

    /// Formatted size string (e.g. "12.3 MB").
    var totalSizeFormatted: String {
        ByteCountFormatter.string(fromByteCount: totalSizeBytes, countStyle: .file)
    }

    /// Clear cached data (preserves settings and DB).
    func clearCache() throws {
        let fm = FileManager.default
        if fm.fileExists(atPath: cacheURL.path) {
            try fm.removeItem(at: cacheURL)
            try fm.createDirectory(at: cacheURL, withIntermediateDirectories: true)
        }
    }

    /// Clear everything (full reset).
    func clearAll() throws {
        let fm = FileManager.default
        for url in [dataURL, logsURL, reportsURL, cacheURL] {
            if fm.fileExists(atPath: url.path) {
                try fm.removeItem(at: url)
                try fm.createDirectory(at: url, withIntermediateDirectories: true)
            }
        }
    }

    /// Open the data folder in Finder.
    func openInFinder() {
        #if os(macOS)
        NSWorkspace.shared.open(appSupportURL)
        #endif
    }

    /// Export all data as a zip archive. Returns URL of exported file.
    func exportData() throws -> URL {
        let timestamp = DateFormatter.localizedString(from: Date(), dateStyle: .short, timeStyle: .short)
            .replacingOccurrences(of: "/", with: "-")
            .replacingOccurrences(of: ":", with: "-")
            .replacingOccurrences(of: " ", with: "_")
        let exportName = "HackGPT_Export_\(timestamp)"
        let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent(exportName)
        try? FileManager.default.removeItem(at: tempDir)
        try FileManager.default.copyItem(at: appSupportURL, to: tempDir)

        // Use ditto to create a zip (macOS built-in)
        let zipURL = FileManager.default.temporaryDirectory.appendingPathComponent("\(exportName).zip")
        try? FileManager.default.removeItem(at: zipURL)
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/ditto")
        proc.arguments = ["-c", "-k", "--sequesterRsrc", tempDir.path, zipURL.path]
        try proc.run()
        proc.waitUntilExit()

        try? FileManager.default.removeItem(at: tempDir)

        return zipURL
    }

    // MARK: - Diagnostics

    /// Collect diagnostic info for bug reports.
    func diagnosticReport() -> String {
        var lines: [String] = []
        lines.append("=== HackGPT Diagnostics ===")
        lines.append("Date: \(Date())")
        lines.append("Data dir: \(appSupportURL.path)")
        lines.append("Total size: \(totalSizeFormatted)")
        lines.append("macOS: \(ProcessInfo.processInfo.operatingSystemVersionString)")
        lines.append("Cores: \(ProcessInfo.processInfo.activeProcessorCount)")
        lines.append("RAM: \(ProcessInfo.processInfo.physicalMemory / 1_073_741_824) GB")
        lines.append("Arch: \(machineArch())")

        // Check Python
        for p in ["/opt/homebrew/bin/python3", "/usr/local/bin/python3"] {
            if FileManager.default.fileExists(atPath: p) {
                lines.append("Python: \(p)")
                break
            }
        }

        // List data directories
        for (label, url) in [("Data", dataURL), ("Logs", logsURL), ("Reports", reportsURL), ("Cache", cacheURL)] {
            let size = ByteCountFormatter.string(fromByteCount: directorySize(url), countStyle: .file)
            lines.append("\(label): \(size)")
        }

        return lines.joined(separator: "\n")
    }

    // MARK: - Private

    private func directorySize(_ url: URL) -> Int64 {
        let fm = FileManager.default
        guard let enumerator = fm.enumerator(at: url, includingPropertiesForKeys: [.fileSizeKey], options: [.skipsHiddenFiles]) else { return 0 }
        var total: Int64 = 0
        for case let file as URL in enumerator {
            if let values = try? file.resourceValues(forKeys: [.fileSizeKey]),
               let size = values.fileSize {
                total += Int64(size)
            }
        }
        return total
    }

    private func machineArch() -> String {
        #if arch(arm64)
        return "arm64 (Apple Silicon)"
        #elseif arch(x86_64)
        return "x86_64 (Intel)"
        #else
        return "unknown"
        #endif
    }
}

// MARK: - Data Management View

struct DataManagementView: View {
    @State private var totalSize = DataDirectoryManager.shared.totalSizeFormatted
    @State private var showClearCacheConfirm = false
    @State private var showClearAllConfirm = false
    @State private var showExportSuccess = false
    @State private var exportPath = ""
    @State private var diagnostics = ""
    @State private var showDiagnostics = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Data Management")
                    .font(.title2.bold())

                // Storage info
                GroupBox("Storage") {
                    VStack(alignment: .leading, spacing: 12) {
                        InfoRow(label: "Location", value: DataDirectoryManager.shared.appSupportURL.path)
                        InfoRow(label: "Total Size", value: totalSize)

                        HStack(spacing: 12) {
                            Button {
                                DataDirectoryManager.shared.openInFinder()
                            } label: {
                                Label("Open in Finder", systemImage: "folder")
                            }

                            Button {
                                refreshSize()
                            } label: {
                                Label("Refresh", systemImage: "arrow.clockwise")
                            }
                        }
                    }
                    .padding(8)
                }

                // Export
                GroupBox("Export") {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Export all local data (settings, cache, reports) as a zip archive.")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Button {
                            exportData()
                        } label: {
                            Label("Export Data", systemImage: "square.and.arrow.up")
                        }
                        .buttonStyle(.borderedProminent)

                        if showExportSuccess {
                            Text("Exported to: \(exportPath)")
                                .font(.caption)
                                .foregroundStyle(.green)
                        }
                    }
                    .padding(8)
                }

                // Clear
                GroupBox("Clear Data") {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack(spacing: 12) {
                            Button(role: .destructive) {
                                showClearCacheConfirm = true
                            } label: {
                                Label("Clear Cache", systemImage: "trash")
                            }
                            .confirmationDialog("Clear cache?", isPresented: $showClearCacheConfirm) {
                                Button("Clear Cache", role: .destructive) {
                                    do {
                                        try DataDirectoryManager.shared.clearCache()
                                        refreshSize()
                                    } catch {
                                        errorMessage = error.localizedDescription
                                    }
                                }
                            } message: {
                                Text("This removes cached data but preserves settings and database.")
                            }

                            Button(role: .destructive) {
                                showClearAllConfirm = true
                            } label: {
                                Label("Clear All Data", systemImage: "trash.fill")
                            }
                            .confirmationDialog("Clear ALL data?", isPresented: $showClearAllConfirm) {
                                Button("Clear Everything", role: .destructive) {
                                    do {
                                        try DataDirectoryManager.shared.clearAll()
                                        refreshSize()
                                    } catch {
                                        errorMessage = error.localizedDescription
                                    }
                                }
                            } message: {
                                Text("This removes all local data including logs, cache, and reports. Settings in Keychain are preserved.")
                            }
                        }
                    }
                    .padding(8)
                }

                // Diagnostics
                GroupBox("Diagnostics") {
                    VStack(alignment: .leading, spacing: 12) {
                        Button {
                            diagnostics = DataDirectoryManager.shared.diagnosticReport()
                            showDiagnostics = true
                        } label: {
                            Label("Generate Diagnostic Report", systemImage: "stethoscope")
                        }

                        if showDiagnostics {
                            ScrollView {
                                Text(diagnostics)
                                    .font(.system(.caption, design: .monospaced))
                                    .textSelection(.enabled)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .frame(maxHeight: 200)
                            .background(Color.black.opacity(0.05))
                            .clipShape(RoundedRectangle(cornerRadius: 6))

                            Button {
                                #if os(macOS)
                                NSPasteboard.general.clearContents()
                                NSPasteboard.general.setString(diagnostics, forType: .string)
                                #endif
                            } label: {
                                Label("Copy to Clipboard", systemImage: "doc.on.doc")
                            }
                        }
                    }
                    .padding(8)
                }

                if let error = errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                }

                Spacer()
            }
            .padding(24)
        }
    }

    private func refreshSize() {
        totalSize = DataDirectoryManager.shared.totalSizeFormatted
    }

    private func exportData() {
        do {
            let url = try DataDirectoryManager.shared.exportData()
            exportPath = url.path
            showExportSuccess = true
            #if os(macOS)
            NSWorkspace.shared.activateFileViewerSelecting([url])
            #endif
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

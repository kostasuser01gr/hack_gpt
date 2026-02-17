// CostControlManager.swift – Per-day usage limits for OpenAI API
// Part of HackGPT Enterprise Desktop

import Foundation

/// Tracks and enforces usage caps for the OpenAI API to prevent surprise costs.
/// Data is stored in a local JSON file under Application Support.
@MainActor
final class CostControlManager: ObservableObject {

    static let shared = CostControlManager()

    // MARK: - Published state

    @Published var enabled: Bool = true
    @Published var dailyRequestLimit: Int = 100
    @Published var dailyTokenBudget: Int = 500_000
    @Published var dailyCostCapUSD: Double = 5.00
    @Published var aiDisabled: Bool = false

    // Today's counters
    @Published var todayRequests: Int = 0
    @Published var todayTokens: Int = 0
    @Published var todayEstimatedCostUSD: Double = 0.0

    // Alerts
    @Published var limitReached: Bool = false
    @Published var limitMessage: String = ""

    // MARK: - Internal

    private var currentDate: String = ""
    private let storageURL: URL

    private init() {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let appDir = appSupport.appendingPathComponent("HackGPT", isDirectory: true)
        try? FileManager.default.createDirectory(at: appDir, withIntermediateDirectories: true)
        storageURL = appDir.appendingPathComponent("cost_controls.json")
        load()
    }

    // MARK: - Usage Recording

    /// Record a completed API request. Returns false if budget is exhausted.
    func recordUsage(tokens: Int, estimatedCostUSD: Double = 0) -> Bool {
        resetIfNewDay()

        guard enabled && !aiDisabled else {
            if aiDisabled {
                limitMessage = "AI is manually disabled."
                limitReached = true
                return false
            }
            return true // controls disabled — allow
        }

        todayRequests += 1
        todayTokens += tokens
        todayEstimatedCostUSD += estimatedCostUSD

        if todayRequests > dailyRequestLimit {
            limitReached = true
            limitMessage = "Daily request limit reached (\(dailyRequestLimit) requests)."
            save()
            return false
        }
        if todayTokens > dailyTokenBudget {
            limitReached = true
            limitMessage = "Daily token budget exceeded (\(dailyTokenBudget) tokens)."
            save()
            return false
        }
        if todayEstimatedCostUSD > dailyCostCapUSD {
            limitReached = true
            limitMessage = String(format: "Daily cost cap exceeded ($%.2f).", dailyCostCapUSD)
            save()
            return false
        }

        save()
        return true
    }

    /// Get a human-readable summary of today's usage.
    var usageSummary: String {
        resetIfNewDay()
        return """
        Requests: \(todayRequests) / \(dailyRequestLimit)
        Tokens: \(todayTokens) / \(dailyTokenBudget)
        Est. cost: $\(String(format: "%.4f", todayEstimatedCostUSD)) / $\(String(format: "%.2f", dailyCostCapUSD))
        """
    }

    func resetTodayCounters() {
        todayRequests = 0
        todayTokens = 0
        todayEstimatedCostUSD = 0
        limitReached = false
        limitMessage = ""
        save()
    }

    // MARK: - Persistence

    private struct CostData: Codable {
        var enabled: Bool
        var dailyRequestLimit: Int
        var dailyTokenBudget: Int
        var dailyCostCapUSD: Double
        var aiDisabled: Bool
        var date: String
        var requests: Int
        var tokens: Int
        var estimatedCostUSD: Double
    }

    private func save() {
        let data = CostData(
            enabled: enabled,
            dailyRequestLimit: dailyRequestLimit,
            dailyTokenBudget: dailyTokenBudget,
            dailyCostCapUSD: dailyCostCapUSD,
            aiDisabled: aiDisabled,
            date: todayString(),
            requests: todayRequests,
            tokens: todayTokens,
            estimatedCostUSD: todayEstimatedCostUSD
        )
        if let encoded = try? JSONEncoder().encode(data) {
            try? encoded.write(to: storageURL, options: .atomic)
        }
    }

    private func load() {
        guard let rawData = try? Data(contentsOf: storageURL),
              let data = try? JSONDecoder().decode(CostData.self, from: rawData) else {
            currentDate = todayString()
            return
        }

        enabled = data.enabled
        dailyRequestLimit = data.dailyRequestLimit
        dailyTokenBudget = data.dailyTokenBudget
        dailyCostCapUSD = data.dailyCostCapUSD
        aiDisabled = data.aiDisabled
        currentDate = data.date

        if data.date == todayString() {
            todayRequests = data.requests
            todayTokens = data.tokens
            todayEstimatedCostUSD = data.estimatedCostUSD
        } else {
            currentDate = todayString()
        }
    }

    private func resetIfNewDay() {
        let today = todayString()
        if currentDate != today {
            currentDate = today
            todayRequests = 0
            todayTokens = 0
            todayEstimatedCostUSD = 0
            limitReached = false
            limitMessage = ""
        }
    }

    private func todayString() -> String {
        let fmt = DateFormatter()
        fmt.dateFormat = "yyyy-MM-dd"
        return fmt.string(from: Date())
    }
}

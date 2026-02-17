// KeychainManager.swift – Secure secret storage via macOS Keychain
// Part of HackGPT Enterprise Desktop

import Foundation
import Security

/// Thread-safe wrapper around Security.framework Keychain Services.
/// Stores API keys and tokens encrypted in the user's login keychain.
final class KeychainManager {
    static let shared = KeychainManager()

    /// Service name used as the Keychain "account group".
    private let service = "com.hackgpt.enterprise"

    private init() {}

    // MARK: - Public API

    /// Save (or update) a value in the Keychain.
    @discardableResult
    func set(_ value: String, forKey key: String) -> Bool {
        guard let data = value.data(using: .utf8) else { return false }

        // Try updating first
        let updateQuery = baseQuery(key: key)
        let updateAttrs: [String: Any] = [kSecValueData as String: data]
        let updateStatus = SecItemUpdate(updateQuery as CFDictionary, updateAttrs as CFDictionary)

        if updateStatus == errSecSuccess {
            return true
        }

        // If item doesn't exist, add it
        if updateStatus == errSecItemNotFound {
            var addQuery = baseQuery(key: key)
            addQuery[kSecValueData as String] = data
            addQuery[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            let addStatus = SecItemAdd(addQuery as CFDictionary, nil)
            return addStatus == errSecSuccess
        }

        return false
    }

    /// Retrieve a value from the Keychain. Returns nil if not found.
    func get(forKey key: String) -> String? {
        var query = baseQuery(key: key)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess, let data = result as? Data else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }

    /// Delete a value from the Keychain.
    @discardableResult
    func delete(forKey key: String) -> Bool {
        let query = baseQuery(key: key)
        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }

    /// Check whether a key exists in the Keychain (without retrieving value).
    func exists(forKey key: String) -> Bool {
        var query = baseQuery(key: key)
        query[kSecReturnData as String] = false
        let status = SecItemCopyMatching(query as CFDictionary, nil)
        return status == errSecSuccess
    }

    // MARK: - Well-Known Keys

    enum Key: String {
        case openAIAPIKey = "openai_api_key"
        case sentryDSN = "sentry_dsn"
        case shodanAPIKey = "shodan_api_key"
        case customToken = "custom_token"
    }

    func set(_ value: String, forKey key: Key) -> Bool {
        set(value, forKey: key.rawValue)
    }

    func get(forKey key: Key) -> String? {
        get(forKey: key.rawValue)
    }

    func delete(forKey key: Key) -> Bool {
        delete(forKey: key.rawValue)
    }

    func exists(forKey key: Key) -> Bool {
        exists(forKey: key.rawValue)
    }

    // MARK: - Validation

    /// Validate an OpenAI API key format (starts with "sk-").
    static func isValidOpenAIKeyFormat(_ key: String) -> Bool {
        let trimmed = key.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.hasPrefix("sk-") && trimmed.count >= 20
    }

    // MARK: - Private

    private func baseQuery(key: String) -> [String: Any] {
        return [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
        ]
    }
}

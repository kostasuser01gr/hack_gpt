"""Privacy utilities – masking, hashing, and reveal controls."""

from __future__ import annotations

import hashlib
import hmac
import re


def hmac_device_key(mac: str, secret: str) -> str:
    """Create a stable, privacy-safe device fingerprint from a MAC address.

    Uses HMAC-SHA256 with a server secret so the key is deterministic but
    cannot be reversed without the secret.
    """
    normalised = _normalise_mac(mac)
    return hmac.new(secret.encode(), normalised.encode(), hashlib.sha256).hexdigest()


def mask_mac(mac: str) -> str:
    """Mask last 3 octets of a MAC address.

    ``AA:BB:CC:DD:EE:FF`` → ``AA:BB:CC:**:**:**``
    """
    normalised = _normalise_mac(mac)
    parts = normalised.split(":")
    if len(parts) != 6:
        return "**:**:**:**:**:**"
    return ":".join([*parts[:3], "**", "**", "**"])


def mask_ip(ip: str) -> str:
    """Mask last octet(s) of an IP address.

    ``192.168.1.42`` → ``192.168.1.***``
    """
    parts = ip.split(".")
    if len(parts) != 4:
        return "***.***.***.***"
    return ".".join([*parts[:3], "***"])


def _normalise_mac(mac: str) -> str:
    """Normalise a MAC to upper-case colon-separated format."""
    cleaned = re.sub(r"[^0-9a-fA-F]", "", mac)
    if len(cleaned) != 12:
        return mac.upper()
    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2)).upper()


def sha256_short(value: str) -> str:
    """Return first 16 hex chars of SHA-256 for dedup keys."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]

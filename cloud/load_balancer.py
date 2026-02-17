#!/usr/bin/env python3
"""
Load Balancer for HackGPT Enterprise
Distributes traffic across multiple instances for scalability
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass
class BackendInstance:
    """Represents a backend server instance"""

    host: str
    port: int
    weight: int = 1
    active: bool = True
    health_check_url: str = "/health"
    last_check: datetime | None = None
    response_time: float = 0.0


class LoadBalancer:
    """Simple load balancer implementation"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.backends: list[BackendInstance] = []
        self._lock = Lock()
        self._current_backend = 0

    def add_backend(self, backend: BackendInstance) -> None:
        """Add a backend instance"""
        with self._lock:
            self.backends.append(backend)
            self.logger.info(f"Added backend: {backend.host}:{backend.port}")

    def remove_backend(self, host: str, port: int) -> bool:
        """Remove a backend instance"""
        with self._lock:
            for i, backend in enumerate(self.backends):
                if backend.host == host and backend.port == port:
                    removed = self.backends.pop(i)
                    self.logger.info(f"Removed backend: {removed.host}:{removed.port}")
                    return True
        return False

    def get_next_backend(self, algorithm: str = "round_robin") -> BackendInstance | None:
        """Get the next backend based on the load balancing algorithm"""
        active_backends = [b for b in self.backends if b.active]

        if not active_backends:
            return None

        if algorithm == "round_robin":
            return self._round_robin(active_backends)
        if algorithm == "weighted":
            return self._weighted_round_robin(active_backends)
        if algorithm == "least_connections":
            return self._least_connections(active_backends)
        if algorithm == "random":
            return random.choice(active_backends)
        return self._round_robin(active_backends)

    def _round_robin(self, backends: list[BackendInstance]) -> BackendInstance:
        """Round-robin load balancing"""
        with self._lock:
            self._current_backend = (self._current_backend + 1) % len(backends)
            return backends[self._current_backend]

    def _weighted_round_robin(self, backends: list[BackendInstance]) -> BackendInstance:
        """Weighted round-robin load balancing"""
        # Simple weighted selection
        weights = [b.weight for b in backends]
        total_weight = sum(weights)

        r = random.uniform(0, total_weight)
        cumulative_weight = 0

        for backend in backends:
            cumulative_weight += backend.weight
            if r <= cumulative_weight:
                return backend

        return backends[-1]  # fallback

    def _least_connections(self, backends: list[BackendInstance]) -> BackendInstance:
        """Least connections load balancing (simplified)"""
        # For this implementation, we'll use response time as a proxy
        return min(backends, key=lambda b: b.response_time)

    def health_check(self) -> None:
        """Perform health checks on all backends"""
        import requests

        for backend in self.backends:
            try:
                start_time = time.time()
                url = f"http://{backend.host}:{backend.port}{backend.health_check_url}"
                response = requests.get(url, timeout=5)
                backend.response_time = time.time() - start_time
                backend.active = response.status_code == 200
                backend.last_check = datetime.now(tz=timezone.utc)

                if backend.active:
                    self.logger.debug(f"Backend {backend.host}:{backend.port} is healthy")
                else:
                    self.logger.warning(
                        f"Backend {backend.host}:{backend.port} health check failed: {response.status_code}"
                    )

            except Exception as e:
                backend.active = False
                backend.last_check = datetime.now(tz=timezone.utc)
                self.logger.error(f"Health check failed for {backend.host}:{backend.port}: {e!s}")

    def get_status(self) -> dict[str, Any]:
        """Get load balancer status"""
        active_count = sum(1 for b in self.backends if b.active)
        total_count = len(self.backends)

        return {
            "total_backends": total_count,
            "active_backends": active_count,
            "inactive_backends": total_count - active_count,
            "backends": [
                {
                    "host": b.host,
                    "port": b.port,
                    "active": b.active,
                    "weight": b.weight,
                    "response_time": b.response_time,
                    "last_check": b.last_check.isoformat() if b.last_check else None,
                }
                for b in self.backends
            ],
        }


# Singleton instance
load_balancer = LoadBalancer()


def get_load_balancer() -> LoadBalancer:
    """Get the singleton load balancer instance"""
    return load_balancer

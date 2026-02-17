"""
Performance and Scalability Module

This module provides performance optimization and scalability features for HackGPT,
including caching, parallel processing, load balancing, and performance monitoring.
"""

from .cache_manager import CacheManager, MemoryCache, RedisCache, get_cache_manager
from .load_balancer import HealthChecker, LoadBalancer, get_load_balancer
from .optimization import (
    QueryOptimizer,
    ResourceOptimizer,
    get_query_optimizer,
    get_resource_optimizer,
)
from .parallel_processor import ParallelProcessor, TaskQueue, get_parallel_processor
from .performance_monitor import PerformanceMonitor, get_performance_monitor

__version__ = "1.0.0"

__all__ = [
    "CacheManager",
    "HealthChecker",
    "LoadBalancer",
    "MemoryCache",
    "ParallelProcessor",
    "PerformanceMonitor",
    "QueryOptimizer",
    "RedisCache",
    "ResourceOptimizer",
    "TaskQueue",
    "get_cache_manager",
    "get_load_balancer",
    "get_parallel_processor",
    "get_performance_monitor",
    "get_query_optimizer",
    "get_resource_optimizer",
]

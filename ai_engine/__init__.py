from .advanced_engine import (
    AdvancedAIEngine,
    AnalysisResult,
    ContextManager,
    PatternRecognizer,
    VulnerabilityCorrelator,
)


def get_advanced_ai_engine():
    """Initialize and return the advanced AI engine"""
    return AdvancedAIEngine()


__all__ = [
    "AdvancedAIEngine",
    "AnalysisResult",
    "ContextManager",
    "PatternRecognizer",
    "VulnerabilityCorrelator",
    "get_advanced_ai_engine",
]

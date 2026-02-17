from .dynamic_reports import ChartGenerator, DynamicReportGenerator, ReportTemplate
from .realtime_dashboard import RealTimeDashboard


def get_realtime_dashboard():
    """Initialize and return the real-time dashboard"""
    return RealTimeDashboard()


__all__ = [
    "ChartGenerator",
    "DynamicReportGenerator",
    "RealTimeDashboard",
    "ReportTemplate",
    "get_realtime_dashboard",
]

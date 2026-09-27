"""M15 adaptive scheduler — DAG analysis and policies (simulator-first)."""

from .critical_path import compute_critical_path_report

__all__ = ["compute_critical_path_report"]

"""Map drift events to semantic categories."""

from __future__ import annotations

from ghostrange_contracts.living_twin_m6 import DriftEventV1, SemanticDriftCategory


def classify_property(property_path: str, entity_name: str) -> SemanticDriftCategory:
    p = property_path.lower()
    n = entity_name.lower()
    if "image" in p or "version" in p or "tag" in p:
        return SemanticDriftCategory.VERSION if "image" in p else SemanticDriftCategory.SERVICE
    if "port" in p or "network" in p:
        return SemanticDriftCategory.NETWORK
    if "env" in p or "config" in p:
        if "auth" in n or "identity" in n:
            return SemanticDriftCategory.IDENTITY
        return SemanticDriftCategory.CONFIGURATION
    if "cpu" in p or "memory" in p or "replica" in p:
        return SemanticDriftCategory.RESOURCE
    if "depends" in p:
        return SemanticDriftCategory.DEPENDENCY
    if "secret" in p:
        return SemanticDriftCategory.SECURITY_CONTROL
    return SemanticDriftCategory.UNKNOWN


def enrich_drift_event(event: DriftEventV1) -> DriftEventV1:
    cat = classify_property(event.property_path, event.entity_name)
    return event.model_copy(update={"semantic_category": cat})


__all__ = ["classify_property", "enrich_drift_event"]

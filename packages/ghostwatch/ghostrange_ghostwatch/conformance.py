"""Approved vs observed deployment — multi-dimensional."""

from __future__ import annotations

from ghostrange_contracts.ghostwatch_m12 import (
    ConformanceDimension,
    ConformanceStatus,
    DeploymentConformanceReportV1,
    ObservedDeploymentStateV1,
)


def compare_deployment(
    approved_artifact_digest: str,
    observed: ObservedDeploymentStateV1,
    *,
    approved_config_fingerprint: str = "",
    approved_service_version: str = "",
) -> DeploymentConformanceReportV1:
    obs = observed.artifact_digest
    dims: dict[str, ConformanceStatus] = {}

    if not obs:
        return DeploymentConformanceReportV1(
            approved_artifact_digest=approved_artifact_digest,
            observed_artifact_digest="",
            status=ConformanceStatus.NOT_OBSERVABLE,
            dimensions={ConformanceDimension.ARTIFACT.value: ConformanceStatus.NOT_OBSERVABLE},
            notes=["No artifact digest observed"],
        )

    dims[ConformanceDimension.ARTIFACT.value] = (
        ConformanceStatus.MATCH if obs == approved_artifact_digest else ConformanceStatus.MATERIAL_DIFFERENCE
    )
    if approved_config_fingerprint and observed.config_fingerprint:
        dims[ConformanceDimension.CONFIGURATION.value] = (
            ConformanceStatus.MATCH
            if observed.config_fingerprint == approved_config_fingerprint
            else ConformanceStatus.MATERIAL_DIFFERENCE
        )
    else:
        dims[ConformanceDimension.CONFIGURATION.value] = ConformanceStatus.UNKNOWN

    if approved_service_version and observed.service_version:
        dims[ConformanceDimension.SERVICE_VERSION.value] = (
            ConformanceStatus.MATCH
            if observed.service_version == approved_service_version
            else ConformanceStatus.MATERIAL_DIFFERENCE
        )
    else:
        dims[ConformanceDimension.SERVICE_VERSION.value] = ConformanceStatus.UNKNOWN

    required = (
        ConformanceDimension.ARTIFACT,
        ConformanceDimension.CONFIGURATION,
    )
    if any(dims.get(d.value) == ConformanceStatus.MATERIAL_DIFFERENCE for d in required):
        overall = ConformanceStatus.MATERIAL_DIFFERENCE
        notes = ["UNAPPROVED_DEPLOYMENT_VARIANCE"]
    elif any(dims.get(d.value) == ConformanceStatus.UNKNOWN for d in required):
        overall = ConformanceStatus.UNKNOWN
        notes = ["UNKNOWN is not PASS — policy may HOLD"]
    elif dims[ConformanceDimension.ARTIFACT.value] == ConformanceStatus.MATCH:
        overall = ConformanceStatus.MATCH
        notes = []
    else:
        overall = ConformanceStatus.FUNCTIONALLY_EQUIVALENT
        notes = []

    return DeploymentConformanceReportV1(
        approved_artifact_digest=approved_artifact_digest,
        observed_artifact_digest=obs,
        status=overall,
        dimensions=dims,
        notes=notes,
    )

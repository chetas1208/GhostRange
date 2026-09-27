# Deployment conformance (M12)

`DeploymentConformanceReportV1` compares **approved** vs **observed** across dimensions:

- ARTIFACT (required)
- CONFIGURATION (required; UNKNOWN ≠ PASS)
- SERVICE_VERSION, …

**MATERIAL_DIFFERENCE** on a required dimension → **HOLD** / `UNAPPROVED_DEPLOYMENT_VARIANCE`.

Ingress: `ExternalDeploymentRecordV1` via GhostWatch external-record API.

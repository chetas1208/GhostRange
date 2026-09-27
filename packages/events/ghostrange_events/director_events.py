"""M9 GhostDirector domain events."""

DIRECTOR_CAMPAIGN_STARTED = "director.campaign_started"
HYPOTHESIS_PROPOSED = "hypothesis.proposed"
HYPOTHESIS_SUPPORTED = "hypothesis.supported"
HYPOTHESIS_WEAKENED = "hypothesis.weakened"
HYPOTHESIS_REFUTED = "hypothesis.refuted"
UNCERTAINTY_CREATED = "uncertainty.created"
EXPERIMENT_PROPOSED = "experiment.proposed"
EXPERIMENT_REJECTED = "experiment.rejected"
EXPERIMENT_SELECTED = "experiment.selected"
EXPERIMENT_COMPLETED = "experiment.completed"
PORTFOLIO_CREATED = "portfolio.created"
DIRECTOR_DECISION = "director.decision"
KNOWLEDGE_UPDATED = "knowledge.updated"
SURPRISE_OBSERVED = "surprise.observed"
DIRECTOR_STOPPED = "director.stopped"

__all__ = [
    "DIRECTOR_CAMPAIGN_STARTED",
    "HYPOTHESIS_PROPOSED",
    "EXPERIMENT_PROPOSED",
    "DIRECTOR_DECISION",
    "SURPRISE_OBSERVED",
    "DIRECTOR_STOPPED",
]

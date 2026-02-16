"""
Objective schemas for scenario goals and success metrics.
"""

from dataclasses import dataclass, field


@dataclass
class MetricDefinition:
    """
    Definition of a success metric for an objective.

    Attributes:
        target: The target value to achieve
        weight: How important this metric is (default 1.0)
        lower_is_better: Whether lower values are better (e.g., time_taken)
        required: Whether this metric must be met to succeed
    """

    target: float
    weight: float = 1.0
    lower_is_better: bool = False
    required: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "MetricDefinition":
        """Create MetricDefinition from dictionary."""
        return cls(
            target=data["target"],
            weight=data.get("weight", 1.0),
            lower_is_better=data.get("lower_is_better", False),
            required=data.get("required", False),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "target": self.target,
            "weight": self.weight,
            "lower_is_better": self.lower_is_better,
            "required": self.required,
        }


@dataclass
class Objective:
    """
    Scenario-defined goals for the agent.

    Objectives are passed from the game scenario to the agent via observations.
    This enables general-purpose agents that adapt to different goals.

    Attributes:
        description: Human-readable description of the objective
        success_metrics: Dictionary of metric names to their definitions
        time_limit: Time limit in ticks (0 = unlimited)

    Example:
        objective = Objective(
            description="Collect resources while avoiding hazards",
            success_metrics={
                "resources_collected": MetricDefinition(target=10, weight=1.0),
                "health_remaining": MetricDefinition(target=50, weight=0.5)
            },
            time_limit=600
        )
    """

    description: str
    success_metrics: dict[str, MetricDefinition] = field(default_factory=dict)
    time_limit: int = 0  # 0 = unlimited

    @classmethod
    def from_dict(cls, data: dict) -> "Objective":
        """
        Create Objective from dictionary.

        Args:
            data: Dictionary from IPC message

        Returns:
            Objective instance
        """
        success_metrics = {}
        for name, metric_data in data.get("success_metrics", {}).items():
            success_metrics[name] = MetricDefinition.from_dict(metric_data)

        return cls(
            description=data["description"],
            success_metrics=success_metrics,
            time_limit=data.get("time_limit", 0),
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "description": self.description,
            "success_metrics": {
                name: metric.to_dict() for name, metric in self.success_metrics.items()
            },
            "time_limit": self.time_limit,
        }

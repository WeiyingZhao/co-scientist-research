"""Workflow configuration for the Co-Scientist multi-agent system.

This module defines the workflow state transitions in a declarative,
configurable format rather than hardcoded if-else blocks.

It also supports parallel execution groups for agents that can run
concurrently without dependencies.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from geospatial_co_scientist.models.state import AgentType, CoScientistState


@dataclass
class ParallelAgentGroup:
    """A group of agents that can be run in parallel.

    When the workflow reaches a state where these agents can all run,
    they will be executed concurrently for improved performance.

    Attributes:
        agents: List of agent types that can run together
        condition: Optional condition that must be true for parallel execution
        description: Human-readable description
    """

    agents: list[AgentType]
    condition: Optional[Callable[[CoScientistState], bool]] = None
    description: str = ""


@dataclass
class TransitionCondition:
    """A condition that determines if a state transition should occur.

    Attributes:
        name: Human-readable name for the condition
        check: Function that takes state and returns True if condition is met
        priority: Higher priority conditions are checked first (default: 0)
    """

    name: str
    check: Callable[[CoScientistState], bool]
    priority: int = 0


@dataclass
class WorkflowTransition:
    """A single transition rule in the workflow.

    Attributes:
        source: The agent type this transition starts from (or None for any)
        target: The agent type to transition to
        conditions: List of conditions that must ALL be true for this transition
        priority: Higher priority transitions are checked first
        description: Human-readable description of when this transition occurs
    """

    target: AgentType
    conditions: list[TransitionCondition] = field(default_factory=list)
    source: Optional[AgentType] = None
    priority: int = 0
    description: str = ""


class WorkflowConfiguration:
    """Configuration for the Co-Scientist workflow transitions.

    This class defines all the state transitions in a declarative way,
    making it easy to modify the workflow without changing code logic.

    It also supports parallel execution groups for improved performance
    where agents can run concurrently.
    """

    def __init__(self, enable_parallel: bool = True):
        """Initialize workflow configuration.

        Args:
            enable_parallel: Whether to enable parallel agent execution
        """
        self._transitions: list[WorkflowTransition] = []
        self._parallel_groups: list[ParallelAgentGroup] = []
        self._enable_parallel = enable_parallel
        self._setup_default_transitions()
        self._setup_parallel_groups()

    def _setup_default_transitions(self):
        """Set up the default Co-Scientist workflow transitions."""

        # Condition: No literature summary yet
        no_literature = TransitionCondition(
            name="no_literature_summary",
            check=lambda s: not s.literature_summary,
            priority=100
        )

        # Condition: No hypotheses generated yet
        no_hypotheses = TransitionCondition(
            name="no_hypotheses",
            check=lambda s: not s.hypotheses,
            priority=90
        )

        # Condition: Unreviewed hypotheses exist
        unreviewed_hypotheses = TransitionCondition(
            name="unreviewed_hypotheses",
            check=lambda s: self._has_unreviewed_hypotheses(s),
            priority=80
        )

        # Condition: Need more rankings
        need_rankings = TransitionCondition(
            name="need_rankings",
            check=lambda s: len(s.hypothesis_rankings) < len(s.hypotheses) - 1,
            priority=70
        )

        # Condition: Need proximity analysis
        need_proximity = TransitionCondition(
            name="need_proximity",
            check=lambda s: not s.hypothesis_clusters or s.current_iteration > 1,
            priority=60
        )

        # Condition: Can evolve hypotheses
        can_evolve = TransitionCondition(
            name="can_evolve",
            check=lambda s: self._can_evolve(s),
            priority=50
        )

        # Condition: Need experiment designs
        need_designs = TransitionCondition(
            name="need_experiment_designs",
            check=lambda s: self._needs_experiment_designs(s),
            priority=40
        )

        # Condition: Max iterations reached
        max_iterations = TransitionCondition(
            name="max_iterations_reached",
            check=lambda s: s.current_iteration >= s.max_iterations,
            priority=30
        )

        # Condition: Can start new iteration
        can_iterate = TransitionCondition(
            name="can_start_new_iteration",
            check=lambda s: s.current_iteration < s.max_iterations,
            priority=20
        )

        # Define transitions
        self._transitions = [
            WorkflowTransition(
                target=AgentType.LITERATURE_SEARCH,
                conditions=[no_literature],
                priority=100,
                description="Initial literature review"
            ),
            WorkflowTransition(
                target=AgentType.GENERATION,
                conditions=[no_hypotheses],
                priority=90,
                description="Generate initial hypotheses"
            ),
            WorkflowTransition(
                target=AgentType.REFLECTION,
                conditions=[unreviewed_hypotheses],
                priority=80,
                description="Review unreviewed hypotheses"
            ),
            WorkflowTransition(
                target=AgentType.RANKING,
                conditions=[need_rankings],
                priority=70,
                description="Rank hypotheses"
            ),
            WorkflowTransition(
                target=AgentType.PROXIMITY,
                conditions=[need_proximity],
                priority=60,
                description="Analyze hypothesis proximity/similarity"
            ),
            WorkflowTransition(
                target=AgentType.EVOLUTION,
                conditions=[can_evolve],
                priority=50,
                description="Evolve top hypotheses"
            ),
            WorkflowTransition(
                target=AgentType.EXPERIMENT_DESIGN,
                conditions=[need_designs],
                priority=40,
                description="Design experiments for top hypotheses"
            ),
            WorkflowTransition(
                target=AgentType.META_REVIEW,
                conditions=[max_iterations],
                priority=30,
                description="Final meta-review"
            ),
            WorkflowTransition(
                target=AgentType.GENERATION,
                conditions=[can_iterate],
                priority=20,
                description="Start new iteration"
            ),
        ]

    def _has_unreviewed_hypotheses(self, state: CoScientistState) -> bool:
        """Check if there are unreviewed hypotheses."""
        reviewed_ids = {r.get("hypothesis_id") for r in state.hypothesis_reviews}
        unreviewed = [h for h in state.hypotheses if h.get("id") not in reviewed_ids]
        return len(unreviewed) > 0

    def _can_evolve(self, state: CoScientistState) -> bool:
        """Check if hypothesis evolution is possible."""
        if state.current_iteration >= state.max_iterations:
            return False

        evolved_this_iteration = [
            h for h in state.hypotheses
            if h.get("generation_iteration") == state.current_iteration
            and h.get("parent_hypothesis_id")
        ]
        return not evolved_this_iteration and len(state.top_hypotheses) > 0

    def _needs_experiment_designs(self, state: CoScientistState) -> bool:
        """Check if experiment designs are needed."""
        designed_ids = {d.get("hypothesis_id") for d in state.experiment_designs}
        need_designs = [
            hid for hid in state.top_hypotheses[:3]
            if hid not in designed_ids
        ]
        return len(need_designs) > 0

    def get_next_agent(self, state: CoScientistState) -> Optional[AgentType]:
        """Determine the next agent based on state and transition rules.

        Args:
            state: Current workflow state

        Returns:
            The next agent type to run, or None if workflow is complete
        """
        # Sort transitions by priority (highest first)
        sorted_transitions = sorted(
            self._transitions,
            key=lambda t: t.priority,
            reverse=True
        )

        for transition in sorted_transitions:
            # Check if all conditions are met
            all_conditions_met = all(
                condition.check(state)
                for condition in transition.conditions
            )

            if all_conditions_met:
                return transition.target

        # Default to meta-review if no transition matches
        return AgentType.META_REVIEW

    def add_transition(self, transition: WorkflowTransition) -> None:
        """Add a custom transition rule.

        Args:
            transition: The transition rule to add
        """
        self._transitions.append(transition)

    def remove_transition(self, target: AgentType) -> None:
        """Remove all transitions targeting a specific agent.

        Args:
            target: The agent type to remove transitions for
        """
        self._transitions = [
            t for t in self._transitions
            if t.target != target
        ]

    def get_transition_graph(self) -> dict[str, list[str]]:
        """Get a simplified view of the transition graph.

        Returns:
            Dictionary mapping transition descriptions to their targets
        """
        return {
            t.description or f"-> {t.target.value}": t.target.value
            for t in self._transitions
        }

    def _setup_parallel_groups(self):
        """Set up default parallel execution groups.

        These groups define agents that can run concurrently when their
        conditions are all met. This improves performance by running
        independent operations in parallel.
        """
        # Ranking and Proximity can run in parallel after Reflection
        # They both operate on hypotheses but don't have dependencies on each other
        self._parallel_groups = [
            ParallelAgentGroup(
                agents=[AgentType.RANKING, AgentType.PROXIMITY],
                condition=lambda s: (
                    # All hypotheses have been reviewed
                    not self._has_unreviewed_hypotheses(s)
                    # But we still need both ranking and proximity
                    and len(s.hypothesis_rankings) < len(s.hypotheses) - 1
                    and (not s.hypothesis_clusters or s.current_iteration > 1)
                ),
                description="Parallel ranking and proximity analysis"
            ),
        ]

    def get_parallel_agents(
        self,
        state: CoScientistState
    ) -> Optional[list[AgentType]]:
        """Get a list of agents that can run in parallel for the current state.

        This checks if any parallel group conditions are met and returns
        the group of agents that can run concurrently.

        Args:
            state: Current workflow state

        Returns:
            List of agents to run in parallel, or None if sequential execution
        """
        if not self._enable_parallel:
            return None

        for group in self._parallel_groups:
            # Check if the group condition is met
            if group.condition and group.condition(state):
                return group.agents

        return None

    @property
    def parallel_groups(self) -> list[ParallelAgentGroup]:
        """Get all configured parallel groups."""
        return self._parallel_groups.copy()

    def add_parallel_group(self, group: ParallelAgentGroup) -> None:
        """Add a custom parallel execution group.

        Args:
            group: The parallel group to add
        """
        self._parallel_groups.append(group)


# Default workflow configuration instance
_default_config: Optional[WorkflowConfiguration] = None


def get_workflow_config() -> WorkflowConfiguration:
    """Get the default workflow configuration instance."""
    global _default_config
    if _default_config is None:
        _default_config = WorkflowConfiguration()
    return _default_config


def set_workflow_config(config: WorkflowConfiguration) -> None:
    """Set a custom workflow configuration."""
    global _default_config
    _default_config = config

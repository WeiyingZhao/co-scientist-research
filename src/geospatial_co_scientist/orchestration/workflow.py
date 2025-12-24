"""Main LangGraph workflow for the Geospatial AI Co-Scientist."""

import logging
from typing import Any, Optional

from langgraph.graph import END, StateGraph

from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.research import ResearchGoal, ResearchOverview
from geospatial_co_scientist.models.state import AgentType, CoScientistState
from geospatial_co_scientist.orchestration.nodes import (
    evolution_node,
    experiment_design_node,
    generation_node,
    human_review_node,
    literature_search_node,
    meta_review_node,
    proximity_node,
    ranking_node,
    reflection_node,
    should_continue,
    supervisor_node,
)

logger = logging.getLogger(__name__)


def create_workflow_graph() -> StateGraph:
    """
    Create the LangGraph workflow for the Co-Scientist.

    The workflow follows this general pattern:
    1. Supervisor decides next action
    2. Execute appropriate agent
    3. Return to supervisor for next decision
    4. Repeat until done

    Returns:
        Compiled LangGraph StateGraph
    """
    # Create the graph with state schema
    workflow = StateGraph(dict)

    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("generation", generation_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("ranking", ranking_node)
    workflow.add_node("proximity", proximity_node)
    workflow.add_node("evolution", evolution_node)
    workflow.add_node("meta_review", meta_review_node)
    workflow.add_node("experiment_design", experiment_design_node)
    workflow.add_node("literature_search", literature_search_node)
    workflow.add_node("human_review", human_review_node)

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Add conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "generation": "generation",
            "reflection": "reflection",
            "ranking": "ranking",
            "proximity": "proximity",
            "evolution": "evolution",
            "meta_review": "meta_review",
            "experiment_design": "experiment_design",
            "literature_search": "literature_search",
            "human_review": "human_review",
            "end": END,
        }
    )

    # All agent nodes return to supervisor
    for node in ["generation", "reflection", "ranking", "proximity",
                 "evolution", "meta_review", "experiment_design",
                 "literature_search"]:
        workflow.add_edge(node, "supervisor")

    # Human review can continue or end
    workflow.add_conditional_edges(
        "human_review",
        lambda state: "end" if not state.get("should_continue", True) else "supervisor",
        {
            "supervisor": "supervisor",
            "end": END,
        }
    )

    return workflow


class GeospatialCoScientist:
    """
    Main interface for the Geospatial AI Co-Scientist.

    This class provides a high-level API for interacting with the
    multi-agent research system.

    Example:
        ```python
        scientist = GeospatialCoScientist()
        result = await scientist.research(
            "How can we detect urban heat islands using satellite imagery?"
        )
        print(result.to_markdown())
        ```
    """

    def __init__(self):
        self.settings = get_settings()
        self.workflow = create_workflow_graph()
        self.compiled_graph = self.workflow.compile()
        self._current_state: Optional[CoScientistState] = None

    async def research(
        self,
        question: str,
        domain: str = "general_gis",
        context: Optional[str] = None,
        constraints: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
        max_iterations: Optional[int] = None
    ) -> ResearchOverview:
        """
        Conduct research on a given question.

        This is the main entry point for using the Co-Scientist.

        Args:
            question: The research question or goal
            domain: Research domain (e.g., "remote_sensing", "urban_planning")
            context: Additional context for the research
            constraints: Specific constraints (e.g., "must use open data")
            keywords: Key terms related to the research
            max_iterations: Maximum generate-refine iterations

        Returns:
            ResearchOverview document with hypotheses and experiment designs
        """
        logger.info(f"Starting research: {question[:100]}...")

        # Create initial state
        goal = ResearchGoal(
            question=question,
            domain=domain,
            context=context,
            constraints=constraints or [],
            keywords=keywords or []
        )

        initial_state = CoScientistState(
            research_goal=goal.model_dump(),
            max_iterations=max_iterations or self.settings.max_iterations
        )

        self._current_state = initial_state

        # Run the workflow
        final_state = await self._run_workflow(initial_state.model_dump())

        # Extract and return the research overview
        overview_data = final_state.get("research_overview")
        if overview_data:
            return ResearchOverview(**overview_data)

        # If no overview was generated, create a basic one
        return self._create_basic_overview(final_state)

    async def _run_workflow(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        """Run the LangGraph workflow."""
        config = {"recursion_limit": 100}

        # Execute the graph
        final_state = None
        async for state in self.compiled_graph.astream(initial_state, config):
            # Update current state for monitoring
            for node_name, node_state in state.items():
                final_state = node_state
                logger.debug(f"Completed node: {node_name}")

        return final_state or initial_state

    def _create_basic_overview(self, state: dict[str, Any]) -> ResearchOverview:
        """Create a basic overview from state if meta-review wasn't run."""
        from geospatial_co_scientist.models.research import (
            ExperimentDesignSummary,
            HypothesisSummary,
            LiteratureSummary,
        )

        goal_data = state.get("research_goal", {})
        goal = ResearchGoal(
            id=goal_data.get("id", "unknown"),
            question=goal_data.get("question", "Unknown"),
            domain=goal_data.get("domain", "general_gis"),
            context=goal_data.get("context"),
            constraints=goal_data.get("constraints", []),
            keywords=goal_data.get("keywords", [])
        )

        lit_data = state.get("literature_summary", {})
        literature_summary = LiteratureSummary(
            goal_id=goal.id,
            summary=lit_data.get("summary", ""),
            key_themes=lit_data.get("key_themes", []),
            research_gaps=lit_data.get("research_gaps", [])
        )

        # Get top hypotheses
        hypotheses = state.get("hypotheses", [])
        sorted_hyps = sorted(
            hypotheses,
            key=lambda x: x.get("elo_score", 1000),
            reverse=True
        )[:3]

        hyp_summaries = [
            HypothesisSummary(
                id=h.get("id", ""),
                title=h.get("title", ""),
                statement=h.get("statement", ""),
                rationale=h.get("rationale", ""),
                novelty_score=0.5,
                feasibility_score=0.5
            )
            for h in sorted_hyps
        ]

        # Get experiment designs
        exp_summaries = [
            ExperimentDesignSummary(
                id=e.get("id", ""),
                title=e.get("title", ""),
                hypothesis_id=e.get("hypothesis_id", ""),
                objective=e.get("objective", ""),
                data_requirements=[],
                methodology_summary="",
                expected_outcomes=[]
            )
            for e in state.get("experiment_designs", [])
        ]

        return ResearchOverview(
            goal=goal,
            literature_summary=literature_summary,
            hypotheses=hyp_summaries,
            experiment_designs=exp_summaries,
            recommendations=["Review the generated hypotheses and select promising ones"],
            next_steps=["Design detailed experiments for top hypotheses"],
            iterations_completed=state.get("current_iteration", 1),
            total_hypotheses_generated=len(hypotheses)
        )

    async def step(self) -> CoScientistState:
        """
        Execute a single step of the workflow.

        Useful for interactive/debugging sessions.

        Returns:
            Updated state after one step
        """
        if not self._current_state:
            raise ValueError("No active research session. Call research() first.")

        state_dict = self._current_state.model_dump()

        # Run one iteration
        async for state in self.compiled_graph.astream(state_dict):
            for node_name, node_state in state.items():
                self._current_state = CoScientistState(**node_state)
                return self._current_state

        return self._current_state

    async def provide_feedback(self, feedback: str) -> CoScientistState:
        """
        Provide human feedback to the system.

        Args:
            feedback: The feedback text

        Returns:
            Updated state after processing feedback
        """
        if not self._current_state:
            raise ValueError("No active research session.")

        self._current_state.human_feedback = feedback
        self._current_state.awaiting_human_input = False

        return await self.step()

    def get_status(self) -> dict[str, Any]:
        """Get the current status of the research session."""
        if not self._current_state:
            return {"status": "no_session"}

        return self._current_state.to_summary()

    def get_hypotheses(self) -> list[dict[str, Any]]:
        """Get all generated hypotheses."""
        if not self._current_state:
            return []
        return self._current_state.hypotheses

    def get_top_hypotheses(self, n: int = 3) -> list[dict[str, Any]]:
        """Get the top N hypotheses by Elo score."""
        if not self._current_state:
            return []
        return self._current_state.get_top_hypotheses_data(n)

    def get_experiment_designs(self) -> list[dict[str, Any]]:
        """Get all experiment designs."""
        if not self._current_state:
            return []
        return self._current_state.experiment_designs


async def run_research_session(
    question: str,
    domain: str = "general_gis",
    **kwargs
) -> ResearchOverview:
    """
    Convenience function to run a research session.

    Args:
        question: Research question
        domain: Research domain
        **kwargs: Additional arguments passed to research()

    Returns:
        ResearchOverview with results
    """
    scientist = GeospatialCoScientist()
    return await scientist.research(question, domain, **kwargs)

"""Supervisor Agent for orchestrating the multi-agent workflow."""

import logging
from typing import Any, Optional

from geospatial_co_scientist.agents.base import BaseAgent
from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.research import LiteratureSummary, ResearchGoal
from geospatial_co_scientist.models.state import AgentType, CoScientistState
from geospatial_co_scientist.tools.literature_search import GeospatialLiteratureSearch

logger = logging.getLogger(__name__)


SUPERVISOR_SYSTEM_PROMPT = """You are a research supervisor coordinating a team of AI agents
working on geospatial science research. Your role is to:

1. Parse and understand user research goals
2. Coordinate the workflow of specialized agents
3. Make strategic decisions about when to iterate vs. finalize
4. Ensure quality and completeness of outputs
5. Manage human-in-the-loop checkpoints

You oversee these agents:
- Generation: Creates hypotheses
- Reflection: Reviews hypotheses
- Ranking: Prioritizes hypotheses
- Proximity: Analyzes hypothesis diversity
- Evolution: Refines hypotheses
- Meta-Review: Synthesizes feedback
- Experiment Design: Creates testing plans

Guide the process efficiently while ensuring high-quality scientific outputs."""


class SupervisorAgent(BaseAgent):
    """Supervisor agent that coordinates the multi-agent workflow."""

    agent_type = AgentType.SUPERVISOR
    default_model = "gpt-4-turbo-preview"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()
        self.literature_search = GeospatialLiteratureSearch()

    @property
    def system_prompt(self) -> str:
        return SUPERVISOR_SYSTEM_PROMPT

    async def process(self, state: CoScientistState) -> CoScientistState:
        """
        Main supervisor process - determines next action based on state.

        This is called by the LangGraph workflow to decide what to do next.
        """
        self.log_action("Supervisor evaluating state")

        # If no research goal, we need one
        if not state.research_goal:
            state.warnings.append("No research goal set. Waiting for user input.")
            state.awaiting_human_input = True
            return state

        # Determine next agent based on current state
        next_agent = self._determine_next_agent(state)
        state.next_agent = next_agent

        # Check for stopping conditions
        if self._should_stop(state):
            state.should_continue = False
            state.next_agent = AgentType.META_REVIEW

        # Log decision
        self.add_message_to_state(
            state,
            f"Next agent: {next_agent.value if next_agent else 'none'}",
            iteration=state.current_iteration
        )

        return state

    def _determine_next_agent(self, state: CoScientistState) -> Optional[AgentType]:
        """Determine which agent should run next based on state."""
        # Initial literature review if not done
        if not state.literature_summary:
            return AgentType.LITERATURE_SEARCH

        # Generate hypotheses if none exist
        if not state.hypotheses:
            return AgentType.GENERATION

        # Review hypotheses if unreviewed exist
        reviewed_ids = {r.get("hypothesis_id") for r in state.hypothesis_reviews}
        unreviewed = [h for h in state.hypotheses if h.get("id") not in reviewed_ids]
        if unreviewed:
            return AgentType.REFLECTION

        # Rank if reviews exist but not enough rankings
        if len(state.hypothesis_rankings) < len(state.hypotheses) - 1:
            return AgentType.RANKING

        # Proximity analysis if not done this iteration
        if not state.hypothesis_clusters or state.current_iteration > 1:
            # Check if we need fresh proximity analysis
            return AgentType.PROXIMITY

        # Evolution for top hypotheses
        if state.current_iteration < state.max_iterations:
            evolved_this_iteration = [
                h for h in state.hypotheses
                if h.get("generation_iteration") == state.current_iteration
                and h.get("parent_hypothesis_id")
            ]
            if not evolved_this_iteration and state.top_hypotheses:
                return AgentType.EVOLUTION

        # Experiment design for top hypotheses
        designed_ids = {d.get("hypothesis_id") for d in state.experiment_designs}
        need_designs = [hid for hid in state.top_hypotheses[:3] if hid not in designed_ids]
        if need_designs:
            return AgentType.EXPERIMENT_DESIGN

        # Meta-review periodically or at end
        if state.current_iteration >= state.max_iterations:
            return AgentType.META_REVIEW

        # Start new iteration
        if state.current_iteration < state.max_iterations:
            state.current_iteration += 1
            return AgentType.GENERATION

        return AgentType.META_REVIEW

    def _should_stop(self, state: CoScientistState) -> bool:
        """Determine if the workflow should stop."""
        # Max iterations reached
        if state.current_iteration >= state.max_iterations:
            return True

        # Convergence detected
        if state.should_stop_iterations():
            return True

        # Explicit stop (e.g., from human)
        if not state.should_continue:
            return True

        return False

    async def initialize_research(
        self,
        question: str,
        domain: str = "general_gis",
        context: Optional[str] = None,
        constraints: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None
    ) -> CoScientistState:
        """
        Initialize a new research session.

        Args:
            question: The research question
            domain: Research domain
            context: Additional context
            constraints: Research constraints
            keywords: Key terms

        Returns:
            Initialized state
        """
        self.log_action(f"Initializing research: {question[:100]}...")

        # Create research goal
        goal = ResearchGoal(
            question=question,
            domain=domain,
            context=context,
            constraints=constraints or [],
            keywords=keywords or []
        )

        # Create initial state
        state = CoScientistState(
            research_goal=goal.model_dump(),
            max_iterations=self.settings.max_iterations
        )

        # Perform initial literature search
        state = await self._perform_literature_review(state)

        self.add_message_to_state(
            state,
            "Research session initialized",
            goal=question[:100]
        )

        return state

    async def _perform_literature_review(
        self,
        state: CoScientistState
    ) -> CoScientistState:
        """Perform initial literature review."""
        self.log_action("Performing literature review")

        if not state.research_goal:
            return state

        query = state.research_goal.get("question", "")
        keywords = state.research_goal.get("keywords", [])

        # Enhance query with keywords
        if keywords:
            query = f"{query} {' '.join(keywords)}"

        try:
            # Search for papers
            results = await self.literature_search.search_geospatial_literature(
                query,
                limit=self.settings.search_results_limit
            )

            # Convert to references
            references = self.literature_search.to_literature_references(results)

            # Add to state
            for ref in references:
                state.literature_references.append(ref.model_dump())

            # Generate summary
            summary = await self._generate_literature_summary(
                state.research_goal.get("question", ""),
                references
            )
            state.literature_summary = summary.model_dump()

            self.log_action(f"Found {len(references)} relevant papers")

        except Exception as e:
            logger.error(f"Literature review failed: {e}")
            state.errors.append(f"Literature review failed: {str(e)}")

        return state

    async def _generate_literature_summary(
        self,
        question: str,
        references: list[Any]
    ) -> LiteratureSummary:
        """Generate a summary of the literature review."""
        # Prepare abstracts for summarization
        abstracts = []
        for ref in references[:10]:  # Limit to top 10
            if ref.abstract:
                abstracts.append(f"**{ref.title}** ({ref.year}): {ref.abstract[:500]}")

        prompt = f"""Summarize the following research papers relevant to the question:
"{question}"

Papers:
{chr(10).join(abstracts)}

Provide:
1. A 2-3 paragraph summary of the current state of research
2. 3-5 key themes
3. 2-3 identified research gaps
4. Common methodologies used

Format your response as:
SUMMARY:
[your summary]

KEY THEMES:
- theme 1
- theme 2
...

RESEARCH GAPS:
- gap 1
- gap 2
...

METHODOLOGIES:
- method 1
- method 2
..."""

        response = await self.invoke(prompt)

        # Parse response
        summary_text = ""
        themes = []
        gaps = []
        methodologies = []
        current_section = None

        for line in response.split("\n"):
            line = line.strip()
            if "SUMMARY" in line.upper():
                current_section = "summary"
            elif "KEY THEMES" in line.upper():
                current_section = "themes"
            elif "RESEARCH GAPS" in line.upper():
                current_section = "gaps"
            elif "METHODOLOGIES" in line.upper():
                current_section = "methods"
            elif line:
                if current_section == "summary" and not line.startswith("-"):
                    summary_text += line + " "
                elif current_section == "themes" and line.startswith("-"):
                    themes.append(line.lstrip("- "))
                elif current_section == "gaps" and line.startswith("-"):
                    gaps.append(line.lstrip("- "))
                elif current_section == "methods" and line.startswith("-"):
                    methodologies.append(line.lstrip("- "))

        return LiteratureSummary(
            goal_id=references[0].id if references else "unknown",
            total_papers_found=len(references),
            papers_reviewed=min(len(references), 10),
            summary=summary_text.strip(),
            key_themes=themes[:5],
            research_gaps=gaps[:3],
            methodologies_used=methodologies[:5]
        )

    async def handle_human_feedback(
        self,
        state: CoScientistState,
        feedback: str
    ) -> CoScientistState:
        """Process human feedback and update state."""
        self.log_action(f"Processing human feedback: {feedback[:100]}...")

        state.human_feedback = feedback
        state.awaiting_human_input = False

        # Parse feedback type
        feedback_lower = feedback.lower()

        if "stop" in feedback_lower or "done" in feedback_lower:
            state.should_continue = False
        elif "continue" in feedback_lower:
            state.should_continue = True
        elif "focus on" in feedback_lower:
            # Add as meta-feedback
            state.meta_feedback.append(f"User guidance: {feedback}")
        elif "drop" in feedback_lower or "remove" in feedback_lower:
            # Try to identify which hypothesis to drop
            state.meta_feedback.append(f"User requested removal: {feedback}")
        else:
            # General feedback
            state.meta_feedback.append(f"User feedback: {feedback}")

        self.add_message_to_state(
            state,
            "Processed human feedback",
            feedback=feedback[:100]
        )

        return state

    def get_status_summary(self, state: CoScientistState) -> dict[str, Any]:
        """Get a summary of the current state for display."""
        return {
            "session_id": state.session_id,
            "research_goal": state.research_goal.get("question", "Not set") if state.research_goal else "Not set",
            "iteration": f"{state.current_iteration}/{state.max_iterations}",
            "hypotheses": len(state.hypotheses),
            "reviews": len(state.hypothesis_reviews),
            "top_hypotheses": len(state.top_hypotheses),
            "experiment_designs": len(state.experiment_designs),
            "status": "completed" if state.research_overview else "in_progress",
            "awaiting_input": state.awaiting_human_input,
            "errors": len(state.errors),
        }

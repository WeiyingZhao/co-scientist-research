"""Meta-Review Agent for synthesizing feedback and compiling final outputs."""

import logging
from datetime import datetime
from typing import Any

from geospatial_co_scientist.agents.base import BaseAgent
from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.research import (
    ExperimentDesignSummary,
    HypothesisSummary,
    LiteratureSummary,
    ResearchGoal,
    ResearchOverview,
)
from geospatial_co_scientist.models.state import AgentType, CoScientistState

logger = logging.getLogger(__name__)


META_REVIEW_SYSTEM_PROMPT = """You are a senior research coordinator and scientific writer.
Your role is to synthesize outputs from multiple research agents into coherent,
actionable research plans and reports.

You excel at:
1. Identifying patterns across multiple reviews and feedback
2. Extracting key insights and recommendations
3. Writing clear, structured scientific documents
4. Providing strategic guidance for research direction
5. Ensuring completeness and consistency of outputs

Your output should be professional, well-organized, and suitable for academic audiences."""


SYNTHESIS_TEMPLATE = """Analyze the research session and provide strategic guidance.

## Research Goal
{research_goal}

## Session Statistics
- Hypotheses generated: {num_hypotheses}
- Reviews completed: {num_reviews}
- Rankings performed: {num_rankings}
- Current iteration: {iteration}/{max_iterations}

## Review Feedback Summary
**Common Strengths:**
{common_strengths}

**Common Weaknesses:**
{common_weaknesses}

## Top Hypotheses (by Elo score)
{top_hypotheses}

## Cluster Analysis
{cluster_info}

Based on this analysis:
1. What patterns do you observe across reviews?
2. What areas are underexplored?
3. What guidance should be given to the Generation agent for the next iteration?
4. Should iterations continue or are results converging?

Provide strategic guidance in 3-5 bullet points."""


FINAL_REPORT_TEMPLATE = """Compile a comprehensive research overview document.

## Research Goal
{research_goal}

## Literature Summary
{literature_summary}

## Top Hypotheses (Final Selection)
{top_hypotheses}

## Experiment Designs
{experiment_designs}

## Session Insights
{session_insights}

Generate a polished research overview document with:
1. Executive summary (2-3 paragraphs)
2. Key recommendations
3. Suggested next steps for the researcher

Write in academic style, suitable for a research proposal."""


class MetaReviewAgent(BaseAgent):
    """Agent responsible for meta-level synthesis and final output compilation."""

    agent_type = AgentType.META_REVIEW
    default_model = "gpt-4-turbo-preview"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()

    @property
    def system_prompt(self) -> str:
        return META_REVIEW_SYSTEM_PROMPT

    async def process(self, state: CoScientistState) -> CoScientistState:
        """Perform meta-review and provide guidance."""
        self.log_action("Starting meta-review synthesis")

        try:
            # Extract patterns from reviews
            patterns = self._extract_review_patterns(state)

            # Generate strategic guidance
            guidance = await self._generate_guidance(state, patterns)
            state.meta_feedback.extend(guidance)

            # Check if final compilation is needed
            if self._should_compile_final(state):
                overview = await self._compile_final_overview(state)
                state.research_overview = overview

            self.add_message_to_state(
                state,
                f"Meta-review complete. Generated {len(guidance)} guidance points.",
                guidance_count=len(guidance)
            )

        except Exception as e:
            logger.error(f"Meta-review failed: {e}")
            state.errors.append(f"Meta-review failed: {str(e)}")

        return state

    def _extract_review_patterns(self, state: CoScientistState) -> dict[str, Any]:
        """Extract patterns from hypothesis reviews."""
        patterns = {
            "common_strengths": [],
            "common_weaknesses": [],
            "score_distribution": {},
            "recommendation_counts": {"proceed": 0, "refine": 0, "drop": 0}
        }

        strength_counts: dict[str, int] = {}
        weakness_counts: dict[str, int] = {}

        for review in state.hypothesis_reviews:
            # Count recommendations
            rec = review.get("recommendation", "refine")
            patterns["recommendation_counts"][rec] = (
                patterns["recommendation_counts"].get(rec, 0) + 1
            )

            # Collect strengths and weaknesses
            for strength in review.get("strengths", []):
                strength_counts[strength] = strength_counts.get(strength, 0) + 1

            for weakness in review.get("weaknesses", []):
                weakness_counts[weakness] = weakness_counts.get(weakness, 0) + 1

        # Get most common
        patterns["common_strengths"] = sorted(
            strength_counts.keys(),
            key=lambda x: strength_counts[x],
            reverse=True
        )[:5]

        patterns["common_weaknesses"] = sorted(
            weakness_counts.keys(),
            key=lambda x: weakness_counts[x],
            reverse=True
        )[:5]

        return patterns

    async def _generate_guidance(
        self,
        state: CoScientistState,
        patterns: dict[str, Any]
    ) -> list[str]:
        """Generate strategic guidance for next iteration."""
        research_goal = ""
        if state.research_goal:
            research_goal = state.research_goal.get("question", "Not specified")

        top_hyps = state.get_top_hypotheses_data(3)
        top_hyps_text = "\n".join([
            f"- {h.get('title', 'Untitled')} (Elo: {h.get('elo_score', 1000):.0f})"
            for h in top_hyps
        ])

        cluster_info = "No clusters identified"
        if state.hypothesis_clusters:
            cluster_info = f"{len(state.hypothesis_clusters)} clusters found"

        prompt = SYNTHESIS_TEMPLATE.format(
            research_goal=research_goal,
            num_hypotheses=len(state.hypotheses),
            num_reviews=len(state.hypothesis_reviews),
            num_rankings=len(state.hypothesis_rankings),
            iteration=state.current_iteration,
            max_iterations=state.max_iterations,
            common_strengths="\n".join(f"- {s}" for s in patterns["common_strengths"]) or "None identified",
            common_weaknesses="\n".join(f"- {w}" for w in patterns["common_weaknesses"]) or "None identified",
            top_hypotheses=top_hyps_text or "None yet",
            cluster_info=cluster_info
        )

        response = await self.invoke(prompt, state)

        # Parse guidance from response
        guidance = []
        for line in response.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•") or line.startswith("*")):
                guidance.append(line.lstrip("-•* "))

        return guidance[:5]  # Limit to 5 points

    def _should_compile_final(self, state: CoScientistState) -> bool:
        """Determine if final report should be compiled."""
        # Compile if at max iterations
        if state.current_iteration >= state.max_iterations:
            return True

        # Compile if explicitly requested (would be set by supervisor)
        if not state.should_continue:
            return True

        return False

    async def _compile_final_overview(
        self,
        state: CoScientistState
    ) -> dict[str, Any]:
        """Compile the final research overview document."""
        self.log_action("Compiling final research overview")

        # Get research goal
        goal_data = state.research_goal or {}
        goal = ResearchGoal(
            id=goal_data.get("id", "unknown"),
            question=goal_data.get("question", "Not specified"),
            domain=goal_data.get("domain", "general_gis"),
            context=goal_data.get("context"),
            constraints=goal_data.get("constraints", []),
            keywords=goal_data.get("keywords", [])
        )

        # Get literature summary
        lit_data = state.literature_summary or {}
        literature_summary = LiteratureSummary(
            goal_id=goal.id,
            total_papers_found=lit_data.get("total_papers_found", 0),
            papers_reviewed=lit_data.get("papers_reviewed", 0),
            references=[],  # Would populate from state.literature_references
            summary=lit_data.get("summary", ""),
            key_themes=lit_data.get("key_themes", []),
            research_gaps=lit_data.get("research_gaps", []),
            methodologies_used=lit_data.get("methodologies_used", []),
            datasets_mentioned=lit_data.get("datasets_mentioned", [])
        )

        # Get top hypotheses
        top_hyps_data = state.get_top_hypotheses_data(3)
        hypotheses_summaries = []
        for h in top_hyps_data:
            # Get review for this hypothesis
            review = self._get_best_review(state, h.get("id", ""))

            summary = HypothesisSummary(
                id=h.get("id", ""),
                title=h.get("title", "Untitled"),
                statement=h.get("statement", ""),
                rationale=h.get("rationale", ""),
                novelty_score=review.get("scores", {}).get("novelty", 0.5) if review else 0.5,
                feasibility_score=review.get("scores", {}).get("feasibility", 0.5) if review else 0.5,
                supporting_references=[]
            )
            hypotheses_summaries.append(summary)

        # Get experiment designs
        experiment_summaries = []
        for exp in state.experiment_designs:
            summary = ExperimentDesignSummary(
                id=exp.get("id", ""),
                title=exp.get("title", "Untitled"),
                hypothesis_id=exp.get("hypothesis_id", ""),
                objective=exp.get("objective", ""),
                data_requirements=[
                    d.get("name", "") for d in exp.get("data_requirements", [])
                ],
                methodology_summary=exp.get("methodology", {}).get("description", ""),
                expected_outcomes=exp.get("expected_outcomes", [])
            )
            experiment_summaries.append(summary)

        # Generate recommendations using LLM
        recommendations, next_steps = await self._generate_recommendations(state)

        # Create overview
        overview = ResearchOverview(
            goal=goal,
            literature_summary=literature_summary,
            hypotheses=hypotheses_summaries,
            experiment_designs=experiment_summaries,
            recommendations=recommendations,
            next_steps=next_steps,
            iterations_completed=state.current_iteration,
            total_hypotheses_generated=len(state.hypotheses)
        )

        return overview.model_dump()

    def _get_best_review(
        self,
        state: CoScientistState,
        hypothesis_id: str
    ) -> dict[str, Any]:
        """Get the best (most recent full) review for a hypothesis."""
        reviews = [
            r for r in state.hypothesis_reviews
            if r.get("hypothesis_id") == hypothesis_id
        ]

        if not reviews:
            return {}

        # Prefer full reviews over initial reviews
        full_reviews = [r for r in reviews if not r.get("is_initial_review", True)]
        if full_reviews:
            return full_reviews[-1]

        return reviews[-1]

    async def _generate_recommendations(
        self,
        state: CoScientistState
    ) -> tuple[list[str], list[str]]:
        """Generate final recommendations and next steps."""
        top_hyps = state.get_top_hypotheses_data(3)
        hyps_text = "\n".join([
            f"- {h.get('title', '')}: {h.get('statement', '')[:200]}"
            for h in top_hyps
        ])

        prompt = f"""Based on the research session with {len(state.hypotheses)} hypotheses generated
and {len(state.hypothesis_reviews)} reviews completed, provide:

Top hypotheses:
{hyps_text}

1. 3-5 key recommendations for the researcher
2. 3-5 concrete next steps to pursue

Format:
RECOMMENDATIONS:
- recommendation 1
- recommendation 2
...

NEXT STEPS:
1. step 1
2. step 2
..."""

        response = await self.invoke(prompt, state)

        recommendations = []
        next_steps = []
        current_section = None

        for line in response.split("\n"):
            line = line.strip()
            if "RECOMMENDATIONS" in line.upper():
                current_section = "rec"
            elif "NEXT STEPS" in line.upper():
                current_section = "steps"
            elif line.startswith(("-", "•", "*")) and current_section == "rec":
                recommendations.append(line.lstrip("-•* "))
            elif (line[0:1].isdigit() or line.startswith(("-", "•"))) and current_section == "steps":
                step = line.lstrip("0123456789.-•* ")
                if step:
                    next_steps.append(step)

        return recommendations[:5], next_steps[:5]

    async def assess_convergence(self, state: CoScientistState) -> bool:
        """Assess whether hypothesis quality has converged."""
        # Check Elo score improvement
        if len(state.hypothesis_rankings) < 5:
            return False

        # Get recent score changes
        recent_rankings = state.hypothesis_rankings[-10:]
        avg_delta = sum(r.get("score_delta", 32) for r in recent_rankings) / len(recent_rankings)

        # If average delta is very small, we've converged
        if avg_delta < 5:
            return True

        # Check if top hypotheses have stabilized
        # (This would require tracking top hypotheses over iterations)

        return False

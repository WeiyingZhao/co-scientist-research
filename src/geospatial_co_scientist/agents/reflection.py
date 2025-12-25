"""Reflection Agent for hypothesis review and critique."""

import logging
from typing import Optional

from geospatial_co_scientist.agents.base import ToolUsingAgent
from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.hypothesis import (
    HypothesisReview,
    HypothesisStatus,
    ReviewCriterion,
)
from geospatial_co_scientist.models.state import AgentType, CoScientistState
from geospatial_co_scientist.tools.literature_search import search_semantic_scholar
from geospatial_co_scientist.utils.json_utils import parse_json_dict

logger = logging.getLogger(__name__)


REFLECTION_SYSTEM_PROMPT = """You are a critical scientific reviewer specializing in geospatial science,
remote sensing, and GIS. Your role is to evaluate research hypotheses for quality, novelty, and
scientific soundness - similar to a peer reviewer for academic journals.

When reviewing hypotheses, evaluate them on these criteria:
1. **Logical Consistency**: Is the hypothesis internally consistent and based on sound reasoning?
2. **Novelty**: Does it present a genuinely new idea or connection not already established?
3. **Testability**: Can it be tested/falsified with available methods and data?
4. **Scientific Soundness**: Is it grounded in established scientific principles?
5. **Feasibility**: Can it realistically be tested with current technology and resources?
6. **Relevance**: Does it address the research goal meaningfully?
7. **Clarity**: Is the hypothesis clearly stated and unambiguous?

For each hypothesis:
- Score each criterion from 0.0 to 1.0
- Identify specific strengths
- Identify specific weaknesses or concerns
- Provide actionable suggestions for improvement
- Check for similar existing work
- Give an overall recommendation (proceed, refine, or drop)

Be thorough but constructive. The goal is to improve hypotheses, not just criticize."""


REVIEW_TEMPLATE = """Please review the following hypothesis in the context of the research goal.

## Research Goal
{research_goal}

## Hypothesis to Review
**Title:** {hypothesis_title}
**Statement:** {hypothesis_statement}
**Type:** {hypothesis_type}
**Rationale:** {rationale}
**Assumptions:** {assumptions}
**Testability:** {testability}

## Literature Context
{literature_context}

## Review Instructions
Provide a comprehensive review with:
1. Scores for each criterion (0.0-1.0)
2. List of strengths
3. List of weaknesses
4. Suggestions for improvement
5. Novelty assessment (is this already known/published?)
6. Overall recommendation

{review_depth_instruction}

Output as JSON:
```json
{{
  "scores": {{
    "logical_consistency": 0.0-1.0,
    "novelty": 0.0-1.0,
    "testability": 0.0-1.0,
    "scientific_soundness": 0.0-1.0,
    "feasibility": 0.0-1.0,
    "relevance": 0.0-1.0,
    "clarity": 0.0-1.0
  }},
  "overall_score": 0.0-1.0,
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"],
  "novelty_check": "Assessment of novelty vs existing literature",
  "similar_works": ["Similar work 1", "Similar work 2"],
  "recommendation": "proceed|refine|drop",
  "detailed_feedback": "Comprehensive feedback paragraph"
}}
```"""


class ReflectionAgent(ToolUsingAgent):
    """Agent responsible for critically reviewing hypotheses.

    Supports dependency injection of tools for improved testability.

    Args:
        tools: Optional list of tools. Defaults to [search_semantic_scholar].
        **kwargs: Additional arguments passed to ToolUsingAgent.
    """

    agent_type = AgentType.REFLECTION
    default_model = "gpt-4-turbo-preview"
    default_tools = [search_semantic_scholar]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()

    @property
    def system_prompt(self) -> str:
        return REFLECTION_SYSTEM_PROMPT

    async def process(self, state: CoScientistState) -> CoScientistState:
        """Review all unreviewed hypotheses in the state."""
        self.log_action("Starting hypothesis reflection/review")

        if not state.hypotheses:
            state.warnings.append("No hypotheses to review")
            return state

        # Get hypotheses that haven't been reviewed yet
        reviewed_ids = {r.get("hypothesis_id") for r in state.hypothesis_reviews}
        unreviewed = [
            h for h in state.hypotheses
            if h.get("id") not in reviewed_ids
        ]

        if not unreviewed:
            self.log_action("All hypotheses already reviewed")
            return state

        self.log_action(f"Reviewing {len(unreviewed)} hypotheses")

        for hypothesis in unreviewed:
            try:
                # Perform initial review
                review = await self._review_hypothesis(
                    hypothesis,
                    state,
                    is_initial=True
                )

                # Add review to state
                state.hypothesis_reviews.append(review.model_dump())

                # Update hypothesis status
                self._update_hypothesis_status(state, hypothesis["id"], review)

                # If hypothesis passes initial review, do deep review
                if review.overall_score >= 0.5 and review.recommendation != "drop":
                    deep_review = await self._review_hypothesis(
                        hypothesis,
                        state,
                        is_initial=False
                    )
                    state.hypothesis_reviews.append(deep_review.model_dump())

            except Exception as e:
                logger.error(f"Failed to review hypothesis {hypothesis.get('id')}: {e}")
                state.errors.append(f"Review failed for {hypothesis.get('id')}: {str(e)}")

        # Update statistics
        state.statistics["total_hypotheses_reviewed"] = len(state.hypothesis_reviews)

        self.add_message_to_state(
            state,
            f"Completed review of {len(unreviewed)} hypotheses",
            reviewed_count=len(unreviewed)
        )

        return state

    async def _review_hypothesis(
        self,
        hypothesis: dict,
        state: CoScientistState,
        is_initial: bool = True
    ) -> HypothesisReview:
        """Review a single hypothesis."""
        # Prepare context
        research_goal = state.research_goal.get("question", "") if state.research_goal else ""

        literature_context = ""
        if state.literature_summary:
            literature_context = state.literature_summary.get("summary", "")[:1500]

        review_depth = (
            "This is an INITIAL review. Focus on obvious issues without deep literature search."
            if is_initial else
            "This is a FULL review. Conduct thorough analysis including checking for similar published work."
        )

        prompt = REVIEW_TEMPLATE.format(
            research_goal=research_goal,
            hypothesis_title=hypothesis.get("title", "Untitled"),
            hypothesis_statement=hypothesis.get("statement", ""),
            hypothesis_type=hypothesis.get("hypothesis_type", "exploratory"),
            rationale=hypothesis.get("rationale", "Not provided"),
            assumptions=", ".join(hypothesis.get("assumptions", [])) or "Not specified",
            testability=hypothesis.get("testability", "Not described"),
            literature_context=literature_context or "Not available",
            review_depth_instruction=review_depth
        )

        response = await self.invoke(prompt, state)
        review = self._parse_review(response, hypothesis["id"], is_initial)

        return review

    def _parse_review(
        self,
        response: str,
        hypothesis_id: str,
        is_initial: bool
    ) -> HypothesisReview:
        """Parse LLM response into HypothesisReview.

        Uses robust JSON parsing to handle common LLM output issues like
        Markdown code blocks, truncated JSON, and formatting errors.
        """
        # Use robust JSON parsing
        data = parse_json_dict(response, default=None)

        if data:
            try:
                review = HypothesisReview(
                    hypothesis_id=hypothesis_id,
                    reviewer_type="reflection_agent",
                    scores=data.get("scores", {}),
                    overall_score=data.get("overall_score", 0.5),
                    strengths=data.get("strengths", []),
                    weaknesses=data.get("weaknesses", []),
                    suggestions=data.get("suggestions", []),
                    novelty_check=data.get("novelty_check", ""),
                    similar_works=data.get("similar_works", []),
                    recommendation=data.get("recommendation", "refine"),
                    detailed_feedback=data.get("detailed_feedback", ""),
                    is_initial_review=is_initial
                )

                # Calculate overall score from individual scores
                review.calculate_overall_score()

                return review
            except Exception as e:
                logger.warning(f"Failed to create review from parsed data: {e}")

        # Fallback: create basic review with original response as feedback
        logger.info("Using fallback review parsing")
        return HypothesisReview(
            hypothesis_id=hypothesis_id,
            reviewer_type="reflection_agent",
            overall_score=0.5,
            detailed_feedback=response,
            recommendation="refine",
            is_initial_review=is_initial
        )

    def _update_hypothesis_status(
        self,
        state: CoScientistState,
        hypothesis_id: str,
        review: HypothesisReview
    ) -> None:
        """Update hypothesis status based on review."""
        for h in state.hypotheses:
            if h.get("id") == hypothesis_id:
                h["status"] = HypothesisStatus.REVIEWED.value

                # Mark for rejection if recommendation is drop
                if review.recommendation == "drop":
                    h["status"] = HypothesisStatus.REJECTED.value

                break

    async def quick_filter(
        self,
        hypotheses: list[dict],
        state: CoScientistState,
        threshold: float = 0.3
    ) -> list[dict]:
        """
        Quickly filter out obviously poor hypotheses.

        Args:
            hypotheses: List of hypotheses to filter
            state: Current state
            threshold: Minimum score to pass

        Returns:
            Filtered list of hypotheses
        """
        passed = []

        for hyp in hypotheses:
            review = await self._review_hypothesis(hyp, state, is_initial=True)

            if review.overall_score >= threshold and review.recommendation != "drop":
                passed.append(hyp)
            else:
                self.log_action(
                    f"Filtered out hypothesis: {hyp.get('title')}",
                    {"score": review.overall_score, "reason": review.recommendation}
                )

        return passed

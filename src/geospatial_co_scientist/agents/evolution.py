"""Evolution Agent for hypothesis refinement and improvement."""

import json
import logging
from typing import Optional

from geospatial_co_scientist.agents.base import BaseAgent
from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.hypothesis import (
    Hypothesis,
    HypothesisEvolution,
    HypothesisStatus,
)
from geospatial_co_scientist.models.state import AgentType, CoScientistState

logger = logging.getLogger(__name__)


EVOLUTION_SYSTEM_PROMPT = """You are a scientific research advisor specializing in geospatial science.
Your role is to evolve and refine research hypotheses, making them stronger, more testable,
and more likely to lead to significant discoveries.

Strategies for hypothesis evolution:
1. **Incorporate Feedback**: Address specific weaknesses identified in reviews
2. **Combine Ideas**: Merge complementary hypotheses into stronger ones
3. **Simplify**: Remove unnecessary complexity while preserving core insights
4. **Expand**: Add depth or breadth where appropriate
5. **Analogical Transfer**: Apply successful patterns from one domain to another
6. **Edge Case Exploration**: Test boundaries and limits of the hypothesis

When evolving a hypothesis:
- Preserve the core insight that made it promising
- Address all identified weaknesses
- Ensure the result is still testable
- Maintain or improve novelty
- Keep the statement clear and specific"""


EVOLUTION_TEMPLATE = """Evolve the following hypothesis based on feedback and context.

## Original Hypothesis
**Title:** {title}
**Statement:** {statement}
**Type:** {hypothesis_type}
**Rationale:** {rationale}
**Current Elo Score:** {elo_score}

## Review Feedback
**Strengths:** {strengths}
**Weaknesses:** {weaknesses}
**Suggestions:** {suggestions}

## Meta-Level Feedback
{meta_feedback}

## Similar Hypotheses (for potential combination)
{similar_hypotheses}

## Evolution Strategy
Apply one or more of these strategies:
1. Address the weaknesses while preserving strengths
2. Consider combining with similar hypotheses if beneficial
3. Simplify if overly complex
4. Expand if too narrow

Generate an evolved version of this hypothesis.

Output as JSON:
```json
{{
  "title": "Improved title",
  "statement": "Refined hypothesis statement",
  "hypothesis_type": "type",
  "rationale": "Updated rationale explaining improvements",
  "assumptions": ["assumption1", "assumption2"],
  "variables": {{
    "independent": "description",
    "dependent": "description",
    "control": "description"
  }},
  "testability": "How to test",
  "evolution_type": "refinement|merge|simplification|expansion|analog",
  "changes_made": ["change1", "change2"],
  "feedback_addressed": ["feedback1", "feedback2"]
}}
```"""


class EvolutionAgent(BaseAgent):
    """Agent responsible for evolving and refining hypotheses."""

    agent_type = AgentType.EVOLUTION
    default_model = "gpt-4-turbo-preview"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()

    @property
    def system_prompt(self) -> str:
        return EVOLUTION_SYSTEM_PROMPT

    async def process(self, state: CoScientistState) -> CoScientistState:
        """Evolve top hypotheses based on feedback."""
        self.log_action("Starting hypothesis evolution")

        # Get top hypotheses to evolve
        top_ids = state.top_hypotheses[:self.settings.top_hypotheses_to_evolve]

        if not top_ids:
            # Fallback: evolve highest scored hypotheses
            sorted_hyps = sorted(
                state.hypotheses,
                key=lambda x: x.get("elo_score", 1000),
                reverse=True
            )
            top_ids = [h["id"] for h in sorted_hyps[:self.settings.top_hypotheses_to_evolve]]

        if not top_ids:
            state.warnings.append("No hypotheses to evolve")
            return state

        evolved_count = 0

        for hyp_id in top_ids:
            hypothesis = state.get_hypothesis_by_id(hyp_id)
            if not hypothesis:
                continue

            try:
                evolved = await self._evolve_hypothesis(hypothesis, state)
                if evolved:
                    state.hypotheses.append(evolved.model_dump())
                    evolved_count += 1

            except Exception as e:
                logger.error(f"Failed to evolve hypothesis {hyp_id}: {e}")
                state.errors.append(f"Evolution failed for {hyp_id}: {str(e)}")

        # Update statistics
        state.statistics["total_evolutions"] = state.statistics.get("total_evolutions", 0) + evolved_count

        self.add_message_to_state(
            state,
            f"Evolved {evolved_count} hypotheses",
            evolved_count=evolved_count
        )

        return state

    async def _evolve_hypothesis(
        self,
        hypothesis: dict,
        state: CoScientistState
    ) -> Optional[Hypothesis]:
        """Evolve a single hypothesis."""
        # Get review feedback
        reviews = [
            r for r in state.hypothesis_reviews
            if r.get("hypothesis_id") == hypothesis["id"]
        ]

        strengths = []
        weaknesses = []
        suggestions = []

        for review in reviews:
            strengths.extend(review.get("strengths", []))
            weaknesses.extend(review.get("weaknesses", []))
            suggestions.extend(review.get("suggestions", []))

        # Get similar hypotheses from clusters
        similar_hyps = self._get_similar_hypotheses(hypothesis["id"], state)

        # Get meta feedback
        meta_feedback = "\n".join(state.meta_feedback[-5:]) if state.meta_feedback else "None"

        prompt = EVOLUTION_TEMPLATE.format(
            title=hypothesis.get("title", "Untitled"),
            statement=hypothesis.get("statement", ""),
            hypothesis_type=hypothesis.get("hypothesis_type", "exploratory"),
            rationale=hypothesis.get("rationale", ""),
            elo_score=hypothesis.get("elo_score", 1000),
            strengths="\n".join(f"- {s}" for s in strengths) or "None identified",
            weaknesses="\n".join(f"- {w}" for w in weaknesses) or "None identified",
            suggestions="\n".join(f"- {s}" for s in suggestions) or "None provided",
            meta_feedback=meta_feedback,
            similar_hypotheses=self._format_similar_hypotheses(similar_hyps)
        )

        response = await self.invoke(prompt, state)
        evolved = self._parse_evolved_hypothesis(response, hypothesis, state)

        return evolved

    def _get_similar_hypotheses(
        self,
        hypothesis_id: str,
        state: CoScientistState
    ) -> list[dict]:
        """Get hypotheses similar to the given one from clusters."""
        similar = []

        for cluster in state.hypothesis_clusters:
            if hypothesis_id in cluster.get("hypothesis_ids", []):
                for other_id in cluster["hypothesis_ids"]:
                    if other_id != hypothesis_id:
                        other = state.get_hypothesis_by_id(other_id)
                        if other:
                            similar.append(other)

        return similar[:3]  # Limit to 3 similar hypotheses

    def _format_similar_hypotheses(self, hypotheses: list[dict]) -> str:
        """Format similar hypotheses for the prompt."""
        if not hypotheses:
            return "None found"

        parts = []
        for h in hypotheses:
            parts.append(f"- **{h.get('title', 'Untitled')}**: {h.get('statement', '')[:200]}")

        return "\n".join(parts)

    def _parse_evolved_hypothesis(
        self,
        response: str,
        original: dict,
        state: CoScientistState
    ) -> Optional[Hypothesis]:
        """Parse the evolved hypothesis from LLM response."""
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)

                evolved = Hypothesis(
                    goal_id=original.get("goal_id", "unknown"),
                    title=data.get("title", original.get("title", "")),
                    statement=data.get("statement", ""),
                    hypothesis_type=data.get("hypothesis_type", "exploratory"),
                    rationale=data.get("rationale", ""),
                    assumptions=data.get("assumptions", []),
                    variables=data.get("variables", {}),
                    testability=data.get("testability", ""),
                    status=HypothesisStatus.EVOLVED,
                    elo_score=original.get("elo_score", 1000),  # Inherit parent score
                    generation_iteration=state.current_iteration,
                    parent_hypothesis_id=original["id"]
                )

                # Record evolution
                evolution = HypothesisEvolution(
                    original_hypothesis_id=original["id"],
                    evolved_hypothesis_id=evolved.id,
                    evolution_type=data.get("evolution_type", "refinement"),
                    changes_made=data.get("changes_made", []),
                    feedback_incorporated=data.get("feedback_addressed", []),
                    rationale=data.get("rationale", "")
                )

                self.log_action(
                    f"Evolved hypothesis: {original.get('title')} -> {evolved.title}",
                    {"evolution_type": evolution.evolution_type}
                )

                return evolved

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse evolved hypothesis JSON: {e}")

        return None

    async def merge_hypotheses(
        self,
        hyp_ids: list[str],
        state: CoScientistState
    ) -> Optional[Hypothesis]:
        """Merge multiple hypotheses into one."""
        hypotheses = [
            state.get_hypothesis_by_id(hid)
            for hid in hyp_ids
            if state.get_hypothesis_by_id(hid)
        ]

        if len(hypotheses) < 2:
            return None

        hyp_texts = "\n\n".join([
            f"**{h.get('title')}**\n{h.get('statement')}\nRationale: {h.get('rationale')}"
            for h in hypotheses
        ])

        prompt = f"""Merge these related hypotheses into a single, stronger hypothesis:

{hyp_texts}

Create a unified hypothesis that:
1. Captures the key insights from all inputs
2. Is more comprehensive than any individual hypothesis
3. Remains testable and clear

Output as JSON with the same structure as the evolution template."""

        response = await self.invoke(prompt, state)

        # Use first hypothesis as "original" for parsing
        merged = self._parse_evolved_hypothesis(response, hypotheses[0], state)

        if merged:
            merged.parent_hypothesis_id = None  # Multiple parents

        return merged

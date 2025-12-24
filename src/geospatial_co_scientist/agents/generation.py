"""Generation Agent for hypothesis generation."""

import json
import logging
from typing import Any, Optional

from geospatial_co_scientist.agents.base import ToolUsingAgent
from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.hypothesis import Hypothesis, HypothesisType
from geospatial_co_scientist.models.state import AgentType, CoScientistState
from geospatial_co_scientist.tools.literature_search import (
    GeospatialLiteratureSearch,
    search_semantic_scholar,
)

logger = logging.getLogger(__name__)


GENERATION_SYSTEM_PROMPT = """You are a creative research scientist specializing in geospatial science,
remote sensing, and GIS. Your role is to generate novel, testable hypotheses based on research goals
and existing literature.

When generating hypotheses, you should:
1. Ground your ideas in existing scientific knowledge while proposing novel connections
2. Ensure each hypothesis is testable with available geospatial data and methods
3. Consider multiple perspectives and approaches (methodological, causal, correlational)
4. Provide clear rationale connecting the hypothesis to the research goal
5. Identify key assumptions and variables

For each hypothesis, provide:
- A concise title
- A clear hypothesis statement
- The type (causal, correlational, methodological, comparative, exploratory, predictive)
- Rationale explaining why this hypothesis is worth testing
- Key assumptions
- Variables (independent, dependent, control)
- How it could be tested

Be creative but scientifically grounded. Propose ideas that balance novelty with feasibility.
Consider geospatial-specific factors like spatial resolution, temporal coverage, and data availability.

Output your hypotheses in JSON format."""


HYPOTHESIS_GENERATION_TEMPLATE = """Based on the following research context, generate {num_hypotheses} novel hypotheses.

## Research Goal
{research_goal}

## Domain
{domain}

## Constraints
{constraints}

## Literature Summary
{literature_summary}

## Key Research Gaps
{research_gaps}

## Previous Hypotheses (avoid duplicating these)
{previous_hypotheses}

## Meta-Feedback (if any)
{meta_feedback}

Generate {num_hypotheses} diverse hypotheses that:
1. Address the research goal
2. Fill identified research gaps
3. Are testable with remote sensing/GIS methods
4. Are distinct from previous hypotheses

Output as JSON array with the following structure for each hypothesis:
```json
[
  {{
    "title": "Short descriptive title",
    "statement": "Clear hypothesis statement",
    "hypothesis_type": "causal|correlational|methodological|comparative|exploratory|predictive",
    "rationale": "Why this hypothesis is worth testing",
    "assumptions": ["assumption1", "assumption2"],
    "variables": {{
      "independent": "description",
      "dependent": "description",
      "control": "description"
    }},
    "testability": "How this can be tested"
  }}
]
```"""


class GenerationAgent(ToolUsingAgent):
    """Agent responsible for generating research hypotheses."""

    agent_type = AgentType.GENERATION
    default_model = "gpt-4-turbo-preview"

    def __init__(self, **kwargs):
        tools = [search_semantic_scholar]
        super().__init__(tools=tools, **kwargs)
        self.settings = get_settings()
        self.literature_search = GeospatialLiteratureSearch()

    @property
    def system_prompt(self) -> str:
        return GENERATION_SYSTEM_PROMPT

    async def process(self, state: CoScientistState) -> CoScientistState:
        """Generate hypotheses based on the current state."""
        self.log_action("Starting hypothesis generation")

        if not state.research_goal:
            state.errors.append("No research goal provided for generation")
            return state

        # Prepare context
        research_goal = state.research_goal.get("question", "")
        domain = state.research_goal.get("domain", "general_gis")
        constraints = state.research_goal.get("constraints", [])

        # Get literature context
        literature_summary = ""
        research_gaps = []
        if state.literature_summary:
            literature_summary = state.literature_summary.get("summary", "")
            research_gaps = state.literature_summary.get("research_gaps", [])

        # Get previous hypotheses to avoid duplication
        previous_hypotheses = [
            h.get("title", "") for h in state.hypotheses
        ]

        # Get meta-feedback if any
        meta_feedback = "\n".join(state.meta_feedback[-5:]) if state.meta_feedback else "None"

        # Format the prompt
        prompt = HYPOTHESIS_GENERATION_TEMPLATE.format(
            num_hypotheses=self.settings.hypotheses_per_iteration,
            research_goal=research_goal,
            domain=domain,
            constraints="\n".join(f"- {c}" for c in constraints) if constraints else "None specified",
            literature_summary=literature_summary[:2000] if literature_summary else "Not available",
            research_gaps="\n".join(f"- {g}" for g in research_gaps) if research_gaps else "Not identified",
            previous_hypotheses="\n".join(f"- {h}" for h in previous_hypotheses) if previous_hypotheses else "None",
            meta_feedback=meta_feedback
        )

        try:
            # Generate hypotheses
            response = await self.invoke(prompt, state)

            # Parse the response
            hypotheses = self._parse_hypotheses(response, state)

            # Add to state
            for hyp in hypotheses:
                hyp_dict = hyp.model_dump()
                state.hypotheses.append(hyp_dict)

            # Update statistics
            state.statistics["total_hypotheses_generated"] = len(state.hypotheses)

            self.add_message_to_state(
                state,
                f"Generated {len(hypotheses)} new hypotheses",
                hypothesis_count=len(hypotheses)
            )

            self.log_action(f"Generated {len(hypotheses)} hypotheses")

        except Exception as e:
            logger.error(f"Hypothesis generation failed: {e}")
            state.errors.append(f"Generation failed: {str(e)}")

        return state

    def _parse_hypotheses(
        self,
        response: str,
        state: CoScientistState
    ) -> list[Hypothesis]:
        """Parse LLM response into Hypothesis objects."""
        hypotheses = []

        # Try to extract JSON from response
        try:
            # Find JSON array in response
            start_idx = response.find("[")
            end_idx = response.rfind("]") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)

                for item in data:
                    hyp = Hypothesis(
                        goal_id=state.research_goal.get("id", "unknown"),
                        title=item.get("title", "Untitled"),
                        statement=item.get("statement", ""),
                        hypothesis_type=self._parse_hypothesis_type(
                            item.get("hypothesis_type", "exploratory")
                        ),
                        rationale=item.get("rationale", ""),
                        assumptions=item.get("assumptions", []),
                        variables=item.get("variables", {}),
                        testability=item.get("testability", ""),
                        generation_iteration=state.current_iteration
                    )
                    hypotheses.append(hyp)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}, attempting text extraction")
            # Fallback: try to extract hypotheses from text
            hypotheses = self._extract_hypotheses_from_text(response, state)

        return hypotheses

    def _parse_hypothesis_type(self, type_str: str) -> HypothesisType:
        """Parse hypothesis type string to enum."""
        type_map = {
            "causal": HypothesisType.CAUSAL,
            "correlational": HypothesisType.CORRELATIONAL,
            "methodological": HypothesisType.METHODOLOGICAL,
            "comparative": HypothesisType.COMPARATIVE,
            "exploratory": HypothesisType.EXPLORATORY,
            "predictive": HypothesisType.PREDICTIVE,
        }
        return type_map.get(type_str.lower(), HypothesisType.EXPLORATORY)

    def _extract_hypotheses_from_text(
        self,
        text: str,
        state: CoScientistState
    ) -> list[Hypothesis]:
        """Fallback extraction of hypotheses from unstructured text."""
        hypotheses = []

        # Simple heuristic: look for numbered items or "Hypothesis" mentions
        lines = text.split("\n")
        current_hypothesis = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for hypothesis markers
            if any(marker in line.lower() for marker in ["hypothesis", "h1:", "h2:", "h3:"]):
                if current_hypothesis:
                    hypotheses.append(current_hypothesis)

                current_hypothesis = Hypothesis(
                    goal_id=state.research_goal.get("id", "unknown"),
                    title=line[:100],
                    statement="",
                    generation_iteration=state.current_iteration
                )
            elif current_hypothesis and not current_hypothesis.statement:
                current_hypothesis.statement = line

        if current_hypothesis:
            hypotheses.append(current_hypothesis)

        return hypotheses

    async def generate_diverse_hypotheses(
        self,
        state: CoScientistState,
        diversity_prompts: Optional[list[str]] = None
    ) -> list[Hypothesis]:
        """
        Generate diverse hypotheses using multiple prompt variations.

        Args:
            state: Current state
            diversity_prompts: Optional list of prompt variations

        Returns:
            List of diverse hypotheses
        """
        if diversity_prompts is None:
            diversity_prompts = [
                "Focus on methodological innovations",
                "Consider unconventional data combinations",
                "Explore interdisciplinary connections",
                "Challenge existing assumptions in the field"
            ]

        all_hypotheses = []

        for diversity_prompt in diversity_prompts:
            modified_state = state.model_copy()
            modified_state.meta_feedback.append(diversity_prompt)

            result_state = await self.process(modified_state)

            # Get new hypotheses
            new_hyps = result_state.hypotheses[len(state.hypotheses):]
            all_hypotheses.extend(new_hyps)

        return [Hypothesis(**h) for h in all_hypotheses]

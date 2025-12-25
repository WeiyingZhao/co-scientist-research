"""Ranking Agent for hypothesis prioritization using Elo rating."""

import json
import logging
import random
from typing import Optional

from geospatial_co_scientist.agents.base import BaseAgent
from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.hypothesis import HypothesisRanking, HypothesisStatus
from geospatial_co_scientist.models.state import AgentType, CoScientistState

logger = logging.getLogger(__name__)


RANKING_SYSTEM_PROMPT = """You are an expert scientific evaluator specializing in geospatial research.
Your role is to compare pairs of research hypotheses and determine which one is more promising
for advancing scientific knowledge.

When comparing hypotheses, consider:
1. **Scientific Impact**: Which hypothesis, if confirmed, would contribute more to the field?
2. **Novelty**: Which presents more original ideas or connections?
3. **Feasibility**: Which is more likely to be successfully tested?
4. **Relevance**: Which better addresses the research goal?
5. **Clarity**: Which is more clearly stated and testable?

Provide clear reasoning for your choice. Be objective and consistent in your evaluations."""


COMPARISON_TEMPLATE = """Compare these two hypotheses and determine which is more promising.

## Research Goal
{research_goal}

## Hypothesis A
**Title:** {title_a}
**Statement:** {statement_a}
**Rationale:** {rationale_a}
**Review Score:** {score_a}

## Hypothesis B
**Title:** {title_b}
**Statement:** {statement_b}
**Rationale:** {rationale_b}
**Review Score:** {score_b}

## Comparison Criteria
Consider: scientific impact, novelty, feasibility, relevance, and clarity.

Which hypothesis is more likely to lead to a significant scientific discovery?

Output as JSON:
```json
{{
  "winner": "A" or "B",
  "confidence": 0.5-1.0,
  "rationale": "Detailed explanation of why the winner is better",
  "comparison_points": [
    {{"criterion": "impact", "advantage": "A" or "B", "explanation": "..."}},
    {{"criterion": "novelty", "advantage": "A" or "B", "explanation": "..."}},
    {{"criterion": "feasibility", "advantage": "A" or "B", "explanation": "..."}}
  ]
}}
```"""


class RankingAgent(BaseAgent):
    """Agent responsible for ranking hypotheses using Elo rating system."""

    agent_type = AgentType.RANKING
    default_model = "gpt-4-turbo-preview"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()
        self.k_factor = self.settings.elo_k_factor

    @property
    def system_prompt(self) -> str:
        return RANKING_SYSTEM_PROMPT

    async def process(self, state: CoScientistState) -> CoScientistState:
        """Perform pairwise ranking of hypotheses."""
        self.log_action("Starting hypothesis ranking")

        # Get hypotheses that are reviewed and not rejected
        eligible = [
            h for h in state.hypotheses
            if h.get("status") not in [HypothesisStatus.REJECTED.value, "rejected"]
        ]

        if len(eligible) < 2:
            state.warnings.append("Not enough hypotheses for ranking")
            return state

        # Determine number of comparisons
        num_comparisons = min(
            self.settings.ranking_comparisons,
            len(eligible) * (len(eligible) - 1) // 2  # Max possible pairs
        )

        self.log_action(f"Performing {num_comparisons} pairwise comparisons")

        # Generate pairs for comparison
        pairs = self._generate_comparison_pairs(eligible, num_comparisons)

        for hyp_a, hyp_b in pairs:
            try:
                ranking = await self._compare_hypotheses(hyp_a, hyp_b, state)
                state.hypothesis_rankings.append(ranking.model_dump())

                # Update Elo scores
                self._update_elo_scores(state, ranking)

            except Exception as e:
                logger.error(f"Comparison failed: {e}")
                state.errors.append(f"Ranking comparison failed: {str(e)}")

        # Update top hypotheses
        self._update_top_hypotheses(state)

        # Update statistics
        state.statistics["total_rankings_performed"] = len(state.hypothesis_rankings)
        if state.hypotheses:
            scores = [h.get("elo_score", 1000) for h in state.hypotheses]
            state.statistics["top_elo_score"] = max(scores)
            state.statistics["average_hypothesis_score"] = sum(scores) / len(scores)

        self.add_message_to_state(
            state,
            f"Completed {len(pairs)} rankings. Top hypotheses updated.",
            comparisons=len(pairs)
        )

        return state

    def _generate_comparison_pairs(
        self,
        hypotheses: list[dict],
        num_pairs: int
    ) -> list[tuple[dict, dict]]:
        """Generate pairs for comparison using tournament-style selection."""
        pairs = []
        n = len(hypotheses)

        # Sort by current Elo score
        sorted_hyps = sorted(
            hypotheses,
            key=lambda x: x.get("elo_score", 1000),
            reverse=True
        )

        # Strategy: compare adjacent hypotheses in ranking + random pairs
        # This helps resolve close rankings while exploring

        # Adjacent comparisons (more important)
        for i in range(min(num_pairs // 2, n - 1)):
            if i + 1 < n:
                pairs.append((sorted_hyps[i], sorted_hyps[i + 1]))

        # Random pairs for exploration
        remaining = num_pairs - len(pairs)
        all_possible = [
            (hypotheses[i], hypotheses[j])
            for i in range(n) for j in range(i + 1, n)
        ]

        # Remove already selected pairs
        existing = {(p[0]["id"], p[1]["id"]) for p in pairs}
        available = [
            p for p in all_possible
            if (p[0]["id"], p[1]["id"]) not in existing
            and (p[1]["id"], p[0]["id"]) not in existing
        ]

        if available and remaining > 0:
            random_pairs = random.sample(available, min(remaining, len(available)))
            pairs.extend(random_pairs)

        return pairs

    async def _compare_hypotheses(
        self,
        hyp_a: dict,
        hyp_b: dict,
        state: CoScientistState
    ) -> HypothesisRanking:
        """Compare two hypotheses and determine the winner."""
        research_goal = state.research_goal.get("question", "") if state.research_goal else ""

        # Get review scores if available
        score_a = self._get_review_score(state, hyp_a["id"])
        score_b = self._get_review_score(state, hyp_b["id"])

        prompt = COMPARISON_TEMPLATE.format(
            research_goal=research_goal,
            title_a=hyp_a.get("title", "Untitled"),
            statement_a=hyp_a.get("statement", ""),
            rationale_a=hyp_a.get("rationale", ""),
            score_a=f"{score_a:.2f}" if score_a else "Not reviewed",
            title_b=hyp_b.get("title", "Untitled"),
            statement_b=hyp_b.get("statement", ""),
            rationale_b=hyp_b.get("rationale", ""),
            score_b=f"{score_b:.2f}" if score_b else "Not reviewed"
        )

        response = await self.invoke(prompt, state)
        ranking = self._parse_comparison(response, hyp_a["id"], hyp_b["id"])

        return ranking

    def _get_review_score(self, state: CoScientistState, hypothesis_id: str) -> Optional[float]:
        """Get the review score for a hypothesis."""
        for review in state.hypothesis_reviews:
            if review.get("hypothesis_id") == hypothesis_id:
                return review.get("overall_score")
        return None

    def _parse_comparison(
        self,
        response: str,
        id_a: str,
        id_b: str
    ) -> HypothesisRanking:
        """Parse comparison response."""
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)

                winner = data.get("winner", "A")
                winner_id = id_a if winner == "A" else id_b
                confidence = data.get("confidence", 0.6)

                # Calculate score delta based on confidence
                score_delta = self.k_factor * confidence

                return HypothesisRanking(
                    hypothesis_a_id=id_a,
                    hypothesis_b_id=id_b,
                    winner_id=winner_id,
                    comparison_rationale=data.get("rationale", ""),
                    score_delta=score_delta,
                    comparison_criteria=[
                        p.get("criterion", "") for p in data.get("comparison_points", [])
                    ]
                )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse comparison JSON: {e}")

        # Fallback: random winner with low confidence
        return HypothesisRanking(
            hypothesis_a_id=id_a,
            hypothesis_b_id=id_b,
            winner_id=random.choice([id_a, id_b]),
            comparison_rationale="Parsing failed, random selection",
            score_delta=self.k_factor * 0.5
        )

    def _update_elo_scores(
        self,
        state: CoScientistState,
        ranking: HypothesisRanking
    ) -> None:
        """Update Elo scores based on ranking result."""
        winner_id = ranking.winner_id
        loser_id = (
            ranking.hypothesis_b_id
            if ranking.winner_id == ranking.hypothesis_a_id
            else ranking.hypothesis_a_id
        )

        # Find hypotheses
        winner = None
        loser = None
        for h in state.hypotheses:
            if h.get("id") == winner_id:
                winner = h
            elif h.get("id") == loser_id:
                loser = h

        if winner and loser:
            # Get current scores
            winner_score = winner.get("elo_score", 1000)
            loser_score = loser.get("elo_score", 1000)

            # Calculate expected scores
            expected_winner = 1 / (1 + 10 ** ((loser_score - winner_score) / 400))
            expected_loser = 1 - expected_winner

            # Update scores
            winner["elo_score"] = winner_score + self.k_factor * (1 - expected_winner)
            loser["elo_score"] = loser_score + self.k_factor * (0 - expected_loser)

            winner["status"] = HypothesisStatus.RANKED.value
            loser["status"] = HypothesisStatus.RANKED.value

    def _update_top_hypotheses(self, state: CoScientistState) -> None:
        """Update the list of top hypotheses."""
        # Sort by Elo score
        sorted_hyps = sorted(
            state.hypotheses,
            key=lambda x: x.get("elo_score", 1000),
            reverse=True
        )

        # Get top N
        n = self.settings.top_hypotheses_to_evolve
        state.top_hypotheses = [h["id"] for h in sorted_hyps[:n]]

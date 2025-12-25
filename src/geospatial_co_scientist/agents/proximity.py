"""Proximity Agent for hypothesis clustering and diversity analysis."""

import logging
from typing import Optional

from geospatial_co_scientist.agents.base import BaseAgent
from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.hypothesis import HypothesisCluster
from geospatial_co_scientist.models.state import AgentType, CoScientistState
from geospatial_co_scientist.tools.embeddings import (
    EmbeddingTool,
    cluster_by_similarity,
    compute_pairwise_similarities,
)

logger = logging.getLogger(__name__)


PROXIMITY_SYSTEM_PROMPT = """You are an expert at analyzing research hypothesis spaces.
Your role is to identify similarities, redundancies, and gaps in a collection of hypotheses.

You help ensure diversity in generated hypotheses by:
1. Identifying clusters of similar hypotheses
2. Recommending which hypotheses to merge or drop
3. Identifying unexplored areas of the hypothesis space
4. Suggesting directions for generating new, diverse hypotheses

Be thorough in your analysis and provide actionable recommendations."""


class ProximityAgent(BaseAgent):
    """Agent responsible for analyzing hypothesis similarity and diversity."""

    agent_type = AgentType.PROXIMITY
    default_model = "gpt-4-turbo-preview"

    def __init__(self, similarity_threshold: float = 0.85, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()
        self.similarity_threshold = similarity_threshold
        self.embedding_tool = EmbeddingTool()

    @property
    def system_prompt(self) -> str:
        return PROXIMITY_SYSTEM_PROMPT

    async def process(self, state: CoScientistState) -> CoScientistState:
        """Analyze hypothesis proximity and identify clusters."""
        self.log_action("Starting proximity analysis")

        if len(state.hypotheses) < 2:
            state.warnings.append("Not enough hypotheses for proximity analysis")
            return state

        try:
            # Get embeddings for all hypotheses
            hypothesis_texts = [
                f"{h.get('title', '')}. {h.get('statement', '')}"
                for h in state.hypotheses
            ]

            embeddings = await self.embedding_tool.embed_texts(hypothesis_texts)

            # Compute similarity matrix
            similarity_matrix = compute_pairwise_similarities(embeddings)

            # Find clusters
            clusters = cluster_by_similarity(embeddings, self.similarity_threshold)

            # Create cluster objects
            for cluster_indices in clusters:
                if len(cluster_indices) > 1:  # Only report clusters with multiple items
                    cluster = await self._create_cluster(
                        cluster_indices,
                        state,
                        similarity_matrix
                    )
                    state.hypothesis_clusters.append(cluster.model_dump())

            # Identify diversity gaps
            gaps = await self._identify_gaps(state, embeddings)
            if gaps:
                state.meta_feedback.extend(gaps)

            # Log redundancies for meta-review
            redundant_pairs = self._find_redundant_pairs(
                state.hypotheses,
                similarity_matrix
            )
            if redundant_pairs:
                state.meta_feedback.append(
                    f"Found {len(redundant_pairs)} pairs of very similar hypotheses"
                )

            self.add_message_to_state(
                state,
                f"Identified {len([c for c in clusters if len(c) > 1])} hypothesis clusters",
                clusters=len(clusters),
                gaps=len(gaps) if gaps else 0
            )

        except Exception as e:
            logger.error(f"Proximity analysis failed: {e}")
            state.errors.append(f"Proximity analysis failed: {str(e)}")

        return state

    async def _create_cluster(
        self,
        indices: list[int],
        state: CoScientistState,
        similarity_matrix
    ) -> HypothesisCluster:
        """Create a cluster object from indices."""
        hypothesis_ids = [state.hypotheses[i]["id"] for i in indices]

        # Find centroid (hypothesis with highest avg similarity to others in cluster)
        cluster_sims = similarity_matrix[indices][:, indices]
        avg_sims = cluster_sims.mean(axis=1)
        centroid_idx = indices[avg_sims.argmax()]
        centroid_id = state.hypotheses[centroid_idx]["id"]

        # Calculate average similarity
        n = len(indices)
        total_sim = 0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                total_sim += cluster_sims[i, j]
                count += 1
        avg_similarity = total_sim / count if count > 0 else 0

        # Generate theme from hypothesis titles
        titles = [state.hypotheses[i].get("title", "") for i in indices]
        theme = await self._identify_cluster_theme(titles)

        # Generate merge recommendation
        merge_rec = await self._generate_merge_recommendation(
            [state.hypotheses[i] for i in indices]
        )

        return HypothesisCluster(
            hypothesis_ids=hypothesis_ids,
            centroid_hypothesis_id=centroid_id,
            theme=theme,
            similarity_score=float(avg_similarity),
            merge_recommendation=merge_rec
        )

    async def _identify_cluster_theme(self, titles: list[str]) -> str:
        """Identify common theme from hypothesis titles."""
        prompt = f"""Given these hypothesis titles, identify the common theme in 5-10 words:

Titles:
{chr(10).join(f'- {t}' for t in titles)}

Theme:"""

        response = await self.invoke(prompt)
        return response.strip()

    async def _generate_merge_recommendation(
        self,
        hypotheses: list[dict]
    ) -> str:
        """Generate recommendation for merging similar hypotheses."""
        hyp_texts = "\n\n".join([
            f"**{h.get('title')}**: {h.get('statement', '')}"
            for h in hypotheses
        ])

        prompt = f"""These hypotheses are very similar:

{hyp_texts}

Should they be merged? If so, provide a brief recommendation on how to combine them.
If not, explain why they should remain separate.

Recommendation (2-3 sentences):"""

        response = await self.invoke(prompt)
        return response.strip()

    async def _identify_gaps(
        self,
        state: CoScientistState,
        embeddings: list[list[float]]
    ) -> list[str]:
        """Identify gaps in hypothesis coverage."""
        gaps = []

        # Get research goal context
        if not state.research_goal:
            return gaps

        goal_text = state.research_goal.get("question", "")
        constraints = state.research_goal.get("constraints", [])
        keywords = state.research_goal.get("keywords", [])

        # Generate potential directions
        prompt = f"""Given this research goal and existing hypotheses, identify 2-3 unexplored directions.

Research Goal: {goal_text}
Keywords: {', '.join(keywords)}
Constraints: {', '.join(constraints)}

Existing hypothesis themes:
{chr(10).join(f'- {h.get("title", "")}' for h in state.hypotheses[:10])}

What important aspects of the research goal are NOT covered by existing hypotheses?
List 2-3 specific unexplored directions that should be considered.

Unexplored directions:"""

        response = await self.invoke(prompt)

        # Parse response into gap suggestions
        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                # Clean up common list prefixes
                for prefix in ["- ", "* ", "1. ", "2. ", "3. "]:
                    if line.startswith(prefix):
                        line = line[len(prefix):]
                if line:
                    gaps.append(f"Unexplored direction: {line}")

        return gaps[:3]  # Limit to top 3

    def _find_redundant_pairs(
        self,
        hypotheses: list[dict],
        similarity_matrix
    ) -> list[tuple[str, str, float]]:
        """Find pairs of hypotheses that are too similar."""
        redundant = []
        n = len(hypotheses)

        for i in range(n):
            for j in range(i + 1, n):
                sim = similarity_matrix[i, j]
                if sim >= 0.9:  # Very high similarity threshold
                    redundant.append((
                        hypotheses[i]["id"],
                        hypotheses[j]["id"],
                        float(sim)
                    ))

        return redundant

    async def get_diversity_score(self, state: CoScientistState) -> float:
        """Calculate overall diversity score for hypothesis set."""
        if len(state.hypotheses) < 2:
            return 1.0

        hypothesis_texts = [
            f"{h.get('title', '')}. {h.get('statement', '')}"
            for h in state.hypotheses
        ]

        embeddings = await self.embedding_tool.embed_texts(hypothesis_texts)
        similarity_matrix = compute_pairwise_similarities(embeddings)

        # Diversity = 1 - average similarity
        n = len(embeddings)
        total_sim = 0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                total_sim += similarity_matrix[i, j]
                count += 1

        avg_sim = total_sim / count if count > 0 else 0
        return 1 - avg_sim

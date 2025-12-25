"""Tests for agents with simulated/mock LLM responses."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from geospatial_co_scientist.agents.generation import GenerationAgent
from geospatial_co_scientist.agents.reflection import ReflectionAgent
from geospatial_co_scientist.agents.ranking import RankingAgent
from geospatial_co_scientist.agents.proximity import ProximityAgent
from geospatial_co_scientist.agents.evolution import EvolutionAgent
from geospatial_co_scientist.models.state import CoScientistState, AgentType
from geospatial_co_scientist.models.research import ResearchGoal, ResearchDomain
from geospatial_co_scientist.models.hypothesis import HypothesisType, HypothesisStatus


# Sample simulated data for testing
SAMPLE_RESEARCH_GOAL = {
    "id": "goal_test_001",
    "question": "How can satellite thermal imagery detect urban heat islands?",
    "domain": ResearchDomain.REMOTE_SENSING.value,
    "context": "Focus on tropical cities with population > 1 million",
    "constraints": [
        "Use freely available satellite data",
        "Analysis should be reproducible"
    ],
    "keywords": ["urban heat island", "thermal imagery", "Landsat", "MODIS"]
}

SAMPLE_LITERATURE_SUMMARY = {
    "goal_id": "goal_test_001",
    "summary": "Research on urban heat islands using remote sensing has grown significantly. "
               "Landsat thermal bands and MODIS provide valuable data for UHI detection. "
               "Key methods include thermal infrared analysis and NDVI correlation studies.",
    "key_themes": [
        "Thermal remote sensing for UHI detection",
        "NDVI-temperature relationships",
        "Urban-rural temperature gradients"
    ],
    "research_gaps": [
        "Limited studies on tropical cities",
        "Need for multi-temporal analysis",
        "Integration of building height data"
    ],
    "methodologies_used": [
        "Land Surface Temperature extraction",
        "NDVI calculation",
        "Spatial statistics"
    ]
}

MOCK_GENERATION_RESPONSE = json.dumps([
    {
        "title": "Thermal-NDVI Correlation in Tropical Cities",
        "statement": "In tropical cities, the correlation between NDVI and land surface temperature "
                    "is stronger during dry seasons compared to wet seasons due to reduced vegetation moisture stress.",
        "hypothesis_type": "correlational",
        "rationale": "Vegetation cooling effect varies with water availability",
        "assumptions": ["Cloud-free imagery available", "Seasonal NDVI variation is significant"],
        "variables": {
            "independent": "NDVI values",
            "dependent": "Land Surface Temperature",
            "control": "Season, Urban density"
        },
        "testability": "Compare NDVI-LST correlations across seasonal Landsat imagery"
    },
    {
        "title": "Nighttime UHI Intensity Detection",
        "statement": "Urban heat island intensity is more accurately quantified using nighttime thermal data "
                    "as it eliminates solar heating interference and reveals true anthropogenic heat signatures.",
        "hypothesis_type": "methodological",
        "rationale": "Daytime measurements include solar heating artifacts",
        "assumptions": ["Nighttime thermal data is available", "Clear sky conditions"],
        "variables": {
            "independent": "Time of acquisition (day vs night)",
            "dependent": "UHI intensity measurement",
            "control": "Location, Season"
        },
        "testability": "Compare UHI intensity maps from day and night Landsat thermal bands"
    }
])

MOCK_REFLECTION_RESPONSE = json.dumps({
    "reviews": [
        {
            "hypothesis_id": "hyp_001",
            "scores": {
                "logical_consistency": 0.85,
                "novelty": 0.7,
                "testability": 0.9,
                "scientific_soundness": 0.8,
                "feasibility": 0.85,
                "relevance": 0.9,
                "clarity": 0.85
            },
            "strengths": [
                "Well-grounded in established science",
                "Testable with available data"
            ],
            "weaknesses": [
                "Could be more specific about tropical cities"
            ],
            "suggestions": [
                "Consider adding building density as a control variable"
            ],
            "recommendation": "proceed"
        }
    ]
})

MOCK_RANKING_RESPONSE = json.dumps({
    "winner": "hyp_001",
    "rationale": "Hypothesis A is more testable and has clearer methodology",
    "comparison_criteria": ["testability", "novelty", "feasibility"]
})


class TestGenerationAgent:
    """Tests for the Generation Agent."""

    @pytest.fixture
    def sample_state(self) -> CoScientistState:
        """Create a sample state for testing."""
        state = CoScientistState(
            research_goal=SAMPLE_RESEARCH_GOAL,
            literature_summary=SAMPLE_LITERATURE_SUMMARY,
            max_iterations=3
        )
        return state

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that returns simulated responses."""
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(return_value=MagicMock(content=MOCK_GENERATION_RESPONSE))
        return mock

    @pytest.mark.asyncio
    async def test_parse_hypotheses_from_json(self, sample_state):
        """Test that hypotheses are correctly parsed from JSON response."""
        agent = GenerationAgent()

        # Test parsing
        hypotheses = agent._parse_hypotheses(MOCK_GENERATION_RESPONSE, sample_state)

        assert len(hypotheses) == 2
        assert hypotheses[0].title == "Thermal-NDVI Correlation in Tropical Cities"
        assert hypotheses[0].hypothesis_type == HypothesisType.CORRELATIONAL
        assert hypotheses[1].hypothesis_type == HypothesisType.METHODOLOGICAL

    @pytest.mark.asyncio
    async def test_parse_hypothesis_type(self):
        """Test hypothesis type parsing."""
        agent = GenerationAgent()

        assert agent._parse_hypothesis_type("causal") == HypothesisType.CAUSAL
        assert agent._parse_hypothesis_type("correlational") == HypothesisType.CORRELATIONAL
        assert agent._parse_hypothesis_type("METHODOLOGICAL") == HypothesisType.METHODOLOGICAL
        assert agent._parse_hypothesis_type("unknown") == HypothesisType.EXPLORATORY

    @pytest.mark.asyncio
    async def test_generation_with_mock_llm(self, sample_state, mock_llm):
        """Test hypothesis generation with mocked LLM."""
        agent = GenerationAgent()
        agent._llm = mock_llm

        result_state = await agent.process(sample_state)

        assert len(result_state.hypotheses) == 2
        assert result_state.statistics["total_hypotheses_generated"] == 2

    def test_format_context(self, sample_state):
        """Test context formatting for prompts."""
        agent = GenerationAgent()
        context = agent.format_context(sample_state)

        assert "urban heat islands" in context.lower()
        assert "Research Goal:" in context

    @pytest.mark.asyncio
    async def test_generation_without_goal_fails(self):
        """Test that generation fails gracefully without research goal."""
        agent = GenerationAgent()
        state = CoScientistState()  # No research goal

        # Create a mock LLM to avoid actual API calls
        mock_llm = AsyncMock()
        agent._llm = mock_llm

        result_state = await agent.process(state)

        assert len(result_state.errors) > 0
        assert "No research goal" in result_state.errors[0]


class TestReflectionAgent:
    """Tests for the Reflection Agent."""

    @pytest.fixture
    def state_with_hypotheses(self) -> CoScientistState:
        """Create a state with hypotheses to review."""
        state = CoScientistState(
            research_goal=SAMPLE_RESEARCH_GOAL,
            hypotheses=[
                {
                    "id": "hyp_001",
                    "title": "Thermal-NDVI Correlation",
                    "statement": "Higher NDVI correlates with lower surface temperature",
                    "hypothesis_type": "correlational",
                    "rationale": "Vegetation has cooling effect",
                    "elo_score": 1000.0,
                    "status": HypothesisStatus.GENERATED.value
                },
                {
                    "id": "hyp_002",
                    "title": "Nighttime UHI Detection",
                    "statement": "Nighttime data better isolates UHI",
                    "hypothesis_type": "methodological",
                    "rationale": "No solar heating at night",
                    "elo_score": 1000.0,
                    "status": HypothesisStatus.GENERATED.value
                }
            ]
        )
        return state

    def test_get_unreviewed_hypotheses(self, state_with_hypotheses):
        """Test identifying hypotheses that need review."""
        # Both hypotheses should need review
        unreviewed = [
            h for h in state_with_hypotheses.hypotheses
            if h.get("status") == HypothesisStatus.GENERATED.value
        ]
        assert len(unreviewed) == 2


class TestRankingAgent:
    """Tests for the Ranking Agent."""

    @pytest.fixture
    def state_with_reviewed_hypotheses(self) -> CoScientistState:
        """Create a state with reviewed hypotheses."""
        state = CoScientistState(
            research_goal=SAMPLE_RESEARCH_GOAL,
            hypotheses=[
                {
                    "id": "hyp_001",
                    "title": "Thermal-NDVI Correlation",
                    "statement": "Higher NDVI correlates with lower surface temperature",
                    "hypothesis_type": "correlational",
                    "elo_score": 1000.0,
                    "status": HypothesisStatus.REVIEWED.value
                },
                {
                    "id": "hyp_002",
                    "title": "Nighttime UHI Detection",
                    "statement": "Nighttime data better isolates UHI",
                    "hypothesis_type": "methodological",
                    "elo_score": 1000.0,
                    "status": HypothesisStatus.REVIEWED.value
                },
                {
                    "id": "hyp_003",
                    "title": "Multi-temporal Analysis",
                    "statement": "Seasonal patterns reveal persistent UHI zones",
                    "hypothesis_type": "exploratory",
                    "elo_score": 1000.0,
                    "status": HypothesisStatus.REVIEWED.value
                }
            ]
        )
        return state

    def test_elo_score_calculation(self):
        """Test Elo score update logic."""
        # Standard Elo formula
        k_factor = 32.0
        initial_score = 1000.0

        # Calculate expected score
        def expected_score(rating_a, rating_b):
            return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

        # When A wins against B with equal ratings
        exp_a = expected_score(initial_score, initial_score)
        new_score_a = initial_score + k_factor * (1 - exp_a)  # Win
        new_score_b = initial_score + k_factor * (0 - exp_a)  # Loss

        assert new_score_a > initial_score  # Winner gains
        assert new_score_b < initial_score  # Loser loses
        assert abs((new_score_a - initial_score) + (new_score_b - initial_score)) < 0.01  # Zero sum

    def test_get_top_hypotheses(self, state_with_reviewed_hypotheses):
        """Test getting top hypotheses by Elo score."""
        # Modify scores
        state_with_reviewed_hypotheses.hypotheses[0]["elo_score"] = 1100.0
        state_with_reviewed_hypotheses.hypotheses[1]["elo_score"] = 1050.0
        state_with_reviewed_hypotheses.hypotheses[2]["elo_score"] = 950.0

        top = state_with_reviewed_hypotheses.get_top_hypotheses_data(2)

        assert len(top) == 2
        assert top[0]["id"] == "hyp_001"  # Highest score
        assert top[1]["id"] == "hyp_002"


class TestProximityAgent:
    """Tests for the Proximity Agent."""

    def test_similarity_calculation(self):
        """Test hypothesis similarity calculation."""
        # Simple cosine similarity test
        vec_a = [1, 0, 0]
        vec_b = [1, 0, 0]
        vec_c = [0, 1, 0]

        from geospatial_co_scientist.tools.embeddings import compute_similarity

        # Identical vectors should have similarity 1
        assert compute_similarity(vec_a, vec_b) == 1.0

        # Orthogonal vectors should have similarity 0
        assert compute_similarity(vec_a, vec_c) == 0.0

    def test_cluster_identification(self):
        """Test clustering of similar hypotheses."""
        from geospatial_co_scientist.tools.embeddings import cluster_by_similarity

        # Test with distinct embeddings
        embeddings = [
            [1, 0, 0],
            [0.99, 0.1, 0],  # Similar to first
            [0, 1, 0],       # Different
            [0, 0.95, 0.05], # Similar to third
        ]

        clusters = cluster_by_similarity(embeddings, threshold=0.9)

        # Should identify clusters of similar items
        assert len(clusters) >= 1


class TestEvolutionAgent:
    """Tests for the Evolution Agent."""

    @pytest.fixture
    def state_with_ranked_hypotheses(self) -> CoScientistState:
        """Create a state with ranked hypotheses."""
        state = CoScientistState(
            research_goal=SAMPLE_RESEARCH_GOAL,
            hypotheses=[
                {
                    "id": "hyp_001",
                    "title": "Thermal-NDVI Correlation",
                    "statement": "Higher NDVI correlates with lower surface temperature",
                    "hypothesis_type": "correlational",
                    "elo_score": 1100.0,
                    "status": HypothesisStatus.RANKED.value
                },
                {
                    "id": "hyp_002",
                    "title": "Nighttime UHI Detection",
                    "statement": "Nighttime data better isolates UHI",
                    "hypothesis_type": "methodological",
                    "elo_score": 1050.0,
                    "status": HypothesisStatus.RANKED.value
                }
            ],
            hypothesis_reviews=[
                {
                    "hypothesis_id": "hyp_001",
                    "strengths": ["Well-grounded"],
                    "weaknesses": ["Could be more specific"],
                    "suggestions": ["Add building density"]
                }
            ],
            top_hypotheses=["hyp_001", "hyp_002"]
        )
        return state

    def test_identify_top_hypotheses(self, state_with_ranked_hypotheses):
        """Test identifying top hypotheses for evolution."""
        top = state_with_ranked_hypotheses.get_top_hypotheses_data(2)

        assert len(top) == 2
        assert top[0]["elo_score"] == 1100.0


class TestAgentIntegration:
    """Integration tests for agent interactions."""

    @pytest.fixture
    def full_research_state(self) -> CoScientistState:
        """Create a comprehensive state for integration testing."""
        return CoScientistState(
            research_goal=SAMPLE_RESEARCH_GOAL,
            literature_summary=SAMPLE_LITERATURE_SUMMARY,
            hypotheses=[
                {
                    "id": "hyp_001",
                    "title": "Thermal-NDVI Correlation in Tropical Cities",
                    "statement": "The correlation between NDVI and land surface temperature "
                               "is stronger during dry seasons in tropical cities.",
                    "hypothesis_type": "correlational",
                    "rationale": "Vegetation cooling effect varies with water availability",
                    "assumptions": ["Cloud-free imagery available"],
                    "variables": {
                        "independent": "NDVI values",
                        "dependent": "Land Surface Temperature",
                        "control": "Season"
                    },
                    "testability": "Compare correlations across seasons",
                    "elo_score": 1000.0,
                    "status": HypothesisStatus.GENERATED.value,
                    "generation_iteration": 1
                },
                {
                    "id": "hyp_002",
                    "title": "Nighttime UHI Intensity Detection",
                    "statement": "Urban heat island intensity is more accurately quantified "
                               "using nighttime thermal data.",
                    "hypothesis_type": "methodological",
                    "rationale": "Eliminates solar heating interference",
                    "assumptions": ["Nighttime thermal data available"],
                    "variables": {
                        "independent": "Time of acquisition",
                        "dependent": "UHI intensity",
                        "control": "Location"
                    },
                    "testability": "Compare day and night UHI maps",
                    "elo_score": 1000.0,
                    "status": HypothesisStatus.GENERATED.value,
                    "generation_iteration": 1
                }
            ],
            max_iterations=3
        )

    def test_state_message_tracking(self, full_research_state):
        """Test that agent messages are properly tracked in state."""
        state = full_research_state

        state.add_message(AgentType.GENERATION, "Generated 2 hypotheses")
        state.add_message(AgentType.REFLECTION, "Reviewed all hypotheses")

        assert len(state.messages) == 2
        assert state.messages[0]["agent_type"] == "generation"
        assert state.messages[1]["agent_type"] == "reflection"

    def test_statistics_update(self, full_research_state):
        """Test statistics are properly updated."""
        state = full_research_state
        state.update_statistics()

        assert state.statistics["total_hypotheses_generated"] == 2
        assert state.statistics["average_hypothesis_score"] == 1000.0

    def test_iteration_control(self, full_research_state):
        """Test iteration control logic."""
        state = full_research_state

        # Should not stop on first iteration
        assert not state.should_stop_iterations()

        # After max iterations
        state.current_iteration = 3
        assert state.should_stop_iterations()


class TestSimulatedWorkflow:
    """Tests simulating full workflow with sample data."""

    @pytest.fixture
    def simulated_workflow_state(self) -> CoScientistState:
        """Create a state simulating a complete workflow."""
        return CoScientistState(
            research_goal=SAMPLE_RESEARCH_GOAL,
            literature_summary=SAMPLE_LITERATURE_SUMMARY,
            hypotheses=[
                {
                    "id": f"hyp_00{i}",
                    "title": f"Test Hypothesis {i}",
                    "statement": f"Statement for hypothesis {i}",
                    "hypothesis_type": "correlational",
                    "rationale": f"Rationale {i}",
                    "elo_score": 1000.0 + (i * 10),
                    "status": HypothesisStatus.REVIEWED.value,
                    "generation_iteration": 1
                }
                for i in range(1, 6)  # 5 hypotheses
            ],
            hypothesis_reviews=[
                {
                    "hypothesis_id": f"hyp_00{i}",
                    "scores": {
                        "logical_consistency": 0.8,
                        "novelty": 0.7 + (i * 0.02),
                        "testability": 0.85,
                        "scientific_soundness": 0.8,
                        "feasibility": 0.75,
                        "relevance": 0.9,
                        "clarity": 0.8
                    },
                    "overall_score": 0.8,
                    "strengths": ["Clear methodology"],
                    "weaknesses": ["Needs more detail"],
                    "suggestions": ["Add more variables"],
                    "recommendation": "proceed"
                }
                for i in range(1, 6)
            ],
            current_iteration=1,
            max_iterations=3
        )

    def test_simulated_hypothesis_ranking(self, simulated_workflow_state):
        """Test ranking of simulated hypotheses."""
        state = simulated_workflow_state

        # Verify hypotheses are ranked by score
        top_3 = state.get_top_hypotheses_data(3)

        assert len(top_3) == 3
        # Should be in descending order of elo_score
        assert top_3[0]["elo_score"] >= top_3[1]["elo_score"]
        assert top_3[1]["elo_score"] >= top_3[2]["elo_score"]

    def test_simulated_review_aggregation(self, simulated_workflow_state):
        """Test aggregation of hypothesis reviews."""
        state = simulated_workflow_state

        # All hypotheses should have reviews
        assert len(state.hypothesis_reviews) == 5

        # Calculate average overall score
        avg_score = sum(r["overall_score"] for r in state.hypothesis_reviews) / 5
        assert 0 < avg_score <= 1

    def test_simulated_full_state_summary(self, simulated_workflow_state):
        """Test full state summary generation."""
        state = simulated_workflow_state
        summary = state.to_summary()

        assert summary["total_hypotheses"] == 5
        assert summary["total_reviews"] == 5
        assert summary["current_iteration"] == 1
        assert "urban heat islands" in summary["research_goal"]

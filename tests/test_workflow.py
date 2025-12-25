"""Tests for the workflow orchestration with simulated data."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from geospatial_co_scientist.orchestration.workflow import GeospatialCoScientist
from geospatial_co_scientist.orchestration.nodes import (
    generation_node,
    reflection_node,
    ranking_node,
    proximity_node,
    evolution_node,
)
from geospatial_co_scientist.models.state import CoScientistState, AgentType, TaskStatus
from geospatial_co_scientist.models.research import ResearchGoal, ResearchDomain
from geospatial_co_scientist.models.hypothesis import HypothesisStatus


# Comprehensive simulated data for workflow testing
WORKFLOW_RESEARCH_GOAL = {
    "id": "goal_workflow_001",
    "question": "How can we combine multi-source satellite data to improve urban heat island mapping accuracy?",
    "domain": ResearchDomain.REMOTE_SENSING.value,
    "context": "Focus on megacities in developing countries where ground-based measurements are limited",
    "constraints": [
        "Must use open-access satellite data",
        "Analysis pipeline should be reproducible",
        "Results should be validated against available ground truth"
    ],
    "keywords": [
        "urban heat island",
        "multi-source fusion",
        "Landsat",
        "Sentinel",
        "MODIS",
        "data fusion"
    ]
}

WORKFLOW_LITERATURE_SUMMARY = {
    "goal_id": "goal_workflow_001",
    "total_papers_found": 150,
    "papers_reviewed": 25,
    "summary": """
    Urban heat island research has evolved significantly with advances in satellite remote sensing.
    Current studies primarily use single-source data (Landsat or MODIS), with limited multi-source integration.
    Key findings include:
    1. Thermal infrared bands provide direct surface temperature measurements
    2. Vegetation indices (NDVI, EVI) show strong negative correlation with LST
    3. Data fusion approaches are emerging but face temporal/spatial resolution challenges
    4. Machine learning is increasingly used for UHI prediction and mapping
    """,
    "key_themes": [
        "Single-source thermal remote sensing",
        "Vegetation-temperature relationships",
        "Spatial resolution vs temporal frequency trade-offs",
        "Machine learning applications in UHI research"
    ],
    "research_gaps": [
        "Limited studies on multi-source data fusion for UHI",
        "Need for validated methods in tropical/developing megacities",
        "Temporal dynamics of UHI poorly understood",
        "Building morphology integration lacking"
    ],
    "methodologies_used": [
        "Land Surface Temperature retrieval",
        "Spectral indices calculation",
        "Spatial statistics",
        "Random Forest classification",
        "Time series analysis"
    ],
    "datasets_mentioned": [
        "Landsat 8/9 Collection 2",
        "Sentinel-2",
        "MODIS Terra/Aqua",
        "ECOSTRESS",
        "ASTER GDEM"
    ]
}

WORKFLOW_HYPOTHESES = [
    {
        "id": "hyp_wf_001",
        "goal_id": "goal_workflow_001",
        "title": "Multi-resolution Fusion for Enhanced UHI Detection",
        "statement": "Combining high spatial resolution Landsat thermal data with high temporal "
                    "resolution MODIS data through a data fusion approach will improve UHI "
                    "detection accuracy compared to single-source methods.",
        "hypothesis_type": "methodological",
        "rationale": "Landsat provides 100m thermal resolution but 16-day revisit, while MODIS "
                    "provides daily coverage at 1km. Fusion can leverage both advantages.",
        "assumptions": [
            "Spatial patterns remain relatively stable between Landsat acquisitions",
            "MODIS captures temporal variation adequately",
            "Atmospheric correction is consistent across sensors"
        ],
        "variables": {
            "independent": "Fusion algorithm (STARFM, ESTARFM, FSDAF)",
            "dependent": "UHI detection accuracy (compared to ground truth)",
            "control": "Study area, season, cloud cover threshold"
        },
        "testability": "Compare UHI maps from fused data vs single-source against weather station data",
        "elo_score": 1050.0,
        "status": HypothesisStatus.REVIEWED.value,
        "generation_iteration": 1
    },
    {
        "id": "hyp_wf_002",
        "goal_id": "goal_workflow_001",
        "title": "Building Density as UHI Predictor",
        "statement": "Building density derived from Sentinel-1 SAR data is a stronger predictor "
                    "of UHI intensity than NDVI alone in dense urban areas.",
        "hypothesis_type": "comparative",
        "rationale": "In highly urbanized areas with little vegetation, NDVI variance is limited. "
                    "SAR-derived building density captures 3D urban structure.",
        "assumptions": [
            "SAR data quality is consistent",
            "Building density can be reliably extracted from SAR"
        ],
        "variables": {
            "independent": "Building density from Sentinel-1",
            "dependent": "UHI intensity",
            "control": "Season, time of day, weather conditions"
        },
        "testability": "Regression analysis comparing explanatory power of building density vs NDVI",
        "elo_score": 1030.0,
        "status": HypothesisStatus.REVIEWED.value,
        "generation_iteration": 1
    },
    {
        "id": "hyp_wf_003",
        "goal_id": "goal_workflow_001",
        "title": "Diurnal UHI Pattern Detection",
        "statement": "ECOSTRESS multi-temporal thermal data reveals distinct diurnal UHI patterns "
                    "that are invisible in single-time Landsat observations.",
        "hypothesis_type": "exploratory",
        "rationale": "UHI varies significantly throughout the day. ECOSTRESS's varying overpass "
                    "times enable diurnal pattern characterization.",
        "assumptions": [
            "Sufficient ECOSTRESS observations available",
            "Cloud cover does not bias temporal sampling"
        ],
        "variables": {
            "independent": "Time of observation (binned by hour)",
            "dependent": "UHI intensity spatial pattern",
            "control": "Season, weather conditions"
        },
        "testability": "Cluster analysis of UHI patterns by time of day",
        "elo_score": 980.0,
        "status": HypothesisStatus.REVIEWED.value,
        "generation_iteration": 1
    }
]

WORKFLOW_REVIEWS = [
    {
        "id": "rev_wf_001",
        "hypothesis_id": "hyp_wf_001",
        "reviewer_type": "reflection_agent",
        "scores": {
            "logical_consistency": 0.90,
            "novelty": 0.75,
            "testability": 0.85,
            "scientific_soundness": 0.88,
            "feasibility": 0.80,
            "relevance": 0.95,
            "clarity": 0.85
        },
        "overall_score": 0.855,
        "strengths": [
            "Addresses key temporal resolution gap",
            "Well-established fusion methods available",
            "Clear validation strategy"
        ],
        "weaknesses": [
            "Fusion algorithms may introduce artifacts",
            "Computational requirements not addressed"
        ],
        "suggestions": [
            "Include uncertainty quantification",
            "Test multiple fusion algorithms"
        ],
        "recommendation": "proceed"
    },
    {
        "id": "rev_wf_002",
        "hypothesis_id": "hyp_wf_002",
        "reviewer_type": "reflection_agent",
        "scores": {
            "logical_consistency": 0.85,
            "novelty": 0.80,
            "testability": 0.90,
            "scientific_soundness": 0.82,
            "feasibility": 0.85,
            "relevance": 0.88,
            "clarity": 0.80
        },
        "overall_score": 0.843,
        "strengths": [
            "Novel use of SAR for UHI research",
            "Addresses limitation of optical-only approaches"
        ],
        "weaknesses": [
            "SAR building extraction may be complex",
            "Comparison with NDVI may be too simplistic"
        ],
        "suggestions": [
            "Consider combined SAR + NDVI model",
            "Include building height if possible"
        ],
        "recommendation": "proceed"
    }
]


class TestWorkflowInitialization:
    """Tests for workflow initialization."""

    def test_create_workflow(self):
        """Test that workflow can be created."""
        workflow = GeospatialCoScientist()
        assert workflow is not None

    def test_workflow_state_initialization(self):
        """Test that workflow state is properly initialized."""
        state = CoScientistState(
            research_goal=WORKFLOW_RESEARCH_GOAL,
            literature_summary=WORKFLOW_LITERATURE_SUMMARY,
            max_iterations=3
        )

        assert state.research_goal is not None
        assert state.current_iteration == 1
        assert state.should_continue is True


class TestWorkflowStateManagement:
    """Tests for workflow state management."""

    @pytest.fixture
    def workflow_state(self) -> CoScientistState:
        """Create a workflow state for testing."""
        return CoScientistState(
            research_goal=WORKFLOW_RESEARCH_GOAL,
            literature_summary=WORKFLOW_LITERATURE_SUMMARY,
            hypotheses=WORKFLOW_HYPOTHESES.copy(),
            hypothesis_reviews=WORKFLOW_REVIEWS.copy(),
            max_iterations=3
        )

    def test_state_transitions(self, workflow_state):
        """Test state transitions through workflow stages."""
        state = workflow_state

        # Initial state
        assert state.current_iteration == 1
        assert state.should_continue is True

        # Simulate iteration completion
        state.current_iteration = 2
        assert state.current_iteration == 2

        # Check stop condition
        state.current_iteration = 3
        assert state.should_stop_iterations() is True

    def test_hypothesis_lifecycle(self, workflow_state):
        """Test hypothesis status changes through workflow."""
        state = workflow_state

        # All hypotheses should be reviewed
        for hyp in state.hypotheses:
            assert hyp["status"] == HypothesisStatus.REVIEWED.value

        # Simulate ranking
        for hyp in state.hypotheses:
            hyp["status"] = HypothesisStatus.RANKED.value

        ranked = [h for h in state.hypotheses if h["status"] == HypothesisStatus.RANKED.value]
        assert len(ranked) == 3

    def test_statistics_update(self, workflow_state):
        """Test workflow statistics tracking."""
        state = workflow_state
        state.update_statistics()

        assert state.statistics["total_hypotheses_generated"] == 3
        assert state.statistics["total_hypotheses_reviewed"] == 2
        assert state.statistics["top_elo_score"] == 1050.0

    def test_top_hypotheses_selection(self, workflow_state):
        """Test selection of top hypotheses."""
        state = workflow_state

        top_2 = state.get_top_hypotheses_data(2)

        assert len(top_2) == 2
        assert top_2[0]["elo_score"] == 1050.0
        assert top_2[1]["elo_score"] == 1030.0


class TestWorkflowNodes:
    """Tests for individual workflow nodes."""

    @pytest.fixture
    def node_test_state(self) -> CoScientistState:
        """Create a state for node testing."""
        return CoScientistState(
            research_goal=WORKFLOW_RESEARCH_GOAL,
            literature_summary=WORKFLOW_LITERATURE_SUMMARY,
            hypotheses=WORKFLOW_HYPOTHESES.copy(),
            max_iterations=3
        )

    def test_state_to_dict_conversion(self, node_test_state):
        """Test state conversion for node processing."""
        state = node_test_state
        state_dict = state.model_dump()

        assert "research_goal" in state_dict
        assert "hypotheses" in state_dict
        assert len(state_dict["hypotheses"]) == 3


class TestWorkflowControlFlow:
    """Tests for workflow control flow logic."""

    @pytest.fixture
    def control_flow_state(self) -> CoScientistState:
        """Create a state for control flow testing."""
        return CoScientistState(
            research_goal=WORKFLOW_RESEARCH_GOAL,
            max_iterations=3
        )

    def test_should_continue_logic(self, control_flow_state):
        """Test continue/stop decision logic."""
        state = control_flow_state

        # Should continue on first iteration
        assert not state.should_stop_iterations()

        # Should continue until max iterations
        state.current_iteration = 2
        assert not state.should_stop_iterations()

        # Should stop at max iterations
        state.current_iteration = 3
        assert state.should_stop_iterations()

    def test_convergence_detection(self, control_flow_state):
        """Test detection of score convergence."""
        state = control_flow_state

        # Add many rankings with small deltas (indicates convergence)
        state.hypothesis_rankings = [
            {"id": f"rank_{i}", "score_delta": 3.0}
            for i in range(15)
        ]

        # Should detect convergence
        assert state.should_stop_iterations() is True

    def test_next_agent_determination(self, control_flow_state):
        """Test next agent selection based on state."""
        state = control_flow_state

        # Without literature, literature search should be next
        state.literature_summary = None
        # (This would be determined by supervisor in actual workflow)

        # With literature but no hypotheses, generation should be next
        state.literature_summary = WORKFLOW_LITERATURE_SUMMARY
        state.hypotheses = []
        # (Generation would be the logical next step)


class TestSimulatedResearchSession:
    """End-to-end simulation of a research session."""

    @pytest.fixture
    def complete_session_state(self) -> CoScientistState:
        """Create a complete simulated session state."""
        state = CoScientistState(
            research_goal=WORKFLOW_RESEARCH_GOAL,
            literature_summary=WORKFLOW_LITERATURE_SUMMARY,
            hypotheses=WORKFLOW_HYPOTHESES.copy(),
            hypothesis_reviews=WORKFLOW_REVIEWS.copy(),
            hypothesis_rankings=[
                {
                    "id": "rank_001",
                    "hypothesis_a_id": "hyp_wf_001",
                    "hypothesis_b_id": "hyp_wf_002",
                    "winner_id": "hyp_wf_001",
                    "comparison_rationale": "Better validation strategy",
                    "score_delta": 16.0
                },
                {
                    "id": "rank_002",
                    "hypothesis_a_id": "hyp_wf_001",
                    "hypothesis_b_id": "hyp_wf_003",
                    "winner_id": "hyp_wf_001",
                    "comparison_rationale": "More feasible with available data",
                    "score_delta": 20.0
                }
            ],
            top_hypotheses=["hyp_wf_001", "hyp_wf_002"],
            current_iteration=2,
            max_iterations=3,
            messages=[
                {
                    "id": "msg_001",
                    "agent_type": "literature_search",
                    "content": "Found 25 relevant papers",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "id": "msg_002",
                    "agent_type": "generation",
                    "content": "Generated 3 hypotheses",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "id": "msg_003",
                    "agent_type": "reflection",
                    "content": "Reviewed 2 hypotheses",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        )
        return state

    def test_session_summary(self, complete_session_state):
        """Test generation of session summary."""
        state = complete_session_state
        summary = state.to_summary()

        assert summary["session_id"].startswith("session_")
        assert summary["total_hypotheses"] == 3
        assert summary["total_reviews"] == 2
        assert summary["top_hypotheses_count"] == 2
        assert summary["current_iteration"] == 2

    def test_message_tracking(self, complete_session_state):
        """Test that all agent messages are tracked."""
        state = complete_session_state

        agent_types = [msg["agent_type"] for msg in state.messages]

        assert "literature_search" in agent_types
        assert "generation" in agent_types
        assert "reflection" in agent_types

    def test_ranking_results(self, complete_session_state):
        """Test that ranking results are properly stored."""
        state = complete_session_state

        # Should have 2 ranking comparisons
        assert len(state.hypothesis_rankings) == 2

        # Top hypothesis should have won both
        winners = [r["winner_id"] for r in state.hypothesis_rankings]
        assert winners.count("hyp_wf_001") == 2

    def test_final_output_readiness(self, complete_session_state):
        """Test state is ready for final output generation."""
        state = complete_session_state

        # Should have necessary components for research overview
        assert state.research_goal is not None
        assert state.literature_summary is not None
        assert len(state.hypotheses) > 0
        assert len(state.top_hypotheses) > 0


class TestErrorHandling:
    """Tests for error handling in workflow."""

    def test_missing_research_goal(self):
        """Test handling of missing research goal."""
        state = CoScientistState()  # No research goal

        # Verify error detection
        if not state.research_goal:
            state.errors.append("No research goal provided")

        assert len(state.errors) == 1
        assert "research goal" in state.errors[0].lower()

    def test_empty_hypotheses_handling(self):
        """Test handling when no hypotheses are generated."""
        state = CoScientistState(
            research_goal=WORKFLOW_RESEARCH_GOAL
        )

        # Attempt to get top hypotheses from empty list
        top = state.get_top_hypotheses_data(3)
        assert len(top) == 0

    def test_state_recovery(self):
        """Test state can be recovered from dict."""
        original_state = CoScientistState(
            research_goal=WORKFLOW_RESEARCH_GOAL,
            hypotheses=WORKFLOW_HYPOTHESES.copy(),
            current_iteration=2
        )

        # Convert to dict and back
        state_dict = original_state.model_dump()
        recovered_state = CoScientistState(**state_dict)

        assert recovered_state.current_iteration == 2
        assert len(recovered_state.hypotheses) == 3

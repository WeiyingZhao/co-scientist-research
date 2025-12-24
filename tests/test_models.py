"""Tests for data models."""

import pytest
from datetime import datetime

from geospatial_co_scientist.models.research import (
    ResearchGoal,
    ResearchDomain,
    LiteratureReference,
    LiteratureSummary,
    ResearchOverview,
    HypothesisSummary,
    ExperimentDesignSummary,
)
from geospatial_co_scientist.models.hypothesis import (
    Hypothesis,
    HypothesisType,
    HypothesisStatus,
    HypothesisReview,
    HypothesisRanking,
    HypothesisCluster,
)
from geospatial_co_scientist.models.experiment import (
    DataRequirement,
    DataSourceType,
    Methodology,
    MethodologyType,
    ExperimentDesign,
    EvaluationMetric,
)
from geospatial_co_scientist.models.state import (
    CoScientistState,
    AgentType,
    TaskStatus,
    TaskQueue,
)


class TestResearchGoal:
    """Tests for ResearchGoal model."""

    def test_create_basic_goal(self):
        goal = ResearchGoal(
            question="How can satellite imagery detect urban heat islands?"
        )
        assert goal.question == "How can satellite imagery detect urban heat islands?"
        assert goal.domain == ResearchDomain.GENERAL_GIS
        assert goal.id.startswith("goal_")

    def test_create_full_goal(self):
        goal = ResearchGoal(
            question="Detect deforestation in Amazon",
            domain=ResearchDomain.REMOTE_SENSING,
            context="Focus on 2020-2023 period",
            constraints=["Use Sentinel-2 data", "Freely available"],
            keywords=["deforestation", "Sentinel-2", "Amazon"]
        )
        assert goal.domain == ResearchDomain.REMOTE_SENSING
        assert len(goal.constraints) == 2
        assert "Amazon" in goal.keywords


class TestHypothesis:
    """Tests for Hypothesis model."""

    def test_create_hypothesis(self):
        hyp = Hypothesis(
            goal_id="goal_123",
            title="Urban Heat Island Detection",
            statement="Combining thermal and NDVI data improves UHI detection",
            hypothesis_type=HypothesisType.METHODOLOGICAL
        )
        assert hyp.title == "Urban Heat Island Detection"
        assert hyp.hypothesis_type == HypothesisType.METHODOLOGICAL
        assert hyp.status == HypothesisStatus.GENERATED
        assert hyp.elo_score == 1000.0

    def test_hypothesis_with_variables(self):
        hyp = Hypothesis(
            goal_id="goal_123",
            title="Temperature-NDVI Correlation",
            statement="Higher NDVI correlates with lower surface temperature",
            variables={
                "independent": "NDVI",
                "dependent": "Land Surface Temperature",
                "control": "Elevation, Urban density"
            }
        )
        assert "NDVI" in hyp.variables["independent"]


class TestHypothesisReview:
    """Tests for HypothesisReview model."""

    def test_calculate_overall_score(self):
        review = HypothesisReview(
            hypothesis_id="hyp_123",
            scores={
                "logical_consistency": 0.8,
                "novelty": 0.7,
                "testability": 0.9,
                "scientific_soundness": 0.8,
                "feasibility": 0.6,
                "relevance": 0.9,
                "clarity": 0.8
            }
        )
        score = review.calculate_overall_score()
        assert 0.7 <= score <= 0.85  # Expected weighted average


class TestExperimentDesign:
    """Tests for ExperimentDesign model."""

    def test_create_experiment(self):
        data_req = DataRequirement(
            name="Landsat 8 Thermal",
            data_type=DataSourceType.SATELLITE_THERMAL,
            description="Thermal infrared bands"
        )

        methodology = Methodology(
            name="Temperature Analysis",
            methodology_type=MethodologyType.THERMAL_ANALYSIS,
            steps=["Download data", "Process", "Analyze"]
        )

        metric = EvaluationMetric(
            name="Correlation coefficient",
            description="Pearson correlation"
        )

        design = ExperimentDesign(
            hypothesis_id="hyp_123",
            title="UHI Detection Experiment",
            objective="Test thermal-NDVI correlation",
            data_requirements=[data_req],
            methodology=methodology,
            evaluation_metrics=[metric]
        )

        assert design.title == "UHI Detection Experiment"
        assert len(design.data_requirements) == 1
        assert design.methodology.name == "Temperature Analysis"

    def test_experiment_to_markdown(self):
        methodology = Methodology(
            name="Simple Analysis",
            methodology_type=MethodologyType.SPATIAL_ANALYSIS,
            description="Basic spatial analysis",
            steps=["Step 1", "Step 2"],
            tools_software=["Python", "QGIS"]
        )

        design = ExperimentDesign(
            hypothesis_id="hyp_123",
            title="Test Experiment",
            objective="Test objective",
            methodology=methodology
        )

        md = design.to_markdown()
        assert "# Experiment Design: Test Experiment" in md
        assert "Test objective" in md


class TestCoScientistState:
    """Tests for CoScientistState model."""

    def test_create_empty_state(self):
        state = CoScientistState()
        assert state.session_id.startswith("session_")
        assert state.current_iteration == 1
        assert state.should_continue is True
        assert len(state.hypotheses) == 0

    def test_add_message(self):
        state = CoScientistState()
        state.add_message(AgentType.GENERATION, "Generated 5 hypotheses")
        assert len(state.messages) == 1
        assert state.messages[0]["agent_type"] == "generation"

    def test_get_hypothesis_by_id(self):
        state = CoScientistState()
        state.hypotheses = [
            {"id": "hyp_1", "title": "Hypothesis 1"},
            {"id": "hyp_2", "title": "Hypothesis 2"},
        ]

        hyp = state.get_hypothesis_by_id("hyp_1")
        assert hyp is not None
        assert hyp["title"] == "Hypothesis 1"

        missing = state.get_hypothesis_by_id("hyp_999")
        assert missing is None

    def test_get_top_hypotheses(self):
        state = CoScientistState()
        state.hypotheses = [
            {"id": "hyp_1", "elo_score": 1050},
            {"id": "hyp_2", "elo_score": 980},
            {"id": "hyp_3", "elo_score": 1100},
        ]

        top = state.get_top_hypotheses_data(2)
        assert len(top) == 2
        assert top[0]["id"] == "hyp_3"  # Highest score first

    def test_update_statistics(self):
        state = CoScientistState()
        state.hypotheses = [
            {"id": "hyp_1", "elo_score": 1000},
            {"id": "hyp_2", "elo_score": 1100},
        ]
        state.hypothesis_reviews = [{"id": "rev_1"}]

        state.update_statistics()
        assert state.statistics["total_hypotheses_generated"] == 2
        assert state.statistics["total_hypotheses_reviewed"] == 1
        assert state.statistics["average_hypothesis_score"] == 1050
        assert state.statistics["top_elo_score"] == 1100


class TestTaskQueue:
    """Tests for TaskQueue model."""

    def test_add_task(self):
        queue = TaskQueue()
        queue.add_task("generation", priority=1, data="test")

        assert len(queue.tasks) == 1
        assert queue.tasks[0]["type"] == "generation"
        assert queue.tasks[0]["priority"] == 1

    def test_task_priority_ordering(self):
        queue = TaskQueue()
        queue.add_task("low", priority=0)
        queue.add_task("high", priority=2)
        queue.add_task("medium", priority=1)

        assert queue.tasks[0]["type"] == "high"
        assert queue.tasks[1]["type"] == "medium"
        assert queue.tasks[2]["type"] == "low"

    def test_get_next_task(self):
        queue = TaskQueue()
        queue.add_task("task1", priority=1)
        queue.add_task("task2", priority=0)

        task = queue.get_next_task()
        assert task["type"] == "task1"
        assert task["status"] == TaskStatus.IN_PROGRESS.value

    def test_complete_task(self):
        queue = TaskQueue()
        queue.add_task("task1")
        task = queue.get_next_task()

        queue.complete_task(task["id"], result="success")

        assert len(queue.tasks) == 0
        assert len(queue.completed_tasks) == 1
        assert queue.completed_tasks[0]["result"] == "success"

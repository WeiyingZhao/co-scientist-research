"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import Generator
from unittest.mock import MagicMock, AsyncMock

from geospatial_co_scientist.models.state import CoScientistState
from geospatial_co_scientist.models.research import ResearchGoal
from geospatial_co_scientist.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_research_goal() -> ResearchGoal:
    """Create a sample research goal for testing."""
    return ResearchGoal(
        question="How can satellite thermal imagery detect urban heat islands?",
        domain="remote_sensing",
        context="Focus on tropical cities with population > 1 million",
        constraints=[
            "Use freely available satellite data",
            "Analysis should be reproducible"
        ],
        keywords=["urban heat island", "thermal imagery", "Landsat", "MODIS"]
    )


@pytest.fixture
def sample_state(sample_research_goal: ResearchGoal) -> CoScientistState:
    """Create a sample state for testing."""
    state = CoScientistState(
        research_goal=sample_research_goal.model_dump(),
        max_iterations=3
    )
    return state


@pytest.fixture
def state_with_hypotheses(sample_state: CoScientistState) -> CoScientistState:
    """Create a state with some hypotheses."""
    sample_state.hypotheses = [
        {
            "id": "hyp_001",
            "title": "Thermal-NDVI Correlation",
            "statement": "Higher NDVI areas show lower surface temperature",
            "hypothesis_type": "correlational",
            "rationale": "Vegetation has cooling effect",
            "elo_score": 1050,
            "status": "reviewed"
        },
        {
            "id": "hyp_002",
            "title": "Nighttime UHI Detection",
            "statement": "Nighttime thermal data better isolates UHI effects",
            "hypothesis_type": "methodological",
            "rationale": "Solar heating is absent at night",
            "elo_score": 1020,
            "status": "reviewed"
        },
        {
            "id": "hyp_003",
            "title": "Multi-temporal Analysis",
            "statement": "Seasonal patterns reveal persistent UHI zones",
            "hypothesis_type": "exploratory",
            "rationale": "UHI varies with season but hot spots persist",
            "elo_score": 980,
            "status": "reviewed"
        }
    ]
    sample_state.top_hypotheses = ["hyp_001", "hyp_002"]
    return sample_state


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing agents."""
    mock = AsyncMock()
    mock.ainvoke.return_value = MagicMock(
        content='{"hypotheses": []}'
    )
    return mock


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        llm_provider="openai",
        openai_api_key="test-key",
        max_iterations=2,
        hypotheses_per_iteration=3,
        ranking_comparisons=5
    )


@pytest.fixture
def mock_search_results():
    """Create mock literature search results."""
    return [
        {
            "title": "Urban Heat Island Detection Using Landsat",
            "authors": ["Smith, J.", "Jones, K."],
            "year": 2023,
            "abstract": "This study presents methods for UHI detection...",
            "doi": "10.1234/test.001",
            "source": "Remote Sensing of Environment"
        },
        {
            "title": "Thermal Remote Sensing in Urban Areas",
            "authors": ["Brown, A."],
            "year": 2022,
            "abstract": "A review of thermal remote sensing applications...",
            "doi": "10.1234/test.002",
            "source": "ISPRS Journal"
        }
    ]


# Markers for test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_api: marks tests that require API keys"
    )

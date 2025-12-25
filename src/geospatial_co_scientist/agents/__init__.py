"""Agents for the Geospatial AI Co-Scientist."""

from geospatial_co_scientist.agents.base import BaseAgent
from geospatial_co_scientist.agents.supervisor import SupervisorAgent
from geospatial_co_scientist.agents.generation import GenerationAgent
from geospatial_co_scientist.agents.reflection import ReflectionAgent
from geospatial_co_scientist.agents.ranking import RankingAgent
from geospatial_co_scientist.agents.proximity import ProximityAgent
from geospatial_co_scientist.agents.evolution import EvolutionAgent
from geospatial_co_scientist.agents.meta_review import MetaReviewAgent
from geospatial_co_scientist.agents.experiment_design import ExperimentDesignAgent

__all__ = [
    "BaseAgent",
    "SupervisorAgent",
    "GenerationAgent",
    "ReflectionAgent",
    "RankingAgent",
    "ProximityAgent",
    "EvolutionAgent",
    "MetaReviewAgent",
    "ExperimentDesignAgent",
]

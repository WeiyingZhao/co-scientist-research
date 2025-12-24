"""
Geospatial AI Co-Scientist

A multi-agent AI system for geospatial and remote sensing research assistance.
Inspired by Google's AI Co-Scientist approach, this system helps researchers with:
- Literature Review
- Hypothesis Generation
- Experiment Design
- Data Analysis

Built with LangGraph for complex multi-agent orchestration.
"""

__version__ = "0.1.0"
__author__ = "GeoReason Labs"

from geospatial_co_scientist.orchestration.workflow import GeospatialCoScientist
from geospatial_co_scientist.models.research import ResearchGoal, ResearchOverview

__all__ = [
    "GeospatialCoScientist",
    "ResearchGoal",
    "ResearchOverview",
]

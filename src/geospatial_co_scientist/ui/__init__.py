"""UI components for the Geospatial AI Co-Scientist."""

from geospatial_co_scientist.ui.api import create_app
from geospatial_co_scientist.ui.routes import router

__all__ = ["create_app", "router"]

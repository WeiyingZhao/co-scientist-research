"""Experiment design data models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DataSourceType(str, Enum):
    """Types of geospatial data sources."""

    SATELLITE_OPTICAL = "satellite_optical"
    SATELLITE_THERMAL = "satellite_thermal"
    SATELLITE_RADAR = "satellite_radar"
    SATELLITE_HYPERSPECTRAL = "satellite_hyperspectral"
    AERIAL_IMAGERY = "aerial_imagery"
    LIDAR = "lidar"
    DEM = "dem"
    VECTOR_DATA = "vector_data"
    GROUND_STATION = "ground_station"
    FIELD_SURVEY = "field_survey"
    CENSUS_DATA = "census_data"
    CLIMATE_DATA = "climate_data"
    SOCIAL_MEDIA = "social_media"
    OTHER = "other"


class MethodologyType(str, Enum):
    """Types of analysis methodologies."""

    STATISTICAL_ANALYSIS = "statistical_analysis"
    MACHINE_LEARNING = "machine_learning"
    DEEP_LEARNING = "deep_learning"
    IMAGE_CLASSIFICATION = "image_classification"
    CHANGE_DETECTION = "change_detection"
    TIME_SERIES_ANALYSIS = "time_series_analysis"
    SPATIAL_ANALYSIS = "spatial_analysis"
    SPECTRAL_ANALYSIS = "spectral_analysis"
    REGRESSION_MODELING = "regression_modeling"
    SIMULATION = "simulation"
    FIELD_EXPERIMENT = "field_experiment"
    COMPARATIVE_STUDY = "comparative_study"
    CASE_STUDY = "case_study"


class DataRequirement(BaseModel):
    """A data requirement for an experiment."""

    id: str = Field(default_factory=lambda: f"data_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    name: str = Field(..., description="Name of the data requirement")
    data_type: DataSourceType = Field(..., description="Type of data source")
    description: str = Field(default="", description="Detailed description of data needed")
    specific_sources: list[str] = Field(
        default_factory=list,
        description="Specific data sources (e.g., 'Landsat 8', 'Sentinel-2')"
    )
    temporal_requirements: Optional[str] = Field(
        default=None,
        description="Time period or frequency requirements"
    )
    spatial_requirements: Optional[str] = Field(
        default=None,
        description="Spatial coverage or resolution requirements"
    )
    availability: str = Field(
        default="unknown",
        description="Data availability status (available, restricted, unavailable)"
    )
    access_method: Optional[str] = Field(
        default=None,
        description="How to access the data (API, download, purchase)"
    )
    preprocessing_needed: list[str] = Field(
        default_factory=list,
        description="Preprocessing steps required"
    )
    estimated_size: Optional[str] = Field(
        default=None,
        description="Estimated data size"
    )
    cost: Optional[str] = Field(
        default=None,
        description="Cost information if applicable"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Landsat 8 Thermal Data",
                "data_type": "satellite_thermal",
                "description": "Thermal infrared bands for surface temperature analysis",
                "specific_sources": ["Landsat 8 Collection 2 Level-2"],
                "temporal_requirements": "Summer months 2018-2023",
                "spatial_requirements": "30m resolution, covering study area",
                "availability": "available",
                "access_method": "USGS EarthExplorer or Google Earth Engine"
            }
        }


class Methodology(BaseModel):
    """A methodology or analytical approach for an experiment."""

    id: str = Field(default_factory=lambda: f"method_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    name: str = Field(..., description="Name of the methodology")
    methodology_type: MethodologyType = Field(..., description="Type of methodology")
    description: str = Field(default="", description="Detailed description")
    steps: list[str] = Field(
        default_factory=list,
        description="Step-by-step procedure"
    )
    algorithms: list[str] = Field(
        default_factory=list,
        description="Specific algorithms or techniques used"
    )
    tools_software: list[str] = Field(
        default_factory=list,
        description="Software tools needed (e.g., QGIS, Python libraries)"
    )
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Key parameters and their suggested values"
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions underlying the methodology"
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Known limitations of the approach"
    )
    references: list[str] = Field(
        default_factory=list,
        description="References for the methodology"
    )
    code_snippet: Optional[str] = Field(
        default=None,
        description="Example code snippet for implementation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Surface Temperature Extraction from Landsat",
                "methodology_type": "image_classification",
                "description": "Extract land surface temperature from thermal bands",
                "steps": [
                    "1. Download Landsat 8 Level-2 data",
                    "2. Convert DN to radiance",
                    "3. Apply emissivity correction",
                    "4. Convert to Kelvin/Celsius"
                ],
                "tools_software": ["Python", "rasterio", "numpy"],
                "parameters": {"emissivity": "0.95 for urban areas"}
            }
        }


class EvaluationMetric(BaseModel):
    """An evaluation metric for assessing experiment results."""

    id: str = Field(default_factory=lambda: f"metric_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    name: str = Field(..., description="Name of the metric")
    description: str = Field(default="", description="What this metric measures")
    formula: Optional[str] = Field(default=None, description="Formula if applicable")
    interpretation: str = Field(
        default="",
        description="How to interpret the metric values"
    )
    success_threshold: Optional[str] = Field(
        default=None,
        description="Threshold for considering the hypothesis supported"
    )
    baseline_comparison: Optional[str] = Field(
        default=None,
        description="Baseline or benchmark for comparison"
    )


class ExperimentDesign(BaseModel):
    """A complete experiment design for testing a hypothesis."""

    id: str = Field(default_factory=lambda: f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    hypothesis_id: str = Field(..., description="ID of the hypothesis being tested")
    title: str = Field(..., description="Title of the experiment")
    objective: str = Field(..., description="Primary objective of the experiment")
    research_questions: list[str] = Field(
        default_factory=list,
        description="Specific research questions to answer"
    )

    # Data requirements
    data_requirements: list[DataRequirement] = Field(
        default_factory=list,
        description="Data needed for the experiment"
    )

    # Methodology
    methodology: Methodology = Field(
        ...,
        description="The analytical methodology"
    )
    alternative_approaches: list[str] = Field(
        default_factory=list,
        description="Alternative approaches that could be used"
    )

    # Study design
    study_area: Optional[str] = Field(
        default=None,
        description="Geographic area of study"
    )
    temporal_scope: Optional[str] = Field(
        default=None,
        description="Time period of the study"
    )
    sample_design: Optional[str] = Field(
        default=None,
        description="Sampling strategy if applicable"
    )

    # Evaluation
    evaluation_metrics: list[EvaluationMetric] = Field(
        default_factory=list,
        description="Metrics for evaluating results"
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Criteria for hypothesis support/rejection"
    )
    expected_outcomes: list[str] = Field(
        default_factory=list,
        description="Expected outcomes if hypothesis is correct"
    )
    potential_challenges: list[str] = Field(
        default_factory=list,
        description="Anticipated challenges and mitigations"
    )

    # Resources
    computational_requirements: Optional[str] = Field(
        default=None,
        description="Computing resources needed"
    )
    estimated_effort: Optional[str] = Field(
        default=None,
        description="Estimated effort/complexity"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Dependencies on other experiments or external factors"
    )

    # Outputs
    deliverables: list[str] = Field(
        default_factory=list,
        description="Expected deliverables from the experiment"
    )
    reproducibility_notes: str = Field(
        default="",
        description="Notes on ensuring reproducibility"
    )

    created_at: datetime = Field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        """Convert experiment design to markdown format."""
        md = f"""# Experiment Design: {self.title}

**Hypothesis ID:** {self.hypothesis_id}
**Created:** {self.created_at.strftime('%Y-%m-%d %H:%M')}

## Objective

{self.objective}

## Research Questions

"""
        for i, q in enumerate(self.research_questions, 1):
            md += f"{i}. {q}\n"

        md += "\n## Data Requirements\n\n"
        for data in self.data_requirements:
            md += f"""### {data.name}
- **Type:** {data.data_type.value}
- **Description:** {data.description}
- **Sources:** {', '.join(data.specific_sources)}
- **Availability:** {data.availability}

"""

        md += f"""## Methodology

### {self.methodology.name}

**Type:** {self.methodology.methodology_type.value}

{self.methodology.description}

#### Steps
"""
        for step in self.methodology.steps:
            md += f"- {step}\n"

        md += "\n#### Tools & Software\n"
        for tool in self.methodology.tools_software:
            md += f"- {tool}\n"

        if self.methodology.code_snippet:
            md += f"\n#### Code Example\n```python\n{self.methodology.code_snippet}\n```\n"

        md += "\n## Evaluation\n\n### Metrics\n"
        for metric in self.evaluation_metrics:
            md += f"- **{metric.name}:** {metric.description}\n"

        md += "\n### Success Criteria\n"
        for criterion in self.success_criteria:
            md += f"- {criterion}\n"

        md += "\n### Expected Outcomes\n"
        for outcome in self.expected_outcomes:
            md += f"- {outcome}\n"

        if self.potential_challenges:
            md += "\n## Potential Challenges\n"
            for challenge in self.potential_challenges:
                md += f"- {challenge}\n"

        if self.computational_requirements:
            md += f"\n## Computational Requirements\n\n{self.computational_requirements}\n"

        return md


class AnalysisResult(BaseModel):
    """Result of data analysis."""

    id: str = Field(default_factory=lambda: f"result_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    experiment_id: str = Field(..., description="ID of the experiment")
    hypothesis_id: str = Field(..., description="ID of the hypothesis")
    status: str = Field(default="pending", description="Analysis status")
    summary: str = Field(default="", description="Summary of results")
    metrics_results: dict[str, float] = Field(
        default_factory=dict,
        description="Computed metric values"
    )
    interpretation: str = Field(default="", description="Interpretation of results")
    supports_hypothesis: Optional[bool] = Field(
        default=None,
        description="Whether results support the hypothesis"
    )
    confidence_level: Optional[str] = Field(
        default=None,
        description="Confidence level of conclusions"
    )
    visualizations: list[str] = Field(
        default_factory=list,
        description="Paths to generated visualizations"
    )
    raw_outputs: dict = Field(
        default_factory=dict,
        description="Raw analysis outputs"
    )
    new_insights: list[str] = Field(
        default_factory=list,
        description="New insights discovered"
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Questions raised by the analysis"
    )
    created_at: datetime = Field(default_factory=datetime.now)

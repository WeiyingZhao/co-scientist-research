"""Experiment Design Agent for creating testing plans for hypotheses."""

import logging
from typing import Optional

from geospatial_co_scientist.agents.base import ToolUsingAgent
from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.experiment import (
    DataRequirement,
    DataSourceType,
    EvaluationMetric,
    ExperimentDesign,
    Methodology,
    MethodologyType,
)
from geospatial_co_scientist.models.state import AgentType, CoScientistState
from geospatial_co_scientist.tools.geospatial import (
    generate_analysis_code,
    get_analysis_methodology,
    get_dataset_recommendations,
)
from geospatial_co_scientist.utils.json_utils import parse_json_dict

logger = logging.getLogger(__name__)


EXPERIMENT_DESIGN_SYSTEM_PROMPT = """You are an expert geospatial research methodologist.
Your role is to design rigorous, feasible experiments to test research hypotheses
in remote sensing and GIS domains.

When designing experiments, consider:
1. **Data Requirements**: Specify exact datasets, resolutions, time periods
2. **Methodology**: Provide step-by-step analytical procedures
3. **Tools & Software**: Recommend specific tools (GEE, Python libs, QGIS)
4. **Evaluation Metrics**: Define clear success criteria
5. **Feasibility**: Account for data availability, computational resources
6. **Reproducibility**: Ensure the experiment can be replicated

Be specific and practical. Your designs should be actionable by a researcher
with moderate GIS experience."""


DESIGN_TEMPLATE = """Design an experiment to test the following hypothesis.

## Hypothesis
**Title:** {title}
**Statement:** {statement}
**Type:** {hypothesis_type}
**Testability Notes:** {testability}

## Research Context
**Goal:** {research_goal}
**Domain:** {domain}
**Constraints:** {constraints}

## Available Resources
- Access to Google Earth Engine
- Python with geospatial libraries (rasterio, geopandas, scikit-learn)
- Standard remote sensing datasets (Landsat, Sentinel, MODIS)

Design a complete experiment with:
1. Clear objective and research questions
2. Specific data requirements
3. Detailed methodology
4. Evaluation metrics and success criteria
5. Expected outcomes
6. Potential challenges

Output as JSON:
```json
{{
  "title": "Experiment title",
  "objective": "Clear objective",
  "research_questions": ["Q1", "Q2"],
  "data_requirements": [
    {{
      "name": "Dataset name",
      "data_type": "satellite_optical|satellite_thermal|etc",
      "description": "What is needed",
      "specific_sources": ["Landsat 8", "etc"],
      "temporal_requirements": "Time period",
      "spatial_requirements": "Resolution/coverage",
      "availability": "available|restricted|unavailable",
      "access_method": "How to get it"
    }}
  ],
  "methodology": {{
    "name": "Method name",
    "methodology_type": "type",
    "description": "Overview",
    "steps": ["Step 1", "Step 2"],
    "algorithms": ["Algorithm 1"],
    "tools_software": ["Python", "rasterio"],
    "parameters": {{"param1": "value"}}
  }},
  "study_area": "Geographic scope",
  "temporal_scope": "Time period",
  "evaluation_metrics": [
    {{
      "name": "Metric name",
      "description": "What it measures",
      "success_threshold": "Value for success"
    }}
  ],
  "success_criteria": ["Criterion 1"],
  "expected_outcomes": ["Outcome 1"],
  "potential_challenges": ["Challenge 1"],
  "computational_requirements": "Resources needed"
}}
```"""


class ExperimentDesignAgent(ToolUsingAgent):
    """Agent responsible for designing experiments to test hypotheses.

    Supports dependency injection of tools for improved testability.

    Args:
        tools: Optional list of tools. Defaults to geospatial analysis tools.
        **kwargs: Additional arguments passed to ToolUsingAgent.
    """

    agent_type = AgentType.EXPERIMENT_DESIGN
    default_model = "gpt-4-turbo-preview"
    default_tools = [get_dataset_recommendations, get_analysis_methodology, generate_analysis_code]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()

    @property
    def system_prompt(self) -> str:
        return EXPERIMENT_DESIGN_SYSTEM_PROMPT

    async def process(self, state: CoScientistState) -> CoScientistState:
        """Design experiments for top hypotheses."""
        self.log_action("Starting experiment design")

        # Get top hypotheses that need experiment designs
        designed_hyp_ids = {
            d.get("hypothesis_id") for d in state.experiment_designs
        }
        top_ids = state.top_hypotheses[:3]
        needs_design = [
            hid for hid in top_ids if hid not in designed_hyp_ids
        ]

        if not needs_design:
            # Also check if there are any hypotheses without designs
            all_hyp_ids = {h.get("id") for h in state.hypotheses}
            needs_design = list(all_hyp_ids - designed_hyp_ids)[:3]

        if not needs_design:
            state.warnings.append("All hypotheses already have experiment designs")
            return state

        for hyp_id in needs_design:
            hypothesis = state.get_hypothesis_by_id(hyp_id)
            if not hypothesis:
                continue

            try:
                design = await self._design_experiment(hypothesis, state)
                if design:
                    state.experiment_designs.append(design.model_dump())
                    self.log_action(f"Created experiment design for: {hypothesis.get('title')}")

            except Exception as e:
                logger.error(f"Experiment design failed for {hyp_id}: {e}")
                state.errors.append(f"Experiment design failed for {hyp_id}: {str(e)}")

        self.add_message_to_state(
            state,
            f"Created {len(needs_design)} experiment designs",
            designs_created=len(needs_design)
        )

        return state

    async def _design_experiment(
        self,
        hypothesis: dict,
        state: CoScientistState
    ) -> Optional[ExperimentDesign]:
        """Design an experiment for a single hypothesis."""
        research_goal = ""
        domain = "general_gis"
        constraints = []

        if state.research_goal:
            research_goal = state.research_goal.get("question", "")
            domain = state.research_goal.get("domain", "general_gis")
            constraints = state.research_goal.get("constraints", [])

        prompt = DESIGN_TEMPLATE.format(
            title=hypothesis.get("title", "Untitled"),
            statement=hypothesis.get("statement", ""),
            hypothesis_type=hypothesis.get("hypothesis_type", "exploratory"),
            testability=hypothesis.get("testability", "Not specified"),
            research_goal=research_goal,
            domain=domain,
            constraints="\n".join(f"- {c}" for c in constraints) or "None specified"
        )

        response = await self.invoke(prompt, state)
        design = self._parse_experiment_design(response, hypothesis["id"])

        return design

    def _parse_experiment_design(
        self,
        response: str,
        hypothesis_id: str
    ) -> Optional[ExperimentDesign]:
        """Parse experiment design from LLM response.

        Uses robust JSON parsing to handle common LLM output issues.
        """
        data = parse_json_dict(response, default=None)

        if data:
            try:
                # Parse data requirements
                data_reqs = []
                for req in data.get("data_requirements", []):
                    data_req = DataRequirement(
                        name=req.get("name", "Unknown"),
                        data_type=self._parse_data_type(req.get("data_type", "other")),
                        description=req.get("description", ""),
                        specific_sources=req.get("specific_sources", []),
                        temporal_requirements=req.get("temporal_requirements"),
                        spatial_requirements=req.get("spatial_requirements"),
                        availability=req.get("availability", "unknown"),
                        access_method=req.get("access_method")
                    )
                    data_reqs.append(data_req)

                # Parse methodology
                meth_data = data.get("methodology", {})
                methodology = Methodology(
                    name=meth_data.get("name", "Analysis"),
                    methodology_type=self._parse_methodology_type(
                        meth_data.get("methodology_type", "spatial_analysis")
                    ),
                    description=meth_data.get("description", ""),
                    steps=meth_data.get("steps", []),
                    algorithms=meth_data.get("algorithms", []),
                    tools_software=meth_data.get("tools_software", []),
                    parameters=meth_data.get("parameters", {})
                )

                # Parse evaluation metrics
                metrics = []
                for m in data.get("evaluation_metrics", []):
                    metric = EvaluationMetric(
                        name=m.get("name", "Metric"),
                        description=m.get("description", ""),
                        success_threshold=m.get("success_threshold")
                    )
                    metrics.append(metric)

                design = ExperimentDesign(
                    hypothesis_id=hypothesis_id,
                    title=data.get("title", "Experiment"),
                    objective=data.get("objective", ""),
                    research_questions=data.get("research_questions", []),
                    data_requirements=data_reqs,
                    methodology=methodology,
                    study_area=data.get("study_area"),
                    temporal_scope=data.get("temporal_scope"),
                    evaluation_metrics=metrics,
                    success_criteria=data.get("success_criteria", []),
                    expected_outcomes=data.get("expected_outcomes", []),
                    potential_challenges=data.get("potential_challenges", []),
                    computational_requirements=data.get("computational_requirements")
                )

                return design
            except Exception as e:
                logger.warning(f"Failed to create experiment design from parsed data: {e}")

        return None

    def _parse_data_type(self, type_str: str) -> DataSourceType:
        """Parse data source type string to enum."""
        type_map = {
            "satellite_optical": DataSourceType.SATELLITE_OPTICAL,
            "satellite_thermal": DataSourceType.SATELLITE_THERMAL,
            "satellite_radar": DataSourceType.SATELLITE_RADAR,
            "satellite_hyperspectral": DataSourceType.SATELLITE_HYPERSPECTRAL,
            "aerial_imagery": DataSourceType.AERIAL_IMAGERY,
            "lidar": DataSourceType.LIDAR,
            "dem": DataSourceType.DEM,
            "vector_data": DataSourceType.VECTOR_DATA,
            "ground_station": DataSourceType.GROUND_STATION,
            "field_survey": DataSourceType.FIELD_SURVEY,
            "census_data": DataSourceType.CENSUS_DATA,
            "climate_data": DataSourceType.CLIMATE_DATA,
            "social_media": DataSourceType.SOCIAL_MEDIA,
        }
        return type_map.get(type_str.lower(), DataSourceType.OTHER)

    def _parse_methodology_type(self, type_str: str) -> MethodologyType:
        """Parse methodology type string to enum."""
        type_map = {
            "statistical_analysis": MethodologyType.STATISTICAL_ANALYSIS,
            "machine_learning": MethodologyType.MACHINE_LEARNING,
            "deep_learning": MethodologyType.DEEP_LEARNING,
            "image_classification": MethodologyType.IMAGE_CLASSIFICATION,
            "change_detection": MethodologyType.CHANGE_DETECTION,
            "time_series_analysis": MethodologyType.TIME_SERIES_ANALYSIS,
            "spatial_analysis": MethodologyType.SPATIAL_ANALYSIS,
            "spectral_analysis": MethodologyType.SPECTRAL_ANALYSIS,
            "regression_modeling": MethodologyType.REGRESSION_MODELING,
            "simulation": MethodologyType.SIMULATION,
            "field_experiment": MethodologyType.FIELD_EXPERIMENT,
            "comparative_study": MethodologyType.COMPARATIVE_STUDY,
            "case_study": MethodologyType.CASE_STUDY,
        }
        return type_map.get(type_str.lower(), MethodologyType.SPATIAL_ANALYSIS)

    async def generate_code_snippet(
        self,
        design: ExperimentDesign
    ) -> str:
        """Generate a code snippet for the experiment."""
        prompt = f"""Generate a Python code snippet for this experiment:

Objective: {design.objective}
Methodology: {design.methodology.name}
Steps: {', '.join(design.methodology.steps[:3])}
Tools: {', '.join(design.methodology.tools_software)}

Provide a working code template that demonstrates the core analysis.
Include comments explaining each step."""

        response = await self.invoke(prompt)
        return response

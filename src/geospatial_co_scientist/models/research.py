"""Research-related data models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ResearchDomain(str, Enum):
    """Geospatial research domains."""

    REMOTE_SENSING = "remote_sensing"
    URBAN_PLANNING = "urban_planning"
    CLIMATE_ANALYSIS = "climate_analysis"
    AGRICULTURE = "agriculture"
    HYDROLOGY = "hydrology"
    LAND_USE = "land_use"
    DISASTER_MANAGEMENT = "disaster_management"
    ENVIRONMENTAL_MONITORING = "environmental_monitoring"
    TRANSPORTATION = "transportation"
    GENERAL_GIS = "general_gis"


class ResearchGoal(BaseModel):
    """A research goal or question provided by the user."""

    id: str = Field(default_factory=lambda: f"goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    question: str = Field(..., description="The main research question or objective")
    domain: ResearchDomain = Field(
        default=ResearchDomain.GENERAL_GIS,
        description="The primary research domain"
    )
    context: Optional[str] = Field(
        default=None,
        description="Additional context or constraints provided by the user"
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Specific constraints for the research (e.g., data availability, region)"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Key terms related to the research"
    )
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "How can we use satellite thermal imagery to detect urban heat islands?",
                "domain": "remote_sensing",
                "context": "Focus on tropical cities with limited ground station data",
                "constraints": ["Must use freely available satellite data"],
                "keywords": ["urban heat island", "thermal imagery", "Landsat", "MODIS"]
            }
        }
    )


class LiteratureReference(BaseModel):
    """A reference to a scientific paper or article."""

    id: str = Field(default_factory=lambda: f"ref_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    title: str = Field(..., description="Title of the paper/article")
    authors: list[str] = Field(default_factory=list, description="List of authors")
    year: Optional[int] = Field(default=None, description="Publication year")
    source: str = Field(..., description="Journal, conference, or source name")
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier")
    url: Optional[str] = Field(default=None, description="URL to the paper")
    abstract: Optional[str] = Field(default=None, description="Paper abstract")
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key findings relevant to the research"
    )
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relevance score to the research goal (0-1)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Remote sensing of urban heat islands using Landsat thermal data",
                "authors": ["Smith, J.", "Johnson, K."],
                "year": 2023,
                "source": "Remote Sensing of Environment",
                "doi": "10.1016/j.rse.2023.01.001",
                "abstract": "This study presents a methodology for...",
                "key_findings": ["NDVI correlation with surface temperature"],
                "relevance_score": 0.85
            }
        }
    )


class LiteratureSummary(BaseModel):
    """A summary of the literature review for a research goal."""

    goal_id: str = Field(..., description="ID of the associated research goal")
    total_papers_found: int = Field(default=0, description="Total papers found in search")
    papers_reviewed: int = Field(default=0, description="Number of papers reviewed in detail")
    references: list[LiteratureReference] = Field(
        default_factory=list,
        description="List of relevant references"
    )
    summary: str = Field(
        default="",
        description="Overall summary of the literature review"
    )
    key_themes: list[str] = Field(
        default_factory=list,
        description="Key themes identified in the literature"
    )
    research_gaps: list[str] = Field(
        default_factory=list,
        description="Identified gaps in current research"
    )
    methodologies_used: list[str] = Field(
        default_factory=list,
        description="Common methodologies found in literature"
    )
    datasets_mentioned: list[str] = Field(
        default_factory=list,
        description="Datasets commonly referenced"
    )
    created_at: datetime = Field(default_factory=datetime.now)

    def get_top_references(self, n: int = 5) -> list[LiteratureReference]:
        """Get top N references by relevance score."""
        sorted_refs = sorted(
            self.references,
            key=lambda x: x.relevance_score,
            reverse=True
        )
        return sorted_refs[:n]


class ResearchOverview(BaseModel):
    """The final research overview document produced by the co-scientist."""

    id: str = Field(default_factory=lambda: f"overview_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    goal: ResearchGoal = Field(..., description="The original research goal")
    literature_summary: LiteratureSummary = Field(
        ...,
        description="Summary of the literature review"
    )
    hypotheses: list["HypothesisSummary"] = Field(
        default_factory=list,
        description="Top hypotheses generated"
    )
    experiment_designs: list["ExperimentDesignSummary"] = Field(
        default_factory=list,
        description="Experiment designs for testing hypotheses"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Overall recommendations for the researcher"
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="Suggested next steps"
    )
    iterations_completed: int = Field(
        default=1,
        description="Number of generate-review-refine iterations completed"
    )
    total_hypotheses_generated: int = Field(
        default=0,
        description="Total hypotheses generated across all iterations"
    )
    created_at: datetime = Field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        """Convert the research overview to a formatted markdown document."""
        md = f"""# Research Overview: {self.goal.question}

**Generated:** {self.created_at.strftime('%Y-%m-%d %H:%M')}
**Domain:** {self.goal.domain.value}
**Iterations:** {self.iterations_completed}

---

## 1. Research Goal

{self.goal.question}

"""
        if self.goal.context:
            md += f"**Context:** {self.goal.context}\n\n"

        if self.goal.constraints:
            md += "**Constraints:**\n"
            for c in self.goal.constraints:
                md += f"- {c}\n"
            md += "\n"

        md += f"""---

## 2. Literature Review

{self.literature_summary.summary}

### Key Themes
"""
        for theme in self.literature_summary.key_themes:
            md += f"- {theme}\n"

        md += "\n### Research Gaps\n"
        for gap in self.literature_summary.research_gaps:
            md += f"- {gap}\n"

        md += "\n### Key References\n"
        for ref in self.literature_summary.get_top_references(5):
            md += f"- **{ref.title}** ({ref.year}) - {ref.source}\n"

        md += "\n---\n\n## 3. Generated Hypotheses\n\n"
        for i, hyp in enumerate(self.hypotheses, 1):
            md += f"""### Hypothesis {i}: {hyp.title}

**Statement:** {hyp.statement}

**Rationale:** {hyp.rationale}

**Novelty Score:** {hyp.novelty_score:.2f} | **Feasibility Score:** {hyp.feasibility_score:.2f}

"""

        md += "---\n\n## 4. Experiment Designs\n\n"
        for i, exp in enumerate(self.experiment_designs, 1):
            md += f"""### Experiment {i}: {exp.title}

**Objective:** {exp.objective}

**Data Requirements:** {', '.join(exp.data_requirements)}

**Methodology:** {exp.methodology_summary}

"""

        md += "---\n\n## 5. Recommendations\n\n"
        for rec in self.recommendations:
            md += f"- {rec}\n"

        md += "\n## 6. Next Steps\n\n"
        for step in self.next_steps:
            md += f"1. {step}\n"

        return md


class HypothesisSummary(BaseModel):
    """Summary of a hypothesis for the research overview."""

    id: str
    title: str
    statement: str
    rationale: str
    novelty_score: float = Field(ge=0.0, le=1.0)
    feasibility_score: float = Field(ge=0.0, le=1.0)
    supporting_references: list[str] = Field(default_factory=list)


class ExperimentDesignSummary(BaseModel):
    """Summary of an experiment design for the research overview."""

    id: str
    title: str
    hypothesis_id: str
    objective: str
    data_requirements: list[str]
    methodology_summary: str
    expected_outcomes: list[str]


# Update forward references
ResearchOverview.model_rebuild()

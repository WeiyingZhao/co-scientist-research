"""State management models for the LangGraph orchestration."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task in the pipeline."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentType(str, Enum):
    """Types of agents in the system."""

    SUPERVISOR = "supervisor"
    GENERATION = "generation"
    REFLECTION = "reflection"
    RANKING = "ranking"
    PROXIMITY = "proximity"
    EVOLUTION = "evolution"
    META_REVIEW = "meta_review"
    EXPERIMENT_DESIGN = "experiment_design"
    DATA_ANALYSIS = "data_analysis"
    LITERATURE_SEARCH = "literature_search"


class AgentMessage(BaseModel):
    """A message from an agent."""

    id: str = Field(default_factory=lambda: f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    agent_type: AgentType = Field(..., description="Type of agent that sent the message")
    content: str = Field(..., description="Message content")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class TaskQueue(BaseModel):
    """A queue of tasks to be executed."""

    tasks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of pending tasks"
    )
    completed_tasks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of completed tasks"
    )

    def add_task(self, task_type: str, priority: int = 0, **kwargs) -> None:
        """Add a task to the queue."""
        task = {
            "id": f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": task_type,
            "priority": priority,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
        self.tasks.append(task)
        # Sort by priority (higher first)
        self.tasks.sort(key=lambda x: x.get("priority", 0), reverse=True)

    def get_next_task(self) -> Optional[dict[str, Any]]:
        """Get the next task from the queue."""
        for task in self.tasks:
            if task.get("status") == TaskStatus.PENDING.value:
                task["status"] = TaskStatus.IN_PROGRESS.value
                return task
        return None

    def complete_task(self, task_id: str, result: Any = None) -> None:
        """Mark a task as completed."""
        for task in self.tasks:
            if task.get("id") == task_id:
                task["status"] = TaskStatus.COMPLETED.value
                task["result"] = result
                task["completed_at"] = datetime.now().isoformat()
                self.completed_tasks.append(task)
                self.tasks.remove(task)
                break


def merge_lists(left: list, right: list) -> list:
    """Merge two lists, avoiding duplicates based on 'id' field."""
    if not left:
        return right
    if not right:
        return left

    # Create a dict of existing items by ID
    existing = {}
    for item in left:
        if hasattr(item, "id"):
            existing[item.id] = item
        elif isinstance(item, dict) and "id" in item:
            existing[item["id"]] = item

    # Add new items
    result = list(left)
    for item in right:
        item_id = item.id if hasattr(item, "id") else item.get("id") if isinstance(item, dict) else None
        if item_id and item_id not in existing:
            result.append(item)
        elif not item_id:
            result.append(item)

    return result


def merge_dicts(left: dict, right: dict) -> dict:
    """Merge two dictionaries, with right taking precedence."""
    if not left:
        return right
    if not right:
        return left
    return {**left, **right}


class CoScientistState(BaseModel):
    """
    The main state object for the Co-Scientist LangGraph workflow.

    This state is shared across all agents and contains the evolving
    context of the research session.
    """

    # Session info
    session_id: str = Field(
        default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description="Unique session identifier"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Research goal
    research_goal: Optional[dict[str, Any]] = Field(
        default=None,
        description="The current research goal"
    )

    # Literature review
    literature_summary: Optional[dict[str, Any]] = Field(
        default=None,
        description="Summary of literature review"
    )
    literature_references: Annotated[list[dict[str, Any]], merge_lists] = Field(
        default_factory=list,
        description="List of literature references found"
    )

    # Hypotheses
    hypotheses: Annotated[list[dict[str, Any]], merge_lists] = Field(
        default_factory=list,
        description="All generated hypotheses"
    )
    hypothesis_reviews: Annotated[list[dict[str, Any]], merge_lists] = Field(
        default_factory=list,
        description="Reviews of hypotheses"
    )
    hypothesis_rankings: Annotated[list[dict[str, Any]], merge_lists] = Field(
        default_factory=list,
        description="Ranking comparisons"
    )
    hypothesis_clusters: Annotated[list[dict[str, Any]], merge_lists] = Field(
        default_factory=list,
        description="Hypothesis clusters from proximity analysis"
    )
    top_hypotheses: list[str] = Field(
        default_factory=list,
        description="IDs of top-ranked hypotheses"
    )

    # Experiment designs
    experiment_designs: Annotated[list[dict[str, Any]], merge_lists] = Field(
        default_factory=list,
        description="Experiment designs"
    )
    analysis_results: Annotated[list[dict[str, Any]], merge_lists] = Field(
        default_factory=list,
        description="Data analysis results"
    )

    # Agent messages and feedback
    messages: Annotated[list[dict[str, Any]], merge_lists] = Field(
        default_factory=list,
        description="Messages from agents"
    )
    meta_feedback: Annotated[list[str], merge_lists] = Field(
        default_factory=list,
        description="Meta-level feedback and patterns observed"
    )

    # Iteration tracking
    current_iteration: int = Field(
        default=1,
        description="Current iteration number"
    )
    max_iterations: int = Field(
        default=3,
        description="Maximum number of iterations"
    )

    # Task queue
    task_queue: TaskQueue = Field(
        default_factory=TaskQueue,
        description="Queue of pending tasks"
    )

    # Control flow
    current_agent: Optional[AgentType] = Field(
        default=None,
        description="Currently active agent"
    )
    next_agent: Optional[AgentType] = Field(
        default=None,
        description="Next agent to execute"
    )
    should_continue: bool = Field(
        default=True,
        description="Whether to continue the workflow"
    )
    awaiting_human_input: bool = Field(
        default=False,
        description="Whether waiting for human input"
    )
    human_feedback: Optional[str] = Field(
        default=None,
        description="Feedback from human"
    )

    # Statistics
    statistics: dict[str, Any] = Field(
        default_factory=lambda: {
            "total_hypotheses_generated": 0,
            "total_hypotheses_reviewed": 0,
            "total_rankings_performed": 0,
            "total_evolutions": 0,
            "average_hypothesis_score": 0.0,
            "top_elo_score": 1000.0,
        },
        description="Statistics about the session"
    )

    # Errors and warnings
    errors: Annotated[list[str], merge_lists] = Field(
        default_factory=list,
        description="Errors encountered"
    )
    warnings: Annotated[list[str], merge_lists] = Field(
        default_factory=list,
        description="Warnings"
    )

    # Final output
    research_overview: Optional[dict[str, Any]] = Field(
        default=None,
        description="Final research overview document"
    )

    class Config:
        arbitrary_types_allowed = True

    def add_message(self, agent_type: AgentType, content: str, **metadata) -> None:
        """Add a message from an agent."""
        message = {
            "id": f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "agent_type": agent_type.value,
            "content": content,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message)

    def get_hypothesis_by_id(self, hypothesis_id: str) -> Optional[dict[str, Any]]:
        """Get a hypothesis by its ID."""
        for h in self.hypotheses:
            if h.get("id") == hypothesis_id:
                return h
        return None

    def get_top_hypotheses_data(self, n: int = 3) -> list[dict[str, Any]]:
        """Get the top N hypotheses by Elo score."""
        sorted_hypotheses = sorted(
            self.hypotheses,
            key=lambda x: x.get("elo_score", 1000.0),
            reverse=True
        )
        return sorted_hypotheses[:n]

    def update_statistics(self) -> None:
        """Update session statistics."""
        self.statistics["total_hypotheses_generated"] = len(self.hypotheses)
        self.statistics["total_hypotheses_reviewed"] = len(self.hypothesis_reviews)
        self.statistics["total_rankings_performed"] = len(self.hypothesis_rankings)

        if self.hypotheses:
            scores = [h.get("elo_score", 1000.0) for h in self.hypotheses]
            self.statistics["average_hypothesis_score"] = sum(scores) / len(scores)
            self.statistics["top_elo_score"] = max(scores)

    def should_stop_iterations(self) -> bool:
        """Determine if iterations should stop."""
        if self.current_iteration >= self.max_iterations:
            return True

        # Stop if top hypotheses haven't improved significantly
        if len(self.hypothesis_rankings) > 10:
            # Check if scores are converging
            recent_rankings = self.hypothesis_rankings[-10:]
            deltas = [r.get("score_delta", 32) for r in recent_rankings]
            if sum(deltas) / len(deltas) < 5:  # Very small changes
                return True

        return False

    def to_summary(self) -> dict[str, Any]:
        """Generate a summary of the current state."""
        return {
            "session_id": self.session_id,
            "research_goal": self.research_goal.get("question") if self.research_goal else None,
            "current_iteration": self.current_iteration,
            "total_hypotheses": len(self.hypotheses),
            "total_reviews": len(self.hypothesis_reviews),
            "top_hypotheses_count": len(self.top_hypotheses),
            "experiment_designs_count": len(self.experiment_designs),
            "has_research_overview": self.research_overview is not None,
            "awaiting_human_input": self.awaiting_human_input,
            "errors_count": len(self.errors),
        }

"""LangGraph workflow nodes for each agent."""

import logging
from typing import Any, Callable

from geospatial_co_scientist.agents.evolution import EvolutionAgent
from geospatial_co_scientist.agents.experiment_design import ExperimentDesignAgent
from geospatial_co_scientist.agents.generation import GenerationAgent
from geospatial_co_scientist.agents.meta_review import MetaReviewAgent
from geospatial_co_scientist.agents.proximity import ProximityAgent
from geospatial_co_scientist.agents.ranking import RankingAgent
from geospatial_co_scientist.agents.reflection import ReflectionAgent
from geospatial_co_scientist.agents.supervisor import SupervisorAgent
from geospatial_co_scientist.models.state import AgentType, CoScientistState

logger = logging.getLogger(__name__)


# Agent instances (lazily initialized)
_agents: dict[AgentType, Any] = {}


def get_agent(agent_type: AgentType) -> Any:
    """Get or create an agent instance."""
    if agent_type not in _agents:
        if agent_type == AgentType.SUPERVISOR:
            _agents[agent_type] = SupervisorAgent()
        elif agent_type == AgentType.GENERATION:
            _agents[agent_type] = GenerationAgent()
        elif agent_type == AgentType.REFLECTION:
            _agents[agent_type] = ReflectionAgent()
        elif agent_type == AgentType.RANKING:
            _agents[agent_type] = RankingAgent()
        elif agent_type == AgentType.PROXIMITY:
            _agents[agent_type] = ProximityAgent()
        elif agent_type == AgentType.EVOLUTION:
            _agents[agent_type] = EvolutionAgent()
        elif agent_type == AgentType.META_REVIEW:
            _agents[agent_type] = MetaReviewAgent()
        elif agent_type == AgentType.EXPERIMENT_DESIGN:
            _agents[agent_type] = ExperimentDesignAgent()
    return _agents.get(agent_type)


async def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Supervisor node - coordinates the workflow.

    This node determines what agent should run next and updates the state accordingly.
    """
    logger.info("Executing supervisor node")

    # Convert dict to state object
    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.SUPERVISOR

    # Get supervisor agent and process
    supervisor = get_agent(AgentType.SUPERVISOR)
    updated_state = await supervisor.process(current_state)

    return updated_state.model_dump()


async def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generation node - creates hypotheses.
    """
    logger.info("Executing generation node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.GENERATION

    agent = get_agent(AgentType.GENERATION)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def reflection_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Reflection node - reviews hypotheses.
    """
    logger.info("Executing reflection node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.REFLECTION

    agent = get_agent(AgentType.REFLECTION)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def ranking_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Ranking node - prioritizes hypotheses using Elo rating.
    """
    logger.info("Executing ranking node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.RANKING

    agent = get_agent(AgentType.RANKING)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def proximity_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Proximity node - analyzes hypothesis similarity and diversity.
    """
    logger.info("Executing proximity node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.PROXIMITY

    agent = get_agent(AgentType.PROXIMITY)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def evolution_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Evolution node - refines and improves hypotheses.
    """
    logger.info("Executing evolution node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.EVOLUTION

    agent = get_agent(AgentType.EVOLUTION)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def meta_review_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Meta-review node - synthesizes feedback and compiles outputs.
    """
    logger.info("Executing meta-review node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.META_REVIEW

    agent = get_agent(AgentType.META_REVIEW)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def experiment_design_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Experiment design node - creates testing plans.
    """
    logger.info("Executing experiment design node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.EXPERIMENT_DESIGN

    agent = get_agent(AgentType.EXPERIMENT_DESIGN)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def literature_search_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Literature search node - performs initial literature review.

    This is handled by the supervisor's initialize method.
    """
    logger.info("Executing literature search node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.LITERATURE_SEARCH

    supervisor = get_agent(AgentType.SUPERVISOR)
    updated_state = await supervisor._perform_literature_review(current_state)

    return updated_state.model_dump()


async def human_review_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Human review node - checkpoint for human input.

    In interactive mode, this node pauses for user input.
    In batch mode, it passes through.
    """
    logger.info("Executing human review node")

    current_state = CoScientistState(**state)

    # If human feedback is provided, process it
    if current_state.human_feedback:
        supervisor = get_agent(AgentType.SUPERVISOR)
        updated_state = await supervisor.handle_human_feedback(
            current_state,
            current_state.human_feedback
        )
        updated_state.human_feedback = None  # Clear after processing
        return updated_state.model_dump()

    # Otherwise, check if we should wait for input
    # (This would be handled by the UI layer in practice)

    return state


def should_continue(state: dict[str, Any]) -> str:
    """
    Conditional edge function - determines next node based on state.

    Returns:
        Name of the next node to execute
    """
    current_state = CoScientistState(**state)

    # Check if we should stop
    if not current_state.should_continue:
        return "end"

    # Check if awaiting human input
    if current_state.awaiting_human_input:
        return "human_review"

    # Get next agent from supervisor decision
    next_agent = current_state.next_agent

    if next_agent is None:
        return "end"

    # Map agent type to node name
    agent_to_node = {
        AgentType.SUPERVISOR: "supervisor",
        AgentType.GENERATION: "generation",
        AgentType.REFLECTION: "reflection",
        AgentType.RANKING: "ranking",
        AgentType.PROXIMITY: "proximity",
        AgentType.EVOLUTION: "evolution",
        AgentType.META_REVIEW: "meta_review",
        AgentType.EXPERIMENT_DESIGN: "experiment_design",
        AgentType.LITERATURE_SEARCH: "literature_search",
    }

    return agent_to_node.get(next_agent, "supervisor")


def create_node_functions() -> dict[str, Callable]:
    """Create a dictionary of node name to function mappings."""
    return {
        "supervisor": supervisor_node,
        "generation": generation_node,
        "reflection": reflection_node,
        "ranking": ranking_node,
        "proximity": proximity_node,
        "evolution": evolution_node,
        "meta_review": meta_review_node,
        "experiment_design": experiment_design_node,
        "literature_search": literature_search_node,
        "human_review": human_review_node,
    }
